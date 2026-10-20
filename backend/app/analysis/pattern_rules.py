"""Line-based pattern checks for languages without an in-process parser (JS/TS, Java, C/C++, Go...)
plus language-independent checks such as hard-coded secrets."""

import re
from dataclasses import dataclass

from .base import Issue


@dataclass(frozen=True)
class Rule:
    rule_id: str
    pattern: re.Pattern
    title: str
    severity: str
    category: str
    message: str
    suggestion: str


def _r(rule_id, regex, title, severity, category, message, suggestion, flags=0) -> Rule:
    return Rule(rule_id, re.compile(regex, flags), title, severity, category, message, suggestion)


JS_RULES = [
    _r("JS001", r"(?<![\w.])eval\s*\(", "Use of eval()", "critical", "security",
       "eval() executes arbitrary strings as code.", "Use JSON.parse for data or a dispatch table for logic."),
    _r("JS002", r"(?<![=!<>])(==|!=)(?!=)(?!\s*(null|undefined)\b)", "Loose equality", "low", "bug",
       "== and != coerce types ('0' == 0 is true), a common source of subtle bugs.",
       "Use === and !==."),
    _r("JS003", r"^\s*var\s+\w", "'var' declaration", "low", "style",
       "var is function-scoped and hoisted, which makes accidental reuse easy.", "Use const, or let when reassigning."),
    _r("JS004", r"\.(innerHTML|outerHTML)\s*\+?=", "Possible XSS via innerHTML", "high", "security",
       "Assigning to innerHTML parses the value as HTML; untrusted input can inject scripts.",
       "Use textContent, or sanitise with a library such as DOMPurify."),
    _r("JS005", r"\bconsole\.(log|debug)\s*\(", "Leftover console logging", "info", "style",
       "Debug logging left in code adds noise and may leak data.", "Remove it or use a configurable logger."),
    _r("JS006", r"\bdocument\.write\s*\(", "Use of document.write", "medium", "security",
       "document.write can inject unescaped HTML and blocks parsing.", "Build DOM nodes or use textContent."),
    _r("JS007", r"\bnew\s+Function\s*\(", "Use of new Function()", "high", "security",
       "new Function() compiles strings into code, like eval.", "Avoid building code from strings."),
    _r("JS008", r"\bset(Timeout|Interval)\s*\(\s*['\"`]", "String passed to setTimeout/setInterval", "medium",
       "security", "A string argument is evaluated like eval().", "Pass a function instead."),
    _r("JS009", r"catch\s*(\(\s*\w*\s*\))?\s*\{\s*\}", "Empty catch block", "medium", "bug",
       "Errors are swallowed silently.", "Log or handle the error, or rethrow it."),
    _r("JS010", r"\b(exec|execSync)\s*\(\s*`[^`]*\$\{", "Shell command built from template", "high", "security",
       "Interpolating values into a shell command allows command injection.",
       "Use execFile/spawn with an argument array."),
    _r("JS011", r"\b(query|execute)\s*\(\s*`[^`]*\$\{", "Possible SQL injection", "critical", "security",
       "SQL built with template literals can be altered by user input.",
       "Use parameterised queries / placeholders."),
]

TS_RULES = JS_RULES + [
    _r("TS001", r"(:\s*any\b|\bas\s+any\b|<any>)", "Use of 'any' type", "low", "maintainability",
       "'any' switches off type checking for this value, so type errors pass silently.",
       "Use a specific type, a generic, or 'unknown' with a type guard."),
    _r("TS002", r"//\s*@ts-(ignore|nocheck)\b", "TypeScript check suppressed", "medium", "maintainability",
       "@ts-ignore / @ts-nocheck hides type errors instead of fixing them.",
       "Fix the underlying type error, or use @ts-expect-error with a comment explaining why."),
]

JAVA_RULES = [
    _r("JV001", r"catch\s*\([^)]*\)\s*\{\s*\}", "Empty catch block", "medium", "bug",
       "The exception is swallowed silently.", "Log it, handle it, or rethrow it."),
    _r("JV002", r"System\.(out|err)\.print", "Console printing", "info", "style",
       "System.out/err printing in application code is hard to control.", "Use a logging framework (SLF4J)."),
    _r("JV003", r"\.(executeQuery|executeUpdate|execute)\s*\(\s*\"[^\"]*\"\s*\+", "Possible SQL injection",
       "critical", "security", "SQL is concatenated with values.", "Use PreparedStatement with ? placeholders."),
    _r("JV004", r"\"\s*==\s*\w|\w\s*==\s*\"", "String compared with ==", "high", "bug",
       "== compares object references, not string contents.", "Use .equals(...)."),
    _r("JV005", r"Runtime\.getRuntime\(\)\.exec\(", "Runtime.exec usage", "medium", "security",
       "Running OS commands with user input can allow command injection.",
       "Use ProcessBuilder with a fixed argument list and validate input."),
]

C_RULES = [
    _r("CC001", r"\b(gets|strcpy|strcat|sprintf)\s*\(", "Unsafe C string function", "high", "security",
       "This function does no bounds checking and can overflow buffers.",
       "Use fgets, strncpy/strlcpy, snprintf, or std::string."),
    _r("CC002", r"\bsystem\s*\(", "Use of system()", "medium", "security",
       "system() runs a shell; interpolated input can inject commands.", "Use execv-family calls with fixed args."),
    _r("CC004", r"\b(printf|syslog)\s*\(\s*[A-Za-z_]\w*\s*\)|\bfprintf\s*\(\s*\w+\s*,\s*[A-Za-z_]\w*\s*\)",
       "Format string vulnerability", "high", "security",
       "A variable is used as the format string. If it contains %s/%n from user input it can leak or "
       "corrupt memory.", 'Pass a literal format: printf("%s", line).'),
]

