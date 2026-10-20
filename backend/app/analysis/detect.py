"""Best-effort language detection from source text, used to catch a wrong language selection."""

import re

SIGNALS: dict[str, list[str]] = {
    "python": [r"^\s*def \w+\(.*\)\s*(->.*)?:\s*$", r"^\s*(from \w[\w.]* )?import \w[\w.]*(\s+as \w+)?\s*$",
               r"^\s*elif\b", r"\bself\.\w+", r"^\s*print\(", r"^\s*class \w+(\(.*\))?:\s*$", r"\bNone\b"],
    "java": [r"\bpublic\s+(static\s+)?(class|void|final)\b", r"\bSystem\.(out|err)\.", r"^\s*import java\.",
             r"\bString\[\]", r"\bnew \w+<.*>\(", r"\bprivate\s+\w+", r"@Override"],
    "cpp": [r"#include\s*<(iostream|vector|string|memory|map)>", r"\bstd::", r"\bcout\s*<<", r"using namespace std",
            r"\btemplate\s*<", r"\bnullptr\b"],
    "c": [r"#include\s*<(stdio|stdlib|string|unistd)\.h>", r"\bprintf\s*\(", r"\bmalloc\s*\(",
          r"\bint main\s*\(\s*(void)?\s*\)", r"\bscanf\s*\("],
    "go": [r"^package \w+", r"^\s*func\b", r"\w+\s*:=", r"\bfmt\.\w+\(", r"\berr != nil\b"],
    "typescript": [r"\binterface \w+\s*\{", r":\s*(string|number|boolean|void|unknown)\b", r"\bexport type\b",
                   r"\bas \w+", r"\bimplements\b", r"\breadonly\b"],
    "javascript": [r"^\s*(const|let|var) \w+\s*=", r"=>", r"\brequire\(", r"\bconsole\.log\(", r"\bdocument\.",
                   r"^\s*function \w+\(", r"\bmodule\.exports\b"],
}
_COMPILED = {lang: [re.compile(p, re.M) for p in pats] for lang, pats in SIGNALS.items()}


def detect_language(code: str) -> str | None:
    scores = {lang: sum(1 for p in pats if p.search(code)) for lang, pats in _COMPILED.items()}
    # C++ and TypeScript are supersets of C and JavaScript signals; prefer the more specific one
    if scores["cpp"]:
        scores["c"] = max(0, scores["c"] - 1)
    if scores["typescript"] >= 2:
        scores["javascript"] = max(0, scores["javascript"] - 1)
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else None
