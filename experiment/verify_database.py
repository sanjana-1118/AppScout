"""
experiment/verify_database.py
-----------------------------
Phase 3: Database Verification and Audit Script for AppScout.

Inspects the PostgreSQL database and reports summary statistics, table counts,
audit logs, and a sample of stored canonical applications.
"""

from __future__ import annotations

import argparse
import logging
import sys

from sqlalchemy import func, select

from .db.database import check_connection, get_db
from .db.models import App, AppCategory, Category, IngestionItem, IngestionRun

logger = logging.getLogger(__name__)


def verify_database(*, sample_limit: int = 10) -> bool:
    """Query PostgreSQL and display comprehensive database statistics and samples."""
    ok, conn_msg = check_connection()
    if not ok:
        print(f"\n[ERROR] Database connection failed: {conn_msg}", file=sys.stderr)
        return False

    print("\n" + "=" * 76)
    print("APPSCOUT - POSTGRESQL DATABASE VERIFICATION")
    print("=" * 76)
    print(f"Status : {conn_msg}\n")

    with get_db() as session:
        # Table counts
        total_apps = session.scalar(select(func.count(App.id))) or 0
        total_categories = session.scalar(select(func.count(Category.id))) or 0
        total_mappings = session.scalar(select(func.count(AppCategory.app_id))) or 0
        total_runs = session.scalar(select(func.count(IngestionRun.id))) or 0
        successful_items = session.scalar(
            select(func.count(IngestionItem.id)).where(IngestionItem.status == "success")
        ) or 0
        failed_items = session.scalar(
            select(func.count(IngestionItem.id)).where(
                IngestionItem.status.in_(["failed", "validation_failed"])
            )
        ) or 0
        skipped_items = session.scalar(
            select(func.count(IngestionItem.id)).where(IngestionItem.status == "skipped")
        ) or 0

        print("TABLE COUNTS & METRICS:")
        print("-" * 76)
        print(f"  Total Canonical Apps        : {total_apps}")
        print(f"  Total Categories            : {total_categories}")
        print(f"  Total App-Category Mappings : {total_mappings}")
        print(f"  Total Ingestion Runs        : {total_runs}")
        print(f"  Successful Ingested Items   : {successful_items}")
        print(f"  Failed / Rejected Items     : {failed_items}")
        print(f"  Skipped Items (Fresh)       : {skipped_items}")

        # Recent Ingestion Runs
        runs = session.scalars(
            select(IngestionRun).order_by(IngestionRun.id.desc()).limit(5)
        ).all()

        if runs:
            print("\nRECENT INGESTION RUNS:")
            print("-" * 76)
            print(f"{'ID':<5} {'Status':<14} {'Requested':<10} {'Succeeded':<10} {'Failed':<8} {'Skipped':<8} {'Started At'}")
            print("-" * 76)
            for r in runs:
                started_str = r.started_at.strftime("%Y-%m-%d %H:%M:%S") if r.started_at else "-"
                print(
                    f"#{r.id:<4} {r.status:<14} {r.apps_requested:<10} {r.apps_succeeded:<10} {r.apps_failed:<8} {r.apps_skipped:<8} {started_str}"
                )

        # Sample Stored Apps
        apps = session.scalars(
            select(App).order_by(App.id.desc()).limit(sample_limit)
        ).all()

        print(f"\nSAMPLE STORED APPLICATIONS (Latest {len(apps)}):")
        print("-" * 76)
        print(f"{'App Name':<30} {'Slug':<22} {'Rating':<8} {'Reviews':<9} {'Categories'}")
        print("-" * 76)
        for a in apps:
            rating_str = f"{a.average_rating:.1f}" if a.average_rating is not None else "-"
            reviews_str = str(a.review_count) if a.review_count is not None else "-"
            cat_str = ", ".join([c.slug for c in a.categories]) or "-"
            if len(cat_str) > 30:
                cat_str = cat_str[:27] + "..."
            name_display = a.app_name[:28] if len(a.app_name) > 28 else a.app_name
            slug_display = a.app_slug[:20] if len(a.app_slug) > 20 else a.app_slug

            print(f"{name_display:<30} {slug_display:<22} {rating_str:<8} {reviews_str:<9} {cat_str}")

        print("=" * 76 + "\n")

    return True


def main(argv: list[str] | None = None) -> int:
    """CLI entry-point for database verification."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
            sys.stderr.reconfigure(errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        prog="python -m experiment.verify_database",
        description="Phase 3: Verify PostgreSQL database records, schema, and statistics.",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=10,
        help="Number of sample apps to display. (default: 10)",
    )
    args = parser.parse_args(argv)

    success = verify_database(sample_limit=args.sample_limit)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
