"""
experiment/ingest.py
--------------------
Phase 3: Automated Database Ingestion Layer for AppScout.

Receives structured and validated pipeline results from the extraction pipeline
and persists canonical app records, normalized categories, many-to-many links,
and ingestion execution logs in PostgreSQL.
"""

from __future__ import annotations

import dataclasses
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from .db import repositories
from .models import AppData, ExtractionMeta

logger = logging.getLogger(__name__)


def ingest_pipeline_result(
    result_dict: dict[str, Any],
    *,
    session: Session,
    run_id: int | None = None,
    frontier_categories: list[str] | None = None,
    result_path: str | None = None,
) -> tuple[bool, str]:
    """Persist a single validated extraction result into PostgreSQL.

    Parameters
    ----------
    result_dict : dict[str, Any]
        Pipeline result (either dict from process_single_app() or serialized experiment_result).
    session : Session
        Active SQLAlchemy session.
    run_id : int | None
        Optional IngestionRun ID for audit logging.
    frontier_categories : list[str] | None
        Optional category slugs discovered from the frontier.
    result_path : str | None
        Optional path to the saved JSON experiment result file.

    Returns
    -------
    (success, message) : tuple[bool, str]
    """
    # 1. Normalize AppData & Fallback identifiers
    app_data: AppData | None = None
    if "app_data" in result_dict and isinstance(result_dict["app_data"], AppData):
        app_data = result_dict["app_data"]
    elif "extracted_data" in result_dict and isinstance(result_dict["extracted_data"], dict):
        ext = result_dict["extracted_data"]
        try:
            app_data = AppData(
                app_name=ext.get("app_name"),
                app_slug=ext.get("app_slug"),
                app_url=ext.get("app_url"),
                developer_name=ext.get("developer_name"),
                description=ext.get("description"),
                average_rating=ext.get("average_rating"),
                review_count=ext.get("review_count"),
                category=ext.get("category"),
            )
        except Exception as exc:
            err_msg = f"Failed to construct AppData from extracted_data: {exc}"
            logger.error(err_msg)
            return False, err_msg

    app_slug = (
        (app_data.app_slug if app_data else None)
        or result_dict.get("slug")
        or result_dict.get("app_slug")
        or "unknown_app"
    )
    app_url = (
        (app_data.app_url if app_data else None)
        or result_dict.get("url")
        or result_dict.get("app_url")
        or f"https://apps.shopify.com/{app_slug}"
    )

    # 2. Normalize Snapshot Path
    snapshot_path = None
    if "extraction_meta" in result_dict:
        em = result_dict["extraction_meta"]
        if isinstance(em, ExtractionMeta):
            snapshot_path = em.html_path
        elif isinstance(em, dict):
            snapshot_path = em.get("html_path")

    if app_data is None or not app_data.app_slug or not app_data.app_name:
        http_status = result_dict.get("http_status") or result_dict.get("status_code")
        status_label = "not_found" if http_status == 404 else "validation_failed"
        err_msg = f"Extracted AppData is empty or missing mandatory fields (app_slug, app_name) [HTTP {http_status}]"
        logger.warning(err_msg)
        if run_id is not None:
            repositories.record_ingestion_item(
                session,
                run_id=run_id,
                app_slug=app_slug,
                app_url=app_url,
                status=status_label,
                error_message=err_msg,
                snapshot_path=snapshot_path,
                result_path=result_path,
            )
        return False, err_msg

    # 3. Validation Gate
    validation = result_dict.get("validation_result") or result_dict.get("validation") or {}
    val_summary = validation.get("summary") or {}
    sanity_passed = val_summary.get("all_sanity_checks_passed", False)
    # Also support direct status='passed' from single-app runner
    if not sanity_passed and validation.get("status") != "passed":
        failed_checks = [k for k, v in validation.get("sanity_checks", {}).items() if not v]
        err_msg = f"Sanity validation failed for app '{app_slug}': failed checks {failed_checks}"
        logger.warning(err_msg)

        if run_id is not None:
            repositories.record_ingestion_item(
                session,
                run_id=run_id,
                app_slug=app_slug,
                app_url=app_url,
                status="validation_failed",
                error_message=err_msg,
                snapshot_path=snapshot_path,
                result_path=result_path,
            )
        return False, err_msg

    # 4. Persist Canonical App & Categories in PostgreSQL
    try:
        app = repositories.upsert_app(
            session,
            app_data,
            last_scraped_at=datetime.now(timezone.utc),
        )

        # Link frontier-level categories if provided
        if frontier_categories:
            for cat_slug in frontier_categories:
                if cat_slug:
                    cat = repositories.upsert_category(session, slug=cat_slug)
                    repositories.link_app_category(session, app.id, cat.id)

        # 5. Log Success Ingestion Item
        if run_id is not None:
            repositories.record_ingestion_item(
                session,
                run_id=run_id,
                app_slug=app.app_slug,
                app_url=app.app_url,
                status="success",
                snapshot_path=snapshot_path,
                result_path=result_path,
            )

        return True, f"Successfully persisted app '{app.app_slug}' (id={app.id})"

    except Exception as exc:
        err_msg = f"Database persistence exception for '{app_slug}': {exc}"
        logger.error(err_msg)
        if run_id is not None:
            repositories.record_ingestion_item(
                session,
                run_id=run_id,
                app_slug=app_slug,
                app_url=app_url,
                status="failed",
                error_message=err_msg,
                snapshot_path=snapshot_path,
                result_path=result_path,
            )
        return False, err_msg
