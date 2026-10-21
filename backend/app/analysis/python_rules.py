"""AST-based checks for Python. The code is parsed, never executed."""

import ast
import builtins
import re

from .base import Issue
from .detect import detect_language

SUPPORTED_LANGUAGE_LABELS = {"java": "Java", "cpp": "C++", "c": "C", "go": "Go",
                             "typescript": "TypeScript", "javascript": "JavaScript"}

SHADOWABLE_BUILTINS = {
    "list", "dict", "set", "str", "int", "float", "id", "type", "input", "max", "min",
    "sum", "len", "filter", "map", "object", "open", "format", "hash", "range", "next",
} & set(dir(builtins))

SQL_METHODS = {"execute", "executemany", "raw"}
WEAK_HASHES = {"md5", "sha1"}
HTTP_CALLS = {f"requests.{m}" for m in ("get", "post", "put", "patch", "delete", "head", "request")}
MAX_COMPLEXITY = 10
MAX_FUNCTION_LINES = 60


def _call_name(node: ast.Call) -> str:
    """Dotted name of the called object, e.g. 'subprocess.run' or 'eval'."""
    parts: list[str] = []
    cur = node.func
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    return ".".join(reversed(parts))


def _kw(node: ast.Call, name: str) -> ast.expr | None:
    return next((k.value for k in node.keywords if k.arg == name), None)


def _is_true(node: ast.expr | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def _is_false(node: ast.expr | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is False


def _is_dynamic_string(node: ast.expr) -> bool:
    """True for f-strings, '%'-formatting, '+' concatenation and .format() on strings."""
    if isinstance(node, ast.JoinedStr):
        return any(isinstance(v, ast.FormattedValue) for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        return True
    return False


def cyclomatic_complexity(fn: ast.AST) -> int:
    score = 1
    for node in ast.walk(fn):
        if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.IfExp, ast.ExceptHandler,
                             ast.With, ast.AsyncWith, ast.Assert, ast.comprehension)):
            score += 1
        elif isinstance(node, ast.BoolOp):
            score += len(node.values) - 1
        elif isinstance(node, ast.Match):
            score += len(node.cases)
    return score


class _Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.issues: list[Issue] = []
        self.functions: list[dict] = []
        self.imported: dict[str, int] = {}
        self.used_names: set[str] = set()

    def add(self, *args, **kwargs) -> None:
        self.issues.append(Issue(*args, **kwargs))

    # ---- imports / names -------------------------------------------------
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imported[(alias.asname or alias.name).split(".")[0]] = node.lineno
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "__future__":  # compiler directives, never "used" by name
            return
        for alias in node.names:
            if alias.name != "*":
                self.imported[alias.asname or alias.name] = node.lineno
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        self.used_names.add(node.id)
        if isinstance(node.ctx, ast.Store) and node.id in SHADOWABLE_BUILTINS:
            self.add("PY006", f"Built-in '{node.id}' is shadowed", "low", "maintainability", node.lineno,
                     f"Assigning to '{node.id}' hides the built-in of the same name in this scope.",
                     f"Rename the variable, e.g. '{node.id}_' or a more descriptive name.")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        root = node
        while isinstance(root, ast.Attribute):
            root = root.value
        if isinstance(root, ast.Name):
            self.used_names.add(root.id)
        self.generic_visit(node)

    # ---- functions -------------------------------------------------------
    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        complexity = cyclomatic_complexity(node)
        length = (node.end_lineno or node.lineno) - node.lineno + 1
        self.functions.append({"name": node.name, "line": node.lineno, "complexity": complexity, "length": length})

        for default in node.args.defaults + [d for d in node.args.kw_defaults if d is not None]:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)) or (
                isinstance(default, ast.Call) and _call_name(default) in {"list", "dict", "set"}
            ):
                self.add("PY002", "Mutable default argument", "high", "bug", default.lineno,
                         f"Function '{node.name}' uses a mutable default value. It is created once and "
                         "shared between calls, so changes leak from one call to the next.",
                         "Default to None and create the object inside the function body.")
        if complexity > MAX_COMPLEXITY:
            self.add("PY010", "High cyclomatic complexity", "medium", "maintainability", node.lineno,
                     f"Function '{node.name}' has complexity {complexity} (threshold {MAX_COMPLEXITY}).",
                     "Split it into smaller functions or replace branching with lookup tables.")
        if length > MAX_FUNCTION_LINES:
            self.add("PY011", "Function is too long", "low", "maintainability", node.lineno,
                     f"Function '{node.name}' spans {length} lines (threshold {MAX_FUNCTION_LINES}).",
                     "Extract cohesive blocks into helper functions.")
        self.generic_visit(node)

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function

    # ---- exceptions ------------------------------------------------------
    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self.add("PY001", "Bare 'except:' clause", "medium", "bug", node.lineno,
                     "A bare except also catches SystemExit and KeyboardInterrupt, hiding real failures.",
                     "Catch the specific exceptions you expect, or at least 'except Exception:'.")
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            # ignoring a specific, named exception is usually deliberate (Bandit B110 rates it low);
            # swallowing everything hides real failures
            broad = node.type is None or (isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"})
            self.add("PY013", "Exception silently swallowed", "medium" if broad else "low", "bug", node.lineno,
                     "The except block only contains 'pass', so "
                     + ("every error disappears without a trace." if broad
                        else "these errors are ignored. Make sure that is intended."),
                     "Log the exception, handle it, or let it propagate"
                     + ("." if broad else "; if ignoring it is intended, add a comment saying why."))
        self.generic_visit(node)

    # ---- comparisons -----------------------------------------------------
    def visit_Compare(self, node: ast.Compare) -> None:
        for op, right in zip(node.ops, node.comparators):
            if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(right, ast.Constant) and right.value is None:
                self.add("PY004", "Comparison to None with ==", "low", "style", node.lineno,
                         "'== None' can be overridden by __eq__; identity comparison is the idiom.",
                         "Use 'is None' / 'is not None'.")
        self.generic_visit(node)

    # ---- calls -----------------------------------------------------------
    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node)
        short = name.rsplit(".", 1)[-1]

        if name in {"eval", "exec"}:
            self.add("PY003", f"Use of {name}()", "critical", "security", node.lineno,
                     f"{name}() runs arbitrary code. If any part of its input comes from users this is "
                     "remote code execution.",
                     "Use ast.literal_eval for literals, or a dispatch table / parser for expressions.")

        if name.startswith("subprocess.") or name in {"os.system", "os.popen"}:
            if name in {"os.system", "os.popen"} or _is_true(_kw(node, "shell")):
                self.add("PY007", "Shell command injection risk", "high", "security", node.lineno,
                         f"{name} runs through the system shell; interpolated input can inject commands.",
                         "Pass an argument list to subprocess.run(...) with shell=False.")

        if name in {"pickle.load", "pickle.loads", "cPickle.loads", "marshal.loads"}:
            self.add("PY008", "Insecure deserialization", "high", "security", node.lineno,
                     "Unpickling untrusted data can execute arbitrary code.",
                     "Use JSON or another data-only format for untrusted input.")

        if name == "yaml.load" and _kw(node, "Loader") is None and len(node.args) < 2:
            self.add("PY014", "yaml.load without a safe Loader", "high", "security", node.lineno,
                     "yaml.load can construct arbitrary Python objects from YAML tags.",
                     "Use yaml.safe_load(...).")

        if name.split(".")[0] in {"requests", "httpx"} and _is_false(_kw(node, "verify")):
            self.add("PY015", "TLS verification disabled", "high", "security", node.lineno,
                     "verify=False accepts any certificate, enabling man-in-the-middle attacks.",
                     "Remove verify=False, or point verify at a trusted CA bundle.")

        if name in HTTP_CALLS and _kw(node, "timeout") is None:
            self.add("PY017", "HTTP request without timeout", "medium", "performance", node.lineno,
                     f"{name}() has no timeout, so a slow or unresponsive server can hang this code forever.",
                     f"Pass a timeout, e.g. {name}(url, timeout=10).")

        if name.startswith("hashlib.") and short in WEAK_HASHES:
            self.add("PY016", f"Weak hash algorithm ({short})", "medium", "security", node.lineno,
                     f"{short.upper()} is broken for security purposes such as password hashing or signatures.",
                     "Use hashlib.sha256 for integrity, and bcrypt/argon2 for passwords.")

        if short in SQL_METHODS and node.args and _is_dynamic_string(node.args[0]):
            self.add("PY012", "Possible SQL injection", "critical", "security", node.lineno,
                     "The SQL text passed to execute() is built with string formatting. Values that reach "
                     "it from users can change the query.",
                     "Use parameterised queries: cursor.execute('... WHERE id = %s', (user_id,)).")

        self.generic_visit(node)


