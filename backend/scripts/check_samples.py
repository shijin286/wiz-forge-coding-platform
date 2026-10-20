"""Print the static-analysis report for every sample in tests/samples.

    python scripts/check_samples.py [sample.py ...]
"""

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.analysis import run_static_analysis  # noqa: E402

SAMPLES = {
    "sample.py": "python", "sample.js": "javascript", "sample.ts": "typescript", "Sample.java": "java",
    "sample.cpp": "cpp", "sample.c": "c", "sample.go": "go", "sample.rb": "other",
}

for name in sys.argv[1:] or SAMPLES:
    code = (BACKEND / "tests" / "samples" / name).read_text()
    r = run_static_analysis(code, SAMPLES[name])
    lines = code.splitlines()
    m = r.metrics
    print(f"\n=== {name} ({SAMPLES[name]}) score={r.score} grade={r.grade} "
          f"loc={m['lines_of_code']} functions={m['functions']} avg_cc={m['avg_complexity']}")
    for i in r.issues:
        src = lines[i.line - 1].strip()[:58] if i.line else ""
        print(f"  L{i.line:<3} {i.severity:<8} {i.rule_id:<6} {i.title:<36} | {src}")
