from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    reviews: Mapped[list["Review"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    language: Mapped[str] = mapped_column(String(32))
    code: Mapped[str] = mapped_column(Text)

    # status of the whole review; ai_status tracks the optional AI pass separately
    status: Mapped[str] = mapped_column(String(20), default="completed")
    ai_status: Mapped[str] = mapped_column(String(20), default="skipped")  # skipped|pending|completed|failed
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_strengths: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    quality_score: Mapped[int] = mapped_column(Integer, default=100)
    grade: Mapped[str] = mapped_column(String(2), default="A")
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)

    # corrected version of the code: deterministic auto-fixes, replaced by the AI's version when available
    fixed_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    fixed_source: Mapped[str | None] = mapped_column(String(10), nullable=True)  # static | ai
    fixes_applied: Mapped[list | None] = mapped_column(JSON, nullable=True)
    fixes_remaining: Mapped[list | None] = mapped_column(JSON, nullable=True)
    fixed_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fixed_grade: Mapped[str | None] = mapped_column(String(2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="reviews")
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="review", cascade="all, delete-orphan", order_by="Finding.id"
    )


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(10))  # static | ai
    rule_id: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(200))
    severity: Mapped[str] = mapped_column(String(10))  # critical|high|medium|low|info
    category: Mapped[str] = mapped_column(String(20))  # bug|security|performance|maintainability|style
    line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str] = mapped_column(Text)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(10), nullable=True)  # AI only: low|medium|high

    review: Mapped[Review] = relationship(back_populates="findings")
