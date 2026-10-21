"""Deterministic unit-test skeletons generated from the code's public API.

The skeletons are a starting point: they import the code, call every public function with
placeholder arguments, and add an exception test wherever the code explicitly raises one.
Expected values are left as TODOs because only the author (or the AI pass) knows them.
"""

import ast
import re
from dataclasses import dataclass

from .flow_rules import blank_strings_and_comments


@dataclass
class TestFile:
    __test__ = False  # not a pytest test class, despite the name

    framework: str
    filename: str
    code: str
    count: int  # number of generated test cases


def _stem(title: str, default: str) -> str:
    name = re.split(r"[\\/]", title or "")[-1]
    name = re.sub(r"\.[^.]+$", "", name)
    name = re.sub(r"\W+", "_", name).strip("_")
    return name or default


# ---------------------------------------------------------------- Python / pytest
def _py_args(fn: ast.FunctionDef | ast.AsyncFunctionDef, skip_self: bool) -> list[str]:
    args = [a.arg for a in fn.args.posonlyargs + fn.args.args]
    if skip_self and args and args[0] in ("self", "cls"):
        args = args[1:]
    required = len(args) - len(fn.args.defaults)
    return args[:max(required, 0)]


def _py_raises(fn: ast.AST) -> list[str]:
    found = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Raise) and node.exc is not None:
            exc = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            if isinstance(exc, ast.Name) and exc.id not in found:
                found.append(exc.id)
    return found


def _python(code: str, module: str) -> TestFile | None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    tests: list[str] = []
    imports: list[str] = []

    def add_function(fn, call_prefix: str, label: str, skip_self: bool, setup: list[str]):
        args = _py_args(fn, skip_self)
        placeholders = ", ".join(f"{a}=None" for a in args)
        call = f"{call_prefix}{fn.name}({', '.join(args)})"
        is_async = isinstance(fn, ast.AsyncFunctionDef)
        await_kw = "await " if is_async else ""
        marker = "@pytest.mark.asyncio\n" if is_async else ""
        prefix = "async " if is_async else ""
        arrange = [f"    {a} = None  # TODO: realistic input" for a in args] if args else []
        body = "\n".join(setup + arrange + [f"    result = {await_kw}{call}",
                                            "    assert result == ...  # TODO: expected value"])
        tests.append(f"{marker}{prefix}def test_{label}():\n{body}\n")
        for exc in _py_raises(fn):
            bad = "\n".join(setup + [f"    {a} = None  # TODO: input that triggers {exc}" for a in args])
            tests.append(f"{marker}{prefix}def test_{label}_raises_{exc.lower()}():\n"
                         + (bad + "\n" if bad else "")
                         + f"    with pytest.raises({exc}):\n        {await_kw}{call}\n")
        del placeholders

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            imports.append(node.name)
            add_function(node, "", node.name, False, [])
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            imports.append(node.name)
            init = next((n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"), None)
            ctor_args = _py_args(init, True) if init else []
            setup = [f"    instance = {node.name}({', '.join(f'{a}=None' for a in ctor_args)})"
                     + ("  # TODO: constructor arguments" if ctor_args else "")]
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith("_"):
                    add_function(item, "instance.", f"{node.name.lower()}_{item.name}", True, setup)

    if not tests:
        return None
    body = "\n\n\n".join(t.rstrip("\n") for t in tests) + "\n"  # PEP 8: two blank lines between tests
    header = ("import pytest\n\n" if "pytest." in body else "") + f"from {module} import {', '.join(imports)}\n\n\n"
    return TestFile("pytest", f"test_{module}.py", header + body, len(tests))


# ---------------------------------------------------------------- JavaScript / TypeScript / Jest
JS_FUNCTION = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)\s*(?:<[^>()]*>\s*)?\(([^)]*)\)"
    r"|^\s*(?:export\s+)?(?:const|let)\s+([A-Za-z_$][\w$]*)\s*(?::[^=]+)?=\s*(?:async\s+)?(?:<[^>()]*>\s*)?(?:\(([^)]*)\)|([A-Za-z_$][\w$]*))\s*(?::[^=]+)?=>",
    re.M,
)
JS_THROW = re.compile(r"\bthrow\s+new\s+([A-Z]\w*)")


