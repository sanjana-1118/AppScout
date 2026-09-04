"""
backend/routers/overview.py
---------------------------
Router for Home / Ecosystem Overview dashboard metrics.
"""

from __future__ import annotations

from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy import func, select, desc, Integer
from sqlalchemy.orm import Session

from experiment.db.models import App, Category, AppCategory, AppPricingPlan
from experiment.reviews.models import Review
from backend.dependencies import get_db_session
from backend.schemas.overview import OverviewDashboardResponse, StatCard
from backend.schemas.apps import AppListItem, CategoryBadge
from backend.schemas.categories import CategoryListItem

router = APIRouter(prefix="/overview", tags=["Overview"])


@router.get("", response_model=OverviewDashboardResponse)
def get_ecosystem_overview(db: Session = Depends(get_db_session)):
    """Return high-level ecosystem metrics, distributions, top categories, and highlighted apps."""
    # 1. Total counts
    total_apps = db.scalar(select(func.count(App.id))) or 0
    total_categories = db.scalar(select(func.count(Category.id))) or 0
    total_pricing_plans = db.scalar(select(func.count(AppPricingPlan.id))) or 0
    total_reviews = db.scalar(select(func.count(Review.id))) or 0
    avg_store_rating = db.scalar(select(func.avg(App.average_rating)).where(App.average_rating != None))

    summary = {
        "total_apps": StatCard(
            label="Total Shopify Apps",
            value=total_apps,
            formatted=f"{total_apps:,}",
            description="Verified canonical active apps in PostgreSQL",
        ),
        "total_categories": StatCard(
            label="Taxonomy Categories",
            value=total_categories,
            formatted=f"{total_categories:,}",
            description="Normalized app categories across the ecosystem",
        ),
        "total_pricing_plans": StatCard(
            label="Structured Pricing Plans",
            value=total_pricing_plans,
            formatted=f"{total_pricing_plans:,}",
            description="Detailed plan tiers extracted and stored",
        ),
        "total_reviews": StatCard(
            label="Merchant Reviews",
            value=total_reviews,
            formatted=f"{total_reviews:,}",
            description="Verified merchant reviews across priority apps",
        ),
        "average_rating": StatCard(
            label="Ecosystem Avg Rating",
            value=round(float(avg_store_rating), 2) if avg_store_rating else 0.0,
            formatted=f"{round(float(avg_store_rating), 2) if avg_store_rating else 0.0} / 5.0",
            description="Mean rating across rated Shopify applications",
        ),
    }

    # 2. Pricing model distribution
    pricing_rows = db.execute(
        select(App.pricing_type, func.count(App.id))
        .group_by(App.pricing_type)
    ).all()
    pricing_distribution = {
        (ptype or "unknown"): count for ptype, count in pricing_rows
    }

    # 3. Rating distribution (rounded to whole integer stars for apps with rating)
    rating_expr = func.floor(App.average_rating).cast(Integer)
    rating_rows = db.execute(
        select(
            rating_expr.label("star"),
            func.count(App.id),
        )
        .where(App.average_rating != None)
        .group_by(rating_expr)
    ).all()
    rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for star, cnt in rating_rows:
        if star in rating_distribution:
            rating_distribution[star] = cnt

    # 4. Top categories by app count
    top_cat_rows = db.execute(
        select(
            Category.id,
            Category.slug,
            Category.name,
            func.count(AppCategory.app_id).label("app_count"),
            func.avg(App.average_rating).label("avg_rating"),
            func.avg(App.review_count).label("avg_reviews"),
        )
        .join(AppCategory, Category.id == AppCategory.category_id)
        .outerjoin(App, AppCategory.app_id == App.id)
        .group_by(Category.id, Category.slug, Category.name)
        .order_by(desc("app_count"))
        .limit(6)
    ).all()

    top_categories = [
        CategoryListItem(
            id=row.id,
            slug=row.slug,
            name=row.name,
            app_count=row.app_count,
            average_rating=round(float(row.avg_rating), 2) if row.avg_rating else None,
            average_review_count=round(float(row.avg_reviews), 1) if row.avg_reviews else None,
        )
        for row in top_cat_rows
    ]

    # 5. Top reviewed apps
    top_reviewed_objs = db.scalars(
        select(App)
        .order_by(App.review_count.desc().nullslast())
        .limit(5)
    ).all()
    top_reviewed_apps = [
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
        for a in top_reviewed_objs
    ]

    # 6. Top rated apps (minimum 50 reviews to ensure statistical significance)
    top_rated_objs = db.scalars(
        select(App)
        .where(App.average_rating != None, App.review_count >= 50)
        .order_by(App.average_rating.desc().nullslast(), App.review_count.desc().nullslast())
        .limit(5)
    ).all()
    top_rated_apps = [
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
        for a in top_rated_objs
    ]

    return OverviewDashboardResponse(
        summary=summary,
        pricing_distribution=pricing_distribution,
        rating_distribution=rating_distribution,
        top_categories=top_categories,
        top_reviewed_apps=top_reviewed_apps,
        top_rated_apps=top_rated_apps,
    )
