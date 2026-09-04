"""
backend/schemas/reviews.py
--------------------------
Pydantic models for the Reviews Explorer endpoint.
"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ReviewItem(BaseModel):
    id: int
    app_id: int | None = None
    app_slug: str
    app_name: str | None = None
    reviewer_name: str | None = None
    reviewer_location: str | None = None
    time_spent_using_app: str | None = None
    rating: int
    review_date: str | None = None
    body: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ReviewsStatsResponse(BaseModel):
    total_reviews: int
    distinct_apps_covered: int
    average_rating: float
    rating_distribution: dict[int, int] = Field(default_factory=dict)