def _js_params(raw: str) -> list[str]:
    params = []
    for p in raw.split(","):
        p = p.strip()
        if not p or p.startswith(("{", "[")) or "=" in p:  # skip destructured / optional params
            continue
        params.append(re.split(r"[\s:?]", p.lstrip("."))[0])
    return [p for p in params if p]


def _javascript(code: str, module: str, ts: bool) -> TestFile | None:
    blank = blank_strings_and_comments(code, keep_strings=True)
    functions: list[tuple[str, list[str], str]] = []
    matches = list(JS_FUNCTION.finditer(blank))
    for i, m in enumerate(matches):
        name = m.group(1) or m.group(3)
        params = _js_params(m.group(2) if m.group(1) else (m.group(4) or m.group(5) or ""))
        body = blank[m.end(): matches[i + 1].start() if i + 1 < len(matches) else len(blank)]
        functions.append((name, params, body))
    if not functions:
        return None

    tests = []
    for name, params, body in functions:
        args = ", ".join(params)
        arrange = "".join(f"    const {p} = undefined; // TODO: realistic input\n" for p in params)
        is_async = "await " if re.search(rf"async\s+function\s+{name}\b|{name}\s*=\s*async\b", blank) else ""
        fn_kw = "async " if is_async else ""
        tests.append(f"  it(\"{name} returns the expected result\", {fn_kw}() => {{\n{arrange}"
                     f"    expect({is_async}{name}({args})).toEqual(undefined); // TODO: expected value\n  }});\n")
        for exc in dict.fromkeys(JS_THROW.findall(body)):
            call = f"{name}({args})"
            matcher = (f"    await expect({call}).rejects.toThrow({exc});\n" if is_async
                       else f"    expect(() => {call}).toThrow({exc});\n")
            tests.append(f"  it(\"{name} throws {exc} for invalid input\", {fn_kw}() => {{\n"
                         + "".join(f"    const {p} = undefined; // TODO: input that triggers {exc}\n" for p in params)
                         + matcher + "  });\n")

    names = ", ".join(dict.fromkeys(n for n, _, _ in functions))
    ext = "ts" if ts else "js"
    header = f'import {{ {names} }} from "./{module}";\n\ndescribe("{module}", () => {{\n'
    return TestFile("Jest", f"{module}.test.{ext}", header + "\n".join(tests) + "});\n", len(tests))


# ---------------------------------------------------------------- Java / JUnit 5
JAVA_CLASS = re.compile(r"\bclass\s+([A-Z]\w*)")
JAVA_METHOD = re.compile(
    r"^\s*public\s+(static\s+)?(?:final\s+)?([\w<>\[\],\s]+?)\s+([a-z]\w*)\s*\(([^)]*)\)\s*(?:throws\s+([\w\s,]+))?\s*\{",
    re.M,
)
JAVA_DEFAULTS = {"int": "0", "long": "0L", "double": "0.0", "float": "0f", "boolean": "false",
                 "char": "'a'", "short": "(short) 0", "byte": "(byte) 0", "String": '""'}


