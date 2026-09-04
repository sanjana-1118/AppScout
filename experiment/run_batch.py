"""
experiment/run_batch.py
-----------------------
Controlled Batch Orchestration Layer for AppScout.

Phase 2B: Sequentially processes a limited batch of discovered app URLs,
reusing existing snapshots when available, acquiring new snapshots with
polite delay, inspecting, extracting, validating, and persisting individual
and consolidated batch results.

Usage
-----
    python -m experiment.run_batch --discovery-file "data/discovered/<file>.json" --limit 5 --delay 2
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import run_experiment

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        level=level,
        stream=sys.stderr,
    )


def run_batch(
    discovery_file: str | Path,
    *,
    limit: int = 5,
    delay: float = 2.0,
    raw_dir: str | Path = "data/raw",
    output_dir: str | Path = "output",
    batches_dir: str | Path = "output/batches",
    ground_truth_path: str | Path = "data/ground_truth.json",
    timeout: int = 30,
) -> dict[str, Any]:
    """Execute batch processing over a selected list of discovered app URLs.

    Parameters
    ----------
    discovery_file : path-like
        Path to the discovered JSON file produced by discover.py.
    limit : int
        Maximum number of URLs from the discovery file to process.
    delay : float
        Polite delay in seconds to wait between sequential HTTP acquisitions.
    raw_dir : path-like
        Directory where raw snapshots are stored/reused.
    output_dir : path-like
        Directory where individual experiment result files are stored.
    batches_dir : path-like
        Directory where batch summary JSON files are stored.
    ground_truth_path : path-like
        Path to ground truth JSON file for validation.
    timeout : int
        Socket timeout in seconds for HTTP requests.

    Returns
    -------
    dict[str, Any]
        Consolidated batch summary dictionary.
    """
    disc_path = Path(discovery_file)
    if not disc_path.exists():
        raise FileNotFoundError(f"Discovery file not found: {disc_path}")

    discovery_data = json.loads(disc_path.read_text(encoding="utf-8"))
    source_category_url = discovery_data.get("source_url", "(unknown)")
    all_urls: list[str] = discovery_data.get("urls", [])

    selected_urls = all_urls[:limit]
    logger.info(
        "Batch starting: %d URLs selected (out of %d total in discovery file)",
        len(selected_urls),
        len(all_urls),
    )

    batch_timestamp = datetime.now(timezone.utc).isoformat()
    processed_count = 0
    successful_count = 0
    failed_count = 0
    snapshots_reused = 0
    new_http_requests = 0
    apps_summaries: list[dict[str, Any]] = []

    print("\n" + "=" * 76)
    print("APPSCOUT - PHASE 2B CONTROLLED BATCH ORCHESTRATION")
    print("=" * 76)
    print(f"Discovery File      : {disc_path.resolve()}")
    print(f"Category Source     : {source_category_url}")
    print(f"Requested Limit     : {limit}")
    print(f"Selected Batch Size : {len(selected_urls)}")
    print(f"Polite Delay        : {delay}s")
    print("=" * 76 + "\n")

    for i, url in enumerate(selected_urls, 1):
        print(f"\n--- Processing [{i}/{len(selected_urls)}]: {url} ---")
        
        app_res = run_experiment.process_single_app(
            url=url,
            raw_dir=raw_dir,
            output_dir=output_dir,
            ground_truth_path=ground_truth_path,
            timeout=timeout,
            verbose_print=True,
        )

        processed_count += 1
        if app_res["status"] == "success":
            successful_count += 1
        else:
            failed_count += 1

        if app_res["snapshot_reused"]:
            snapshots_reused += 1
        else:
            new_http_requests += 1

        apps_summaries.append({
            "url": app_res["url"],
            "slug": app_res["slug"],
            "status": app_res["status"],
            "snapshot_reused": app_res["snapshot_reused"],
            "http_status": app_res["http_status"],
            "fields_extracted": app_res["fields_extracted"],
            "missing_fields": app_res["missing_fields"],
            "sanity_checks_passed": app_res["sanity_checks_passed"],
            "error": app_res["error"],
        })

        # Polite delay between items (skip on last item)
        if i < len(selected_urls) and delay > 0:
            logger.debug("Sleeping for %s seconds before next app...", delay)
            time.sleep(delay)

    # ── Consolidate and Save Batch Summary ───────────────────────────────────
    batch_summary: dict[str, Any] = {
        "batch_timestamp": batch_timestamp,
        "source_discovery_file": str(disc_path.resolve()),
        "source_category_url": source_category_url,
        "requested_limit": limit,
        "processed_count": processed_count,
        "successful_count": successful_count,
        "failed_count": failed_count,
        "snapshots_reused": snapshots_reused,
        "new_http_requests": new_http_requests,
        "delay_seconds": delay,
        "apps": apps_summaries,
    }

    b_dir = Path(batches_dir)
    b_dir.mkdir(parents=True, exist_ok=True)

    compact_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summary_filename = f"batch_{compact_ts}_summary.json"
    summary_path = b_dir / summary_filename
    summary_path.write_text(
        json.dumps(batch_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("Batch summary saved to: %s", summary_path.resolve())

    # ── Print Final Summary Table ────────────────────────────────────────────
    print("\n" + "=" * 76)
    print("APPSCOUT - BATCH EXECUTION SUMMARY")
    print("=" * 76)
    print(f"Processed: {processed_count} | Success: {successful_count} | Failed: {failed_count}")
    print(f"Snapshots Reused: {snapshots_reused} | New HTTP Requests: {new_http_requests}")
    print("-" * 76)
    print(f"{'App Slug':<30} {'Reused':<8} {'HTTP':<6} {'Fields':<8} {'Sanity':<8} {'Status'}")
    print("-" * 76)
    for app in apps_summaries:
        reused_str = "Yes" if app["snapshot_reused"] else "No"
        http_str = str(app["http_status"]) if app["http_status"] is not None else "ERR"
        fields_str = f"{app['fields_extracted']}/8"
        sanity_str = "PASS" if app["sanity_checks_passed"] else "FAIL"
        print(f"{app['slug']:<30} {reused_str:<8} {http_str:<6} {fields_str:<8} {sanity_str:<8} {app['status']}")
    print("=" * 76)
    print(f"\n[OK] Consolidated batch summary saved to: {summary_path.resolve()}\n")

    return batch_summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m experiment.run_batch",
        description="Phase 2B: Controlled sequential batch processing of discovered Shopify apps.",
    )
    parser.add_argument(
        "--discovery-file",
        required=True,
        metavar="FILE",
        help="Path to the discovery JSON file (e.g. data/discovered/<file>.json).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        metavar="N",
        help="Maximum number of apps to process. (default: 5)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        metavar="SECONDS",
        help="Delay in seconds between sequential requests. (default: 2.0)",
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
        help="Directory where individual result files are written. (default: output)",
    )
    parser.add_argument(
        "--batches-dir",
        default="output/batches",
        metavar="DIR",
        help="Directory where batch summary JSON files are written. (default: output/batches)",
    )
    parser.add_argument(
        "--ground-truth",
        default="data/ground_truth.json",
        metavar="FILE",
        help="Path to ground truth JSON file for validation. (default: data/ground_truth.json)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        metavar="SECONDS",
        help="HTTP request timeout in seconds. (default: 30)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry-point for batch execution."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
            sys.stderr.reconfigure(errors="replace")
        except Exception:
            pass

    args = _parse_args(argv)
    _configure_logging(args.verbose)

    try:
        summary = run_batch(
            discovery_file=args.discovery_file,
            limit=args.limit,
            delay=args.delay,
            raw_dir=args.raw_dir,
            output_dir=args.output_dir,
            batches_dir=args.batches_dir,
            ground_truth_path=args.ground_truth,
            timeout=args.timeout,
        )
        return 0 if summary["failed_count"] == 0 else 1
    except Exception as exc:
        logger.error("Batch execution aborted: %s", exc)
        print(f"\n[ERROR] Batch execution aborted: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
