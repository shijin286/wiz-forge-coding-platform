"""Every language gets one deliberately flawed file (all planted issues must be found)
and one well-written file (nothing may be flagged)."""

from pathlib import Path

import pytest

from app.analysis import run_static_analysis

SAMPLES = Path(__file__).parent / "samples"

FLAWED = {
    ("sample.py", "python"): {"SEC001", "PY012", "PY002", "PY015", "PY008", "PY007", "PY017",
                              "PY001", "PY013", "PY004", "PY005"},
    ("sample.js", "javascript"): {"SEC001", "JS011", "JS001", "JS010", "JS004", "JS009", "JS008",
                                  "JS002", "JS003", "JS005"},
    ("sample.ts", "typescript"): {"SEC001", "JS004", "JS007", "TS001", "JS002"},
    ("Sample.java", "java"): {"SEC001", "JV003", "JV004", "JV005", "JV001", "JV002"},
    ("sample.cpp", "cpp"): {"SEC001", "CC001", "CC002", "CC003", "CC005"},
    ("sample.c", "c"): {"SEC001", "CC001", "CC002", "CC004"},
    ("sample.go", "go"): {"SEC001", "GO001", "GO002", "GO003"},
    ("sample.rb", "other"): {"SEC001", "SEC002", "GEN001"},
}

CLEAN = [
    ("clean.py", "python"), ("clean.js", "javascript"), ("clean.ts", "typescript"), ("Clean.java", "java"),
    ("clean.cpp", "cpp"), ("clean.c", "c"), ("clean.go", "go"),
    # harder cases: dangerous-looking text in comments/strings, multi-line statements, generics, macros
    ("tricky.py", "python"), ("tricky.js", "javascript"), ("tricky.ts", "typescript"), ("Tricky.java", "java"),
    ("tricky.cpp", "cpp"), ("tricky.c", "c"), ("tricky.go", "go"),
]


@pytest.mark.parametrize(("name", "language"), list(FLAWED))
def test_flawed_sample_finds_every_planted_issue(name, language):
    result = run_static_analysis((SAMPLES / name).read_text(), language)
    found = {i.rule_id for i in result.issues}
    assert FLAWED[(name, language)] <= found, f"missing: {FLAWED[(name, language)] - found}"
    assert found <= FLAWED[(name, language)], f"unexpected: {found - FLAWED[(name, language)]}"
    assert result.grade in {"D", "F"}
    assert all(i.line for i in result.issues), "every static finding should point at a line"


@pytest.mark.parametrize(("name", "language"), CLEAN)
def test_clean_sample_has_no_findings(name, language):
    result = run_static_analysis((SAMPLES / name).read_text(), language)
    assert result.issues == [], [(i.line, i.rule_id) for i in result.issues]
    assert (result.score, result.grade) == (100, "A")


def test_user_java_program_bugs_found_on_the_right_lines():
    code = (SAMPLES / "Employee.java").read_text()
    result = run_static_analysis(code, "java")
    by_rule = {(i.rule_id, i.line) for i in result.issues}
    assert ("CF001", 17) in by_rule  # return salary * 0.10   <- no semicolon
    assert ("CF002", 44) in by_rule  # totalbonus vs totalBonus
    assert ("CF003", 47) in by_rule  # e = null; e.name
    assert result.grade == "F"
    prints = [i for i in result.issues if i.rule_id == "JV002"]
    assert len(prints) == 1 and "6×" in prints[0].title  # repeated notes are grouped


def test_wrong_language_selection_is_explained():
    code = (SAMPLES / "Employee.java").read_text()
    result = run_static_analysis(code, "python")
    assert result.issues[0].title == "Not Python? This looks like Java"
    assert result.grade == "F"


def test_null_check_and_reassignment_are_not_flagged():
    code = """
class A {
    void f() {
        User u = null;
        if (u != null) {
            System.out.println(u.name);
        }
        User v = null;
        v = load();
        v.save();
    }
}
"""
    ids = {i.rule_id for i in run_static_analysis(code, "java").issues}
    assert "CF003" not in ids


def test_class_vs_instance_naming_is_not_a_typo():
    code = "const user = new User();\nconst map = new Map();\nuser.save(map);\n"
    assert "CF002" not in {i.rule_id for i in run_static_analysis(code, "javascript").issues}


@pytest.mark.parametrize("name", sorted(p.name for p in SAMPLES.iterdir() if p.suffix != ".rb"))
def test_language_detection(name):
    from app.analysis.detect import detect_language
    expected = {".py": "python", ".js": "javascript", ".ts": "typescript", ".java": "java",
                ".cpp": "cpp", ".c": "c", ".go": "go"}[Path(name).suffix]
    assert detect_language((SAMPLES / name).read_text()) == expected


def test_fixed_user_java_program_only_keeps_the_style_note():
    result = run_static_analysis((SAMPLES / "EmployeeFixed.java").read_text(), "java")
    assert [i.rule_id for i in result.issues] == ["JV002"]
    assert result.grade == "A"
