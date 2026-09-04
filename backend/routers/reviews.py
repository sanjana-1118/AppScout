"""
backend/routers/reviews.py
--------------------------
Router for merchant review exploration and sentiment dataset inspection.
"""

from __future__ import annotations

from typing import Literal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, desc, asc
from sqlalchemy.orm import Session

from experiment.db.models import App
from experiment.reviews.models import Review
from backend.dependencies import get_db_session, PaginationParams
from backend.schemas.common import PaginatedResponse
from backend.schemas.reviews import ReviewItem, ReviewsStatsResponse

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get("", response_model=PaginatedResponse[ReviewItem])
def list_reviews(
    q: str | None = Query(None, description="Search review text body or reviewer name"),
    app_slug: str | None = Query(None, description="Filter by app slug"),
    rating: int | None = Query(None, ge=1, le=5, description="Filter by exact star rating (1-5)"),
    sort_by: Literal["date", "rating", "newest"] = Query("date", description="Sort field"),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db_session),
):
    """List, search, filter, and paginate merchant reviews across Shopify apps."""
    query = (
        select(Review, App.app_name)
        .outerjoin(App, Review.app_id == App.id)
    )

    if q and q.strip():
        search_pattern = f"%{q.strip()}%"
        query = query.where(
            (Review.body.ilike(search_pattern))
            | (Review.reviewer_name.ilike(search_pattern))
            | (Review.app_slug.ilike(search_pattern))
        )

    if app_slug:
        query = query.where(Review.app_slug == app_slug)

    if rating is not None:
        query = query.where(Review.rating == rating)

    # Count total
    count_subq = query.order_by(None).subquery()
    total = db.scalar(select(func.count()).select_from(count_subq)) or 0

    # Sorting
    if sort_by == "rating":
        order_col = Review.rating.asc() if sort_order == "asc" else Review.rating.desc()
    elif sort_by == "newest":
        order_col = Review.created_at.asc() if sort_order == "asc" else Review.created_at.desc()
    else:  # date
        order_col = Review.review_date.asc() if sort_order == "asc" else Review.review_date.desc()

    query = query.order_by(order_col, Review.id.desc())

    rows = db.execute(query.offset(pagination.offset).limit(pagination.limit)).all()

    items = [
        ReviewItem(
            id=r.id,
            app_id=r.app_id,
            app_slug=r.app_slug,
            app_name=app_name or r.app_slug,
            reviewer_name=r.reviewer_name,
            reviewer_location=r.reviewer_location,
            time_spent_using_app=r.time_spent_using_app,
            rating=r.rating,
            review_date=r.review_date,
            body=r.body,
            created_at=r.created_at,
        )
        for r, app_name in rows
    ]

    return PaginatedResponse.create(items=items, total=total, page=pagination.page, limit=pagination.limit)


@router.get("/stats", response_model=ReviewsStatsResponse)
def get_reviews_stats(db: Session = Depends(get_db_session)):
    """Return aggregate statistics across the merchant review intelligence dataset."""
    total_reviews = db.scalar(select(func.count(Review.id))) or 0
    distinct_apps = db.scalar(select(func.count(func.distinct(Review.app_slug)))) or 0
    avg_rating = db.scalar(select(func.avg(Review.rating))) or 0.0

    dist_rows = db.execute(
        select(Review.rating, func.count(Review.id))
        .group_by(Review.rating)
        .order_by(Review.rating.asc())
    ).all()

    rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r, cnt in dist_rows:
        if r in rating_dist:
            rating_dist[r] = cnt

    return ReviewsStatsResponse(
        total_reviews=total_reviews,
        distinct_apps_covered=distinct_apps,
        average_rating=round(float(avg_rating), 2),
        rating_distribution=rating_dist,
    )
