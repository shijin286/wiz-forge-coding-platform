"""Import a single source file from a public GitHub URL.

Only github.com file links and raw.githubusercontent.com URLs are accepted, they are rewritten to
a fixed raw.githubusercontent.com address, and redirects are not followed, so this endpoint can't
be used to make the server fetch arbitrary or internal URLs (SSRF).
"""

import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..config import get_settings
from ..deps import get_current_user
from ..models import User
from ..ratelimit import import_limiter

router = APIRouter(prefix="/api/import", tags=["import"])

SEGMENT = r"[A-Za-z0-9_.-]+"
BLOB_URL = re.compile(rf"^https://github\.com/({SEGMENT})/({SEGMENT})/blob/([^\s?#]+)$")
RAW_URL = re.compile(rf"^https://raw\.githubusercontent\.com/({SEGMENT})/({SEGMENT})/([^\s?#]+)$")

EXTENSIONS = {
    "py": "python", "js": "javascript", "jsx": "javascript", "mjs": "javascript", "cjs": "javascript",
    "ts": "typescript", "tsx": "typescript", "java": "java", "c": "c", "h": "c",
    "cpp": "cpp", "cc": "cpp", "cxx": "cpp", "hpp": "cpp", "go": "go",
}


class GithubImportIn(BaseModel):
    url: str = Field(max_length=500)


class GithubImportOut(BaseModel):
    filename: str
    language: str
    code: str


def to_raw_url(url: str) -> str:
    url = url.strip()
    m = BLOB_URL.match(url) or RAW_URL.match(url)
    if not m:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "Use a GitHub file link like https://github.com/owner/repo/blob/main/path/file.py")
    owner, repo, rest = m.groups()
    if ".." in rest.split("/"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid file path")
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{rest}"


def fetch(url: str) -> httpx.Response:
    """Isolated so tests can replace the network call."""
    with httpx.Client(timeout=10.0, follow_redirects=False) as client:
        return client.get(url, headers={"User-Agent": "WizForge-AI"})


@router.post("/github", response_model=GithubImportOut)
def import_github(data: GithubImportIn, user: User = Depends(get_current_user)):
    import_limiter.hit(f"user:{user.id}")
    raw_url = to_raw_url(data.url)
    try:
        res = fetch(raw_url)
    except httpx.HTTPError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not reach GitHub. Try again.") from e

    if res.status_code == 404:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "File not found. Check the link, and note that only public repositories work.")
    if res.status_code != 200:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"GitHub returned an error ({res.status_code}).")

    limit = get_settings().max_code_chars
    if len(res.content) > limit * 4:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"File exceeds {limit:,} characters")
    try:
        code = res.content.decode("utf-8")
    except UnicodeDecodeError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "That file is not a text source file.") from e
    if len(code) > limit:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"File exceeds {limit:,} characters")

    filename = raw_url.rsplit("/", 1)[-1]
    language = EXTENSIONS.get(filename.rsplit(".", 1)[-1].lower(), "other") if "." in filename else "other"
    return GithubImportOut(filename=filename, language=language, code=code)
