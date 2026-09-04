"""
backend/schemas/apps.py
-----------------------
Pydantic models for App listings, search, filtering, and detail representations.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class CategoryBadge(BaseModel):
    id: int
    slug: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class PricingPlanCard(BaseModel):
    id: int
    plan_name: str
    price_amount: float | None = None
    currency: str = "USD"
    billing_interval: str = "monthly"
    free_trial_days: int | None = None
    features: str | list[str] | None = None

    model_config = ConfigDict(from_attributes=True)


class ReviewSummary(BaseModel):
    total_reviews_in_db: int = 0
    average_rating_in_db: float | None = None
    rating_breakdown: dict[int, int] = Field(default_factory=dict)


class ReviewBrief(BaseModel):
    id: int
    reviewer_name: str | None = None
    reviewer_location: str | None = None
    time_spent_using_app: str | None = None
    rating: int
    review_date: str | None = None
    body: str

    model_config = ConfigDict(from_attributes=True)


class AppListItem(BaseModel):
    """Compact app representation for search, explorer, and category listings."""

    id: int
    app_slug: str
    app_name: str
    app_url: str
    developer_name: str | None = None
    description: str | None = None
    average_rating: float | None = None
    review_count: int | None = 0
    pricing_type: str | None = "unknown"
    free_trial_days: int | None = None
    categories: list[CategoryBadge] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AppDetail(BaseModel):
    """Full application view including categories, pricing plans, and reviews."""

    id: int
    app_slug: str
    app_name: str
    app_url: str
    developer_name: str | None = None
    description: str | None = None
    average_rating: float | None = None
    review_count: int | None = 0
    pricing_type: str | None = "unknown"
    free_trial_days: int | None = None
    first_discovered_at: datetime | None = None
    last_scraped_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    categories: list[CategoryBadge] = Field(default_factory=list)
    pricing_plans: list[PricingPlanCard] = Field(default_factory=list)
    review_summary: ReviewSummary = Field(default_factory=ReviewSummary)
    recent_reviews: list[ReviewBrief] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
