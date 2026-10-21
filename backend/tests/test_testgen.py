import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from app.analysis.testgen import generate_test_skeleton

SAMPLES = Path(__file__).parent / "samples"
NODE = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"


def test_python_skeleton_is_collected_by_pytest(tmp_path):
    code = (SAMPLES / "tricky.py").read_text()
    skel = generate_test_skeleton(code, "python", "helpers.py")
    assert skel.framework == "pytest" and skel.filename == "test_helpers.py"
    ast.parse(skel.code)
    (tmp_path / "helpers.py").write_text(code)
    (tmp_path / skel.filename).write_text(skel.code)
    # --collect-only imports the module and the tests without running them
    out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", str(tmp_path)],
                         capture_output=True, text=True, cwd=tmp_path)
    assert out.returncode == 0, out.stdout + out.stderr
    assert f"{skel.count} tests collected" in out.stdout


def test_python_skeleton_covers_methods_and_raised_errors():
    code = '''
class Account:
    def __init__(self, owner, balance=0):
        self.owner = owner

    def withdraw(self, amount):
        if amount <= 0:
            raise ValueError("amount must be positive")
        return amount

    def _private(self):
        pass


def helper():
    return 1
'''
    skel = generate_test_skeleton(code, "python", "bank/account.py")
    assert "from account import Account, helper" in skel.code
    assert "instance = Account(owner=None)" in skel.code
    assert "def test_account_withdraw():" in skel.code
    assert "def test_account_withdraw_raises_valueerror():" in skel.code
    assert "with pytest.raises(ValueError):" in skel.code and skel.code.startswith("import pytest")
    assert "_private" not in skel.code
    assert skel.count == 3


@pytest.mark.skipif(not Path(NODE).exists(), reason="node not installed")
def test_javascript_skeleton_is_valid_syntax(tmp_path):
    skel = generate_test_skeleton((SAMPLES / "clean.js").read_text(), "javascript", "lib/user.js")
    assert skel.framework == "Jest" and skel.filename == "user.test.js"
    path = tmp_path / "user.test.mjs"
    path.write_text(skel.code.replace("describe(", "globalThis.describe?.(") )
    assert subprocess.run([NODE, "--check", str(path)], capture_output=True).returncode == 0
    assert "expect(await loadUser(db, id))" in skel.code  # async functions are awaited


def test_javascript_throw_becomes_tothrow_test():
    code = 'export function parse(raw) {\n  if (!raw) throw new TypeError("empty");\n  return JSON.parse(raw);\n}\n'
    skel = generate_test_skeleton(code, "javascript", "parse.js")
    assert "expect(() => parse(raw)).toThrow(TypeError);" in skel.code


def test_typescript_generics_detected():
    skel = generate_test_skeleton((SAMPLES / "tricky.ts").read_text(), "typescript", "ui/result.ts")
    assert skel.filename == "result.test.ts"
    assert 'import { mapResult, greet, first } from "./result";' in skel.code


def test_java_skeleton():
    skel = generate_test_skeleton((SAMPLES / "Clean.java").read_text(), "java", "UserRepository.java")
    assert skel.filename == "UserRepositoryTest.java"
    assert "import java.sql.*;" in skel.code  # source imports carried over
    assert "boolean result = subject.isAdmin(role);" in skel.code
    assert "assertEquals(false, result);" in skel.code
    assert skel.code.count("@Test") == skel.count == 2


def test_java_throw_becomes_assertthrows():
    code = ("public class Calc {\n    public int divide(int a, int b) {\n"
            "        if (b == 0) {\n            throw new IllegalArgumentException(\"b\");\n        }\n"
            "        return a / b;\n    }\n}\n")
    skel = generate_test_skeleton(code, "java", "Calc.java")
    assert "assertThrows(IllegalArgumentException.class, () -> subject.divide(a, b));" in skel.code


def test_go_skeleton():
    skel = generate_test_skeleton((SAMPLES / "tricky.go").read_text(), "go", "store.go")
    assert skel.filename == "store_test.go" and skel.code.startswith("package store")
    assert "func TestNames(t *testing.T)" in skel.code and "func TestLabel(t *testing.T)" in skel.code


def test_unsupported_language_returns_none():
    assert generate_test_skeleton("int main(void) { return 0; }", "c", "main.c") is None
