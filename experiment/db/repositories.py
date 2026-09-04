"""
experiment/db/repositories.py
-----------------------------
Reusable data access layer and repository functions for AppScout PostgreSQL models.

Provides atomic upsert operations, association linking, and execution tracking
without embedding raw SQL queries in pipeline orchestrators.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ..models import AppData
from .models import App, AppCategory, Category, IngestionItem, IngestionRun

logger = logging.getLogger(__name__)


def upsert_category(
    session: Session,
    slug: str,
    name: str | None = None,
) -> Category:
    """Find an existing category by slug or insert a new normalized record."""
    clean_slug = slug.strip().lower()
    display_name = name.strip() if name else clean_slug.replace("-", " ").capitalize()

    stmt = select(Category).where(Category.slug == clean_slug)
    category = session.scalars(stmt).first()

    if category is None:
        category = Category(
            slug=clean_slug,
            name=display_name,
        )
        session.add(category)
        session.flush()
        logger.debug("Inserted new category: %s (%s)", clean_slug, display_name)
    elif name and category.name != display_name:
        category.name = display_name
        session.flush()

    return category


def upsert_app(
    session: Session,
    app_data: AppData,
    *,
    last_scraped_at: datetime | None = None,
) -> App:
    """Insert or update a canonical application record from validated AppData."""
    scraped_ts = last_scraped_at or datetime.now(timezone.utc)
    rating_val = Decimal(str(app_data.average_rating)) if app_data.average_rating is not None else None

    stmt = select(App).where(App.app_slug == app_data.app_slug)
    app = session.scalars(stmt).first()

    if app is None:
        app = App(
            app_slug=app_data.app_slug,
            app_name=app_data.app_name,
            app_url=app_data.app_url,
            developer_name=app_data.developer_name,
            description=app_data.description,
            average_rating=rating_val,
            review_count=app_data.review_count,
            pricing_type=getattr(app_data, "pricing_type", None),
            free_trial_days=getattr(app_data, "free_trial_days", None),
            first_discovered_at=scraped_ts,
            last_scraped_at=scraped_ts,
        )
        session.add(app)
        session.flush()
        logger.info("Inserted new app in PostgreSQL: %s (id=%d)", app.app_slug, app.id)
    else:
        app.app_name = app_data.app_name
        app.app_url = app_data.app_url
        app.developer_name = app_data.developer_name
        app.description = app_data.description
        app.average_rating = rating_val
        app.review_count = app_data.review_count
        if getattr(app_data, "pricing_type", None):
            app.pricing_type = app_data.pricing_type
        if getattr(app_data, "free_trial_days", None) is not None:
            app.free_trial_days = app_data.free_trial_days
        app.last_scraped_at = scraped_ts
        session.flush()
        logger.info("Updated existing app in PostgreSQL: %s (id=%d)", app.app_slug, app.id)

    # Link primary category if extracted
    if app_data.category:
        cat = upsert_category(session, slug=app_data.category)
        link_app_category(session, app.id, cat.id)

    # Upsert pricing plans if extracted
    plans = getattr(app_data, "pricing_plans", None)
    if plans:
        upsert_pricing_plans(session, app.id, app.app_slug, plans)

    return app


def upsert_pricing_plans(
    session: Session,
    app_id: int,
    app_slug: str,
    plans: list[dict[str, Any]],
) -> list[AppPricingPlan]:
    """Upsert pricing plans for a canonical application."""
    from .models import AppPricingPlan
    import json

    # Clean existing plans for this app to avoid stale duplicate rows
    session.query(AppPricingPlan).filter(AppPricingPlan.app_id == app_id).delete()
    session.flush()

    inserted_plans = []
    for p in plans:
        plan_name = p.get("plan_name", "Default Plan")
        price_val = Decimal(str(p["price_amount"])) if p.get("price_amount") is not None else None
        features_val = json.dumps(p.get("features", [])) if isinstance(p.get("features"), (list, dict)) else p.get("features")

        plan_obj = AppPricingPlan(
            app_id=app_id,
            app_slug=app_slug,
            plan_name=plan_name,
            price_amount=price_val,
            currency=p.get("currency", "USD"),
            billing_interval=p.get("billing_interval", "monthly"),
            free_trial_days=p.get("free_trial_days"),
            features=features_val,
        )
        session.add(plan_obj)
        inserted_plans.append(plan_obj)

    session.flush()
    logger.debug("Persisted %d pricing plans for app id=%d (%s)", len(inserted_plans), app_id, app_slug)
    return inserted_plans


def link_app_category(
    session: Session,
    app_id: int,
    category_id: int,
) -> None:
    """Ensure a many-to-many relationship exists between an app and a category."""
    stmt = select(AppCategory).where(
        AppCategory.app_id == app_id,
        AppCategory.category_id == category_id,
    )
    existing = session.scalars(stmt).first()
    if existing is None:
        mapping = AppCategory(app_id=app_id, category_id=category_id)
        session.add(mapping)
        session.flush()
        logger.debug("Linked app id=%d to category id=%d", app_id, category_id)


def get_app_by_slug(session: Session, slug: str) -> App | None:
    """Retrieve an app by slug."""
    stmt = select(App).where(App.app_slug == slug.strip().lower())
    return session.scalars(stmt).first()


def is_app_fresh(
    session: Session,
    slug: str,
    max_age_hours: float | None = 168.0,
) -> bool:
    """Check if an app is already stored in PostgreSQL and within freshness threshold."""
    if max_age_hours is None:
        return False

    app = get_app_by_slug(session, slug)
    if app is None or app.last_scraped_at is None:
        return False

    now = datetime.now(timezone.utc)
    threshold = now - timedelta(hours=max_age_hours)
    return app.last_scraped_at >= threshold


def create_ingestion_run(
    session: Session,
    apps_requested: int = 0,
    notes: str | None = None,
) -> IngestionRun:
    """Create a new IngestionRun record in 'running' status."""
    run = IngestionRun(
        apps_requested=apps_requested,
        status="running",
        notes=notes,
    )
    session.add(run)
    session.flush()
    logger.info("Created IngestionRun id=%d (requested=%d)", run.id, apps_requested)
    return run


def record_ingestion_item(
    session: Session,
    run_id: int,
    app_slug: str,
    app_url: str,
    status: str,
    *,
    error_message: str | None = None,
    snapshot_path: str | None = None,
    result_path: str | None = None,
) -> IngestionItem:
    """Log the individual processing result for an app within a run."""
    item = IngestionItem(
        ingestion_run_id=run_id,
        app_slug=app_slug,
        app_url=app_url,
        status=status,
        error_message=error_message,
        snapshot_path=snapshot_path,
        result_path=result_path,
        processed_at=datetime.now(timezone.utc),
    )
    session.add(item)
    session.flush()
    return item


def complete_ingestion_run(
    session: Session,
    run_id: int,
    *,
    apps_processed: int,
    apps_succeeded: int,
    apps_failed: int,
    apps_skipped: int,
    snapshots_reused: int,
    new_http_requests: int,
    notes: str | None = None,
) -> IngestionRun:
    """Finalize an IngestionRun with completed counts and status."""
    run = session.get(IngestionRun, run_id)
    if run is None:
        raise ValueError(f"IngestionRun id={run_id} not found")

    run.completed_at = datetime.now(timezone.utc)
    run.apps_processed = apps_processed
    run.apps_succeeded = apps_succeeded
    run.apps_failed = apps_failed
    run.apps_skipped = apps_skipped
    run.snapshots_reused = snapshots_reused
    run.new_http_requests = new_http_requests
    if notes:
        run.notes = notes

    if apps_failed == 0:
        run.status = "completed"
    elif apps_succeeded > 0:
        run.status = "completed_with_errors"
    else:
        run.status = "failed"

    session.flush()
    logger.info("Finalized IngestionRun id=%d status=%s", run.id, run.status)
    return run
