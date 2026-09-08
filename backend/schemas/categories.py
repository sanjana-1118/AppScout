"""
backend/schemas/categories.py
----------------------------
Pydantic models for Category intelligence endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from backend.schemas.apps import AppListItem


class CategoryListItem(BaseModel):
    id: int
    slug: str
    name: str
    app_count: int = 0
    average_rating: float | None = None
    average_review_count: float | None = None

    model_config = ConfigDict(from_attributes=True)


class EvidenceSummary(BaseModel):
    sufficient_count: int = 0  # review_count >= 20
    limited_count: int = 0     # 0 < review_count < 20
    unreviewed_count: int = 0  # review_count == 0 or NULL

    model_config = ConfigDict(from_attributes=True)


class CategoryDetail(BaseModel):
    id: int
    slug: str
    name: str
    app_count: int = 0
    average_rating: float | None = None
    average_review_count: float | None = None
    pricing_breakdown: dict[str, int] = Field(default_factory=dict)
    evidence_summary: EvidenceSummary = Field(default_factory=EvidenceSummary)
    most_reviewed_apps: list[AppListItem] = Field(default_factory=list)
    highest_rated_apps: list[AppListItem] = Field(default_factory=list)
    lowest_rated_apps: list[AppListItem] = Field(default_factory=list)
    top_apps: list[AppListItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

