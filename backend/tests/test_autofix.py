import ast
import shutil
import subprocess
from pathlib import Path

import pytest

from app.analysis import run_static_analysis
from app.analysis.autofix import autofix, to_env_name

SAMPLES = Path(__file__).parent / "samples"
FLAWED = [("sample.py", "python"), ("sample.js", "javascript"), ("sample.ts", "typescript"),
          ("Sample.java", "java"), ("sample.cpp", "cpp"), ("sample.c", "c"), ("sample.go", "go"),
          ("Employee.java", "java")]


def fix(code: str, language: str):
    return autofix(code, language, run_static_analysis(code, language).issues)


@pytest.mark.parametrize(("name", "language"), FLAWED)
def test_autofix_improves_score_and_never_adds_issues(name, language):
    code = (SAMPLES / name).read_text()
    before = run_static_analysis(code, language)
    result = fix(code, language)
    after = run_static_analysis(result.code, language)
    assert result.applied, "expected at least one automatic fix"
    assert after.score > before.score
    assert {i.rule_id for i in after.issues} <= {i.rule_id for i in before.issues}


def test_fixed_python_still_parses_and_is_correct():
    result = fix((SAMPLES / "sample.py").read_text(), "python")
    ast.parse(result.code)
    assert 'os.environ["API_TOKEN"]' in result.code and result.code.startswith("import os")
    assert 'cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))' in result.code
    assert "def add_item(item, cart=None):\n    if cart is None:\n        cart = []\n    cart.append(item)" in result.code
    assert 'subprocess.run(["zip", "backup.zip", name])' in result.code
    assert "requests.get(url, timeout=10)" in result.code and "verify=False" not in result.code
    assert "except Exception:" in result.code and "if user is None:" in result.code


@pytest.mark.skipif(shutil.which("node") is None and not Path(r"C:\Program Files\nodejs\node.exe").exists(),
                    reason="node not installed")
def test_fixed_javascript_is_valid_syntax(tmp_path):
    node = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    result = fix((SAMPLES / "sample.js").read_text(), "javascript")
    path = tmp_path / "fixed.js"
    path.write_text(result.code)
    # --check only parses the file; it never runs it
    assert subprocess.run([node, "--check", str(path)], capture_output=True).returncode == 0
    assert ".textContent =" in result.code and "a === b" in result.code
    assert "setTimeout(() => { counter++; }, 100)" in result.code and "let counter" in result.code


def test_user_java_program_fixes():
    result = fix((SAMPLES / "Employee.java").read_text(), "java")
    assert "return salary * 0.10;" in result.code
    assert "totalbonus" not in result.code and result.code.count("totalBonus") == 3
    remaining = {r["rule_id"] for r in result.remaining}
    assert "CF003" in remaining  # a null dereference needs a human (or the AI) to decide the fix


def test_c_fixes_only_when_buffer_size_is_known():
    result = fix((SAMPLES / "sample.c").read_text(), "c")
    assert "fgets(input, sizeof input, stdin)" in result.code
    assert 'printf("%s", line)' in result.code
    # buf is a malloc'd pointer: sizeof would be wrong, so strcat is left for a manual fix
    assert 'strcat(buf, "data")' in result.code


def test_go_secret_moves_to_env_and_imports_os():
    result = fix((SAMPLES / "sample.go").read_text(), "go")
    assert 'var apiSecret = os.Getenv("API_SECRET")' in result.code
    assert '\t"os"\n\t"os/exec"' in result.code  # inserted in sorted position


def test_strings_and_comments_are_never_rewritten():
    code = 'var x = 1;\n// keep: if (a == b) {}\nconst s = "a == b";\nif (x == 2) {}\n'
    result = fix(code, "javascript")
    assert "// keep: if (a == b) {}" in result.code and '"a == b"' in result.code
    assert "if (x === 2) {}" in result.code


def test_clean_code_is_left_untouched():
    code = (SAMPLES / "clean.py").read_text()
    result = fix(code, "python")
    assert result.code == code and not result.applied


@pytest.mark.parametrize(("name", "env"), [("apiKey", "API_KEY"), ("DB_PASSWORD", "DB_PASSWORD"),
                                          ("secret_key", "SECRET_KEY"), ("apiSecret", "API_SECRET")])
def test_env_names(name, env):
    assert to_env_name(name) == env
