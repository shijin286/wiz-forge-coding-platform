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
