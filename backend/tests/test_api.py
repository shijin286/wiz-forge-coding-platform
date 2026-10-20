from app import services
from app.ai import AIReview, AIReviewError

VULNERABLE = "import os\n\ndef run(cmd):\n    eval(cmd)\n    return os.getcwd()\n"


def test_register_login_me(client):
    r = client.post("/api/auth/register", json={"email": "A@x.com", "name": "A", "password": "password123"})
    assert r.status_code == 201
    assert client.post("/api/auth/register", json={"email": "a@x.com", "name": "A", "password": "password123"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "a@x.com", "password": "wrong-pass"}).status_code == 401
    token = client.post("/api/auth/login", json={"email": "a@x.com", "password": "password123"}).json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == "a@x.com"


def test_requires_auth(client):
    assert client.get("/api/reviews").status_code == 401
    assert client.get("/api/reviews", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_static_only_review(auth_client):
    r = auth_client.post("/api/reviews", json={"title": "eval", "language": "python", "code": VULNERABLE, "use_ai": False})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "completed" and body["ai_status"] == "skipped"
    assert any(f["rule_id"] == "PY003" for f in body["findings"])
    assert body["finding_counts"]["critical"] == 1


def test_ai_review_merges_findings(auth_client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pretend Claude is configured
    def fake_review(code, language, static_issues):
        assert any(i.rule_id == "PY003" for i in static_issues)
        return AIReview(summary="Risky.", strengths=["Short"], findings=[{
            "title": "Unvalidated input", "severity": "high", "category": "security", "line": 4,
            "explanation": "cmd comes from callers.", "suggestion": "Validate it.", "confidence": "high",
        }])
    monkeypatch.setattr(services, "review_with_claude", fake_review)

    r = auth_client.post("/api/reviews", json={"title": "t", "language": "python", "code": VULNERABLE})
    review_id = r.json()["id"]
    # TestClient runs background tasks before returning, so the AI pass is already done
    detail = auth_client.get(f"/api/reviews/{review_id}").json()
    assert detail["ai_status"] == "completed" and detail["status"] == "completed"
    assert detail["ai_summary"] == "Risky."
    ai = [f for f in detail["findings"] if f["source"] == "ai"]
    assert len(ai) == 1 and ai[0]["confidence"] == "high"
    assert detail["quality_score"] < r.json()["quality_score"]


def test_ai_failure_is_recorded(auth_client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    def failing(*_):
        raise AIReviewError("No Claude API credentials configured (set ANTHROPIC_API_KEY).")
    monkeypatch.setattr(services, "review_with_claude", failing)
    review_id = auth_client.post("/api/reviews", json={"language": "python", "code": "x = 1\n"}).json()["id"]
    detail = auth_client.get(f"/api/reviews/{review_id}").json()
    assert detail["status"] == "completed" and detail["ai_status"] == "failed"
    assert "ANTHROPIC_API_KEY" in detail["ai_error"]


def test_list_filter_stats_delete_and_ownership(auth_client, client):
    for title, lang in [("alpha", "python"), ("beta", "javascript"), ("alphabet", "javascript")]:
        auth_client.post("/api/reviews", json={"title": title, "language": lang, "code": "var a = 1;\n", "use_ai": False})

    assert auth_client.get("/api/reviews").json()["total"] == 3
    assert auth_client.get("/api/reviews", params={"search": "alpha"}).json()["total"] == 2
    assert auth_client.get("/api/reviews", params={"language": "javascript"}).json()["total"] == 2

    stats = auth_client.get("/api/stats").json()
    assert stats["total_reviews"] == 3 and len(stats["recent"]) == 3
    assert stats["by_language"] == {"python": 1, "javascript": 2}

    review_id = auth_client.get("/api/reviews").json()["items"][0]["id"]

    # another user cannot see or delete it
    other = client.post("/api/auth/register", json={"email": "b@x.com", "name": "B", "password": "password123"}).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get(f"/api/reviews/{review_id}", headers=headers).status_code == 404
    assert client.delete(f"/api/reviews/{review_id}", headers=headers).status_code == 404

    assert auth_client.delete(f"/api/reviews/{review_id}").status_code == 204
    assert auth_client.get("/api/reviews").json()["total"] == 2


def test_validation(auth_client):
    assert auth_client.post("/api/reviews", json={"language": "cobol", "code": "x"}).status_code == 422
    assert auth_client.post("/api/reviews", json={"language": "python", "code": ""}).status_code == 422
    big = "x = 1\n" * 20_000
    assert auth_client.post("/api/reviews", json={"language": "python", "code": big, "use_ai": False}).status_code == 413


def test_timestamps_are_utc_aware(auth_client):
    r = auth_client.post("/api/reviews", json={"language": "python", "code": "x = 1\n", "use_ai": False}).json()
    assert r["created_at"].endswith(("Z", "+00:00"))
    assert auth_client.get("/api/stats").json()["score_trend"][0]["created_at"].endswith(("Z", "+00:00"))


def test_detect_language_endpoint(auth_client):
    r = auth_client.post("/api/detect-language", json={"code": "public class A {\n  public static void main(String[] a) {\n    System.out.println(1);\n  }\n}\n"})
    assert r.status_code == 200 and r.json() == {"language": "java"}
    assert auth_client.post("/api/detect-language", json={"code": "hello"}).json() == {"language": None}


def test_ai_skipped_cleanly_without_credentials(auth_client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    r = auth_client.post("/api/reviews", json={"language": "python", "code": "x = 1\n", "use_ai": True}).json()
    assert r["status"] == "completed" and r["ai_status"] == "skipped" and r["ai_error"] is None
    assert auth_client.get("/api/health").json()["ai_configured"] is False


def test_review_includes_static_corrected_code(auth_client):
    code = "def f(user):\n    if user == None:\n        return 1\n"
    r = auth_client.post("/api/reviews", json={"language": "python", "code": code, "use_ai": False}).json()
    assert r["fixed_source"] == "static"
    assert "if user is None:" in r["fixed_code"]
    assert r["fixes_applied"][0]["rule_id"] == "PY004"
    assert r["fixes_remaining"] == [] and r["fixed_grade"] == "A"


def test_ai_corrected_code_replaces_static_fix(auth_client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    fixed = "import os\n\ndef run(cmd):\n    return os.getcwd()\n"
    monkeypatch.setattr(services, "review_with_claude", lambda *a: AIReview(
        summary="ok", strengths=[], findings=[], fixed_code=fixed, changes=["Removed the eval() call"]))
    review_id = auth_client.post("/api/reviews", json={"language": "python", "code": VULNERABLE}).json()["id"]
    detail = auth_client.get(f"/api/reviews/{review_id}").json()
    assert detail["fixed_source"] == "ai" and detail["fixed_code"] == fixed
    assert detail["fixes_applied"] == [{"line": None, "rule_id": "AI", "description": "Removed the eval() call"}]
    assert detail["fixed_score"] == 100 and detail["fixes_remaining"] == []
