import json
from pathlib import Path

import requests


def load_config(path: Path) -> dict:
    """Read a JSON config file."""
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def fetch_status(url: str) -> int:
    response = requests.get(url, timeout=10)
    return response.status_code


def find_user(cur, user_id: int):
    cur.execute("SELECT id, name FROM users WHERE id = %s", (user_id,))
    return cur.fetchone()


def is_missing(value) -> bool:
    return value is None


password_hint = "Use at least 12 characters"
