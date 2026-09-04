"""
backend/schemas/coverage.py
---------------------------
Pydantic models for Data Coverage and System Health metrics.
"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class FieldFillRate(BaseModel):
    field_name: str
    populated_count: int
    total_count: int
    fill_percentage: float


class IngestionRunSummary(BaseModel):
    id: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: str
    apps_requested: int
    apps_processed: int
    apps_succeeded: int
    apps_failed: int
    apps_skipped: int


class DataCoverageResponse(BaseModel):
    master_frontier_total: int
    canonical_apps_in_db: int
    rejected_inactive_apps: int
    unaccounted_apps: int
    reconciliation_status: str

    total_categories: int
    total_app_category_links: int
    total_pricing_plans: int
    apps_with_pricing: int
    pricing_coverage_percentage: float

    total_merchant_reviews: int
    priority_apps_with_reviews: int

    field_fill_rates: list[FieldFillRate]
    recent_ingestion_runs: list[IngestionRunSummary]
    integrity_status: dict[str, bool]


class HealthResponse(BaseModel):
    status: str = "healthy"
    database_connected: bool
    postgres_version: str | None = None
    timestamp: datetime
