"""Import a single source file from a public GitHub URL.

Only github.com file links and raw.githubusercontent.com URLs are accepted, they are rewritten to
a fixed raw.githubusercontent.com address, and redirects are not followed, so this endpoint can't
be used to make the server fetch arbitrary or internal URLs (SSRF).
"""

import re
from urllib.parse import quote

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..ratelimit import import_limiter
from ..schemas import ReviewCreate
from ..services import create_review, finding_counts, run_ai_review

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


PR_URL = re.compile(rf"^https://github\.com/({SEGMENT})/({SEGMENT})/pull/(\d+)(?:/[a-z]*)?/?$")
MAX_PR_FILES = 20


class PullRequestIn(BaseModel):
    url: str = Field(max_length=500)
    use_ai: bool = True


class PullRequestFile(BaseModel):
    path: str
    review_id: int | None = None
    quality_score: int | None = None
    grade: str | None = None
    finding_counts: dict[str, int] = {}
    skipped: str | None = None  # reason the file was not reviewed


class PullRequestOut(BaseModel):
    title: str
    number: int
    repository: str
    files: list[PullRequestFile]


def github_api(path: str) -> httpx.Response:
    """GET from the GitHub REST API. Isolated so tests can replace the network call."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "WizForge-AI",
               "X-GitHub-Api-Version": "2022-11-28"}
    token = get_settings().github_token
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with httpx.Client(base_url="https://api.github.com", timeout=10.0, follow_redirects=False) as client:
        return client.get(path, headers=headers)


def _api_json(path: str):
    try:
        res = github_api(path)
    except httpx.HTTPError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not reach GitHub. Try again.") from e
    if res.status_code == 404:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pull request not found. Only public repositories work.")
    if res.status_code in (403, 429):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "GitHub's API rate limit was reached. Try again later, or set GITHUB_TOKEN.")
    if res.status_code != 200:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"GitHub returned an error ({res.status_code}).")
    return res.json()


@router.post("/github-pr", response_model=PullRequestOut)
def review_pull_request(data: PullRequestIn, background: BackgroundTasks, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    """Review every changed source file of a public GitHub pull request at its latest commit."""
    import_limiter.hit(f"user:{user.id}")
    m = PR_URL.match(data.url.strip())
    if not m:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "Use a pull request link like https://github.com/owner/repo/pull/123")
    owner, repo, number = m.group(1), m.group(2), int(m.group(3))

    pr = _api_json(f"/repos/{owner}/{repo}/pulls/{number}")
    head_repo = (pr.get("head") or {}).get("repo") or {}
    head_name, head_sha = head_repo.get("full_name"), (pr.get("head") or {}).get("sha")
    if not head_name or not head_sha or not re.fullmatch(rf"{SEGMENT}/{SEGMENT}", head_name) \
            or not re.fullmatch(r"[0-9a-f]{40}", head_sha):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The pull request's source branch is no longer available.")

    changed = _api_json(f"/repos/{owner}/{repo}/pulls/{number}/files?per_page=100")
    results: list[PullRequestFile] = []
    reviewed = 0
    for f in changed:
        path = f.get("filename", "")
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if f.get("status") == "removed":
            results.append(PullRequestFile(path=path, skipped="deleted in this pull request"))
            continue
        if ext not in EXTENSIONS:
            results.append(PullRequestFile(path=path, skipped="not a supported source file"))
            continue
        if reviewed >= MAX_PR_FILES:
            results.append(PullRequestFile(path=path, skipped=f"only the first {MAX_PR_FILES} source files are reviewed"))
            continue
        raw = f"https://raw.githubusercontent.com/{head_name}/{head_sha}/{quote(path)}"
        try:
            res = fetch(raw)
            code = res.content.decode("utf-8") if res.status_code == 200 else None
        except (httpx.HTTPError, UnicodeDecodeError):
            code = None
        if not code or not code.strip():
            results.append(PullRequestFile(path=path, skipped="could not download the file"))
            continue
        if len(code) > get_settings().max_code_chars:
            results.append(PullRequestFile(path=path, skipped="file is too large"))
            continue

        review, ai_scheduled = create_review(db, user, ReviewCreate(
            title=f"PR #{number}: {path}"[:200], language=EXTENSIONS[ext], code=code, use_ai=data.use_ai))
        if ai_scheduled:
            background.add_task(run_ai_review, review.id)
        reviewed += 1
        results.append(PullRequestFile(path=path, review_id=review.id, quality_score=review.quality_score,
                                       grade=review.grade, finding_counts=finding_counts(review)))

    return PullRequestOut(title=pr.get("title", f"Pull request #{number}"), number=number,
                          repository=f"{owner}/{repo}", files=results)


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
