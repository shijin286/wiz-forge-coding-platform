"""Deterministic auto-fixes for findings whose fix is mechanical and safe.

Only edits that cannot change behaviour in an unintended way are made; everything else is reported
as "needs a manual fix" (or is left to the AI pass). The submitted code is never executed.
"""

import re
from dataclasses import dataclass, field

from .base import Issue
from .flow_rules import blank_strings_and_comments

C_FAMILY = {"javascript", "typescript", "java", "c", "cpp", "go"}
HTTP_CALL = re.compile(r"\brequests\.(get|post|put|patch|delete|head|request)\s*\(")

# rules applied in this order when several hit the same line
ORDER = ["PY015", "PY017", "PY012", "PY007", "PY002", "PY004", "PY001", "JS002", "JS003", "JS004", "JS008", "JS009",
         "JV004", "CC004", "CC001", "CF001", "SEC001"]
SUBPROCESS_SHELL = re.compile(
    r"\bsubprocess\.(run|call|check_call|check_output|Popen)\(\s*(['\"])([^'\"]*)\2\s*\+\s*([A-Za-z_]\w*)\s*,"
    r"\s*shell\s*=\s*True\s*\)"
)


@dataclass
class FixResult:
    code: str
    applied: list[dict] = field(default_factory=list)    # {"line", "rule_id", "description"}
    remaining: list[dict] = field(default_factory=list)  # {"line", "rule_id", "title"}

    @property
    def changed(self) -> bool:
        return bool(self.applied)


def to_env_name(identifier: str) -> str:
    """apiKey / API_KEY / dbPassword -> API_KEY / API_KEY / DB_PASSWORD"""
    snake = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", identifier)
    return snake.upper()


def _sub_in_code(line: str, blank: str, pattern: re.Pattern, repl) -> tuple[str, int]:
    """Apply a regex replacement only where it matches real code (not strings/comments).
    `blank` is the same line with strings and comments blanked, so positions line up."""
    matches = list(pattern.finditer(blank))
    for m in reversed(matches):
        replacement = repl(m) if callable(repl) else m.expand(repl)
        line = line[: m.start()] + replacement + line[m.end():]
    return line, len(matches)


def _matching_paren(text: str, open_idx: int) -> int | None:
    depth = 0
    quote = None
    for i in range(open_idx, len(text)):
        ch = text[i]
        if quote:
            if ch == quote and text[i - 1] != "\\":
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
    return None


def _declared_array(code: str, name: str) -> bool:
    """sizeof only gives the buffer size for real arrays, not pointers."""
    return re.search(rf"\b(char|wchar_t)\s+{re.escape(name)}\s*\[", code) is not None


