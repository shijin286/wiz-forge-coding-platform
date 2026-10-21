import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..analysis import SUPPORTED_LANGUAGES
from ..ai import AIReviewError, generate_tests_with_claude
from ..analysis.detect import detect_language
from ..analysis.testgen import generate_test_skeleton
from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Review, User
from ..ratelimit import review_limiter
from ..report import build_report
from ..schemas import DetectIn, ReviewCreate, ReviewDetail, ReviewPage, TestsIn, TestsOut
from ..services import backfill_corrected_code, create_review, finding_counts, run_ai_review, to_summary

router = APIRouter(prefix="/api", tags=["reviews"])


def _get_owned(db: Session, user: User, review_id: int) -> Review:
    review = db.scalar(
        select(Review).options(selectinload(Review.findings))
        .where(Review.id == review_id, Review.user_id == user.id)
    )
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review not found")
    return review


def _detail(review: Review) -> ReviewDetail:
    d = ReviewDetail.model_validate(review)
    d.finding_counts = finding_counts(review)
    return d


@router.get("/languages")
def languages():
    return [{"id": k, "label": v} for k, v in SUPPORTED_LANGUAGES.items()]


@router.post("/detect-language")
def detect(data: DetectIn, _: User = Depends(get_current_user)):
    return {"language": detect_language(data.code[: get_settings().max_code_chars])}


@router.post("/reviews", response_model=ReviewDetail, status_code=status.HTTP_201_CREATED)
def submit_review(
    data: ReviewCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    review_limiter.hit(f"user:{user.id}")
    limit = get_settings().max_code_chars
    if len(data.code) > limit:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"Code exceeds {limit:,} characters")
    review, ai_scheduled = create_review(db, user, data)
    if ai_scheduled:
        background.add_task(run_ai_review, review.id)
    return _detail(review)


@router.get("/reviews", response_model=ReviewPage)
def list_reviews(
    search: str | None = None,
    language: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Review).where(Review.user_id == user.id)
    if search:
        q = q.where(Review.title.ilike(f"%{search}%"))
    if language:
        q = q.where(Review.language == language)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(
        q.options(selectinload(Review.findings)).order_by(Review.created_at.desc(), Review.id.desc())
        .limit(limit).offset(offset)
    ).all()
    return ReviewPage(items=[to_summary(r) for r in rows], total=total)


@router.get("/reviews/{review_id}", response_model=ReviewDetail)
def get_review(review_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    review = _get_owned(db, user, review_id)
    if review.fixed_code is None and review.status == "completed":
        # reviews created before auto-fix existed get their corrected code on first view
        backfill_corrected_code(review)
        db.commit()
    return _detail(review)


@router.post("/reviews/{review_id}/tests", response_model=TestsOut)
def generate_tests(review_id: int, data: TestsIn, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """Unit tests for the reviewed code: an instant skeleton, or complete tests from Claude."""
    review_limiter.hit(f"user:{user.id}")
    review = _get_owned(db, user, review_id)
    module = re.sub(r"\.[^./\\]+$", "", review.title.replace("\\", "/")).strip("/") or "module"

    if data.use_ai and get_settings().ai_configured:
        try:
            result = generate_tests_with_claude(review.code, review.language, module)
        except AIReviewError as e:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e
        return TestsOut(source="ai", framework=result["framework"], filename=result["filename"],
                        code=result["code"], notes=result["notes"], count=None)

    skeleton = generate_test_skeleton(review.code, review.language, review.title)
    if skeleton is None:
        reason = ("No public functions or methods were found to test."
                  if review.language in ("python", "javascript", "typescript", "java", "go")
                  else "Test skeletons are available for Python, JavaScript, TypeScript, Java and Go.")
        hint = "" if get_settings().ai_configured else " Add ANTHROPIC_API_KEY to generate full tests with Claude."
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, reason + hint)
    return TestsOut(source="static", framework=skeleton.framework, filename=skeleton.filename,
                    code=skeleton.code, count=skeleton.count,
                    notes=f"{skeleton.count} test stubs generated from the public API. Fill in the inputs and "
                          "expected values marked TODO.")


@router.get("/reviews/{review_id}/report.pdf")
def review_report(review_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    review = _get_owned(db, user, review_id)
    if review.fixed_code is None:
        backfill_corrected_code(review)
        db.commit()
    safe_name = re.sub(r"[^\w.-]+", "_", review.title).strip("_") or "review"
    return Response(
        build_report(review),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}-report.pdf"'},
    )


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(review_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.delete(_get_owned(db, user, review_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
