import logging
from collections import Counter

from sqlalchemy.orm import Session

from .ai import AIReviewError, review_with_claude
from .analysis import run_static_analysis
from .analysis.autofix import autofix
from .analysis.base import Issue
from .analysis.metrics import quality_score
from .config import get_settings
from .database import SessionLocal
from .models import Finding, Review, User, utcnow
from .schemas import ReviewCreate, ReviewSummary

log = logging.getLogger(__name__)


def finding_counts(review: Review) -> dict[str, int]:
    return dict(Counter(f.severity for f in review.findings))


def to_summary(review: Review) -> ReviewSummary:
    s = ReviewSummary.model_validate(review)
    s.finding_counts = finding_counts(review)
    return s


def set_corrected_code(review: Review, fixed_code: str, source: str, applied: list[dict]) -> None:
    """Store a corrected version of the code. What is still wrong is measured by re-analysing the
    fixed code, so the 'remaining' list is always accurate whoever produced the fix."""
    after = run_static_analysis(fixed_code, review.language)
    review.fixed_code = fixed_code
    review.fixed_source = source
    review.fixes_applied = applied
    review.fixes_remaining = [{"line": i.line, "rule_id": i.rule_id, "title": i.title} for i in after.issues]
    review.fixed_score, review.fixed_grade = after.score, after.grade


def create_review(db: Session, user: User, data: ReviewCreate) -> tuple[Review, bool]:
    """Runs static analysis synchronously and stores the review.
    Returns (review, ai_scheduled) - the caller schedules run_ai_review when ai_scheduled is True."""
    result = run_static_analysis(data.code, data.language)
    # without credentials the AI pass is skipped up front instead of failing in the background
    ai_wanted = data.use_ai and get_settings().ai_configured

    review = Review(
        user_id=user.id,
        title=data.title.strip() or "Untitled review",
        language=data.language,
        code=data.code,
        status="processing" if ai_wanted else "completed",
        ai_status="pending" if ai_wanted else "skipped",
        quality_score=result.score,
        grade=result.grade,
        metrics=result.metrics,
        completed_at=None if ai_wanted else utcnow(),
    )
    review.findings = [
        Finding(source="static", **i.to_dict()) for i in result.issues
    ]
    fix = autofix(data.code, data.language, result.issues)
    set_corrected_code(review, fix.code, "static", fix.applied)
    db.add(review)
    db.commit()
    db.refresh(review)
    return review, ai_wanted


def run_ai_review(review_id: int) -> None:
    """Background task: adds AI findings to an existing review. Uses its own DB session."""
    db = SessionLocal()
    try:
        review = db.get(Review, review_id)
        if review is None:
            return
        static_findings = [f for f in review.findings if f.source == "static"]
        static_issues = [
            Issue(f.rule_id, f.title, f.severity, f.category, f.line, f.message, f.suggestion)
            for f in static_findings
        ]
        try:
            ai = review_with_claude(review.code, review.language, static_issues)
        except AIReviewError as e:
            review.ai_status, review.ai_error = "failed", str(e)
        except Exception:  # never leave a review stuck in "processing"
            log.exception("AI review %s crashed", review_id)
            review.ai_status, review.ai_error = "failed", "Unexpected error during AI review."
        else:
            for n, f in enumerate(ai.findings, start=1):
                review.findings.append(Finding(
                    source="ai", rule_id=f"AI{n:03d}", title=f["title"][:200], severity=f["severity"],
                    category=f["category"], line=f["line"], message=f["explanation"],
                    suggestion=f.get("suggestion"), confidence=f["confidence"],
                ))
            review.ai_status, review.ai_summary, review.ai_strengths = "completed", ai.summary, ai.strengths
            # low-confidence AI findings are shown but don't affect the score
            scored = static_issues + [
                Issue(f"AI{n}", f["title"], f["severity"], f["category"], f["line"], "")
                for n, f in enumerate(ai.findings) if f["confidence"] != "low"
            ]
            review.quality_score, review.grade = quality_score(scored, review.metrics.get("lines_of_code", 0))
            if ai.fixed_code and ai.fixed_code.strip() != review.code.strip():
                applied = [{"line": None, "rule_id": "AI", "description": c} for c in ai.changes]
                set_corrected_code(review, ai.fixed_code, "ai", applied)
        review.status = "completed"
        review.completed_at = utcnow()
        db.commit()
    finally:
        db.close()


def backfill_corrected_code(review: Review) -> None:
    result = run_static_analysis(review.code, review.language)
    fix = autofix(review.code, review.language, result.issues)
    set_corrected_code(review, fix.code, "static", fix.applied)
