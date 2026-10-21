"""Capture the README screenshots from a locally running app.

Start the backend (port 8000) and frontend first, then:

    python scripts/take_screenshots.py [--frontend http://localhost:5173]

Uses Playwright with the locally installed Microsoft Edge (no browser download) and a dedicated
local showcase account, so your own reviews never appear in the images.
Local development only: the credentials below are public test values.
"""

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BACKEND = Path(__file__).resolve().parents[1]
OUT = BACKEND.parent / "docs" / "screenshots"
API = "http://localhost:8000/api"

SHOWCASE_EMAIL = "showcase@example.com"
SHOWCASE_PASSWORD = "showcase-pass-2026"

REVIEWS = [  # (title, language, sample file) - oldest first, so the user's program ends up on top
    ("auth/login.c", "c", "sample.c"),
    ("api/handlers.go", "go", "sample.go"),
    ("server/routes.js", "javascript", "sample.js"),
    ("utils/math_helpers.py", "python", "clean.py"),
    ("orders/service.py", "python", "sample.py"),
    ("payroll/Employee.java", "java", "Employee.java"),
]


def call(method: str, path: str, body: dict | None = None, token: str | None = None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body else None)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read() or b"null")


def showcase_token() -> str:
    try:
        return call("POST", "/auth/register", {"email": SHOWCASE_EMAIL, "name": "Arjun Kumar",
                                                "password": SHOWCASE_PASSWORD})["access_token"]
    except urllib.error.HTTPError as e:
        if e.code != 409:
            raise
        return call("POST", "/auth/login", {"email": SHOWCASE_EMAIL, "password": SHOWCASE_PASSWORD})["access_token"]


def ensure_reviews(token: str) -> int:
    """Create the showcase reviews once; returns the id of the Employee.java review."""
    existing = {r["title"]: r["id"] for r in call("GET", "/reviews?limit=100", token=token)["items"]}
    for title, language, sample in REVIEWS:
        if title not in existing:
            code = (BACKEND / "tests" / "samples" / sample).read_text()
            existing[title] = call("POST", "/reviews", {"title": title, "language": language, "code": code,
                                                        "use_ai": False}, token)["id"]
    return existing["payroll/Employee.java"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend", default="http://localhost:5174")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    token = showcase_token()
    review_id = ensure_reviews(token)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme="dark")
        page = ctx.new_page()

        def shot(name: str, **kwargs) -> None:
            page.wait_for_timeout(800)
            page.screenshot(path=str(OUT / f"{name}.png"), **kwargs)
            print("saved", name)

        page.goto(f"{args.frontend}/login")
        page.wait_for_selector("text=Welcome back")
        shot("login")

        page.evaluate("t => localStorage.setItem('wizforge.token', t)", token)

        page.goto(f"{args.frontend}/")
        page.wait_for_selector("text=Findings by severity")
        shot("dashboard")

        page.goto(f"{args.frontend}/review/new")
        page.wait_for_selector(".monaco-editor")
        page.select_option("select", "java")
        page.click("text=Sample")
        page.wait_for_timeout(1200)
        shot("new-review")

        page.goto(f"{args.frontend}/review/{review_id}")
        page.wait_for_selector(".monaco-editor")
        page.click("text=Missing semicolon")  # expand a finding and jump to its line
        shot("review")

        section = page.locator("section", has_text="Corrected code")
        section.scroll_into_view_if_needed()
        page.wait_for_selector(".monaco-diff-editor")
        page.wait_for_timeout(1500)
        section.screenshot(path=str(OUT / "corrected-code.png"))
        print("saved corrected-code")

        page.goto(f"{args.frontend}/history")
        page.wait_for_selector("text=Review history")
        shot("history")

        browser.close()


if __name__ == "__main__":
    main()
