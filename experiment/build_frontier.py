"""
experiment/build_frontier.py
----------------------------
Phase 4A: Master App URL Frontier Builder for Shopify App Store.

Orchestrates multi-category discovery by:
1. Discovering the complete Shopify category taxonomy across all root sections.
2. Selecting crawlable leaf categories (with optional limit for controlled execution).
3. Sequentially traversing category pagination via traverse_category.py.
4. Performing global ordered deduplication across all categories.
5. Preserving multi-category provenance for every unique app URL.
6. Checkpointing progress state after every category to enable safe resume.
7. Persisting the final Master Frontier artifact to data/frontier/.

Usage
-----
    python -m experiment.build_frontier --delay 1.5
    python -m experiment.build_frontier --resume
    python -m experiment.build_frontier --category-limit 2 --max-pages-per-category 3
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import acquire, discover_categories, traverse_category
from .models import MasterFrontierResult

logger = logging.getLogger(__name__)

PROGRESS_FILENAME = "_frontier_progress.json"


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        level=level,
        stream=sys.stderr,
    )


def load_progress(progress_file: Path) -> dict[str, Any] | None:
    """Load existing checkpoint state from progress JSON file if present."""
    if not progress_file.exists():
        return None
    try:
        data = json.loads(progress_file.read_text(encoding="utf-8"))
        logger.info("Loaded existing progress checkpoint from: %s", progress_file.resolve())
        return data
    except Exception as exc:
        logger.warning("Could not read progress file (%s): %s", progress_file, exc)
        return None


def save_progress(progress_file: Path, state: dict[str, Any]) -> None:
    """Atomically write checkpoint state to progress JSON file."""
    temp_file = progress_file.with_suffix(".tmp")
    try:
        temp_file.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temp_file.replace(progress_file)
        logger.debug("Checkpoint saved to %s", progress_file.name)
    except Exception as exc:
        logger.error("Failed to save progress file: %s", exc)


def build_master_frontier(
    *,
    source_url: str = "https://apps.shopify.com",
    category_limit: int | None = None,
    max_pages_per_category: int | None = None,
    delay: float = 1.5,
    resume: bool = True,
    force_restart: bool = False,
    raw_dir: str | Path = "data/raw",
    output_dir: str | Path = "data/frontier",
    timeout: int = 30,
) -> dict[str, Any]:
    """Discover categories, traverse pagination, and build a deduplicated Master Frontier.

    Parameters
    ----------
    source_url : str
        Base URL to discover category taxonomy from.
    category_limit : int | None
        Optional maximum number of crawlable categories to process.
    max_pages_per_category : int | None
        Optional maximum pages to traverse per category.
    delay : float
        Polite delay in seconds between live HTTP requests.
    resume : bool
        If True, resumes from existing progress checkpoint if available.
    force_restart : bool
        If True, clears previous progress file and starts fresh.
    raw_dir : path-like
        Directory for raw snapshot caching/reuse.
    output_dir : path-like
        Directory where Master Frontier JSON is persisted.
    timeout : int
        HTTP socket timeout.

    Returns
    -------
    dict[str, Any]
        Consolidated Master Frontier dictionary with provenance.
    """
    raw_path_dir = Path(raw_dir)
    raw_path_dir.mkdir(parents=True, exist_ok=True)

    out_path_dir = Path(output_dir)
    out_path_dir.mkdir(parents=True, exist_ok=True)

    progress_file = out_path_dir / PROGRESS_FILENAME

    if force_restart and progress_file.exists():
        logger.info("Force restart requested: removing existing progress file.")
        progress_file.unlink(missing_ok=True)

    print("\n" + "=" * 76)
    print("APPSCOUT - PHASE 4A MASTER APP URL FRONTIER BUILDER")
    print("=" * 76)
    print(f"Taxonomy Source URL       : {source_url}")
    print(f"Category Limit            : {category_limit if category_limit is not None else 'All crawlable categories'}")
    print(f"Max Pages Per Category    : {max_pages_per_category if max_pages_per_category is not None else 'Unlimited (Follow rel=next)'}")
    print(f"Polite Delay              : {delay}s (applied only on new HTTP requests)")
    print(f"Resume Enabled            : {resume and not force_restart}")
    print("=" * 76 + "\n")

    # ── Step 1: Discover Taxonomy ────────────────────────────────────────────
    logger.info("Step 1 — Discovering category taxonomy from %s", source_url)
    all_categories = discover_categories.discover_category_taxonomy(
        source_url=source_url,
        deep=True,
        raw_dir=raw_path_dir,
        timeout=timeout,
    )

    crawlable_categories = [c for c in all_categories if c.get("crawlable")]
    logger.info("Discovered %d total categories (%d crawlable leaf categories)", len(all_categories), len(crawlable_categories))

    if category_limit is not None:
        selected_categories = crawlable_categories[:category_limit]
    else:
        selected_categories = crawlable_categories

    print(f"[OK] Discovered {len(all_categories)} total categories ({len(crawlable_categories)} crawlable leaf categories).")
    print(f"[OK] Selected {len(selected_categories)} categories for traversal in this run.\n")

    # ── Step 2: Initialize State (or Load from Progress) ─────────────────────
    master_apps_map: dict[str, dict[str, Any]] = {}
    master_ordered_urls: list[str] = []
    completed_categories: dict[str, dict[str, Any]] = {}
    failed_categories: dict[str, dict[str, Any]] = {}

    total_category_urls_encountered = 0
    global_duplicates_removed = 0
    total_snapshots_reused = 0
    total_new_http_requests = 0
    total_pages_processed = 0

    if resume and not force_restart:
        progress_data = load_progress(progress_file)
        if progress_data:
            completed_categories = progress_data.get("completed_categories", {})
            failed_categories = progress_data.get("failed_categories", {})
            master_apps_map = progress_data.get("master_apps_map", {})
            master_ordered_urls = progress_data.get("master_ordered_urls", list(master_apps_map.keys()))
            total_category_urls_encountered = progress_data.get("total_category_urls_encountered", 0)
            global_duplicates_removed = progress_data.get("global_duplicates_removed", 0)
            total_snapshots_reused = progress_data.get("total_snapshots_reused", 0)
            total_new_http_requests = progress_data.get("total_new_http_requests", 0)
            total_pages_processed = progress_data.get("total_pages_processed", 0)

            print(
                f"[RESUME] Resuming from checkpoint: {len(completed_categories)} categories already completed, "
                f"{len(master_ordered_urls)} unique apps already discovered.\n"
            )

    # ── Step 3: Traverse Categories & Checkpoint ─────────────────────────────
    for idx, cat in enumerate(selected_categories, 1):
        cat_url = cat["url"]
        cat_slug = cat["slug"]
        cat_label = cat.get("label", cat_slug)

        # Check if already completed
        if cat_slug in completed_categories:
            c_info = completed_categories[cat_slug]
            print(
                f"[{idx}/{len(selected_categories)}] Category '{cat_slug}' already completed "
                f"({c_info.get('apps_discovered', 0)} apps). Skipping."
            )
            continue

        print(f"\n--- Processing Category [{idx}/{len(selected_categories)}]: {cat_label} ({cat_slug}) ---")

        try:
            traversal_res = traverse_category.traverse_category(
                category_url=cat_url,
                max_pages=max_pages_per_category,
                delay=delay,
                raw_dir=raw_path_dir,
                timeout=timeout,
            )

            total_snapshots_reused += traversal_res.snapshots_reused
            total_new_http_requests += traversal_res.new_http_requests
            total_pages_processed += traversal_res.pages_processed

            cat_apps_count = len(traversal_res.app_urls)
            total_category_urls_encountered += cat_apps_count

            # Merge into master map with category provenance
            new_in_this_cat = 0
            dups_in_this_cat = 0

            for app_url in traversal_res.app_urls:
                slug = acquire._slug_from_url(app_url)
                if app_url not in master_apps_map:
                    master_apps_map[app_url] = {
                        "url": app_url,
                        "slug": slug,
                        "categories": [cat_slug],
                    }
                    master_ordered_urls.append(app_url)
                    new_in_this_cat += 1
                else:
                    global_duplicates_removed += 1
                    dups_in_this_cat += 1
                    if cat_slug not in master_apps_map[app_url]["categories"]:
                        master_apps_map[app_url]["categories"].append(cat_slug)

            # Record category success
            completed_categories[cat_slug] = {
                "category_url": cat_url,
                "category_slug": cat_slug,
                "category_label": cat_label,
                "pages_processed": traversal_res.pages_processed,
                "apps_discovered": cat_apps_count,
                "new_unique_apps": new_in_this_cat,
                "cross_category_dups": dups_in_this_cat,
                "snapshots_reused": traversal_res.snapshots_reused,
                "new_http_requests": traversal_res.new_http_requests,
                "stopped_reason": traversal_res.stopped_reason,
                "status": "success",
            }

            print(
                f"[Category Complete] {cat_slug}: {cat_apps_count} apps "
                f"(New unique: {new_in_this_cat}, Already in frontier: {dups_in_this_cat}) | "
                f"Master Frontier Total: {len(master_ordered_urls)} unique apps"
            )

        except Exception as exc:
            logger.error("Failed to traverse category %s: %s", cat_slug, exc)
            failed_categories[cat_slug] = {
                "category_url": cat_url,
                "category_slug": cat_slug,
                "category_label": cat_label,
                "error": str(exc),
                "status": "failed",
            }
            print(f"[Category FAILED] {cat_slug}: {exc}")

        # ── Checkpoint Progress State ────────────────────────────────────────
        state_to_save = {
            "last_updated_at": datetime.now(timezone.utc).isoformat(),
            "target_source_url": source_url,
            "category_limit": category_limit,
            "max_pages_per_category": max_pages_per_category,
            "total_pages_processed": total_pages_processed,
            "total_category_urls_encountered": total_category_urls_encountered,
            "global_duplicates_removed": global_duplicates_removed,
            "total_snapshots_reused": total_snapshots_reused,
            "total_new_http_requests": total_new_http_requests,
            "completed_categories": completed_categories,
            "failed_categories": failed_categories,
            "master_apps_map": master_apps_map,
            "master_ordered_urls": master_ordered_urls,
        }
        save_progress(progress_file, state_to_save)

    # ── Step 4: Compile Final Master Frontier ────────────────────────────────
    created_at = datetime.now(timezone.utc).isoformat()
    compact_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    apps_list = [master_apps_map[u] for u in master_ordered_urls]
    multi_category_apps_count = sum(1 for a in apps_list if len(a["categories"]) > 1)

    summary_data = {
        "total_categories_discovered": len(all_categories),
        "total_crawlable_categories": len(crawlable_categories),
        "categories_attempted": len(selected_categories),
        "categories_succeeded": len(completed_categories),
        "categories_failed": len(failed_categories),
        "total_pages_processed": total_pages_processed,
        "total_category_urls_encountered": total_category_urls_encountered,
        "unique_app_urls": len(apps_list),
        "global_duplicates_removed": global_duplicates_removed,
        "multi_category_apps_count": multi_category_apps_count,
        "total_snapshots_reused": total_snapshots_reused,
        "total_new_http_requests": total_new_http_requests,
    }

    frontier_payload = {
        "created_at": created_at,
        "summary": summary_data,
        "categories_processed": list(completed_categories.values()),
        "failed_categories": list(failed_categories.values()),
        "apps": apps_list,
    }

    out_filename = f"master_app_frontier_{compact_ts}.json"
    out_file_path = out_path_dir / out_filename
    out_file_path.write_text(
        json.dumps(frontier_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info("Master App Frontier saved to: %s", out_file_path.resolve())

    # ── Step 5: Summary Table ────────────────────────────────────────────────
    print("\n" + "=" * 76)
    print("APPSCOUT - GLOBAL MASTER APP URL FRONTIER SUMMARY")
    print("=" * 76)
    print(f"Total Taxonomy Categories   : {summary_data['total_categories_discovered']}")
    print(f"Total Crawlable Categories  : {summary_data['total_crawlable_categories']}")
    print(f"Categories Succeeded        : {summary_data['categories_succeeded']}/{summary_data['categories_attempted']}")
    print(f"Categories Failed           : {summary_data['categories_failed']}")
    print(f"Total Pages Processed       : {summary_data['total_pages_processed']}")
    print(f"Total Category URLs Seen    : {summary_data['total_category_urls_encountered']}")
    print(f"Unique App URLs in Frontier : {summary_data['unique_app_urls']}")
    print(f"Cross-Category Duplicates   : {summary_data['global_duplicates_removed']}")
    print(f"Multi-Category Apps         : {summary_data['multi_category_apps_count']}")
    print(f"Total Snapshots Reused      : {summary_data['total_snapshots_reused']}")
    print(f"Total New HTTP Requests     : {summary_data['total_new_http_requests']}")
    print("=" * 76)
    print(f"\n[OK] Complete Master Frontier JSON saved to:\n  {out_file_path.resolve()}\n")

    return frontier_payload


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m experiment.build_frontier",
        description="Phase 4A: Discover categories, traverse pagination, and build a Master App URL Frontier.",
    )
    parser.add_argument(
        "--source-url",
        default="https://apps.shopify.com",
        metavar="URL",
        help="Category taxonomy directory URL. (default: https://apps.shopify.com)",
    )
    parser.add_argument(
        "--category-limit",
        type=int,
        default=None,
        metavar="N",
        help="Optional maximum number of crawlable leaf categories to traverse.",
    )
    parser.add_argument(
        "--max-pages-per-category",
        type=int,
        default=None,
        metavar="N",
        help="Optional safety limit on maximum pages per category.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        metavar="SECONDS",
        help="Polite delay in seconds between new live HTTP requests. (default: 1.5)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="Resume from existing progress checkpoint if available. (default: True)",
    )
    parser.add_argument(
        "--force-restart",
        action="store_true",
        help="Ignore and delete existing progress checkpoint, starting completely fresh.",
    )
    parser.add_argument(
        "--raw-dir",
        default="data/raw",
        metavar="DIR",
        help="Directory where raw snapshots are stored/reused. (default: data/raw)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/frontier",
        metavar="DIR",
        help="Directory where Master Frontier JSON is saved. (default: data/frontier)",
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
    """CLI entry-point for master frontier builder."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
            sys.stderr.reconfigure(errors="replace")
        except Exception:
            pass

    args = _parse_args(argv)
    _configure_logging(args.verbose)

    try:
        build_master_frontier(
            source_url=args.source_url,
            category_limit=args.category_limit,
            max_pages_per_category=args.max_pages_per_category,
            delay=args.delay,
            resume=args.resume,
            force_restart=args.force_restart,
            raw_dir=args.raw_dir,
            output_dir=args.output_dir,
            timeout=args.timeout,
        )
        return 0
    except Exception as exc:
        logger.error("Master Frontier build aborted: %s", exc)
        print(f"\n[ERROR] Master Frontier build aborted: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