class _Fixer:
    def __init__(self, code: str, language: str):
        self.code = code
        self.language = language
        self.lines = code.splitlines()
        blank = blank_strings_and_comments(code) if language in C_FAMILY else code
        self.blank = blank.splitlines()
        self.needs_import_os = False
        # structural edits are deferred so every fixer can keep using original line numbers
        self.inserts: list[tuple[int, str]] = []  # (insert before original line index, text)
        self.deletes: set[int] = set()

    # each fixer returns a description when it changed the line, else None
    def PY015(self, n: int, issue: Issue) -> str | None:
        line = self.lines[n]
        new = re.sub(r",\s*verify\s*=\s*False\b|\bverify\s*=\s*False\s*,\s*", "", line)
        if new == line:
            return None
        self.lines[n] = new
        return "Removed verify=False so TLS certificates are checked"

    def PY017(self, n: int, issue: Issue) -> str | None:
        line = self.lines[n]
        m = HTTP_CALL.search(line)
        if not m:
            return None
        close = _matching_paren(line, m.end() - 1)
        if close is None or "timeout" in line[m.end():close]:
            return None
        inner = line[m.end():close].strip()
        insert = "timeout=10" if not inner else ", timeout=10"
        self.lines[n] = line[:close] + insert + line[close:]
        return f"Added timeout=10 to requests.{m.group(1)}()"

    def PY012(self, n: int, issue: Issue) -> str | None:
        # cur.execute("... %s ..." % value)  ->  cur.execute("... %s ...", (value,))
        line = self.lines[n]
        new = re.sub(r"\.(execute|executemany)\(\s*(['\"])([^'\"]*%s[^'\"]*)\2\s*%\s*([A-Za-z_][\w.]*)\s*\)",
                     r".\1(\2\3\2, (\4,))", line)
        if new == line:
            return None
        self.lines[n] = new
        return "Turned the formatted SQL into a parameterised query"

    def PY007(self, n: int, issue: Issue) -> str | None:
        # subprocess.run("zip backup.zip " + name, shell=True)  ->  subprocess.run(["zip", "backup.zip", name])
        line = self.lines[n]
        m = SUBPROCESS_SHELL.search(line)
        if not m:
            return None
        args = ", ".join(f'"{part}"' for part in m.group(3).split()) + f", {m.group(4)}"
        self.lines[n] = line[:m.start()] + f"subprocess.{m.group(1)}([{args}])" + line[m.end():]
        return "Passed the command as an argument list instead of a shell string"

    def PY002(self, n: int, issue: Issue) -> str | None:
        # def f(x, items=[]):  ->  def f(x, items=None):  +  if items is None: items = []
        line = self.lines[n]
        m = re.search(r"\b([A-Za-z_]\w*)\s*=\s*(\[\]|\{\}|set\(\)|list\(\)|dict\(\))", line)
        if not m or not re.match(r"\s*(async\s+)?def\b", line) or not line.rstrip().endswith(":"):
            return None
        body = n + 1
        while body < len(self.lines) and not self.lines[body].strip():
            body += 1
        if body >= len(self.lines):
            return None
        name, empty = m.group(1), m.group(2)
        indent = re.match(r"\s*", self.lines[body]).group(0)
        first = self.lines[body].strip()
        if first.startswith(('"""', "'''")):  # keep the docstring as the first statement
            quote = first[:3]
            if not (len(first) >= 6 and first.endswith(quote)):
                body += 1
                while body < len(self.lines) and quote not in self.lines[body]:
                    body += 1
            body += 1
        self.lines[n] = line[:m.start()] + f"{name}=None" + line[m.end():]
        self.inserts.append((body, f"{indent}if {name} is None:"))
        self.inserts.append((body, f"{indent}    {name} = {empty}"))
        return f"Defaulted '{name}' to None and create a new {empty} on each call"

    def JS004(self, n: int, issue: Issue) -> str | None:
        # el.innerHTML = "Hello " + name  ->  el.textContent = ...   (only when no markup is built)
        line = self.lines[n]
        m = re.search(r"\.innerHTML\s*=(?!=)(.*)$", line)
        if not m or "<" in m.group(1):
            return None
        self.lines[n] = line[:m.start()] + ".textContent =" + m.group(1)
        return "Used textContent so the value is shown as text, not parsed as HTML"

    def JS008(self, n: int, issue: Issue) -> str | None:
        line = self.lines[n]
        new = re.sub(r"\bset(Timeout|Interval)\(\s*(['\"])([^'\"]+)\2\s*,", r"set\1(() => { \3; },", line)
        if new == line:
            return None
        self.lines[n] = new
        return "Passed a function instead of a code string"

    def JS009(self, n: int, issue: Issue) -> str | None:
        line = self.lines[n]
        m = re.search(r"catch\s*\(\s*(\w+)\s*\)\s*\{\s*\}", line)
        if not m:
            return None
        self.lines[n] = line[:m.start()] + f"catch ({m.group(1)}) {{ console.error({m.group(1)}); }}" + line[m.end():]
        return "Logged the caught error instead of ignoring it"

    def PY004(self, n: int, issue: Issue) -> str | None:
        line = self.lines[n]
        new = re.sub(r"\s*!=\s*None\b", " is not None", line)
        new = re.sub(r"\s*==\s*None\b", " is None", new)
        if new == line:
            return None
        self.lines[n] = new
        return "Replaced == None with 'is None'"

    def PY001(self, n: int, issue: Issue) -> str | None:
        line = self.lines[n]
        new = re.sub(r"\bexcept\s*:", "except Exception:", line, count=1)
        if new == line:
            return None
        self.lines[n] = new
        return "Narrowed bare 'except:' to 'except Exception:'"

    def JS002(self, n: int, issue: Issue) -> str | None:
        pattern = re.compile(r"(?<![=!<>])(==|!=)(?!=)(?!\s*(null|undefined)\b)")
        new, count = _sub_in_code(self.lines[n], self.blank[n], pattern, lambda m: m.group(1) + "=")
        if not count:
            return None
        self.lines[n] = new
        return "Replaced loose equality with === / !=="

    def JS003(self, n: int, issue: Issue) -> str | None:
        new, count = _sub_in_code(self.lines[n], self.blank[n], re.compile(r"^(\s*)var\b"), r"\1let")
        if not count:
            return None
        self.lines[n] = new
        return "Replaced 'var' with 'let'"

    def JV004(self, n: int, issue: Issue) -> str | None:
        line = self.lines[n]
        lit = r'("(?:[^"\\]|\\.)*")'
        new = re.sub(rf"([A-Za-z_][\w.]*)\s*==\s*{lit}", r"\2.equals(\1)", line)
        new = re.sub(rf"{lit}\s*==\s*([A-Za-z_][\w.]*)", r"\1.equals(\2)", new)
        if new == line:
            return None
        self.lines[n] = new
        return "Compared strings with .equals() instead of =="

    def CC004(self, n: int, issue: Issue) -> str | None:
        new, count = _sub_in_code(self.lines[n], self.blank[n],
                                  re.compile(r"\bprintf\s*\(\s*([A-Za-z_]\w*)\s*\)"), r'printf("%s", \1)')
        if not count:
            return None
        self.lines[n] = new
        return 'Passed a literal format string: printf("%s", ...)'

    def CC001(self, n: int, issue: Issue) -> str | None:
        line = self.lines[n]
        m = re.search(r"\b(gets|strcpy|strcat|sprintf)\s*\(\s*([A-Za-z_]\w*)\s*([,)])", line)
        if not m or not _declared_array(self.code, m.group(2)):
            return None  # unknown buffer size -> a mechanical fix could be wrong
        fn, buf = m.group(1), m.group(2)
        if fn == "gets":
            new = re.sub(rf"\bgets\s*\(\s*{buf}\s*\)", f"fgets({buf}, sizeof {buf}, stdin)", line)
        elif fn == "sprintf":
            new = re.sub(rf"\bsprintf\s*\(\s*{buf}\s*,", f"snprintf({buf}, sizeof {buf},", line)
        elif fn == "strcpy":
            new = re.sub(rf"\bstrcpy\s*\(\s*{buf}\s*,\s*(.+?)\)\s*;", rf'snprintf({buf}, sizeof {buf}, "%s", \1);', line)
        else:
            new = re.sub(rf"\bstrcat\s*\(\s*{buf}\s*,\s*(.+?)\)\s*;",
                         rf"strncat({buf}, \1, sizeof {buf} - strlen({buf}) - 1);", line)
        if new == line:
            return None
        self.lines[n] = new
        return f"Replaced {fn}() with a bounds-checked call"

    def CF001(self, n: int, issue: Issue) -> str | None:
        line, blank = self.lines[n], self.blank[n]
        end = len(blank.rstrip())
        if end == 0 or blank.rstrip().endswith(";"):
            return None
        self.lines[n] = line[:end] + ";" + line[end:]
        return "Added the missing semicolon"

    def SEC001(self, n: int, issue: Issue) -> str | None:
        line = self.lines[n]
        lang = self.language
        if lang == "python":
            m = re.match(r"^(\s*)([A-Za-z_]\w*)\s*=\s*(['\"]).*\3\s*(#.*)?$", line)
            if not m:
                return None
            env = to_env_name(m.group(2))
            self.lines[n] = f'{m.group(1)}{m.group(2)} = os.environ["{env}"]'
            self.needs_import_os = True
        elif lang in ("javascript", "typescript"):
            m = re.match(r"^(\s*(?:export\s+)?(?:const|let|var)\s+)([A-Za-z_$][\w$]*)(\s*:\s*\w+)?\s*=\s*(['\"`]).*\4\s*;?\s*$", line)
            if not m:
                return None
            env = to_env_name(m.group(2))
            fallback = ' ?? ""' if m.group(3) else ""
            self.lines[n] = f"{m.group(1)}{m.group(2)}{m.group(3) or ''} = process.env.{env}{fallback};"
        elif lang == "java":
            m = re.match(r'^(\s*.*?\b)([A-Za-z_]\w*)\s*=\s*"(?:[^"\\]|\\.)*"\s*;\s*$', line)
            if not m:
                return None
            env = to_env_name(m.group(2))
            self.lines[n] = f'{m.group(1)}{m.group(2)} = System.getenv("{env}");'
        elif lang in ("c", "cpp"):
            m = re.match(r'^(\s*(?:static\s+)?(?:const\s+)?char\s*\*\s*)([A-Za-z_]\w*)\s*=\s*"(?:[^"\\]|\\.)*"\s*;\s*$', line)
            if not m:
                return None  # e.g. #define NAME "..." needs a manual change at every use
            env = to_env_name(m.group(2))
            getenv = "std::getenv" if lang == "cpp" else "getenv"
            self.lines[n] = f'{m.group(1)}{m.group(2)} = {getenv}("{env}");'
            self._ensure_include("<cstdlib>" if lang == "cpp" else "<stdlib.h>")
        elif lang == "go":
            m = re.match(r'^(\s*)(?:const|var)\s+([A-Za-z_]\w*)\s*=\s*"(?:[^"\\]|\\.)*"\s*$', line)
            if not m:
                return None
            env = to_env_name(m.group(2))
            self.lines[n] = f'{m.group(1)}var {m.group(2)} = os.Getenv("{env}")'
            self._ensure_go_import("os")
        else:
            return None
        return f"Moved the secret to the {env} environment variable"

    def _insert(self, idx: int, text: str) -> None:
        if (idx, text) not in self.inserts:
            self.inserts.append((idx, text))

    def _ensure_include(self, header: str) -> None:
        if any(re.match(rf"\s*#include\s*{re.escape(header)}", l) for l in self.lines):
            return
        includes = [i for i, l in enumerate(self.lines) if l.lstrip().startswith("#include")]
        self._insert(includes[-1] + 1 if includes else 0, f"#include {header}")

    def _ensure_go_import(self, pkg: str) -> None:
        if any(re.search(rf'"{pkg}"', l) for l in self.lines):
            return
        start = next((i for i, l in enumerate(self.lines) if l.strip() == "import ("), None)
        if start is None:
            return
        idx = start + 1
        while idx < len(self.lines) and self.lines[idx].strip() != ")" and self.lines[idx].strip().strip('"') < pkg:
            idx += 1
        self._insert(idx, f'\t"{pkg}"')

    def CF002(self, issue: Issue) -> str | None:
        """Rename a case-typo everywhere it appears in code."""
        wrong = re.search(r"'(\w+)'", issue.title)
        right = re.search(r"'(\w+)'", issue.suggestion or "")
        if not wrong or not right:
            return None
        pattern = re.compile(rf"\b{re.escape(wrong.group(1))}\b")
        total = 0
        for i in range(len(self.lines)):
            self.lines[i], count = _sub_in_code(self.lines[i], self.blank[i], pattern, right.group(1))
            total += count
        return f"Renamed '{wrong.group(1)}' to '{right.group(1)}'" if total else None

    def PY005(self, n: int, issue: Issue) -> bool:
        name = re.search(r"'(\w+)'", issue.title)
        line = self.lines[n]
        if not name:
            return False
        nm = re.escape(name.group(1))
        return bool(re.fullmatch(rf"\s*import {nm}\s*|\s*from [\w.]+ import {nm}\s*", line))


