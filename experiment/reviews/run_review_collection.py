"""
experiment/reviews/run_review_collection.py
-------------------------------------------
AppScout Production Review Collection Engine for Neon Cloud PostgreSQL.

High-Speed Adaptive Review Collector:
- Collects ALL available reviews for every eligible app without arbitrary caps.
- Dynamic worker auto-scaling: Starts with 10 workers, tests 20 apps, and safely scales to 20 workers.
- Automated error backpressure: Monitors HTTP 429s, network timeouts, and Neon DB load,
  automatically reducing active workers and increasing delay if any contention is detected.
- Detects Shopify 1,000-page limit and marks apps as 'capped_shopify_limit' to avoid restarting.
- Resumes strictly from unfinished apps, preventing duplicate crawls.
- Transactional per-page and per-app persistence directly into Neon PostgreSQL.
- Checkpointing, instant resumability, and live audit logging.

Usage:
  # Check live database and collection progress:
  python -m experiment.reviews.run_review_collection --status

  # Run Phase 1 Test (20 apps, 10 workers) and automatically scale to 20 workers:
  python -m experiment.reviews.run_review_collection --batch-size 20 --workers 10 --max-workers 20 --auto-scale --resume
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
from sqlalchemy.orm import Session

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


class AdaptiveConcurrencyController:
    """Dynamic concurrency and error backpressure controller.

    Monitors HTTP response codes (e.g. 429 rate limits), timeouts, and database connection
    latencies. Uses a thread-safe Condition variable to dynamically gate worker threads between
    min_workers and max_workers (up to 30).
    """

    def __init__(
        self,
        initial_workers: int = 12,
        max_workers: int = 30,
        min_workers: int = 2,
        base_delay: float = 0.5,
    ):
        self.max_workers = max_workers
        self.min_workers = min_workers
        self.current_workers = min(initial_workers, max_workers)
        self.base_delay = base_delay
        self.current_delay = base_delay

        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._active_slots = 0
        self._consecutive_success = 0
        self._total_429s = 0
        self._total_timeouts = 0
        self._total_db_errors = 0
        self._total_reviews_collected = 0
        self._start_time = time.time()

    def acquire_slot(self) -> None:
        """Block until an active concurrency slot is available."""
        with self._lock:
            while self._active_slots >= self.current_workers:
                self._cv.wait(timeout=0.5)
            self._active_slots += 1

    def release_slot(self) -> None:
        """Release an active concurrency slot."""
        with self._lock:
            self._active_slots = max(0, self._active_slots - 1)
            self._cv.notify_all()

    def get_delay(self) -> float:
        """Return the current dynamic rate delay in seconds."""
        with self._lock:
            return self.current_delay

    def record_success(self, reviews_saved: int = 0) -> None:
        """Record a successful app/page scrape and evaluate ramp-up towards target max_workers."""
        with self._lock:
            self._consecutive_success += 1
            self._total_reviews_collected += reviews_saved
            # After 10 consecutive successful page scrapes, step delay down or workers up
            if self._consecutive_success >= 10:
                self._consecutive_success = 0
                changed = False
                old_workers = self.current_workers
                old_delay = self.current_delay
                if self.current_delay > self.base_delay:
                    self.current_delay = max(self.base_delay, round(self.current_delay - 0.1, 2))
                    changed = True
                elif self.current_workers < self.max_workers:
                    self.current_workers = min(self.max_workers, self.current_workers + 1)
                    changed = True

                if changed:
                    logger.info(
                        "[AUTO-SCALE] Responses healthy (0 errors). Concurrency: %d -> %d workers (delay: %.2fs -> %.2fs)",
                        old_workers,
                        self.current_workers,
                        old_delay,
                        self.current_delay,
                    )
                    self._cv.notify_all()

    def record_error(self, err_msg: str) -> None:
        """Record an error and trigger dynamic backpressure / auto-reduction."""
        err_lower = err_msg.lower()
        with self._lock:
            self._consecutive_success = 0
            is_429 = "429" in err_lower
            is_timeout = "timeout" in err_lower
            is_db_err = any(k in err_lower for k in ("pool", "connection", "operationalerror", "timeout expired"))

            if is_429:
                self._total_429s += 1
            elif is_timeout:
                self._total_timeouts += 1
            elif is_db_err:
                self._total_db_errors += 1

            if is_429 or is_timeout or is_db_err:
                old_workers = self.current_workers
                self.current_workers = max(self.min_workers, self.current_workers - 2)
                self.current_delay = min(1.5, round(self.current_delay + 0.25, 2))
                logger.warning(
                    "[AUTO-THROTTLE DOWN] %s detected. Downshifting concurrency: %d -> %d workers, increasing delay to %.2fs (Total 429s: %d, timeouts: %d, DB errors: %d)",
                    "Rate limit (HTTP 429)" if is_429 else ("Timeout" if is_timeout else "Database error"),
                    old_workers,
                    self.current_workers,
                    self.current_delay,
                    self._total_429s,
                    self._total_timeouts,
                    self._total_db_errors,
                )
                self._cv.notify_all()

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            elapsed = max(time.time() - self._start_time, 0.1)
            rev_per_min = round(self._total_reviews_collected / (elapsed / 60.0), 1)
            return {
                "active_workers": self.current_workers,
                "current_delay": round(self.current_delay, 2),
                "reviews_per_minute": rev_per_min,
                "total_reviews_in_run": self._total_reviews_collected,
                "total_429s": self._total_429s,
                "total_timeouts": self._total_timeouts,
                "total_db_errors": self._total_db_errors,
                "elapsed_seconds": round(elapsed, 1),
            }


def get_completed_app_slugs(session: Session) -> set[str]:
    """Return slugs of apps that are genuinely and fully completed in Neon PostgreSQL.

    An app is ONLY considered completed if:
    1. It has a recorded ReviewCollectionItem with status in ('completed', 'capped_shopify_limit'), OR
    2. Its stored review count in Neon meets or exceeds its known review_count in the App table, OR
    3. It has stored >= 10,000 reviews in Neon (Shopify's public review ceiling).

    Apps with partial reviews (e.g. 50 reviews stored when 1,000 are available) are NOT complete
    and will be resumed to collect all remaining missing reviews.
    """
    # 1. Apps with recorded completed or capped_shopify_limit audit status
    completed_audit_slugs = set(
        session.scalars(
            select(ReviewCollectionItem.app_slug)
            .where(ReviewCollectionItem.status.in_(["completed", "capped_shopify_limit"]))
        ).all()
    )

    # 2. Apps whose collected review count in DB meets or exceeds App.review_count OR is >= 10,000
    review_counts = session.execute(
        select(Review.app_slug, func.count(Review.id), App.review_count)
        .outerjoin(App, Review.app_slug == App.app_slug)
        .group_by(Review.app_slug, App.review_count)
    ).all()

    target_satisfied_slugs = set()
    for slug, count_in_db, known_rc in review_counts:
        if count_in_db:
            if count_in_db >= 10000:
                target_satisfied_slugs.add(slug)
            elif known_rc and count_in_db >= known_rc:
                target_satisfied_slugs.add(slug)

    return completed_audit_slugs.union(target_satisfied_slugs)


def get_collection_status(print_output: bool = True) -> dict[str, Any]:
    """Inspect the live Neon database and return an exact audit of collection progress."""
    with get_db() as session:
        total_eligible = session.scalar(select(func.count(App.id)).where(App.review_count > 0)) or 0
        total_reviews_in_neon = session.scalar(select(func.count(Review.id))) or 0
        distinct_apps_with_reviews = session.scalar(select(func.count(func.distinct(Review.app_slug)))) or 0
        avg_rating = session.scalar(select(func.avg(Review.rating))) or 0.0

        # Genuinely completed apps
        completed_slugs = get_completed_app_slugs(session)
        fully_completed_count = len(completed_slugs)

        # Capped at 1000-page limit apps
        capped_count = session.scalar(
            select(func.count(func.distinct(ReviewCollectionItem.app_slug)))
            .where(ReviewCollectionItem.status == "capped_shopify_limit")
        ) or 0

        # Count partial vs zero
        rev_counts = dict(
            session.execute(
                select(Review.app_slug, func.count(Review.id)).group_by(Review.app_slug)
            ).all()
        )

        all_eligible = session.execute(
            select(App.app_slug, App.review_count).where(App.review_count > 0)
        ).all()

        partially_collected = 0
        zero_collected = 0

        for slug, rc in all_eligible:
            if slug in completed_slugs:
                continue
            collected = rev_counts.get(slug, 0)
            if collected > 0:
                partially_collected += 1
            else:
                zero_collected += 1

        total_remaining = partially_collected + zero_collected

        # Latest run info
        latest_run = session.scalars(
            select(ReviewCollectionRun).order_by(desc(ReviewCollectionRun.id))
        ).first()

    status_data = {
        "total_eligible_apps": total_eligible,
        "fully_completed_apps": fully_completed_count,
        "capped_at_limit_apps": capped_count,
        "partially_collected_apps": partially_collected,
        "zero_collected_apps": zero_collected,
        "total_remaining_apps": total_remaining,
        "total_reviews_in_neon": total_reviews_in_neon,
        "distinct_apps_with_reviews": distinct_apps_with_reviews,
        "avg_rating": float(avg_rating),
        "latest_run_id": latest_run.id if latest_run else None,
        "latest_run_status": latest_run.status if latest_run else None,
    }

    if print_output:
        pct_done = round(fully_completed_count / max(total_eligible, 1) * 100, 2)
        print("\n" + "=" * 76)
        print("APPSCOUT -- LIVE REVIEW COLLECTION STATUS (NEON CLOUD DATABASE)")
        print("=" * 76)
        print(f"Total Eligible Apps (review_count > 0) : {total_eligible:,}")
        print(f"Genuinely Completed Apps               : {fully_completed_count:,} ({pct_done}%)")
        print(f"Capped at Shopify 1,000-Page Limit     : {capped_count:,} apps")
        print(f"Partially Collected Apps (Need More)   : {partially_collected:,}")
        print(f"Zero Reviews Collected (Unstarted)     : {zero_collected:,}")
        print(f"Total Apps Remaining to Collect        : {total_remaining:,}")
        print("-" * 76)
        print(f"Total Merchant Reviews in Neon DB      : {total_reviews_in_neon:,}")
        print(f"Distinct Apps with Reviews in Neon     : {distinct_apps_with_reviews:,}")
        print(f"Average Review Rating in Neon          : {avg_rating:.2f} / 5.0")
        if latest_run:
            print(f"Latest Run ID: #{latest_run.id} | Status: {latest_run.status} | Apps: {latest_run.apps_processed} | Reviews: {latest_run.reviews_collected}")
        print("=" * 76 + "\n")

    return status_data


def get_priority_apps(
    limit: int | None = None,
    exclude_collected: bool = True,
    sort_order: str = "asc",
) -> list[dict[str, Any]]:
    """Deterministically select priority apps from Neon PostgreSQL for review intelligence.

    If exclude_collected is True, only apps that are already fully completed are omitted.
    Partially collected apps are included so their collection continues to completion.
    """
    with get_db() as session:
        stmt = (
            select(App.id, App.app_slug, App.app_name, App.review_count, App.average_rating)
            .where(App.review_count != None)
            .where(App.review_count > 0)
        )
        if exclude_collected:
            completed_slugs = get_completed_app_slugs(session)
            if completed_slugs:
                stmt = stmt.where(~App.app_slug.in_(completed_slugs))

        if sort_order == "asc":
            stmt = stmt.order_by(App.review_count.asc(), desc(App.average_rating), App.id.asc())
        else:
            stmt = stmt.order_by(desc(App.review_count), desc(App.average_rating), App.id.asc())

        if limit and limit > 0:
            stmt = stmt.limit(limit)

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


def run_batch(
    apps: list[dict[str, Any]],
    controller: AdaptiveConcurrencyController,
    max_reviews_per_app: int | None = None,
    checkpoint_file: str | Path = "data/reviews/_review_collection_progress.json",
    raw_dir: str | Path = "data/raw",
) -> dict[str, Any]:
    """Execute collection for a single batch of apps using dynamic concurrency."""
    chk_path = Path(checkpoint_file)
    chk_path.parent.mkdir(parents=True, exist_ok=True)

    # Checkpoint state
    processed_slugs: set[str] = set()
    with get_db() as session:
        processed_slugs.update(get_completed_app_slugs(session))

    if chk_path.exists():
        try:
            state = json.loads(chk_path.read_text(encoding="utf-8"))
            processed_slugs.update(state.get("processed_slugs", []))
        except Exception as e:
            logger.warning("Failed to load checkpoint file: %s", e)

    remaining = [a for a in apps if a["slug"] not in processed_slugs]
    if not remaining:
        return {
            "processed": 0,
            "reviews_saved": 0,
            "duplicates": 0,
            "pages": 0,
            "errors": 0,
            "capped": 0,
            "elapsed": 0.0,
        }

    mode_label = "ALL AVAILABLE REVIEWS (No Cap)" if max_reviews_per_app is None else f"Capped at {max_reviews_per_app}"

    # Audit Run Record in PostgreSQL
    with get_db() as session:
        run_record = ReviewCollectionRun(
            apps_requested=len(remaining),
            status="running",
            notes=(
                f"Batch Collection: {len(remaining)} apps, Workers: {controller.current_workers}, Strategy: {mode_label}"
            ),
        )
        session.add(run_record)
        session.commit()
        run_id = run_record.id

    state_lock = threading.Lock()
    total_reviews_collected = 0
    total_duplicates_avoided = 0
    total_pages_crawled = 0
    completed_in_batch = 0
    capped_in_batch = 0
    failed_in_batch = 0
    start_time = time.time()

    def _save_checkpoint() -> None:
        state = {
            "run_id": run_id,
            "last_updated_at": datetime.now(timezone.utc).isoformat(),
            "total_completed_apps": len(processed_slugs),
            "completed_in_this_batch": completed_in_batch,
            "total_reviews_collected_in_batch": total_reviews_collected,
            "total_duplicates_avoided": total_duplicates_avoided,
            "total_pages_crawled": total_pages_crawled,
            "failed_apps_count": failed_in_batch,
            "processed_slugs": sorted(list(processed_slugs)),
        }
        temp_file = chk_path.with_suffix(".tmp")
        temp_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        for _ in range(5):
            try:
                temp_file.replace(chk_path)
                break
            except (PermissionError, OSError):
                time.sleep(0.1)

    def _worker_task(app_info: dict[str, Any]) -> dict[str, Any]:
        nonlocal total_reviews_collected, total_duplicates_avoided
        nonlocal total_pages_crawled, completed_in_batch, failed_in_batch, capped_in_batch

        slug = app_info["slug"]
        known_rc = app_info.get("review_count") or 0

        controller.acquire_slot()
        try:
            import random
            time.sleep(random.uniform(0.1, 0.4))
            worker_delay = controller.get_delay()

            with SessionLocal() as db_session:
                saved, dupes, pages, status = collect_reviews_for_app(
                    slug,
                    session=db_session,
                    max_reviews=max_reviews_per_app,
                    delay=worker_delay,
                    raw_dir=raw_dir,
                    on_page_success=controller.record_success,
                    on_error=controller.record_error,
                )

                if status in ("completed", "capped", "success"):
                    item_status = "completed"
                    err_msg = None
                elif status == "capped_shopify_limit":
                    item_status = "capped_shopify_limit"
                    err_msg = "Reached Shopify 1,000-page limit (10,000 reviews). Shopify returns 404 for page 1001."
                elif status == "not_found":
                    item_status = "not_found"
                    err_msg = "Shopify review page returned HTTP 404 (App or reviews not found)"
                else:
                    item_status = "failed"
                    err_msg = str(status)[:1000]
                    controller.record_error(err_msg)

            with SessionLocal() as audit_session:
                audit_item = ReviewCollectionItem(
                    run_id=run_id,
                    app_slug=slug,
                    reviews_collected=saved,
                    pages_scraped=pages,
                    status=item_status,
                    error_message=err_msg,
                )
                audit_session.add(audit_item)
                audit_session.commit()

            with state_lock:
                total_reviews_collected += saved
                total_duplicates_avoided += dupes
                total_pages_crawled += pages
                completed_in_batch += 1

                if status == "capped_shopify_limit":
                    capped_in_batch += 1
                    processed_slugs.add(slug)
                elif status in ("completed", "capped", "success"):
                    processed_slugs.add(slug)
                else:
                    failed_in_batch += 1

                elapsed = max(time.time() - start_time, 0.1)
                rate = round(completed_in_batch / (elapsed / 60.0), 1)
                pct = round(completed_in_batch / max(len(remaining), 1) * 100, 1)

                display_status = status
                if status == "capped_shopify_limit":
                    display_status = "CAPPED_AT_SHOPIFY_LIMIT"

                logger.info(
                    "App %s completed: +%d revs (%d pgs), status: %s",
                    slug, saved, pages, display_status,
                )
                print(
                    f"[{completed_in_batch:>3}/{len(remaining)} - {pct:>5.1f}%] "
                    f"App: {slug:<30} ({known_rc:>5} store) | "
                    f"+{saved:>3} revs ({pages:>2} pgs) | "
                    f"Batch Total: {total_reviews_collected:>5,} | "
                    f"Speed: {rate:>4.1f} apps/min | Status: {display_status}",
                    flush=True,
                )

                _save_checkpoint()

            return {
                "slug": slug,
                "reviews_saved": saved,
                "duplicates": dupes,
                "pages": pages,
                "status": status,
            }
        finally:
            controller.release_slot()

    try:
        # Launch with thread pool sized to max_workers
        with ThreadPoolExecutor(max_workers=controller.max_workers) as executor:
            futures = {executor.submit(_worker_task, a): a for a in remaining}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error("Unhandled worker exception: %s", e)
    except KeyboardInterrupt:
        print("\n[PAUSE] Batch interrupted by user (Ctrl+C). Saving checkpoint...")
    finally:
        _save_checkpoint()

    elapsed = max(time.time() - start_time, 0.1)

    # Finalize Run Record
    try:
        with get_db() as final_session:
            run_obj = final_session.get(ReviewCollectionRun, run_id)
            if run_obj:
                run_obj.completed_at = datetime.now(timezone.utc)
                run_obj.status = "completed" if completed_in_batch >= len(remaining) else "interrupted"
                run_obj.apps_processed = completed_in_batch
                run_obj.reviews_collected = total_reviews_collected
                final_session.commit()
    except Exception as exc:
        logger.warning("Could not finalize Run Record due to transient network/DB issue: %s", exc)

    return {
        "processed": completed_in_batch,
        "reviews_saved": total_reviews_collected,
        "duplicates": total_duplicates_avoided,
        "pages": total_pages_crawled,
        "errors": failed_in_batch,
        "capped": capped_in_batch,
        "elapsed": elapsed,
    }


def run_review_collection(
    limit: int | None = None,
    batch_size: int = 20,
    max_reviews_per_app: int | None = None,
    workers: int = 10,
    max_workers: int = 20,
    delay: float = 0.4,
    resume: bool = True,
    exclude_collected: bool = True,
    auto_scale: bool = True,
    sort_order: str = "asc",
    checkpoint_file: str | Path = "data/reviews/_review_collection_progress.json",
    raw_dir: str | Path | None = None,
) -> None:
    """Execute high-speed review collection in progressive stages."""
    print("\n" + "=" * 76)
    print("APPSCOUT -- HIGH-SPEED ADAPTIVE REVIEW COLLECTION")
    print("=" * 76)
    print(f"Initial Test Batch Size : {batch_size} apps")
    print(f"Initial Worker Threads  : {workers} concurrent workers")
    print(f"Target Max Workers      : {max_workers} concurrent workers")
    print(f"Base Polite Delay       : {delay}s / request")
    print(f"Queue Sort Order        : {sort_order.upper()} (Smallest reviews first: {sort_order == 'asc'})")
    print(f"In-Memory HTML Mode     : {'Enabled (Zero disk I/O latency)' if raw_dir is None else f'Saving to {raw_dir}'}")
    print(f"Auto-Scaling Enabled    : {auto_scale}")
    print(f"Resume Mode             : {resume}")
    print("=" * 76 + "\n")

    controller = AdaptiveConcurrencyController(
        initial_workers=workers,
        max_workers=max_workers,
        min_workers=2,
        base_delay=delay,
    )

    batch_number = 1
    current_batch_size = batch_size

    while True:
        # Fetch next remaining priority apps with retry for transient network hiccups
        try:
            priority_apps = get_priority_apps(
                limit=current_batch_size,
                exclude_collected=exclude_collected,
                sort_order=sort_order,
            )
        except Exception as q_exc:
            logger.warning("Transient error querying priority queue (%s). Retrying in 5s...", q_exc)
            time.sleep(5)
            continue

        if not priority_apps:
            print("\n[COMPLETE] All eligible Shopify apps in Neon database are fully completed!")
            break

        print("\n" + "-" * 76)
        print(f"STARTING BATCH #{batch_number} -- {len(priority_apps)} APPS (Active Workers: {controller.current_workers}, Delay: {controller.current_delay:.2f}s, Order: {sort_order})")
        print("-" * 76)

        batch_result = run_batch(
            apps=priority_apps,
            controller=controller,
            max_reviews_per_app=max_reviews_per_app,
            checkpoint_file=checkpoint_file,
            raw_dir=raw_dir,
        )

        stats = controller.get_stats()
        speed_apps_min = round(batch_result["processed"] / max(batch_result["elapsed"] / 60.0, 0.01), 1)
        revs_per_min = stats["reviews_per_minute"]

        print("\n" + "=" * 76)
        print(f"BATCH #{batch_number} SUMMARY")
        print("=" * 76)
        print(f"Apps Processed in Batch     : {batch_result['processed']:,} / {len(priority_apps):,}")
        print(f"Reviews Saved to Neon       : {batch_result['reviews_saved']:,}")
        print(f"Duplicates Avoided          : {batch_result['duplicates']:,}")
        print(f"Pages Scraped               : {batch_result['pages']:,}")
        print(f"Apps Capped at Shopify Limit: {batch_result['capped']:,}")
        print(f"Failed / Errored Apps       : {batch_result['errors']:,}")
        print(f"HTTP 429 Rate Limits Hit    : {stats['total_429s']}")
        print(f"Network Timeouts            : {stats['total_timeouts']}")
        print(f"Database Pool Errors        : {stats['total_db_errors']}")
        print(f"Active Worker Concurrency   : {stats['active_workers']} workers (delay: {stats['current_delay']}s)")
        print(f"Ingestion Throughput Speed  : {revs_per_min} reviews/min ({speed_apps_min} apps/min)")
        print(f"Batch Elapsed Time          : {batch_result['elapsed']:.1f}s")
        print("=" * 76 + "\n", flush=True)

        # Evaluate scaling criteria
        if batch_number == 1 and auto_scale:
            if batch_result["errors"] == 0 and stats["total_429s"] == 0 and stats["total_db_errors"] == 0:
                print(">> [HEALTHY TEST] Initial batch passed with 0 errors and zero DB contention!")
                print(f">> [SCALE UP] Gradually scaling concurrency toward {max_workers} concurrent workers...\n", flush=True)
                current_batch_size = max(current_batch_size, batch_size)
            else:
                print(">> [MONITOR] Contention detected during initial batch. Maintaining stable concurrency.\n", flush=True)
                current_batch_size = max(20, batch_size)

        batch_number += 1

        # Check total remaining apps with transient error protection
        try:
            with get_db() as check_session:
                completed_count = len(get_completed_app_slugs(check_session))
                total_eligible = check_session.scalar(select(func.count(App.id)).where(App.review_count > 0)) or 0
                remaining_total = total_eligible - completed_count
                print(f"[STATUS] Overall Progress: {completed_count:,} / {total_eligible:,} apps completed ({remaining_total:,} remaining)\n", flush=True)

                if remaining_total <= 0:
                    print("[SUCCESS] All eligible apps have been collected or reached the Shopify platform ceiling!", flush=True)
                    break
        except Exception as check_exc:
            logger.warning("Transient error checking overall progress status: %s", check_exc)

    # Final live status
    get_collection_status(print_output=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AppScout Production Review Collector")
    parser.add_argument("--status", action="store_true", help="Check live Neon database review collection status")
    parser.add_argument("--batch-size", type=int, default=30, help="Batch size (default: 30)")
    parser.add_argument("--workers", type=int, default=16, help="Initial concurrent worker threads (default: 16)")
    parser.add_argument("--max-workers", type=int, default=30, help="Target max concurrent worker threads (default: 30)")
    parser.add_argument("--delay", type=float, default=0.5, help="Polite base rate delay in seconds (default: 0.5)")
    parser.add_argument("--sort-order", choices=["asc", "desc"], default="asc", help="Queue sort order (default: asc for smallest apps first)")
    parser.add_argument("--raw-dir", type=str, default=None, help="Directory to save raw HTML files (default: None for in-memory streaming)")
    parser.add_argument("--limit", type=int, default=None, help="Total limit of apps to process")
    parser.add_argument("--max-reviews-per-app", type=int, default=None, help="Cap reviews per app (default: None, collects ALL available reviews)")
    parser.add_argument("--resume", action="store_true", default=True, help="Resume from checkpoint and DB state (default: True)")
    parser.add_argument("--auto-scale", action="store_true", default=True, help="Automatically scale workers if healthy (default: True)")
    args = parser.parse_args()

    if args.status:
        get_collection_status(print_output=True)
        sys.exit(0)

    run_review_collection(
        limit=args.limit,
        batch_size=args.batch_size,
        max_reviews_per_app=args.max_reviews_per_app,
        workers=args.workers,
        max_workers=args.max_workers,
        delay=args.delay,
        resume=args.resume,
        auto_scale=args.auto_scale,
        sort_order=args.sort_order,
        raw_dir=args.raw_dir,
    )
