import os
import sys
from pathlib import Path

# Tests always use a throwaway SQLite database, never the dev PostgreSQL one.
_DB = Path(__file__).parent / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB.as_posix()}"
os.environ["ANTHROPIC_API_KEY"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_client(client):
    r = client.post("/api/auth/register", json={"email": "dev@example.com", "name": "Dev", "password": "password123"})
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return client


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    _DB.unlink(missing_ok=True)