def autofix(code: str, language: str, issues: list[Issue]) -> FixResult:
    fx = _Fixer(code, language)
    applied: list[dict] = []
    fixed_ids: set[int] = set()

    def record(issue: Issue, description: str | None) -> None:
        if description:
            applied.append({"line": issue.line, "rule_id": issue.rule_id, "description": description})
            fixed_ids.add(id(issue))

    # 1. renames touch many lines; do them first, while line numbers are still original
    for issue in issues:
        if issue.rule_id == "CF002":
            record(issue, fx.CF002(issue))

    # 2. single-line edits, in a stable order
    for issue in sorted((i for i in issues if i.rule_id in ORDER and i.line),
                        key=lambda i: (i.line, ORDER.index(i.rule_id))):
        if issue.line - 1 < len(fx.lines):
            record(issue, getattr(fx, issue.rule_id)(issue.line - 1, issue))

    # 3. unused imports (marked for deletion; applied in the final pass)
    for issue in issues:
        if issue.rule_id == "PY005" and issue.line and fx.PY005(issue.line - 1, issue):
            name = re.search(r"'(\w+)'", issue.title).group(1)
            if not (name == "os" and fx.needs_import_os):
                fx.deletes.add(issue.line - 1)
                record(issue, f"Removed unused import '{name}'")

    if fx.needs_import_os and not any(re.match(r"\s*import os\s*$", l) for l in fx.lines):
        at = 0
        while at < len(fx.lines) and re.match(r'\s*(#|"""|from __future__)', fx.lines[at]):
            at += 1
        fx.inserts.append((at, "import os"))

    out: list[str] = []
    for idx in range(len(fx.lines) + 1):
        out.extend(text for at, text in fx.inserts if at == idx)
        if idx < len(fx.lines) and idx not in fx.deletes:
            out.append(fx.lines[idx])

    newline = "\r\n" if "\r\n" in code else "\n"
    fixed = newline.join(out) + (newline if code.endswith(("\n", "\r\n")) else "")
    remaining = [{"line": i.line, "rule_id": i.rule_id, "title": i.title}
                 for i in issues if id(i) not in fixed_ids]
    return FixResult(code=fixed, applied=sorted(applied, key=lambda a: a["line"] or 0), remaining=remaining)
