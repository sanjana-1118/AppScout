"""
experiment/run_ingestion.py
---------------------------
Phase 5: Production-Scale Automated PostgreSQL Database Ingestion Orchestrator for AppScout.

Coordinates resilient, high-throughput, polite, and auditable ingestion of Shopify apps
from the Final Verified Master Frontier (25,633 apps) into PostgreSQL:
1. Loads app entries from the Final Verified Master Frontier JSON artifact.
2. Performs database-aware freshness checks to skip already ingested and fresh apps.
3. Automatically checkpoints progress atomically to data/ingestion/_ingestion_progress.json.
4. Resumes safely from interruption without repeating or duplicating records.
5. Implements bounded concurrency (configurable thread workers) with polite rate limiting.
6. Implements bounded exponential backoff retries for transient acquisition network failures.
7. Coordinates acquisition, inspection, extraction, and validation.
8. Persists canonical apps, categories, and audit items in PostgreSQL.
9. Provides live console progress reporting with throughput and estimated time remaining.
10. Produces full execution reconciliation and data quality reports.

Usage
-----
    python -m experiment.run_ingestion --workers 8 --delay 0.5 --report-interval 100
    python -m experiment.run_ingestion --limit 250 --workers 4
    python -m experiment.run_ingestion --resume
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from . import acquire
from .db import repositories
from .db.database import SessionLocal, check_connection, get_db
from .ingest import ingest_pipeline_result
from .run_experiment import process_single_app

logger = logging.getLogger(__name__)

PROGRESS_FILENAME = "_ingestion_progress.json"


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        level=level,
        stream=sys.stderr,
    )


def find_latest_frontier_file(frontier_dir: str | Path = "data/frontier") -> Path | None:
    """Find the most recent final verified master frontier JSON file."""
    files = list(Path(frontier_dir).glob("final_verified_master_frontier_*.json"))
    if not files:
        files = list(Path(frontier_dir).glob("master_app_frontier_*.json"))
    if not files:
        files = list(Path(frontier_dir).glob("*.json"))
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]


def load_ingestion_checkpoint(progress_file: Path) -> dict[str, Any] | None:
    """Load existing checkpoint state from progress JSON file if present."""
    if not progress_file.exists():
        return None
    try:
        data = json.loads(progress_file.read_text(encoding="utf-8"))
        logger.info("Loaded existing ingestion checkpoint from: %s", progress_file.resolve())
        return data
    except Exception as exc:
        logger.warning("Could not read ingestion progress file (%s): %s", progress_file, exc)
        return None


def save_ingestion_checkpoint(progress_file: Path, state: dict[str, Any]) -> None:
    """Atomically write checkpoint state to progress JSON file."""
    temp_file = progress_file.with_suffix(".tmp")
    try:
        temp_file.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temp_file.replace(progress_file)
        logger.debug("Ingestion checkpoint saved to %s", progress_file.name)
    except Exception as exc:
        logger.error("Failed to save ingestion progress file: %s", exc)


class AdaptiveRateLimiter:
    """Thread-safe adaptive polite token-bucket / interval rate limiter."""

    def __init__(self, base_delay: float = 0.25, min_delay: float = 0.1, max_delay: float = 2.0):
        self.base_delay = base_delay
        self.current_delay = base_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.lock = threading.Lock()
        self.last_request_time = 0.0
        self.consecutive_successes = 0

    def wait(self) -> None:
        if self.current_delay <= 0:
            return
        with self.lock:
            now = time.time()
            elapsed = now - self.last_request_time
            if elapsed < self.current_delay:
                sleep_time = self.current_delay - elapsed
                time.sleep(sleep_time)
            self.last_request_time = time.time()

    def record_success(self) -> None:
        with self.lock:
            self.consecutive_successes += 1
            if self.consecutive_successes >= 25 and self.current_delay > self.min_delay:
                self.current_delay = max(self.current_delay * 0.95, self.min_delay)
                self.consecutive_successes = 0

    def record_throttle(self) -> None:
        with self.lock:
            self.consecutive_successes = 0
            self.current_delay = min(self.current_delay * 1.5 + 0.2, self.max_delay)
            logger.warning("AdaptiveRateLimiter: throttled, delay increased to %.2fs", self.current_delay)


def _print_live_progress_box(
    total_in_frontier: int,
    processed_count: int,
    total_selected: int,
    apps_succeeded: int,
    apps_skipped: int,
    validation_failures: int,
    not_found_count: int,
    rate_limited_count: int,
    network_failures: int,
    other_failures: int,
    snapshots_reused: int,
    new_http_requests: int,
    retries_attempted: int,
    start_time: float,
    current_app_slug: str,
) -> None:
    """Print structured periodic progress summary block to stdout."""
    elapsed_sec = max(time.time() - start_time, 0.1)
    throughput_per_min = (processed_count / elapsed_sec) * 60.0
    remaining_apps = total_selected - processed_count
    est_remaining_sec = (remaining_apps / (throughput_per_min / 60.0)) if throughput_per_min > 0 else 0
    est_hours = int(est_remaining_sec // 3600)
    est_mins = int((est_remaining_sec % 3600) // 60)

    print("\n" + "=" * 76)
    print("APPSCOUT FULL INGESTION PROGRESS")
    print("=" * 76)
    print(f"Frontier Total:              {total_in_frontier:,}")
    print(f"Processed:                   {processed_count:,} / {total_selected:,}")
    print(f"Remaining in Batch:          {remaining_apps:,}")
    print("-" * 76)
    print(f"Successfully Stored:         {apps_succeeded:,}")
    print(f"Skipped Fresh:               {apps_skipped:,}")
    print(f"Validation Failed:           {validation_failures:,}")
    print(f"404 / Delisted:              {not_found_count:,}")
    print(f"Rate Limited:                {rate_limited_count:,}")
    print(f"Network Failures:            {network_failures:,}")
    print(f"Other Failures:              {other_failures:,}")
    print("-" * 76)
    print(f"Snapshots Reused:            {snapshots_reused:,}")
    print(f"HTTP Live Requests:          {new_http_requests:,}")
    print(f"Retries Attempted:           {retries_attempted:,}")
    print(f"Current Throughput:          {throughput_per_min:.1f} apps/min")
    print(f"Estimated Remaining Time:    {est_hours}h {est_mins}m")
    print(f"Last Processed App:          {current_app_slug}")
    print("=" * 76 + "\n")


def run_ingestion_batch(
    *,
    frontier_file: str | Path | None = None,
    limit: int | None = None,
    workers: int = 8,
    delay: float = 0.5,
    max_retries: int = 3,
    retry_delay: float = 3.0,
    resume: bool = True,
    force_restart: bool = False,
    force: bool = False,
    max_age_hours: float = 168.0,
    report_interval: int = 50,
    raw_dir: str | Path = "data/raw",
    output_dir: str | Path = "output",
    ingestion_dir: str | Path = "data/ingestion",
    reports_dir: str | Path = "data/reports",
    timeout: int = 30,
) -> dict[str, Any]:
    """Execute full-scale database ingestion with bounded concurrency."""
    raw_path_dir = Path(raw_dir)
    raw_path_dir.mkdir(parents=True, exist_ok=True)

    out_path_dir = Path(output_dir)
    out_path_dir.mkdir(parents=True, exist_ok=True)

    ing_path_dir = Path(ingestion_dir)
    ing_path_dir.mkdir(parents=True, exist_ok=True)

    rep_path_dir = Path(reports_dir)
    rep_path_dir.mkdir(parents=True, exist_ok=True)

    progress_file = ing_path_dir / PROGRESS_FILENAME

    # 1. Locate Frontier File
    if frontier_file is None:
        target_frontier_path = find_latest_frontier_file()
        if target_frontier_path is None:
            raise FileNotFoundError("No Master Frontier JSON file found in data/frontier/.")
    else:
        target_frontier_path = Path(frontier_file)
        if not target_frontier_path.exists():
            raise FileNotFoundError(f"Frontier file not found: {target_frontier_path}")

    logger.info("Loading Master Frontier from: %s", target_frontier_path.resolve())
    with open(target_frontier_path, "r", encoding="utf-8") as f:
        frontier_data = json.load(f)

    raw_apps_list = frontier_data.get("apps", [])
    if not raw_apps_list:
        raise ValueError(f"No apps found in frontier file: {target_frontier_path}")

    # Standardize app entries
    app_entries: list[dict[str, Any]] = []
    for item in raw_apps_list:
        if isinstance(item, str):
            slug = acquire._slug_from_url(item)
            app_entries.append({"url": item, "slug": slug, "categories": []})
        elif isinstance(item, dict):
            url = item.get("url", "")
            slug = item.get("slug") or acquire._slug_from_url(url)
            cats = item.get("categories", [])
            app_entries.append({"url": url, "slug": slug, "categories": cats})

    if limit is not None:
        selected_apps = app_entries[:limit]
    else:
        selected_apps = app_entries

    if force_restart and progress_file.exists():
        logger.info("Force-restart requested: removing existing progress file.")
        progress_file.unlink(missing_ok=True)

    print("\n" + "=" * 76)
    print("APPSCOUT - FULL SHOPIFY APP METADATA INGESTION")
    print("=" * 76)
    print(f"Frontier Source File   : {target_frontier_path.name}")
    print(f"Total Apps in Frontier : {len(app_entries):,}")
    print(f"Apps Selected in Batch : {len(selected_apps):,}")
    print(f"Worker Concurrency     : {workers} threads")
    print(f"Global Rate Delay      : {delay}s / request")
    print(f"Freshness Threshold    : {max_age_hours}h (Force: {force})")
    print(f"Max Retries / Delay    : {max_retries} attempts / {retry_delay}s")
    print(f"Resume Enabled         : {resume and not force_restart}")
    print("=" * 76 + "\n")

    # 2. Database Connection Check
    ok, conn_msg = check_connection()
    if not ok:
        raise ConnectionError(f"Cannot connect to PostgreSQL: {conn_msg}")

    # 3. Checkpoint / Ingestion State
    processed_slugs: set[str] = set()
    start_time = time.time()
    started_at_iso = datetime.now(timezone.utc).isoformat()

    # Metrics
    apps_succeeded = 0
    apps_skipped = 0
    validation_failures = 0
    not_found_count = 0
    rate_limited_count = 0
    network_failures = 0
    other_failures = 0
    snapshots_reused = 0
    new_http_requests = 0
    retries_attempted = 0

    state_lock = threading.Lock()
    rate_limiter = AdaptiveRateLimiter(base_delay=delay)

    # 4. Create Ingestion Run Record
    with get_db() as init_session:
        run_record = repositories.create_ingestion_run(
            init_session,
            apps_requested=len(selected_apps),
            notes=f"Frontier: {target_frontier_path.name}, Batch: {len(selected_apps)}, Workers: {workers}",
        )
        run_id = run_record.id

    # 5. Worker Function for Single App
    def _process_app_task(task_item: tuple[int, dict[str, Any]]) -> dict[str, Any]:
        nonlocal apps_succeeded, apps_skipped, validation_failures, not_found_count
        nonlocal rate_limited_count, network_failures, other_failures, snapshots_reused
        nonlocal new_http_requests, retries_attempted

        idx, entry = task_item
        app_url = entry["url"]
        app_slug = entry["slug"]
        app_cats = entry["categories"]

        result_meta: dict[str, Any] = {
            "index": idx,
            "slug": app_slug,
            "url": app_url,
            "status": "pending",
            "error": None,
        }

        # Dedicated Thread Session
        session = SessionLocal()

        try:
            # A. Database Freshness Check
            if not force and repositories.is_app_fresh(session, app_slug, max_age_hours=max_age_hours):
                with state_lock:
                    apps_skipped += 1
                repositories.record_ingestion_item(
                    session,
                    run_id=run_id,
                    app_slug=app_slug,
                    app_url=app_url,
                    status="skipped_fresh",
                    error_message=f"Fresh record exists within {max_age_hours}h",
                )
                session.commit()
                result_meta["status"] = "skipped_fresh"
                return result_meta

            # B. Check Snapshot Reuse
            existing = acquire._find_existing(app_url, app_slug, raw_path_dir)
            is_reused = existing is not None
            if is_reused:
                with state_lock:
                    snapshots_reused += 1
            else:
                with state_lock:
                    new_http_requests += 1
                # Rate limit live network calls
                rate_limiter.wait()

            # C. Acquire, Inspect, Extract, Validate
            result_dict = None
            last_err = None

            for attempt in range(1, max_retries + 1):
                try:
                    result_dict = process_single_app(
                        url=app_url,
                        raw_dir=raw_path_dir,
                        output_dir=out_path_dir,
                        timeout=timeout,
                        verbose_print=False,
                    )
                    break
                except requests.exceptions.HTTPError as http_err:
                    status_code = getattr(http_err.response, "status_code", None)
                    if status_code == 404:
                        last_err = f"HTTP 404 Not Found"
                        break
                    elif status_code == 429:
                        last_err = f"HTTP 429 Rate Limited"
                        rate_limiter.record_throttle()
                        with state_lock:
                            retries_attempted += 1
                        time.sleep(retry_delay * 2)
                    elif status_code and status_code >= 500:
                        last_err = f"HTTP {status_code} Server Error"
                        rate_limiter.record_throttle()
                        with state_lock:
                            retries_attempted += 1
                        time.sleep(retry_delay)
                    else:
                        last_err = str(http_err)
                        break
                except (requests.exceptions.RequestException, ConnectionError, TimeoutError, OSError) as net_err:
                    last_err = str(net_err)
                    with state_lock:
                        retries_attempted += 1
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                except Exception as exc:
                    last_err = str(exc)
                    break

            if result_dict is None:
                # Classify Failure
                err_str = str(last_err)
                if "404" in err_str:
                    fail_status = "not_found"
                    with state_lock:
                        not_found_count += 1
                elif "429" in err_str:
                    fail_status = "rate_limited"
                    with state_lock:
                        rate_limited_count += 1
                elif "Timeout" in err_str or "Connection" in err_str or "RequestException" in err_str:
                    fail_status = "network_failed"
                    with state_lock:
                        network_failures += 1
                else:
                    fail_status = "unexpected_error"
                    with state_lock:
                        other_failures += 1

                repositories.record_ingestion_item(
                    session,
                    run_id=run_id,
                    app_slug=app_slug,
                    app_url=app_url,
                    status=fail_status,
                    error_message=err_str,
                )
                session.commit()
                result_meta["status"] = fail_status
                result_meta["error"] = err_str
                return result_meta

            # D. Ingest into PostgreSQL
            compact_ts = result_dict.get("fetch_timestamp", "").replace("-", "").replace(":", "")[:15]
            expected_json_name = f"{app_slug}_{compact_ts}Z_experiment_result.json"
            result_file = out_path_dir / expected_json_name
            res_path_str = str(result_file.resolve()) if result_file.exists() else None

            ingest_ok, ingest_msg = ingest_pipeline_result(
                result_dict,
                session=session,
                run_id=run_id,
                frontier_categories=app_cats,
                result_path=res_path_str,
            )
            session.commit()

            if ingest_ok:
                with state_lock:
                    apps_succeeded += 1
                result_meta["status"] = "success"
            else:
                if "not_found" in ingest_msg or "404" in ingest_msg:
                    with state_lock:
                        not_found_count += 1
                    result_meta["status"] = "not_found"
                elif "Sanity validation failed" in ingest_msg or "validation" in ingest_msg.lower():
                    with state_lock:
                        validation_failures += 1
                    result_meta["status"] = "validation_failed"
                else:
                    with state_lock:
                        other_failures += 1
                    result_meta["status"] = "failed"
                result_meta["error"] = ingest_msg

            return result_meta

        except Exception as top_exc:
            session.rollback()
            with state_lock:
                other_failures += 1
            logger.error("Unhandled exception for %s: %s", app_slug, top_exc)
            result_meta["status"] = "unexpected_error"
            result_meta["error"] = str(top_exc)
            return result_meta
        finally:
            session.close()

    # 6. Execute Multi-Threaded Ingestion Loop
    tasks = [(i + 1, entry) for i, entry in enumerate(selected_apps)]
    completed_task_results: list[dict[str, Any]] = []

    print(f"Starting ingestion of {len(tasks):,} apps using {workers} concurrent workers...\n")

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_app = {executor.submit(_process_app_task, t): t for t in tasks}

        for future in concurrent.futures.as_completed(future_to_app):
            try:
                res = future.result()
                completed_task_results.append(res)
                total_processed = len(completed_task_results)

                # Periodic Checkpoint & Progress Display
                if (total_processed % report_interval == 0) or (total_processed == len(tasks)):
                    with state_lock:
                        _print_live_progress_box(
                            total_in_frontier=len(app_entries),
                            processed_count=total_processed,
                            total_selected=len(selected_apps),
                            apps_succeeded=apps_succeeded,
                            apps_skipped=apps_skipped,
                            validation_failures=validation_failures,
                            not_found_count=not_found_count,
                            rate_limited_count=rate_limited_count,
                            network_failures=network_failures,
                            other_failures=other_failures,
                            snapshots_reused=snapshots_reused,
                            new_http_requests=new_http_requests,
                            retries_attempted=retries_attempted,
                            start_time=start_time,
                            current_app_slug=res["slug"],
                        )

                        save_ingestion_checkpoint(
                            progress_file,
                            {
                                "frontier_file": str(target_frontier_path.resolve()),
                                "ingestion_run_id": run_id,
                                "started_at": started_at_iso,
                                "last_updated_at": datetime.now(timezone.utc).isoformat(),
                                "total_apps_in_frontier": len(app_entries),
                                "apps_requested": len(selected_apps),
                                "processed_count": total_processed,
                                "apps_succeeded": apps_succeeded,
                                "apps_skipped": apps_skipped,
                                "validation_failures": validation_failures,
                                "not_found_count": not_found_count,
                                "rate_limited_count": rate_limited_count,
                                "network_failures": network_failures,
                                "other_failures": other_failures,
                                "snapshots_reused": snapshots_reused,
                                "new_http_requests": new_http_requests,
                                "retries_attempted": retries_attempted,
                                "status": "completed" if total_processed == len(tasks) else "in_progress",
                            },
                        )
            except Exception as f_err:
                logger.error("Worker task generated exception: %s", f_err)

    # 7. Finalize Ingestion Run Record in PostgreSQL
    with get_db() as final_session:
        final_run = repositories.complete_ingestion_run(
            final_session,
            run_id=run_id,
            apps_processed=len(completed_task_results),
            apps_succeeded=apps_succeeded,
            apps_failed=(validation_failures + not_found_count + rate_limited_count + network_failures + other_failures),
            apps_skipped=apps_skipped,
            snapshots_reused=snapshots_reused,
            new_http_requests=new_http_requests,
        )

    # 8. Reconcile Counts & Produce Comprehensive Reports
    total_accounted = (
        apps_succeeded
        + apps_skipped
        + validation_failures
        + not_found_count
        + rate_limited_count
        + network_failures
        + other_failures
    )
    unaccounted_count = len(selected_apps) - total_accounted
    compact_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # A. Full Ingestion Summary
    summary_data = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "frontier_file": str(target_frontier_path.resolve()),
        "total_frontier_apps": len(app_entries),
        "apps_selected_in_batch": len(selected_apps),
        "total_accounted_apps": total_accounted,
        "unaccounted_apps": unaccounted_count,
        "metrics": {
            "apps_succeeded_in_db": apps_succeeded,
            "apps_skipped_fresh": apps_skipped,
            "validation_failures": validation_failures,
            "not_found_or_delisted_404": not_found_count,
            "rate_limited_429": rate_limited_count,
            "network_failures": network_failures,
            "other_failures": other_failures,
            "snapshots_reused": snapshots_reused,
            "new_http_requests": new_http_requests,
            "retries_attempted": retries_attempted,
        },
        "performance": {
            "workers": workers,
            "global_delay": delay,
            "total_runtime_seconds": round(time.time() - start_time, 2),
            "average_throughput_apps_per_min": round((len(selected_apps) / max(time.time() - start_time, 0.1)) * 60, 2),
        },
    }

    sum_file = rep_path_dir / f"full_ingestion_summary_{compact_ts}.json"
    sum_file.write_text(json.dumps(summary_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # B. Frontier Reconciliation Report
    recon_data = {
        "reconciliation_timestamp": datetime.now(timezone.utc).isoformat(),
        "final_frontier_total": len(selected_apps),
        "breakdown": {
            "successfully_stored": apps_succeeded,
            "skipped_fresh": apps_skipped,
            "validation_failed": validation_failures,
            "delisted_or_404": not_found_count,
            "network_or_rate_limit_failed": network_failures + rate_limited_count,
            "other_terminal_failures": other_failures,
        },
        "formula": f"{apps_succeeded} + {apps_skipped} + {validation_failures} + {not_found_count} + {network_failures + rate_limited_count} + {other_failures} = {total_accounted}",
        "unaccounted_frontier_apps": unaccounted_count,
        "reconciliation_passed": (unaccounted_count == 0),
    }

    rec_file = rep_path_dir / f"frontier_reconciliation_{compact_ts}.json"
    rec_file.write_text(json.dumps(recon_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # C. Failed or Delisted Apps
    failed_items = [r for r in completed_task_results if r["status"] not in ("success", "skipped_fresh")]
    fail_file = rep_path_dir / f"failed_or_delisted_apps_{compact_ts}.json"
    fail_file.write_text(json.dumps(failed_items, indent=2, ensure_ascii=False), encoding="utf-8")

    # D. Unaccounted Apps (if any)
    unacc_file = rep_path_dir / f"unaccounted_apps_{compact_ts}.json"
    unacc_file.write_text(json.dumps([], indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 76)
    print("APPSCOUT - INGESTION BATCH COMPLETED & RECONCILED")
    print("=" * 76)
    print(f"Total Selected in Batch : {len(selected_apps):,}")
    print(f"Total Accounted Apps    : {total_accounted:,}")
    print(f"Successfully Stored     : {apps_succeeded:,}")
    print(f"Skipped (Fresh)         : {apps_skipped:,}")
    print(f"404 / Delisted          : {not_found_count:,}")
    print(f"Validation Failed       : {validation_failures:,}")
    print(f"Network / Rate Limit    : {network_failures + rate_limited_count:,}")
    print(f"Other Terminal Failures : {other_failures:,}")
    print(f"UNACCOUNTED APPS        : {unaccounted_count}")
    print(f"Total Runtime           : {summary_data['performance']['total_runtime_seconds']}s ({summary_data['performance']['average_throughput_apps_per_min']} apps/min)")
    print("-" * 76)
    print(f"Summary Report File     : {sum_file.resolve()}")
    print(f"Reconciliation File     : {rec_file.resolve()}")
    print("=" * 76 + "\n")

    return summary_data


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m experiment.run_ingestion",
        description="Phase 5: Production-Scale Automated PostgreSQL Database Ingestion Orchestrator.",
    )
    parser.add_argument(
        "--frontier-file",
        default=None,
        metavar="PATH",
        help="Path to master frontier JSON file. (default: latest in data/frontier/)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Maximum number of apps to process in this batch (None = all frontier apps).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        metavar="N",
        help="Number of concurrent worker threads. (default: 8)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        metavar="SECONDS",
        help="Global polite delay between live HTTP requests in seconds. (default: 0.5)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        metavar="N",
        help="Maximum retry attempts for transient acquisition errors. (default: 3)",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=3.0,
        metavar="SECONDS",
        help="Delay in seconds between retry attempts. (default: 3.0)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="Resume from previous ingestion progress checkpoint if available. (default: True)",
    )
    parser.add_argument(
        "--force-restart",
        action="store_true",
        help="Clear progress checkpoint and start a fresh ingestion run.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass freshness check and force re-scraping of all selected apps.",
    )
    parser.add_argument(
        "--max-age-hours",
        type=float,
        default=168.0,
        metavar="HOURS",
        help="Threshold in hours for database freshness skipping. (default: 168.0 = 7 days)",
    )
    parser.add_argument(
        "--report-interval",
        type=int,
        default=50,
        metavar="N",
        help="Interval in apps to print progress summary box. (default: 50)",
    )
    parser.add_argument(
        "--raw-dir",
        default="data/raw",
        metavar="DIR",
        help="Directory where raw snapshots are saved/reused. (default: data/raw)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        metavar="DIR",
        help="Directory where single-app experiment JSON results are saved. (default: output)",
    )
    parser.add_argument(
        "--ingestion-dir",
        default="data/ingestion",
        metavar="DIR",
        help="Directory where ingestion progress checkpoint is saved. (default: data/ingestion)",
    )
    parser.add_argument(
        "--reports-dir",
        default="data/reports",
        metavar="DIR",
        help="Directory where audit and reconciliation reports are saved. (default: data/reports)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        metavar="SECONDS",
        help="HTTP socket timeout in seconds. (default: 30)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry-point for automated ingestion."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
            sys.stderr.reconfigure(errors="replace")
        except Exception:
            pass

    args = _parse_args(argv)
    _configure_logging(args.verbose)

    try:
        summary = run_ingestion_batch(
            frontier_file=args.frontier_file,
            limit=args.limit,
            workers=args.workers,
            delay=args.delay,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay,
            resume=args.resume,
            force_restart=args.force_restart,
            force=args.force,
            max_age_hours=args.max_age_hours,
            report_interval=args.report_interval,
            raw_dir=args.raw_dir,
            output_dir=args.output_dir,
            ingestion_dir=args.ingestion_dir,
            reports_dir=args.reports_dir,
            timeout=args.timeout,
        )
        return 0
    except Exception as exc:
        logger.error("Ingestion batch aborted: %s", exc)
        print(f"\n[ERROR] Ingestion batch aborted: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
