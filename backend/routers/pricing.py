"""
backend/routers/pricing.py
--------------------------
Router for Pricing Intelligence and Plan Explorer endpoints.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Literal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, desc, asc, and_
from sqlalchemy.orm import Session

from experiment.db.models import App, AppPricingPlan
from backend.dependencies import get_db_session, PaginationParams
from backend.schemas.common import PaginatedResponse
from backend.schemas.pricing import (
    PricingOverviewResponse,
    PricingModelStats,
    PriceAmountDistribution,
    IntervalBreakdown,
    FreeTrialStats,
    PlanExplorerItem,
)

router = APIRouter(prefix="/pricing", tags=["Pricing"])


@router.get("/overview", response_model=PricingOverviewResponse)
def get_pricing_overview(db: Session = Depends(get_db_session)):
    """Return high-level pricing intelligence metrics across all Shopify apps."""
    total_apps = db.scalar(select(func.count(App.id))) or 0
    total_pricing_plans = db.scalar(select(func.count(AppPricingPlan.id))) or 0

    # 1. Model breakdown
    model_counts = db.execute(
        select(App.pricing_type, func.count(App.id))
        .group_by(App.pricing_type)
    ).all()

    model_breakdown = []
    for m_type, count in model_counts:
        name = m_type or "unknown"
        pct = round((count / total_apps * 100), 2) if total_apps > 0 else 0.0
        model_breakdown.append(
            PricingModelStats(model=name, count=count, percentage=pct)
        )
    model_breakdown.sort(key=lambda x: x.count, reverse=True)

    # 2. Price distribution across paid tiers (price_amount > 0)
    paid_stats = db.execute(
        select(
            func.min(AppPricingPlan.price_amount),
            func.max(AppPricingPlan.price_amount),
            func.avg(AppPricingPlan.price_amount),
            func.percentile_cont(0.50).within_group(AppPricingPlan.price_amount),
            func.percentile_cont(0.25).within_group(AppPricingPlan.price_amount),
            func.percentile_cont(0.75).within_group(AppPricingPlan.price_amount),
        ).where(AppPricingPlan.price_amount > 0)
    ).first()

    price_distribution = PriceAmountDistribution(
        min_price=float(paid_stats[0]) if paid_stats and paid_stats[0] is not None else 0.0,
        max_price=float(paid_stats[1]) if paid_stats and paid_stats[1] is not None else 0.0,
        avg_price=round(float(paid_stats[2]), 2) if paid_stats and paid_stats[2] is not None else 0.0,
        median_price=round(float(paid_stats[3]), 2) if paid_stats and paid_stats[3] is not None else 0.0,
        p25_price=round(float(paid_stats[4]), 2) if paid_stats and paid_stats[4] is not None else 0.0,
        p75_price=round(float(paid_stats[5]), 2) if paid_stats and paid_stats[5] is not None else 0.0,
    )

    # 3. Interval breakdown
    interval_rows = db.execute(
        select(AppPricingPlan.billing_interval, func.count(AppPricingPlan.id))
        .group_by(AppPricingPlan.billing_interval)
    ).all()

    interval_breakdown = []
    for interval, count in interval_rows:
        pct = round((count / total_pricing_plans * 100), 2) if total_pricing_plans > 0 else 0.0
        interval_breakdown.append(
            IntervalBreakdown(billing_interval=interval or "unspecified", plan_count=count, percentage=pct)
        )
    interval_breakdown.sort(key=lambda x: x.plan_count, reverse=True)

    # 4. Free trial stats
    trial_count = db.scalar(
        select(func.count(App.id)).where(App.free_trial_days != None, App.free_trial_days > 0)
    ) or 0
    no_trial_count = total_apps - trial_count
    trial_pct = round((trial_count / total_apps * 100), 2) if total_apps > 0 else 0.0

    durations = db.execute(
        select(App.free_trial_days, func.count(App.id))
        .where(App.free_trial_days != None, App.free_trial_days > 0)
        .group_by(App.free_trial_days)
        .order_by(desc(func.count(App.id)))
        .limit(6)
    ).all()
    popular_durations = {int(days): count for days, count in durations}

    free_trial_stats = FreeTrialStats(
        has_trial_count=trial_count,
        no_trial_count=no_trial_count,
        trial_percentage=trial_pct,
        popular_durations=popular_durations,
    )

    return PricingOverviewResponse(
        total_apps=total_apps,
        total_pricing_plans=total_pricing_plans,
        model_breakdown=model_breakdown,
        price_distribution=price_distribution,
        interval_breakdown=interval_breakdown,
        free_trial_stats=free_trial_stats,
    )


@router.get("/plans", response_model=PaginatedResponse[PlanExplorerItem])
def list_pricing_plans(
    q: str | None = Query(None, description="Search plan name, features, or app slug"),
    app_slug: str | None = Query(None, description="Filter by app slug"),
    billing_interval: str | None = Query(None, description="Filter by interval (monthly, annual, etc.)"),
    min_price: float | None = Query(None, ge=0, description="Minimum price amount"),
    max_price: float | None = Query(None, ge=0, description="Maximum price amount"),
    has_free_trial: bool | None = Query(None, description="Filter by plans offering free trial"),
    sort_by: Literal["price", "plan_name", "app", "newest"] = Query("price", description="Sort field"),
    sort_order: Literal["asc", "desc"] = Query("asc", description="Sort order"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db_session),
):
    """List, search, and filter structured pricing plan tiers across Shopify applications."""
    query = (
        select(AppPricingPlan, App.app_name)
        .join(App, AppPricingPlan.app_id == App.id)
    )

    if q and q.strip():
        search_pattern = f"%{q.strip()}%"
        query = query.where(
            (AppPricingPlan.plan_name.ilike(search_pattern))
            | (AppPricingPlan.app_slug.ilike(search_pattern))
            | (App.app_name.ilike(search_pattern))
            | (AppPricingPlan.features.ilike(search_pattern))
        )

    if app_slug:
        query = query.where(AppPricingPlan.app_slug == app_slug)

    if billing_interval:
        query = query.where(AppPricingPlan.billing_interval == billing_interval)

    if min_price is not None:
        query = query.where(AppPricingPlan.price_amount >= Decimal(str(min_price)))

    if max_price is not None:
        query = query.where(AppPricingPlan.price_amount <= Decimal(str(max_price)))

    if has_free_trial is True:
        query = query.where(AppPricingPlan.free_trial_days != None, AppPricingPlan.free_trial_days > 0)
    elif has_free_trial is False:
        query = query.where(
            (AppPricingPlan.free_trial_days == None) | (AppPricingPlan.free_trial_days == 0)
        )

    # Count total matching plans
    count_subq = query.order_by(None).subquery()
    total = db.scalar(select(func.count()).select_from(count_subq)) or 0

    # Sorting
    if sort_by == "price":
        order_col = AppPricingPlan.price_amount.asc() if sort_order == "asc" else AppPricingPlan.price_amount.desc()
    elif sort_by == "plan_name":
        order_col = AppPricingPlan.plan_name.asc() if sort_order == "asc" else AppPricingPlan.plan_name.desc()
    elif sort_by == "app":
        order_col = App.app_name.asc() if sort_order == "asc" else App.app_name.desc()
    else:
        order_col = AppPricingPlan.created_at.desc() if sort_order == "desc" else AppPricingPlan.created_at.asc()

    query = query.order_by(order_col, AppPricingPlan.id.asc())

    rows = db.execute(query.offset(pagination.offset).limit(pagination.limit)).all()

    items = []
    for plan, app_name in rows:
        features_val = plan.features
        if isinstance(features_val, str) and features_val.startswith("["):
            try:
                features_val = json.loads(features_val)
            except Exception:
                pass

        items.append(
            PlanExplorerItem(
                id=plan.id,
                app_id=plan.app_id,
                app_slug=plan.app_slug,
                app_name=app_name,
                plan_name=plan.plan_name,
                price_amount=float(plan.price_amount) if plan.price_amount is not None else None,
                currency=plan.currency,
                billing_interval=plan.billing_interval,
                free_trial_days=plan.free_trial_days,
                features=features_val,
                created_at=plan.created_at,
            )
        )

    return PaginatedResponse.create(items=items, total=total, page=pagination.page, limit=pagination.limit)
