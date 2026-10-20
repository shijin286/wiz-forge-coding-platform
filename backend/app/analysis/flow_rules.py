"""Light structural checks for C-family languages (Java, C, C++, JS/TS, Go).

They work on a copy of the source where string literals and comments are blanked out
(line structure preserved), so text inside strings or comments never triggers a rule.
"""

import re
from collections import defaultdict

from .base import Issue

SEMICOLON_LANGUAGES = {"java", "c", "cpp"}
TYPO_LANGUAGES = {"java", "c", "cpp", "javascript", "typescript", "go"}
NULL_LANGUAGES = {"java", "c", "cpp", "javascript", "typescript"}

NULL_LITERALS = {"java": "null", "javascript": "null|undefined", "typescript": "null|undefined",
                 "c": "NULL", "cpp": "NULL|nullptr"}

STATEMENT_KEYWORDS = re.compile(
    r"^(if|else|for|while|do|switch|case|default|try|catch|finally|class|interface|enum|struct|union|"
    r"namespace|template|public|private|protected|static|extern|typedef|package|import|module|#|@|//|\*)\b"
)
CONTINUES_LINE = (";", "{", "}", ",", "(", "[", ":", "&&", "||", "+", "-", "*", "/", "%", "=", "?", "<",
                  ">", "|", "&", ".", "\\", "^", "!")


def blank_strings_and_comments(code: str, keep_strings: bool = False) -> str:
    """Replace comments (and, unless keep_strings, string contents) with spaces, keeping line breaks."""
    out: list[str] = []
    i, n = 0, len(code)
    while i < n:
        ch, nxt = code[i], code[i + 1] if i + 1 < n else ""
        if ch == "/" and nxt == "/":
            while i < n and code[i] != "\n":
                out.append(" ")
                i += 1
        elif ch == "/" and nxt == "*":
            end = code.find("*/", i + 2)
            end = n if end == -1 else end + 2
            out.extend("\n" if c == "\n" else " " for c in code[i:end])
            i = end
        elif ch in "\"'`":
            out.append(ch)
            i += 1
            while i < n and code[i] != ch:
                if code[i] == "\\":
                    out.append(code[i] if keep_strings else " ")
                    i += 1
                if i < n:
                    out.append(code[i] if keep_strings or code[i] == "\n" else " ")
                    i += 1
            if i < n:
                out.append(ch)
                i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def missing_semicolons(lines: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    depth = 0  # open ( and [ carried over from previous lines
    for idx, raw in enumerate(lines):
        s = raw.strip()
        start_depth = depth
        depth = max(0, depth + s.count("(") + s.count("[") - s.count(")") - s.count("]"))
        if not s or start_depth > 0 or depth > 0 or s.endswith(CONTINUES_LINE) or STATEMENT_KEYWORDS.match(s):
            continue
        nxt = next((l.strip() for l in lines[idx + 1:] if l.strip()), "")
        if nxt.startswith(("{", ".", ")", "+", "-", "*", "/", "&&", "||", "?", ":", "->", "<<", ">>", "=")):
            continue
        is_statement = (
            s.startswith(("return ", "throw ", "break", "continue"))
            or re.search(r"[^=!<>]=[^=]", s)  # assignment
            or re.fullmatch(r"[\w.\->\[\]]+\(.*\)", s)  # bare call
            or re.fullmatch(r"[\w.\->\[\]]+(\+\+|--)", s)
        )
        if is_statement:
            issues.append(Issue("CF001", "Missing semicolon", "critical", "bug", idx + 1,
                                "This statement does not end with ';', so the file will not compile.",
                                "Add ';' at the end of the statement."))
    return issues


def identifier_typos(text: str) -> list[Issue]:
    first_line: dict[str, int] = {}
    counts: dict[str, int] = defaultdict(int)
    for lineno, line in enumerate(text.splitlines(), start=1):
        for name in re.findall(r"\b[A-Za-z_]\w{3,}\b", line):
            counts[name] += 1
            first_line.setdefault(name, lineno)

    groups: dict[str, list[str]] = defaultdict(list)
    for name in counts:
        groups[name.lower()].append(name)

    issues: list[Issue] = []
    for variants in groups.values():
        if len(variants) < 2:
            continue
        variants.sort(key=lambda v: (-counts[v], first_line[v]))
        canonical = variants[0]
        for other in variants[1:]:
            # Foo / foo is the usual class-vs-instance convention, not a typo
            if other[1:] == canonical[1:]:
                continue
            issues.append(Issue("CF002", f"Possible typo: '{other}'", "high", "bug", first_line[other],
                                f"'{other}' differs from '{canonical}' only by letter case. Most of these "
                                "languages are case-sensitive, so this is likely an undefined name.",
                                f"Did you mean '{canonical}'?"))
    return issues


def null_dereferences(lines: list[str], language: str) -> list[Issue]:
    null_re = NULL_LITERALS[language]
    assign_null = re.compile(rf"(?:^|[\s(;])(?:[\w<>\[\]*]+\s+)?\**(\w+)\s*=\s*(?:{null_re})\s*;?\s*$")
    issues: list[Issue] = []
    tracked: dict[str, tuple[int, int]] = {}  # variable -> (brace depth, line) where it was set to null
    depth = 0
    for idx, line in enumerate(lines):
        for var, (var_depth, set_line) in list(tracked.items()):
            if depth < var_depth:  # left the block the variable lived in
                del tracked[var]
            elif re.search(rf"\b{var}\s*(!=|==)|\b(if|while)\s*\(.*\b{var}\b|\b{var}\s*=[^=]|\b{var}\s*\?", line):
                del tracked[var]  # null-checked or reassigned
            elif re.search(rf"\b{var}\s*(\.|->|\[)\s*\w", line):
                issues.append(Issue("CF003", f"Null dereference of '{var}'", "critical", "bug", idx + 1,
                                    f"'{var}' is set to null on line {set_line} and used here without being "
                                    "assigned or checked, which crashes at runtime (NullPointerException, "
                                    "segmentation fault or TypeError).",
                                    f"Give '{var}' a real value first, or guard the access with a null check."))
                del tracked[var]
        m = assign_null.search(line)
        if m:
            tracked[m.group(1)] = (depth, idx + 1)
        depth += line.count("{") - line.count("}")
    return issues


def analyze_flow(code: str, language: str) -> list[Issue]:
    text = blank_strings_and_comments(code)
    lines = text.splitlines()
    issues: list[Issue] = []
    if language in SEMICOLON_LANGUAGES:
        issues.extend(missing_semicolons(lines))
    if language in TYPO_LANGUAGES:
        issues.extend(identifier_typos(text))
    if language in NULL_LANGUAGES:
        issues.extend(null_dereferences(lines, language))
    return issues
