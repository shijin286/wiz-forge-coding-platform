from app.analysis import run_static_analysis


def rule_ids(code: str, language: str) -> set[str]:
    return {i.rule_id for i in run_static_analysis(code, language).issues}


def test_python_security_rules():
    code = '''
import os
import pickle
import subprocess
import hashlib

def run(cmd, data, user_id, cur):
    eval(cmd)
    subprocess.run(cmd, shell=True)
    pickle.loads(data)
    hashlib.md5(data)
    cur.execute(f"SELECT * FROM users WHERE id = {user_id}")
'''
    ids = rule_ids(code, "python")
    assert {"PY003", "PY007", "PY008", "PY016", "PY012"} <= ids
    assert "PY005" in ids  # 'os' is unused


def test_python_bug_rules():
    code = '''
def add(item, bucket=[]):
    bucket.append(item)
    if item == None:
        pass
    try:
        list = [1]
    except:
        pass
    return bucket
'''
    ids = rule_ids(code, "python")
    assert {"PY002", "PY004", "PY001", "PY013", "PY006"} <= ids


def test_parameterised_sql_is_not_flagged():
    code = 'def q(cur, uid):\n    cur.execute("SELECT * FROM t WHERE id = %s", (uid,))\n'
    assert "PY012" not in rule_ids(code, "python")


def test_python_syntax_error():
    result = run_static_analysis("def broken(:\n    pass\n", "python")
    assert result.issues[0].rule_id == "PY000"
    assert result.issues[0].severity == "critical"


def test_clean_code_scores_well():
    code = 'def greet(name: str) -> str:\n    """Return a greeting."""\n    return f"Hello, {name}"\n'
    result = run_static_analysis(code, "python")
    assert result.issues == []
    assert result.score == 100 and result.grade == "A"


def test_javascript_rules():
    code = '''
var x = 1;
if (x == "1") { el.innerHTML = userInput; }
try { risky(); } catch (e) {}
db.query(`SELECT * FROM users WHERE id = ${id}`);
eval(code);
'''
    ids = rule_ids(code, "javascript")
    assert {"JS003", "JS002", "JS004", "JS009", "JS011", "JS001"} <= ids


def test_strict_equality_and_null_check_not_flagged():
    assert "JS002" not in rule_ids("if (a === b && c != null) {}\n", "javascript")


def test_patterns_in_comments_are_ignored():
    assert "JS001" not in rule_ids("// never call eval(x) here\n", "javascript")


def test_secrets_detected_any_language():
    code = 'api_key = "abcd1234efgh5678"\nAWS = "AKIAABCDEFGHIJKLMNOP"\n'
    ids = rule_ids(code, "other")
    assert {"SEC001", "SEC002"} <= ids


def test_score_decreases_with_severity():
    clean = run_static_analysis("x = 1\n", "python").score
    dirty = run_static_analysis("eval(input())\n", "python").score
    assert dirty < clean


def test_metrics():
    m = run_static_analysis("# comment\n\ndef f():\n    return 1\n", "python").metrics
    assert m["lines_of_code"] == 2 and m["comment_lines"] == 1 and m["blank_lines"] == 1
    assert m["functions"] == 1


def test_secret_in_compound_name():
    ids = rule_ids('SECRET_KEY = "super-secret-signing-key"\nDB_PASSWORD = "hunter2-prod"\n', "python")
    assert "SEC001" in ids
    assert len([i for i in run_static_analysis('DB_PASSWORD = "hunter2-prod"\n', "python").issues if i.rule_id == "SEC001"]) == 1


def test_noqa_and_dunder_all_mark_imports_as_intended():
    code = ("from ._internal import (  # noqa: F401\n    HEADER_VALIDATORS,\n)\n"
            "import os  # noqa\nimport sys\nfrom json import dumps\n__all__ = ['dumps']\n")
    unused = {i.title for i in run_static_analysis(code, "python").issues if i.rule_id == "PY005"}
    assert unused == {"Unused import 'sys'"}


def test_noqa_for_another_code_does_not_hide_unused_import():
    unused = [i for i in run_static_analysis("import os  # noqa: E501\n", "python").issues if i.rule_id == "PY005"]
    assert len(unused) == 1


def test_swallowed_specific_exception_is_low_broad_is_medium():
    code = ("try:\n    x = 1\nexcept (KeyError, ValueError):\n    pass\n"
            "try:\n    y = 2\nexcept Exception:\n    pass\n")
    sev = {i.line: i.severity for i in run_static_analysis(code, "python").issues if i.rule_id == "PY013"}
    assert sev == {3: "low", 7: "medium"}
