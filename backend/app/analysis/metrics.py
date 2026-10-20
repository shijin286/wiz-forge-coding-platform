import re

from .base import Issue

COMMENT_PREFIX = {"python": ("#",), "default": ("//", "/*", "*", "*/")}
BRANCH_KEYWORDS = re.compile(r"\b(if|for|while|case|catch|elif|except)\b|&&|\|\||\?(?!\.)")
# control-flow lines such as "if (x) {" look like definitions to the C-family patterns
_NOT_CONTROL = r"(?!\s*(if|else|for|while|switch|do|return|catch|try)\b)"
FUNCTION_DEF = {
    "javascript": re.compile(r"\bfunction\b|=>"),
    "typescript": re.compile(r"\bfunction\b|=>"),
    "java": re.compile(_NOT_CONTROL + r"^\s*(public|private|protected|static|\s)+[\w<>\[\],\s]+\s+\w+\s*\([^;]*\)\s*(throws [\w, ]+)?\s*\{"),
    "go": re.compile(r"^\s*func\b"),
    "c": re.compile(_NOT_CONTROL + r"^\s*[\w\*\s]+\s+\**\w+\s*\([^;]*\)\s*\{"),
    "cpp": re.compile(_NOT_CONTROL + r"^\s*[\w:<>\*&\s]+\s+[\*&]*[\w:]+\s*\([^;]*\)\s*(const)?\s*\{"),
}

SEVERITY_PENALTY = {"critical": 20, "high": 10, "medium": 4, "low": 1.5, "info": 0.25}


def line_metrics(code: str, language: str) -> dict:
    prefixes = COMMENT_PREFIX.get(language, COMMENT_PREFIX["default"])
    lines = code.splitlines()
    blank = sum(1 for l in lines if not l.strip())
    comments = sum(1 for l in lines if l.strip().startswith(prefixes))
    loc = len(lines) - blank - comments
    return {
        "total_lines": len(lines),
        "lines_of_code": loc,
        "comment_lines": comments,
        "blank_lines": blank,
        "comment_ratio": round(comments / max(loc + comments, 1), 2),
    }


def approximate_complexity(code: str, language: str) -> dict:
    """Rough per-file complexity for languages we only pattern-match."""
    fn_re = FUNCTION_DEF.get(language)
    functions = sum(1 for l in code.splitlines() if fn_re and fn_re.search(l)) if fn_re else 0
    branches = len(BRANCH_KEYWORDS.findall(code))
    per_fn = (branches / functions + 1) if functions else branches + 1
    return {"functions": functions, "avg_complexity": round(per_fn, 1), "max_complexity": None}


def quality_score(issues: list[Issue], loc: int) -> tuple[int, str]:
    """100 minus weighted penalties, softened for larger files so a big file isn't punished
    for having the same density of issues as a small one."""
    penalty = sum(SEVERITY_PENALTY.get(i.severity, 0) for i in issues)
    size_factor = max(1.0, (loc / 200) ** 0.5)
    score = max(0, min(100, round(100 - penalty / size_factor)))
    for threshold, grade in ((90, "A"), (80, "B"), (70, "C"), (55, "D")):
        if score >= threshold:
            return score, grade
    return score, "F"
