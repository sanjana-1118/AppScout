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


class OverviewDashboardResponse(BaseModel):
    summary: dict[str, StatCard]
    pricing_distribution: dict[str, int]
    rating_distribution: dict[int, int]
    top_categories: list[CategoryListItem]
    top_reviewed_apps: list[AppListItem]
    top_rated_apps: list[AppListItem]