NOQA = re.compile(r"#\s*noqa(?::\s*[\w, ]*\bF401\b)?(?![:\w])|#\s*noqa:\s*[\w, ]*\bF401\b", re.I)


def _has_noqa(lines: list[str], lineno: int) -> bool:
    """flake8-style '# noqa' / '# noqa: F401' on the import line marks an unused import as intended."""
    return 0 < lineno <= len(lines) and NOQA.search(lines[lineno - 1]) is not None


def _dunder_all(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets) and \
                    isinstance(node.value, (ast.List, ast.Tuple)):
                names |= {e.value for e in node.value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)}
    return names


def analyze_python(code: str) -> tuple[list[Issue], dict]:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        detected = detect_language(code)
        if detected and detected != "python":
            label = SUPPORTED_LANGUAGE_LABELS.get(detected, detected)
            issue = Issue("PY000", f"Not Python? This looks like {label}", "critical", "bug", e.lineno,
                          f"The code does not parse as Python ({e.msg}), and it looks like {label}.",
                          f"Select {label} as the language and run the review again.")
        else:
            issue = Issue("PY000", "Syntax error", "critical", "bug", e.lineno,
                          f"The code does not parse: {e.msg}.", "Fix the syntax error before other checks can run.")
        return [issue], {"functions": 0, "avg_complexity": 0, "max_complexity": 0, "parsed": False}

    v = _Visitor()
    v.visit(tree)

    exported = _dunder_all(tree)
    lines = code.splitlines()
    for name, line in v.imported.items():
        if name in v.used_names or name in exported or _has_noqa(lines, line):
            continue  # used, re-exported via __all__, or explicitly marked as intentional
        v.add("PY005", f"Unused import '{name}'", "info", "style", line,
              f"'{name}' is imported but never used.", "Remove the import.")

    complexities = [f["complexity"] for f in v.functions]
    facts = {
        "functions": len(v.functions),
        "avg_complexity": round(sum(complexities) / len(complexities), 1) if complexities else 1,
        "max_complexity": max(complexities, default=1),
        "parsed": True,
    }
    return v.issues, facts
