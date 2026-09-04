"""
backend/routers/categories.py
-----------------------------
Router for Category Taxonomy Intelligence and category-specific analytics.
"""

from __future__ import annotations

from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, desc, asc
from sqlalchemy.orm import Session

from experiment.db.models import App, Category, AppCategory
from backend.dependencies import get_db_session, PaginationParams
from backend.schemas.common import PaginatedResponse
from backend.schemas.apps import AppListItem, CategoryBadge
from backend.schemas.categories import CategoryListItem, CategoryDetail

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=PaginatedResponse[CategoryListItem])
def list_categories(
    q: str | None = Query(None, description="Search category name or slug"),
    sort_by: Literal["app_count", "name", "rating", "reviews"] = Query(
        "app_count", description="Sort field"
    ),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db_session),
):
    """List normalized categories enriched with app counts and aggregate ratings."""
    base_query = (
        select(
            Category.id,
            Category.slug,
            Category.name,
            func.count(AppCategory.app_id).label("app_count"),
            func.avg(App.average_rating).label("avg_rating"),
            func.avg(App.review_count).label("avg_reviews"),
        )
        .outerjoin(AppCategory, Category.id == AppCategory.category_id)
        .outerjoin(App, AppCategory.app_id == App.id)
        .group_by(Category.id, Category.slug, Category.name)
    )

    if q and q.strip():
        search_pattern = f"%{q.strip()}%"
        base_query = base_query.where(
            (Category.name.ilike(search_pattern)) | (Category.slug.ilike(search_pattern))
        )

    # Count total matching categories
    count_subq = base_query.subquery()
    total = db.scalar(select(func.count()).select_from(count_subq)) or 0

    # Sorting
    sort_col_map = {
        "app_count": desc("app_count") if sort_order == "desc" else asc("app_count"),
        "name": desc(Category.name) if sort_order == "desc" else asc(Category.name),
        "rating": desc("avg_rating") if sort_order == "desc" else asc("avg_rating"),
        "reviews": desc("avg_reviews") if sort_order == "desc" else asc("avg_reviews"),
    }
    order_clause = sort_col_map.get(sort_by, desc("app_count"))
    query = base_query.order_by(order_clause, Category.id.asc())

    rows = db.execute(query.offset(pagination.offset).limit(pagination.limit)).all()

    items = [
        CategoryListItem(
            id=r.id,
            slug=r.slug,
            name=r.name,
            app_count=r.app_count or 0,
            average_rating=round(float(r.avg_rating), 2) if r.avg_rating else None,
            average_review_count=round(float(r.avg_reviews), 1) if r.avg_reviews else None,
        )
        for r in rows
    ]

    return PaginatedResponse.create(items=items, total=total, page=pagination.page, limit=pagination.limit)


@router.get("/{slug_or_id}", response_model=CategoryDetail)
def get_category_detail(slug_or_id: str, db: Session = Depends(get_db_session)):
    """Retrieve category details, aggregate ratings, pricing distribution, and top apps."""
    if slug_or_id.isdigit():
        cat = db.scalar(select(Category).where(Category.id == int(slug_or_id)))
    else:
        cat = db.scalar(select(Category).where(Category.slug == slug_or_id))

    if not cat:
        raise HTTPException(status_code=404, detail=f"Category '{slug_or_id}' not found")

    # Aggregates for this category
    stats_row = db.execute(
        select(
            func.count(App.id).label("app_count"),
            func.avg(App.average_rating).label("avg_rating"),
            func.avg(App.review_count).label("avg_reviews"),
        )
        .join(AppCategory, App.id == AppCategory.app_id)
        .where(AppCategory.category_id == cat.id)
    ).first()

    app_count = stats_row.app_count if stats_row else 0
    avg_rating = round(float(stats_row.avg_rating), 2) if stats_row and stats_row.avg_rating else None
    avg_reviews = round(float(stats_row.avg_reviews), 1) if stats_row and stats_row.avg_reviews else None

    # Pricing breakdown within category
    pricing_rows = db.execute(
        select(App.pricing_type, func.count(App.id))
        .join(AppCategory, App.id == AppCategory.app_id)
        .where(AppCategory.category_id == cat.id)
        .group_by(App.pricing_type)
    ).all()
    pricing_breakdown = {
        (ptype or "unknown"): count for ptype, count in pricing_rows
    }

    # Top 10 apps in this category
    top_apps_objs = db.scalars(
        select(App)
        .join(AppCategory, App.id == AppCategory.app_id)
        .where(AppCategory.category_id == cat.id)
        .order_by(App.review_count.desc().nullslast())
        .limit(10)
    ).all()

    top_apps = [
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
        for a in top_apps_objs
    ]

    return CategoryDetail(
        id=cat.id,
        slug=cat.slug,
        name=cat.name,
        app_count=app_count,
        average_rating=avg_rating,
        average_review_count=avg_reviews,
        pricing_breakdown=pricing_breakdown,
        top_apps=top_apps,
    )
