from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

from .analysis import SUPPORTED_LANGUAGES

Language = Literal[tuple(SUPPORTED_LANGUAGES)]  # type: ignore[valid-type]

# SQLite drops tzinfo; all stored times are UTC, so make that explicit in the API output.
UTCDatetime = Annotated[datetime, AfterValidator(lambda d: d if d.tzinfo else d.replace(tzinfo=timezone.utc))]


class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: str = Field(max_length=255)  # only matched against existing accounts, so no format check
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str
    created_at: UTCDatetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ReviewCreate(BaseModel):
    title: str = Field(default="Untitled review", max_length=200)
    language: Language
    code: str = Field(min_length=1)
    use_ai: bool = True


class DetectIn(BaseModel):
    code: str


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source: str
    rule_id: str
    title: str
    severity: str
    category: str
    line: int | None
    message: str
    suggestion: str | None
    confidence: str | None


class ReviewSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    language: str
    status: str
    ai_status: str
    quality_score: int
    grade: str
    created_at: UTCDatetime
    finding_counts: dict[str, int] = {}


class ReviewDetail(ReviewSummary):
    code: str
    ai_summary: str | None
    ai_strengths: list[str] | None
    ai_error: str | None
    metrics: dict
    completed_at: UTCDatetime | None
    findings: list[FindingOut]
    fixed_code: str | None = None
    fixed_source: str | None = None
    fixes_applied: list[dict] | None = None
    fixes_remaining: list[dict] | None = None
    fixed_score: int | None = None
    fixed_grade: str | None = None


class ReviewPage(BaseModel):
    items: list[ReviewSummary]
    total: int


class TrendPoint(BaseModel):
    id: int
    title: str
    score: int
    created_at: UTCDatetime


class StatsOut(BaseModel):
    total_reviews: int
    average_score: float | None
    total_findings: int
    by_severity: dict[str, int]
    by_category: dict[str, int]
    by_language: dict[str, int]
    score_trend: list[TrendPoint]
    recent: list[ReviewSummary]
