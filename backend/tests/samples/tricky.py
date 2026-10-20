"""Helpers. Never call eval(user_input) or pickle.loads(untrusted)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

SQL_EXAMPLE = "SELECT * FROM t WHERE id = %s"  # passed as a parameter, not formatted


@dataclass
class Cart:
    items: list[str] = field(default_factory=list)

    def add(self, item: str) -> None:
        self.items.append(item)


def safe_div(a: float, b: float) -> float | None:
    try:
        return a / b
    except ZeroDivisionError:
        log.warning("division by zero")
        return None


def query(cur, user_id: int):
    cur.execute(SQL_EXAMPLE, (user_id,))
    return cur.fetchall()


def describe(value) -> str:
    if value is None:
        return "nothing"
    return f"value={value!r}"