CPP_RULES = C_RULES + [
    _r("CC003", r"using\s+namespace\s+std\s*;", "'using namespace std'", "low", "style",
       "Pulls the whole std namespace into scope and risks name clashes.", "Qualify names, e.g. std::vector."),
    _r("CC005", r"=\s*new\s+[\w:<>]+\s*[\[(]", "Manual memory allocation with new", "medium", "bug",
       "Raw new requires a matching delete on every path; early returns and exceptions leak memory.",
       "Use std::vector, std::make_unique or std::make_shared instead of raw new."),
]

GO_RULES = [
    _r("GO001", r"(^|[\s,(])_\s*(,\s*\w+\s*)?:?=\s*[\w.]+\(|\b\w+\s*,\s*_\s*:?=\s*[\w.]+\(", "Ignored error",
       "medium", "bug",
       "An error return value is discarded with _, so failures go unnoticed.",
       "Capture the error and handle it: if err != nil { return err }."),
    _r("GO002", r"\bfmt\.Sprintf\([^)]*(SELECT|INSERT|UPDATE|DELETE)", "Possible SQL injection", "critical",
       "security", "SQL is built with fmt.Sprintf.", "Use db.Query with ? / $1 placeholders.", re.I),
    _r("GO003", r"exec\.Command\(\s*\"(sh|bash|cmd)\"\s*,\s*\"(-c|/c)\"", "Shell command injection risk", "high",
       "security", "Running commands through a shell lets interpolated input inject extra commands.",
       'Call the program directly with separate arguments: exec.Command("ping", host).'),
]

SECRET_RULES = [
    # NAME = "value", NAME: Type = "value", "name": "value" and C's #define NAME "value".
    # Names like passwordLabel / tokenHeader are UI text, and the value must look like a secret
    # (contain a digit or symbol, or be long), so "Password" or "Authorization" are not flagged.
    _r("SEC001", r"(?i)\b\w*(password|passwd|pwd|secret|api[_-]?key|token|private[_-]?key)\w*"
                 r"(?<!label)(?<!header)(?<!hint)(?<!field)(?<!placeholder)(?<!prompt)(?<!name)(?<!url)"
                 r"(?<!path)(?<!type)(?<!message)['\"]?"
                 r"(\s*:\s*[\w\[\]<>|. ]+?)?(\s*[:=]\s*|\s+)"
                 r"['\"](?=[^'\"\s]*[\d\-_@!#$%^&*+/=.]|[^'\"\s]{20})[^'\"\s]{6,}['\"]",
       "Hard-coded secret", "critical", "security",
       "A credential appears to be written directly in source code, where it ends up in version control.",
       "Load it from an environment variable or a secrets manager, and rotate the exposed value."),
    _r("SEC002", r"\bAKIA[0-9A-Z]{16}\b", "AWS access key ID", "critical", "security",
       "This looks like an AWS access key ID.", "Revoke the key and load credentials from the environment."),
    _r("SEC003", r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", "Embedded private key", "critical",
       "security", "A private key is embedded in the source.", "Remove it, rotate it, and load it from a secure store."),
    _r("SEC004", r"\b(sk-ant-[A-Za-z0-9_-]{10,}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|xox[bp]-[A-Za-z0-9-]{10,})",
       "API token in source", "critical", "security",
       "This matches the format of a provider API token.", "Revoke it and load tokens from the environment."),
]

GENERIC_RULES = [
    _r("GEN001", r"(?i)(#|//|/\*|\*)\s*(TODO|FIXME|HACK|XXX)\b", "Unresolved TODO/FIXME", "info", "maintainability",
       "A TODO-style marker indicates unfinished work.", "Resolve it or track it in an issue."),
]

LANGUAGE_RULES = {
    "javascript": JS_RULES,
    "typescript": TS_RULES,
    "java": JAVA_RULES,
    "c": C_RULES,
    "cpp": CPP_RULES,
    "go": GO_RULES,
}

MAX_LINE_LENGTH = 120


# rules that must see what is inside string literals (SQL text, shell commands, template literals)
READS_STRINGS = {"JS010", "JS011", "GO002", "GO003"}


def analyze_patterns(code: str, language: str) -> list[Issue]:
    # local import: flow_rules owns the tokenizer-ish blanking helper
    from .flow_rules import blank_strings_and_comments

    issues: list[Issue] = []
    lang_rules = LANGUAGE_RULES.get(language, [])
    raw_lines = code.splitlines()
    # comments and string contents are blanked so that text like "never call eval()" in a
    # comment or a string is not reported as code
    code_lines = blank_strings_and_comments(code).splitlines()
    string_lines = blank_strings_and_comments(code, keep_strings=True).splitlines()
    long_lines = 0

    for lineno, raw in enumerate(raw_lines, start=1):
        # secrets and TODOs are checked on the raw line (they often live in strings and comments)
        for rule in SECRET_RULES + GENERIC_RULES:
            if rule.pattern.search(raw):
                issues.append(Issue(rule.rule_id, rule.title, rule.severity, rule.category, lineno,
                                    rule.message, rule.suggestion))
        for rule in lang_rules:
            text = (string_lines if rule.rule_id in READS_STRINGS else code_lines)[lineno - 1]
            if rule.pattern.search(text):
                issues.append(Issue(rule.rule_id, rule.title, rule.severity, rule.category, lineno,
                                    rule.message, rule.suggestion))
        if len(raw) > MAX_LINE_LENGTH:
            long_lines += 1
            if long_lines <= 3:  # avoid flooding the report
                issues.append(Issue("GEN002", "Line too long", "info", "style", lineno,
                                    f"Line is {len(raw)} characters (limit {MAX_LINE_LENGTH}).",
                                    "Break the expression across lines."))
    return issues