def _java(code: str) -> TestFile | None:
    blank = blank_strings_and_comments(code, keep_strings=True)
    public_class = re.search(r"public\s+(?:final\s+)?class\s+([A-Z]\w*)", blank)
    cls = (public_class or JAVA_CLASS.search(blank))
    if not cls:
        return None
    name = cls.group(1)
    tests = []
    for m in JAVA_METHOD.finditer(blank):
        static, ret, method, raw_params = m.group(1), m.group(2).strip(), m.group(3), m.group(4)
        if method == "main":
            continue
        params = []
        for p in filter(None, (x.strip() for x in raw_params.split(","))):
            ptype, pname = p.rsplit(None, 1)
            params.append((ptype.replace("final ", "").strip(), pname))
        arrange = "".join(f"        {t} {n} = {JAVA_DEFAULTS.get(t, 'null')}; // TODO: realistic input\n"
                          for t, n in params)
        target = name if static else "subject"
        call = f"{target}.{method}({', '.join(n for _, n in params)})"
        if ret == "void":
            act = f"        {call};\n        // TODO: assert the side effect\n"
        else:
            expected = JAVA_DEFAULTS.get(ret, "null")
            act = f"        {ret} result = {call};\n        assertEquals({expected}, result); // TODO: expected value\n"
        tests.append(f"    @Test\n    void {method}ReturnsExpectedResult() {{\n{arrange}{act}    }}\n")
        body_end = blank.find("\n    }", m.end())
        for exc in dict.fromkeys(re.findall(r"throw\s+new\s+([A-Z]\w*)", blank[m.end(): body_end if body_end > 0 else None])):
            tests.append(f"    @Test\n    void {method}Throws{exc}() {{\n"
                         + arrange.replace("realistic input", f"input that triggers {exc}")
                         + f"        assertThrows({exc}.class, () -> {call});\n    }}\n")
    if not tests:
        return None
    needs_instance = any("subject." in t for t in tests)
    setup = (f"    private final {name} subject = new {name}(); // TODO: constructor arguments\n\n"
             if needs_instance else "")
    # reuse the source file's imports so the types used in the tests resolve
    source_imports = "".join(f"{line.strip()}\n" for line in code.splitlines() if line.strip().startswith("import "))
    header = ("import static org.junit.jupiter.api.Assertions.*;\n\n" + source_imports
              + "import org.junit.jupiter.api.Test;\n\n" + f"class {name}Test {{\n\n{setup}")
    return TestFile("JUnit 5", f"{name}Test.java", header + "\n".join(tests) + "}\n", len(tests))


# ---------------------------------------------------------------- Go / testing
GO_FUNC = re.compile(r"^func\s+([A-Z]\w*)\s*\(([^)]*)\)", re.M)


def _go(code: str) -> TestFile | None:
    package = re.search(r"^package\s+(\w+)", code, re.M)
    funcs = GO_FUNC.findall(blank_strings_and_comments(code, keep_strings=True))
    if not package or not funcs:
        return None
    tests = []
    for name, raw in funcs:
        fields = ", ".join(f"{p.strip()}" for p in raw.split(",") if p.strip())
        tests.append(
            f"func Test{name}(t *testing.T) {{\n"
            f"\ttests := []struct {{\n\t\tname string\n" + (f"\t\t// inputs: {fields}\n" if fields else "")
            + "\t}{\n\t\t{name: \"TODO: describe the case\"},\n\t}\n"
            f"\tfor _, tt := range tests {{\n\t\tt.Run(tt.name, func(t *testing.T) {{\n"
            f"\t\t\t// TODO: call {name}(...) and compare with the expected result\n"
            f"\t\t\tt.Skip(\"not implemented\")\n\t\t}})\n\t}}\n}}\n")
    header = f"package {package.group(1)}\n\nimport \"testing\"\n\n"
    return TestFile("Go testing", "main_test.go" if package.group(1) == "main" else f"{package.group(1)}_test.go",
                    header + "\n".join(tests), len(tests))


def generate_test_skeleton(code: str, language: str, title: str) -> TestFile | None:
    module = _stem(title, "module")
    if language == "python":
        return _python(code, module)
    if language in ("javascript", "typescript"):
        return _javascript(code, module, language == "typescript")
    if language == "java":
        return _java(code)
    if language == "go":
        return _go(code)
    return None
