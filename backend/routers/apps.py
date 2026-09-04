"""
backend/routers/apps.py
-----------------------
Router for Shopify App Explorer and detailed application intelligence.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, or_, desc, asc
from sqlalchemy.orm import Session

from experiment.db.models import App, Category, AppCategory, AppPricingPlan
from experiment.reviews.models import Review
from backend.dependencies import get_db_session, PaginationParams
from backend.schemas.common import PaginatedResponse
from backend.schemas.apps import (
    AppListItem,
    AppDetail,
    CategoryBadge,
    PricingPlanCard,
    ReviewSummary,
    ReviewBrief,
)

router = APIRouter(prefix="/apps", tags=["Apps"])


@router.get("", response_model=PaginatedResponse[AppListItem])
def list_apps(
    q: str | None = Query(None, description="Search term for app name, developer, or description"),
    category: str | None = Query(None, description="Filter by category slug"),
    pricing_type: str | None = Query(None, description="Filter by pricing model: free, freemium, paid, unknown"),
    min_rating: float | None = Query(None, ge=1.0, le=5.0, description="Minimum average rating"),
    max_rating: float | None = Query(None, ge=1.0, le=5.0, description="Maximum average rating"),
    min_reviews: int | None = Query(None, ge=0, description="Minimum review count"),
    max_reviews: int | None = Query(None, ge=0, description="Maximum review count"),
    has_free_trial: bool | None = Query(None, description="Whether the app offers a free trial"),
    sort_by: Literal["reviews", "rating", "name", "newest", "pricing"] = Query(
        "reviews", description="Sort field"
    ),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort direction"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db_session),
):
    """List, search, filter, and paginate through canonical Shopify applications."""
    query = select(App).distinct()

    # Join categories if filtering by category
    if category:
        query = query.join(AppCategory, App.id == AppCategory.app_id).join(
            Category, AppCategory.category_id == Category.id
        ).where(Category.slug == category)

    # Search filter
    if q and q.strip():
        search_pattern = f"%{q.strip()}%"
        query = query.where(
            or_(
                App.app_name.ilike(search_pattern),
                App.developer_name.ilike(search_pattern),
                App.description.ilike(search_pattern),
                App.app_slug.ilike(search_pattern),
            )
        )

    # Pricing type filter
    if pricing_type:
        query = query.where(App.pricing_type == pricing_type)

    # Rating filter
    if min_rating is not None:
        query = query.where(App.average_rating >= Decimal(str(min_rating)))
    if max_rating is not None:
        query = query.where(App.average_rating <= Decimal(str(max_rating)))

    # Review count filter
    if min_reviews is not None:
        query = query.where(App.review_count >= min_reviews)
    if max_reviews is not None:
        query = query.where(App.review_count <= max_reviews)

    # Free trial filter
    if has_free_trial is True:
        query = query.where(App.free_trial_days != None, App.free_trial_days > 0)
    elif has_free_trial is False:
        query = query.where(or_(App.free_trial_days == None, App.free_trial_days == 0))

    # Total matching count calculation
    count_subq = query.order_by(None).subquery()
    total = db.scalar(select(func.count()).select_from(count_subq)) or 0

    # Sorting
    sort_column_map = {
        "reviews": App.review_count,
        "rating": App.average_rating,
        "name": App.app_name,
        "newest": App.created_at,
        "pricing": App.pricing_type,
    }
    column = sort_column_map.get(sort_by, App.review_count)

    if sort_order == "asc":
        query = query.order_by(column.asc().nullslast(), App.id.asc())
    else:
        query = query.order_by(column.desc().nullslast(), App.id.desc())

    # Pagination
    app_records = db.scalars(query.offset(pagination.offset).limit(pagination.limit)).all()

    items = [
        AppListItem(
            id=a.id,
            app_slug=a.app_slug,
            app_name=a.app_name,
            app_url=a.app_url,
            developer_name=a.developer_name,
            description=a.description,
            average_rating=float(a.average_rating) if a.average_rating is not None else None,
            review_count=a.review_count or 0,
            pricing_type=a.pricing_type or "unknown",
            free_trial_days=a.free_trial_days,
            categories=[CategoryBadge(id=c.id, slug=c.slug, name=c.name) for c in a.categories],
        )
        for a in app_records
    ]

    return PaginatedResponse.create(items=items, total=total, page=pagination.page, limit=pagination.limit)


@router.get("/{slug_or_id}", response_model=AppDetail)
def get_app_detail(slug_or_id: str, db: Session = Depends(get_db_session)):
    """Retrieve full app intelligence details by slug or numeric ID."""
    if slug_or_id.isdigit():
        app_obj = db.scalar(select(App).where(App.id == int(slug_or_id)))
    else:
        app_obj = db.scalar(select(App).where(App.app_slug == slug_or_id))

    if not app_obj:
        raise HTTPException(status_code=404, detail=f"App '{slug_or_id}' not found")

    # Categories
    categories = [
        CategoryBadge(id=c.id, slug=c.slug, name=c.name) for c in app_obj.categories
    ]

    # Pricing Plans
    pricing_plans = []
    for p in app_obj.pricing_plans:
        features_val = p.features
        if isinstance(features_val, str) and features_val.startswith("["):
            try:
                features_val = json.loads(features_val)
            except Exception:
                pass

        pricing_plans.append(
            PricingPlanCard(
                id=p.id,
                plan_name=p.plan_name,
                price_amount=float(p.price_amount) if p.price_amount is not None else None,
                currency=p.currency,
                billing_interval=p.billing_interval,
                free_trial_days=p.free_trial_days,
                features=features_val,
            )
        )

    # Reviews and Review Summary
    reviews_in_db = db.scalars(
        select(Review)
        .where(or_(Review.app_id == app_obj.id, Review.app_slug == app_obj.app_slug))
        .order_by(desc(Review.id))
    ).all()

    total_revs = len(reviews_in_db)
    avg_rev_rating = None
    rating_breakdown = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    if total_revs > 0:
        avg_rev_rating = round(sum(r.rating for r in reviews_in_db) / total_revs, 2)
        for r in reviews_in_db:
            if r.rating in rating_breakdown:
                rating_breakdown[r.rating] += 1

    recent_reviews = [
        ReviewBrief(
            id=r.id,
            reviewer_name=r.reviewer_name,
            reviewer_location=r.reviewer_location,
            time_spent_using_app=r.time_spent_using_app,
            rating=r.rating,
            review_date=r.review_date,
            body=r.body,
        )
        for r in reviews_in_db[:10]  # top 10 recent
    ]

    return AppDetail(
        id=app_obj.id,
        app_slug=app_obj.app_slug,
        app_name=app_obj.app_name,
        app_url=app_obj.app_url,
        developer_name=app_obj.developer_name,
        description=app_obj.description,
        average_rating=float(app_obj.average_rating) if app_obj.average_rating is not None else None,
        review_count=app_obj.review_count or 0,
        pricing_type=app_obj.pricing_type or "unknown",
        free_trial_days=app_obj.free_trial_days,
        first_discovered_at=app_obj.first_discovered_at,
        last_scraped_at=app_obj.last_scraped_at,
        created_at=app_obj.created_at,
        updated_at=app_obj.updated_at,
        categories=categories,
        pricing_plans=pricing_plans,
        review_summary=ReviewSummary(
            total_reviews_in_db=total_revs,
            average_rating_in_db=avg_rev_rating,
            rating_breakdown=rating_breakdown,
        ),
        recent_reviews=recent_reviews,
    )
