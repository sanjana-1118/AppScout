"""
backend/schemas/overview.py
---------------------------
Pydantic models for the Home / Ecosystem Overview dashboard.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from backend.schemas.apps import AppListItem
from backend.schemas.categories import CategoryListItem


class StatCard(BaseModel):
    label: str
    value: int | float
    formatted: str
    description: str | None = None


class ReviewAvailability(BaseModel):
    total_active_apps: int
    apps_with_public_reviews: int
    apps_with_no_public_reviews: int
    total_stored_reviews: int
    apps_with_stored_reviews: int
    uncollected_apps_count: int


class OverviewDashboardResponse(BaseModel):
    summary: dict[str, StatCard]
    review_availability: ReviewAvailability
    pricing_distribution: dict[str, int]
    rating_distribution: dict[int, int]
    top_categories: list[CategoryListItem]
    top_reviewed_apps: list[AppListItem]
    top_rated_apps: list[AppListItem]
