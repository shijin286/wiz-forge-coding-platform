from dataclasses import dataclass, replace

from .base import SEVERITIES, Issue
from .flow_rules import analyze_flow
from .metrics import approximate_complexity, line_metrics, quality_score
from .pattern_rules import analyze_patterns
from .python_rules import analyze_python

SUPPORTED_LANGUAGES = {
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "java": "Java",
    "cpp": "C++",
    "c": "C",
    "go": "Go",
    "other": "Other",
}


@dataclass
class StaticResult:
    issues: list[Issue]
    metrics: dict
    score: int
    grade: str


def _collapse_repeated_notes(issues: list[Issue]) -> list[Issue]:
    """Low/info findings that repeat (console prints, 'var', long lines...) become one finding
    listing every line, so they don't bury the important results."""
    by_rule: dict[str, list[Issue]] = {}
    for i in issues:
        if i.severity in ("low", "info"):
            by_rule.setdefault(i.rule_id, []).append(i)
    out = []
    for i in issues:
        group = by_rule.get(i.rule_id)
        if not group or len(group) == 1:
            out.append(i)
        elif i is group[0]:
            lines = ", ".join(str(g.line) for g in group[1:])
            out.append(replace(i, title=f"{i.title} ({len(group)}×)",
                               message=f"{i.message} Also on lines {lines}."))
    return out


def run_static_analysis(code: str, language: str) -> StaticResult:
    """Deterministic analysis. Parses/pattern-matches only: submitted code is never executed."""
    issues: list[Issue] = []
    metrics = line_metrics(code, language)

    if language == "python":
        py_issues, facts = analyze_python(code)
        issues.extend(py_issues)
        metrics.update(facts)
    else:
        metrics.update(approximate_complexity(code, language))

    issues.extend(analyze_patterns(code, language))
    issues.extend(analyze_flow(code, language))

    # same rule on the same line is reported once
    seen: set[tuple] = set()
    unique = []
    for i in issues:
        key = (i.rule_id, i.line)
        if key not in seen:
            seen.add(key)
            unique.append(i)
    unique = _collapse_repeated_notes(unique)
    unique.sort(key=lambda i: (SEVERITIES.index(i.severity), i.line or 0))

    score, grade = quality_score(unique, metrics["lines_of_code"])
    if not metrics.get("parsed", True) or any(i.rule_id == "CF001" for i in unique):
        # code that doesn't parse/compile can't pass, whatever else was (not) found
        score, grade = min(score, 40), "F"
    return StaticResult(unique, metrics, score, grade)
