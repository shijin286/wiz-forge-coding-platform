"""Show what the auto-fixer changes in every flawed sample, and confirm it never adds new issues.

    python scripts/check_autofix.py
"""

import difflib
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.analysis import run_static_analysis  # noqa: E402
from app.analysis.autofix import autofix  # noqa: E402

SAMPLES = {
    "sample.py": "python", "sample.js": "javascript", "sample.ts": "typescript", "Sample.java": "java",
    "sample.cpp": "cpp", "sample.c": "c", "sample.go": "go", "Employee.java": "java",
}

for name, lang in SAMPLES.items():
    code = (BACKEND / "tests" / "samples" / name).read_text()
    before = run_static_analysis(code, lang)
    fx = autofix(code, lang, before.issues)
    after = run_static_analysis(fx.code, lang)
    print(f"\n##### {name}: {before.score} {before.grade} -> {after.score} {after.grade}  ({len(fx.applied)} fixes)")
    for line in difflib.unified_diff(code.splitlines(), fx.code.splitlines(), lineterm="", n=0):
        if not line.startswith(("---", "+++", "@@")):
            print("   ", line)
    print("   still present:", [(i.line, i.rule_id) for i in after.issues])
    new = {i.rule_id for i in after.issues} - {i.rule_id for i in before.issues}
    if new:
        print("   !!! NEW ISSUES INTRODUCED:", new)
