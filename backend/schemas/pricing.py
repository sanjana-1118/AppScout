"""
backend/schemas/pricing.py
--------------------------
Pydantic models for Pricing Intelligence analytics and plan exploration.
"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PricingModelStats(BaseModel):
    model: str
    count: int
    percentage: float


class PriceAmountDistribution(BaseModel):
    min_price: float | None = None
    max_price: float | None = None
    avg_price: float | None = None
    median_price: float | None = None
    p25_price: float | None = None
    p75_price: float | None = None


class IntervalBreakdown(BaseModel):
    billing_interval: str
    plan_count: int
    percentage: float


class FreeTrialStats(BaseModel):
    has_trial_count: int
    no_trial_count: int
    trial_percentage: float
    popular_durations: dict[int, int] = Field(default_factory=dict)


class PricingOverviewResponse(BaseModel):
    total_apps: int
    total_pricing_plans: int
    model_breakdown: list[PricingModelStats]
    price_distribution: PriceAmountDistribution
    interval_breakdown: list[IntervalBreakdown]
    free_trial_stats: FreeTrialStats


class PlanExplorerItem(BaseModel):
    id: int
    app_id: int
    app_slug: str
    app_name: str
    plan_name: str
    price_amount: float | None = None
    currency: str = "USD"
    billing_interval: str = "monthly"
    free_trial_days: int | None = None
    features: str | list[str] | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
