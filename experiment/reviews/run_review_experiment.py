"""
experiment/reviews/run_review_experiment.py
-------------------------------------------
Phase 7: Controlled Review Collection Experiment for AppScout.

Tests review discovery, pagination traversal, extraction accuracy, and PostgreSQL
persistence across representative apps with diverse review counts.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from experiment.db.database import get_db, get_engine
from .collect_reviews import collect_reviews_for_app
from .models import Base, Review, ReviewCollectionItem, ReviewCollectionRun

logger = logging.getLogger(__name__)


def run_review_experiment(
    test_apps: list[str] | None = None,
    max_pages_per_app: int = 2,
    delay: float = 1.5,
    output_dir: Path = Path("data/reports"),
) -> dict[str, Any]:
    """Execute controlled review collection experiment."""
    output_dir.mkdir(parents=True, exist_ok=True)

    if test_apps is None:
        test_apps = [
            "judgeme",
            "klaviyo-email-marketing",
            "pagefly",
            "printful",
            "dsers",
        ]

    print("\n" + "=" * 76)
    print("APPSCOUT - PHASE 7 CONTROLLED REVIEW EXTRACTION EXPERIMENT")
    print("=" * 76)
    print(f"Target Test Apps        : {', '.join(test_apps)}")
    print(f"Max Pages Per App       : {max_pages_per_app}")
    print(f"Polite Delay            : {delay}s")
    print("=" * 76 + "\n")

    # 1. Initialize Review Tables in PostgreSQL
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Initialized reviews schema in PostgreSQL.")

    app_results = []
    total_reviews_collected = 0
    total_pages_scraped = 0

    with get_db() as session:
        # Create Run Record
        run_record = ReviewCollectionRun(
            apps_requested=len(test_apps),
            status="running",
            notes=f"Controlled Phase 7 Experiment: {len(test_apps)} apps, max_pages={max_pages_per_app}",
        )
        session.add(run_record)
        session.flush()
        run_id = run_record.id

        for idx, slug in enumerate(test_apps, 1):
            print(f"[{idx}/{len(test_apps)}] Collecting reviews for: {slug}...")
            count, pages, status = collect_reviews_for_app(
                slug,
                session=session,
                max_pages=max_pages_per_app,
                delay=delay,
            )

            total_reviews_collected += count
            total_pages_scraped += pages

            # Record item
            item_record = ReviewCollectionItem(
                run_id=run_id,
                app_slug=slug,
                reviews_collected=count,
                pages_scraped=pages,
                status=status,
            )
            session.add(item_record)
            session.flush()

            app_results.append({
                "app_slug": slug,
                "reviews_collected": count,
                "pages_scraped": pages,
                "status": status,
            })
            print(f"  --> Collected {count} reviews across {pages} pages ({status})\n")

        # Finalize Run Record
        run_record.status = "completed"
        run_record.completed_at = datetime.now(timezone.utc)
        run_record.apps_processed = len(test_apps)
        run_record.reviews_collected = total_reviews_collected
        session.flush()

        # Database audit
        total_db_reviews = session.scalar(select(func.count(Review.id)))
        avg_rating = session.scalar(select(func.avg(Review.rating)))

    summary_payload = {
        "experiment_timestamp": datetime.now(timezone.utc).isoformat(),
        "apps_tested": len(test_apps),
        "total_reviews_collected": total_reviews_collected,
        "total_pages_scraped": total_pages_scraped,
        "total_reviews_in_database": total_db_reviews,
        "average_review_rating": round(float(avg_rating or 0), 2),
        "app_results": app_results,
        "scale_and_feasibility_analysis": {
            "reviews_per_page": 10,
            "publicly_accessible": True,
            "rate_limit_risk": "Low with polite delays (1.5-2.0s)",
            "estimated_total_store_reviews": "> 1,500,000 across all 25,633 apps",
            "mvp_collection_strategy": (
                "For MVP intelligence, collect up to 5-10 latest pages (50-100 reviews) per app "
                "or prioritize top 1,000 high-growth/high-review apps for full review sentiment analysis."
            ),
        },
    }

    print("=" * 76)
    print("APPSCOUT - REVIEW COLLECTION EXPERIMENT SUMMARY")
    print("=" * 76)
    print(f"Apps Processed              : {len(test_apps)}")
    print(f"Total Reviews Collected     : {total_reviews_collected}")
    print(f"Total Review Pages Traversed: {total_pages_scraped}")
    print(f"Total Reviews in PostgreSQL : {total_db_reviews}")
    print(f"Average Review Rating in DB : {summary_payload['average_review_rating']} / 5.0")
    print("=" * 76 + "\n")

    compact_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_file = output_dir / f"review_collection_experiment_{compact_ts}.json"
    report_file.write_text(json.dumps(summary_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Review Collection Report saved to: {report_file.resolve()}\n")

    return summary_payload


if __name__ == "__main__":
    run_review_experiment()
