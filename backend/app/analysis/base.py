from dataclasses import asdict, dataclass

SEVERITIES = ("critical", "high", "medium", "low", "info")
CATEGORIES = ("bug", "security", "performance", "maintainability", "style")


@dataclass
class Issue:
    rule_id: str
    title: str
    severity: str
    category: str
    line: int | None
    message: str
    suggestion: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)
