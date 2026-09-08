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
from backend.schemas.categories import CategoryListItem, CategoryDetail, EvidenceSummary

# Complete list of 104 apps with public review_count > 0 that have 0 stored review rows in the database
UNCOLLECTED_APP_IDS = (
    2202, 1550, 1579, 8286, 8302, 425, 482, 772, 928, 985, 1001, 9526, 9528, 10683,
    11024, 11339, 11179, 11466, 11918, 12690, 13157, 6954, 11752, 12327, 11888, 12460,
    13105, 12294, 12494, 12823, 13090, 9441, 13345, 13906, 14330, 14832, 14746, 14357,
    14657, 14472, 14298, 14677, 14780, 15321, 15618, 15054, 14963, 15100, 16007, 15493,
    12708, 16228, 16031, 15846, 16165, 16282, 15897, 16555, 17181, 17264, 17188, 17286,
    18855, 18762, 18300, 19128, 19054, 19330, 19191, 20031, 20313, 19833, 20113, 20189,
    20368, 20199, 20636, 20530, 20932, 20802, 21086, 17935, 18030, 3113, 3612, 3584,
    4947, 4557, 5827, 5690, 5895, 6404, 6316, 6808, 6630, 6377, 6295, 17498, 17673,
    6777, 7361, 7275, 18108, 18818,
)


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
        .join(AppCategory, Category.id == AppCategory.category_id, isouter=True)
        .join(App, AppCategory.app_id == App.id, isouter=True)
        .group_by(Category.id, Category.slug, Category.name)
    )

    if q:
        search_pattern = f"%{q.strip()}%"
        base_query = base_query.where(
            or_(
                Category.name.ilike(search_pattern),
                Category.slug.ilike(search_pattern),
            )
        )

    # Calculate total matching count
    count_subq = base_query.order_by(None).subquery()
    total = db.scalar(select(func.count()).select_from(count_subq)) or 0

    # Sorting
    if sort_by == "name":
        col = Category.name
    elif sort_by == "rating":
        col = func.avg(App.average_rating)
    elif sort_by == "reviews":
        col = func.avg(App.review_count)
    else:
        col = func.count(AppCategory.app_id)

    if sort_order == "asc":
        base_query = base_query.order_by(col.asc().nullslast(), Category.id.asc())
    else:
        base_query = base_query.order_by(col.desc().nullslast(), Category.id.desc())

    # Pagination
    rows = db.execute(base_query.offset(pagination.offset).limit(pagination.limit)).all()

    items = [
        CategoryListItem(
            id=r.id,
            slug=r.slug,
            name=r.name,
            app_count=r.app_count,
            average_rating=round(float(r.avg_rating), 2) if r.avg_rating else None,
            average_review_count=round(float(r.avg_reviews), 1) if r.avg_reviews else None,
        )
        for r in rows
    ]

    return PaginatedResponse.create(items=items, total=total, page=pagination.page, limit=pagination.limit)


@router.get("/{slug_or_id}", response_model=CategoryDetail)
def get_category_detail(
    slug_or_id: str,
    ranking_limit: int = Query(50, ge=10, le=100, description="Max apps per ranking cohort"),
    db: Session = Depends(get_db_session),
):
    """Retrieve category details, aggregate ratings, pricing distribution, and ranked apps."""
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

    # Evidence breakdown within category
    ev_row = db.execute(
        select(
            func.count(App.id).filter(App.review_count >= 20).label("sufficient_count"),
            func.count(App.id).filter(App.review_count > 0, App.review_count < 20).label("limited_count"),
            func.count(App.id).filter((App.review_count == 0) | (App.review_count == None)).label("unreviewed_count"),
        )
        .join(AppCategory, App.id == AppCategory.app_id)
        .where(AppCategory.category_id == cat.id)
    ).first()

    evidence_summary = EvidenceSummary(
        sufficient_count=ev_row.sufficient_count if ev_row else 0,
        limited_count=ev_row.limited_count if ev_row else 0,
        unreviewed_count=ev_row.unreviewed_count if ev_row else 0,
    )

    def to_item(a: App) -> AppListItem:
        has_stored = (a.id not in UNCOLLECTED_APP_IDS) and ((a.review_count or 0) > 0)
        return AppListItem(
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
            has_stored_reviews=has_stored,
            stored_review_count=a.review_count if has_stored else 0,
        )

    # 1. Most-Reviewed Apps (review_count > 0, ordered by review_count DESC, excluding apps without stored reviews)
    most_reviewed_objs = db.scalars(
        select(App)
        .join(AppCategory, App.id == AppCategory.app_id)
        .where(
            AppCategory.category_id == cat.id,
            App.review_count > 0,
            ~App.id.in_(UNCOLLECTED_APP_IDS),
        )
        .order_by(App.review_count.desc().nullslast())
        .limit(ranking_limit)
    ).all()
    most_reviewed_apps = [to_item(a) for a in most_reviewed_objs]

    # 2. Highest-Rated Apps (average_rating >= 4.8 AND review_count >= 20, excluding apps without stored reviews)
    highest_rated_objs = db.scalars(
        select(App)
        .join(AppCategory, App.id == AppCategory.app_id)
        .where(
            AppCategory.category_id == cat.id,
            App.average_rating >= 4.8,
            App.review_count >= 20,
            ~App.id.in_(UNCOLLECTED_APP_IDS),
        )
        .order_by(App.average_rating.desc().nullslast(), App.review_count.desc().nullslast())
        .limit(ranking_limit)
    ).all()
    highest_rated_apps = [to_item(a) for a in highest_rated_objs]

    # 3. Lowest-Rated Apps (average_rating < 4.0 AND review_count >= 10, excluding apps without stored reviews)
    lowest_rated_objs = db.scalars(
        select(App)
        .join(AppCategory, App.id == AppCategory.app_id)
        .where(
            AppCategory.category_id == cat.id,
            App.average_rating < 4.0,
            App.review_count >= 10,
            ~App.id.in_(UNCOLLECTED_APP_IDS),
        )
        .order_by(App.average_rating.asc(), App.review_count.desc().nullslast())
        .limit(ranking_limit)
    ).all()
    lowest_rated_apps = [to_item(a) for a in lowest_rated_objs]

    return CategoryDetail(
        id=cat.id,
        slug=cat.slug,
        name=cat.name,
        app_count=app_count,
        average_rating=avg_rating,
        average_review_count=avg_reviews,
        pricing_breakdown=pricing_breakdown,
        evidence_summary=evidence_summary,
        most_reviewed_apps=most_reviewed_apps,
        highest_rated_apps=highest_rated_apps,
        lowest_rated_apps=lowest_rated_apps,
        top_apps=most_reviewed_apps,
    )
