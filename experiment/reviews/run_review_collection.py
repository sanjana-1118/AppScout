"""
experiment/reviews/run_review_collection.py
-------------------------------------------
Production Review Intelligence Collection Pipeline for AppScout.

Collects structured merchant reviews for top priority Shopify apps:
- Deterministic priority selection based on review_count and average_rating.
- Multi-threaded bounded worker pool with per-thread DB sessions.
- SHA-256 review fingerprinting for strict idempotent deduplication.
- Checkpointing, resumability, and execution audit tracking.

Usage:
  python -m experiment.reviews.run_review_collection --limit 500 --reviews-per-app 50 --workers 4 --delay 0.8 --resume
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import desc, func, select

from experiment.db.database import get_db, SessionLocal
from experiment.db.models import App
from .collect_reviews import collect_reviews_for_app
from .models import Review, ReviewCollectionItem, ReviewCollectionRun

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("experiment.reviews.runner")


class AdaptiveReviewRateLimiter:
    """Thread-safe rate limiter for review page collection."""

    def __init__(self, delay_seconds: float = 0.8):
        self.delay = delay_seconds
        self.lock = threading.Lock()
        self.last_req = 0.0

    def wait(self) -> None:
        if self.delay <= 0:
            return
        with self.lock:
            now = time.time()
            elapsed = now - self.last_req
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)
            self.last_req = time.time()


def get_priority_apps(limit: int = 500) -> list[dict[str, Any]]:
    """Deterministically select top priority apps from PostgreSQL for review intelligence."""
    with get_db() as session:
        stmt = (
            select(App.id, App.app_slug, App.app_name, App.review_count, App.average_rating)
            .where(App.review_count != None)
            .where(App.review_count > 0)
            .order_by(desc(App.review_count), desc(App.average_rating), App.id.asc())
            .limit(limit)
        )
        rows = session.execute(stmt).all()

    priority_list = [
        {
            "id": r[0],
            "slug": r[1],
            "name": r[2],
            "review_count": r[3],
            "average_rating": float(r[4]) if r[4] is not None else None,
        }
        for r in rows
    ]
    return priority_list


def run_review_collection(
    limit: int = 500,
    reviews_per_app: int = 50,
    workers: int = 4,
    delay: float = 0.8,
    resume: bool = True,
    checkpoint_file: str | Path = "data/reviews/_review_collection_progress.json",
    raw_dir: str | Path = "data/raw",
) -> dict[str, Any]:
    chk_path = Path(checkpoint_file)
    chk_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Deterministic Priority Selection
    priority_apps = get_priority_apps(limit=limit)
    if not priority_apps:
        print("[WARNING] No priority apps found in PostgreSQL with review_count > 0. Ingestion may still be filling DB.")
        return {"status": "no_apps"}

    print("\n" + "=" * 76)
    print("APPSCOUT — PRODUCTION REVIEW INTELLIGENCE COLLECTION")
    print("=" * 76)
    print(f"Priority Selection Target  : {len(priority_apps):,} apps")
    print(f"Reviews Capped Per App     : {reviews_per_app} reviews")
    print(f"Worker Concurrency         : {workers} threads")
    print(f"Rate Delay                 : {delay}s / request")
    print(f"Resume Mode                : {resume}")
    print(f"Checkpoint File            : {chk_path.name}")
    print("=" * 76 + "\n")

    # 2. Checkpoint Resume
    processed_slugs: set[str] = set()
    checkpoint_state: dict[str, Any] = {}

    if resume and chk_path.exists():
        try:
            checkpoint_state = json.loads(chk_path.read_text(encoding="utf-8"))
            processed_slugs = set(checkpoint_state.get("processed_slugs", []))
            print(f"[RESUME] Loaded checkpoint: {len(processed_slugs):,} apps already completed.")
        except Exception as e:
            logger.warning("Failed to load checkpoint file: %s", e)

    # 3. Create Audit Run Record
    with get_db() as session:
        run_record = ReviewCollectionRun(
            apps_requested=len(priority_apps),
            status="running",
            notes=f"Priority: {len(priority_apps)} apps, Cap: {reviews_per_app} reviews, Workers: {workers}",
        )
        session.add(run_record)
        session.commit()
        run_id = run_record.id

    remaining_tasks = [a for a in priority_apps if a["slug"] not in processed_slugs]
    print(f"Apps Remaining to Process  : {len(remaining_tasks):,}\n")

    # 4. Concurrency State
    state_lock = threading.Lock()
    rate_limiter = AdaptiveReviewRateLimiter(delay_seconds=delay)
    
    total_reviews_collected = checkpoint_state.get("total_reviews_collected", 0)
    total_duplicates_avoided = checkpoint_state.get("total_duplicates_avoided", 0)
    total_pages_crawled = checkpoint_state.get("total_pages_crawled", 0)
    processed_count = len(processed_slugs)
    failed_count = 0
    start_time = time.time()

    def _save_checkpoint() -> None:
        state = {
            "run_id": run_id,
            "last_updated_at": datetime.now(timezone.utc).isoformat(),
            "processed_count": processed_count,
            "total_reviews_collected": total_reviews_collected,
            "total_duplicates_avoided": total_duplicates_avoided,
            "total_pages_crawled": total_pages_crawled,
            "processed_slugs": list(processed_slugs),
        }
        temp_file = chk_path.with_suffix(".tmp")
        temp_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        temp_file.replace(chk_path)

    # 5. Worker Function
    def _worker_task(app_info: dict[str, Any]) -> dict[str, Any]:
        nonlocal total_reviews_collected, total_duplicates_avoided
        nonlocal total_pages_crawled, processed_count, failed_count

        slug = app_info["slug"]
        rate_limiter.wait()

        with SessionLocal() as db_session:
            saved, dupes, pages, status = collect_reviews_for_app(
                slug,
                session=db_session,
                max_reviews=reviews_per_app,
                delay=delay,
                raw_dir=raw_dir,
            )

            # Audit Item
            audit_item = ReviewCollectionItem(
                run_id=run_id,
                app_slug=slug,
                reviews_collected=saved,
                pages_scraped=pages,
                status=status,
                error_message=None if status == "success" else status,
            )
            db_session.add(audit_item)
            db_session.commit()

        with state_lock:
            total_reviews_collected += saved
            total_duplicates_avoided += dupes
            total_pages_crawled += pages
            processed_slugs.add(slug)
            processed_count += 1
            if status != "success":
                failed_count += 1

            if processed_count % 10 == 0 or processed_count == len(priority_apps):
                _save_checkpoint()
                elapsed = max(time.time() - start_time, 0.1)
                rate = round(processed_count / (elapsed / 60.0), 1)
                print(
                    f"Progress: {processed_count}/{len(priority_apps)} apps ({round(processed_count/len(priority_apps)*100, 1)}%) | "
                    f"Reviews: {total_reviews_collected:,} | Duplicates Avoided: {total_duplicates_avoided:,} | "
                    f"Speed: {rate} apps/min"
                )

        return {
            "slug": slug,
            "reviews_saved": saved,
            "duplicates": dupes,
            "pages": pages,
            "status": status,
        }

    # 6. Execute Multi-Threaded Pool
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_worker_task, a): a for a in remaining_tasks}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.error("Unhandled worker exception: %s", e)

    # 7. Finalize Run Record
    _save_checkpoint()
    elapsed_total = max(time.time() - start_time, 0.1)

    with get_db() as final_session:
        run_obj = final_session.get(ReviewCollectionRun, run_id)
        if run_obj:
            run_obj.completed_at = datetime.now(timezone.utc)
            run_obj.status = "completed"
            run_obj.apps_processed = processed_count
            run_obj.reviews_collected = total_reviews_collected
            final_session.commit()

        total_reviews_in_db = final_session.scalar(select(func.count(Review.id))) or 0
        avg_rating = final_session.scalar(select(func.avg(Review.rating))) or 0.0

    print("\n" + "=" * 76)
    print("REVIEW INTELLIGENCE COLLECTION COMPLETED")
    print("=" * 76)
    print(f"Total Priority Apps Handled : {processed_count:,}")
    print(f"Total Reviews Collected     : {total_reviews_collected:,}")
    print(f"Total Duplicate Checks Avoid: {total_duplicates_avoided:,}")
    print(f"Total Review Pages Crawled  : {total_pages_crawled:,}")
    print(f"Total Reviews in PostgreSQL : {total_reviews_in_db:,}")
    print(f"Average Review Rating       : {avg_rating:.2f} / 5.0")
    print(f"Total Execution Time        : {elapsed_total:.2f}s")
    print("=" * 76 + "\n")

    return {
        "apps_processed": processed_count,
        "reviews_collected": total_reviews_collected,
        "duplicates_avoided": total_duplicates_avoided,
        "total_reviews_in_db": total_reviews_in_db,
        "avg_rating": float(avg_rating),
        "elapsed_seconds": elapsed_total,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AppScout Production Review Collector")
    parser.add_argument("--limit", type=int, default=500, help="Number of priority apps to collect")
    parser.add_argument("--reviews-per-app", type=int, default=50, help="Maximum reviews to collect per app")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent worker threads")
    parser.add_argument("--delay", type=float, default=0.8, help="Polite rate delay between requests in seconds")
    parser.add_argument("--resume", action="store_true", default=True, help="Resume from checkpoint")
    args = parser.parse_args()

    run_review_collection(
        limit=args.limit,
        reviews_per_app=args.reviews_per_app,
        workers=args.workers,
        delay=args.delay,
        resume=args.resume,
    )
