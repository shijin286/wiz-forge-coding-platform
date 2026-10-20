from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..analysis import SUPPORTED_LANGUAGES
from ..analysis.detect import detect_language
from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Review, User
from ..schemas import DetectIn, ReviewCreate, ReviewDetail, ReviewPage
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


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(review_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.delete(_get_owned(db, user, review_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
