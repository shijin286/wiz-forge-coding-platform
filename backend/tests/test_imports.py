import httpx
import pytest

from app.routers import imports


class FakeResponse:
    def __init__(self, status_code: int, content: bytes = b""):
        self.status_code = status_code
        self.content = content


@pytest.fixture()
def fake_github(monkeypatch):
    calls = []

    def fake_fetch(url):
        calls.append(url)
        if url.endswith("missing.py"):
            return FakeResponse(404)
        if url.endswith("logo.png"):
            return FakeResponse(200, b"\x89PNG\r\n\x1a\n\xff\xfe")
        return FakeResponse(200, b"def hello():\n    return 'hi'\n")

    monkeypatch.setattr(imports, "fetch", fake_fetch)
    return calls


def test_blob_url_is_rewritten_to_raw(auth_client, fake_github):
    r = auth_client.post("/api/import/github",
                         json={"url": "https://github.com/octo/demo/blob/main/src/app.py"})
    assert r.status_code == 200
    assert r.json() == {"filename": "app.py", "language": "python", "code": "def hello():\n    return 'hi'\n"}
    assert fake_github == ["https://raw.githubusercontent.com/octo/demo/main/src/app.py"]


def test_raw_url_accepted(auth_client, fake_github):
    r = auth_client.post("/api/import/github",
                         json={"url": "https://raw.githubusercontent.com/octo/demo/main/Main.java"})
    assert r.status_code == 200 and r.json()["language"] == "java"


@pytest.mark.parametrize("url", [
    "http://github.com/octo/demo/blob/main/a.py",            # not https
    "https://evil.com/octo/demo/blob/main/a.py",             # other host
    "https://github.com.evil.com/octo/demo/blob/main/a.py",  # look-alike host
    "https://github.com/octo/demo/tree/main/src",            # a folder, not a file
    "https://127.0.0.1/octo/demo/blob/main/a.py",            # internal address
    "https://github.com/octo/demo/blob/main/../../etc/passwd",
    "file:///etc/passwd",
])
def test_unsafe_or_invalid_urls_rejected(auth_client, fake_github, url):
    assert auth_client.post("/api/import/github", json={"url": url}).status_code == 422
    assert fake_github == []  # nothing was fetched


def test_missing_file_and_binary_file(auth_client, fake_github):
    assert auth_client.post("/api/import/github", json={
        "url": "https://github.com/octo/demo/blob/main/missing.py"}).status_code == 404
    assert auth_client.post("/api/import/github", json={
        "url": "https://github.com/octo/demo/blob/main/logo.png"}).status_code == 422


def test_network_error(auth_client, monkeypatch):
    def boom(url):
        raise httpx.ConnectError("offline")
    monkeypatch.setattr(imports, "fetch", boom)
    r = auth_client.post("/api/import/github", json={"url": "https://github.com/octo/demo/blob/main/a.py"})
    assert r.status_code == 502


def test_requires_login(client):
    assert client.post("/api/import/github", json={"url": "https://github.com/o/r/blob/main/a.py"}).status_code == 401


SHA = "a" * 40
PR = {"title": "Add payment helpers", "head": {"sha": SHA, "repo": {"full_name": "forker/demo"}}}
FILES = [
    {"filename": "src/pay.py", "status": "modified"},
    {"filename": "src/old.py", "status": "removed"},
    {"filename": "README.md", "status": "modified"},
    {"filename": "web/app.js", "status": "added"},
]
CODE = {
    "src/pay.py": b"def charge(amount, items=[]):\n    eval(amount)\n    return items\n",
    "web/app.js": b"var total = 0;\n",
}


@pytest.fixture()
def fake_pr(monkeypatch):
    fetched = []

    def api(path):
        if path.endswith("/pulls/7"):
            return FakeJSON(200, PR)
        if path.endswith("/pulls/7/files?per_page=100"):
            return FakeJSON(200, FILES)
        if path.endswith("/pulls/8"):
            return FakeJSON(403, {})
        return FakeJSON(404, {})

    def raw(url):
        fetched.append(url)
        path = url.split(f"/{SHA}/", 1)[1]
        return FakeResponse(200, CODE[path]) if path in CODE else FakeResponse(404)

    monkeypatch.setattr(imports, "github_api", api)
    monkeypatch.setattr(imports, "fetch", raw)
    return fetched


class FakeJSON(FakeResponse):
    def __init__(self, status_code, data):
        super().__init__(status_code)
        self._data = data

    def json(self):
        return self._data


def test_pull_request_review(auth_client, fake_pr):
    r = auth_client.post("/api/import/github-pr", json={"url": "https://github.com/octo/demo/pull/7", "use_ai": False})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["title"] == "Add payment helpers" and body["number"] == 7 and body["repository"] == "octo/demo"
    files = {f["path"]: f for f in body["files"]}
    assert files["src/pay.py"]["review_id"] and files["src/pay.py"]["finding_counts"]["critical"] == 1
    assert files["web/app.js"]["review_id"] and files["web/app.js"]["grade"]
    assert files["src/old.py"]["skipped"] == "deleted in this pull request"
    assert files["README.md"]["skipped"] == "not a supported source file"
    # files are read from the PR's head commit, in the fork it came from
    assert fake_pr == [f"https://raw.githubusercontent.com/forker/demo/{SHA}/src/pay.py",
                       f"https://raw.githubusercontent.com/forker/demo/{SHA}/web/app.js"]
    # each reviewed file becomes a normal review in the history
    titles = {i["title"] for i in auth_client.get("/api/reviews").json()["items"]}
    assert titles == {"PR #7: src/pay.py", "PR #7: web/app.js"}


def test_pull_request_errors(auth_client, fake_pr):
    post = lambda url: auth_client.post("/api/import/github-pr", json={"url": url, "use_ai": False})
    assert post("https://github.com/octo/demo/pull/8").status_code == 429   # GitHub rate limit
    assert post("https://github.com/octo/demo/pull/9").status_code == 404   # no such PR
    assert post("https://github.com/octo/demo/issues/7").status_code == 422  # not a PR link
    assert post("https://evil.com/octo/demo/pull/7").status_code == 422
    assert fake_pr == []


def test_pull_request_file_limit(auth_client, monkeypatch, fake_pr):
    many = [{"filename": f"src/m{i}.py", "status": "added"} for i in range(imports.MAX_PR_FILES + 3)]
    monkeypatch.setattr(imports, "github_api",
                        lambda path: FakeJSON(200, many if path.endswith("per_page=100") else PR))
    monkeypatch.setattr(imports, "fetch", lambda url: FakeResponse(200, b"x = 1\n"))
    files = auth_client.post("/api/import/github-pr", json={"url": "https://github.com/o/r/pull/1", "use_ai": False}).json()["files"]
    assert sum(1 for f in files if f["review_id"]) == imports.MAX_PR_FILES
    assert sum(1 for f in files if f["skipped"]) == 3
