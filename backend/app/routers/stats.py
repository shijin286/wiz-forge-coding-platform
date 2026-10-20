from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..analysis.base import CATEGORIES, SEVERITIES
from ..database import get_db
from ..deps import get_current_user
from ..models import Finding, Review, User
from ..schemas import StatsOut, TrendPoint
from ..services import to_summary

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    mine = Review.user_id == user.id
    total = db.scalar(select(func.count(Review.id)).where(mine)) or 0
    avg = db.scalar(select(func.avg(Review.quality_score)).where(mine))

    finding_rows = db.execute(
        select(Finding.severity, Finding.category, func.count())
        .join(Review).where(mine).group_by(Finding.severity, Finding.category)
    ).all()
    by_severity = dict.fromkeys(SEVERITIES, 0)
    by_category = dict.fromkeys(CATEGORIES, 0)
    for severity, category, n in finding_rows:
        by_severity[severity] = by_severity.get(severity, 0) + n
        by_category[category] = by_category.get(category, 0) + n

    by_language = dict(db.execute(
        select(Review.language, func.count()).where(mine).group_by(Review.language)
    ).all())

    latest = db.scalars(
        select(Review).options(selectinload(Review.findings)).where(mine)
        .order_by(Review.created_at.desc(), Review.id.desc()).limit(10)
    ).all()

    return StatsOut(
        total_reviews=total,
        average_score=round(float(avg), 1) if avg is not None else None,
        total_findings=sum(by_severity.values()),
        by_severity=by_severity,
        by_category=by_category,
        by_language=by_language,
        score_trend=[TrendPoint(id=r.id, title=r.title, score=r.quality_score, created_at=r.created_at)
                     for r in reversed(latest)],
        recent=[to_summary(r) for r in latest[:5]],
    )
