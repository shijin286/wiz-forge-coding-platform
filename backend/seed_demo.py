"""Create a local demo account with a few static-analysis reviews.

    python seed_demo.py

Local development only - the credentials below are public test values.
"""

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import User
from app.schemas import ReviewCreate
from app.security import hash_password
from app.services import create_review

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo-pass-2026"

SNIPPETS = [
    ("auth/session.py", "python", '''import pickle
import hashlib

SECRET_KEY = "super-secret-signing-key"


def hash_password(pw):
    return hashlib.md5(pw.encode()).hexdigest()


def load(blob):
    try:
        return pickle.loads(blob)
    except:
        pass
'''),
    ("utils/math_helpers.py", "python", '''def mean(values: list[float]) -> float:
    """Arithmetic mean of a non-empty list."""
    if not values:
        raise ValueError("values must not be empty")
    return sum(values) / len(values)
'''),
    ("web/comments.js", "javascript", '''var token = "abc";
function show(c) {
  document.getElementById("out").innerHTML = c.body;
}
try { load(); } catch (e) {}
'''),
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if user is None:
            user = User(email=DEMO_EMAIL, name="Demo User", password_hash=hash_password(DEMO_PASSWORD))
            db.add(user)
            db.commit()
            for title, language, code in SNIPPETS:
                create_review(db, user, ReviewCreate(title=title, language=language, code=code, use_ai=False))
            print(f"Created demo user {DEMO_EMAIL} with {len(SNIPPETS)} reviews.")
        else:
            print("Demo user already exists.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
