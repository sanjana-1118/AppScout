"""
experiment/backfill_pricing.py
------------------------------
High-Performance Offline Pricing & Plan Backfill Engine for AppScout.

Enriches all canonical apps in PostgreSQL using existing local HTML snapshots
in data/raw/ with zero network calls, using multi-threaded batch commits.
"""

from __future__ import annotations

import glob
import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from sqlalchemy import func, select

from experiment.db.database import get_db, SessionLocal
from experiment.db.models import App, AppPricingPlan
from experiment.db import repositories
from experiment.extract_pricing import extract_pricing_from_soup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("experiment.backfill_pricing")


def run_pricing_backfill(
    workers: int = 8,
    batch_size: int = 100,
    raw_dir: str | Path = "data/raw",
    checkpoint_file: str | Path = "data/ingestion/_pricing_backfill_progress.json",
) -> dict[str, Any]:
    raw_path = Path(raw_dir)
    chk_path = Path(checkpoint_file)
    chk_path.parent.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 76)
    print("APPSCOUT — HIGH-PERFORMANCE OFFLINE PRICING & PLANS BACKFILL")
    print("=" * 76)

    # 1. Query all apps from PostgreSQL
    with get_db() as session:
        all_apps = session.execute(
            select(App.id, App.app_slug, App.pricing_type)
            .order_by(App.id.asc())
        ).all()

    total_apps = len(all_apps)
    print(f"Total Canonical Apps in DB : {total_apps:,}")

    # Index snapshot files by slug using fast directory scan
    print("Indexing local HTML snapshots in data/raw/ ...")
    snapshot_map: dict[str, str] = {}
    for entry in os.scandir(str(raw_path)):
        if entry.is_file() and entry.name.endswith(".html"):
            stem = entry.name[:-5]
            if "_" in stem:
                slug = stem.rsplit("_", 1)[0]
                if slug not in snapshot_map:
                    snapshot_map[slug] = entry.path

    print(f"Found HTML Snapshots       : {len(snapshot_map):,} unique app snapshots")

    processed = 0
    updated_apps = 0
    plans_inserted = 0
    missing_snapshots = 0
    start_time = time.time()
    lock = threading.Lock()

    type_counts = {"free": 0, "freemium": 0, "paid": 0, "unknown": 0}

    def _worker_chunk(chunk: list[tuple[int, str, str | None]]) -> dict[str, Any]:
        nonlocal processed, updated_apps, plans_inserted, missing_snapshots
        local_updated = 0
        local_plans = 0
        local_types: dict[str, int] = {}

        with SessionLocal() as db_session:
            for app_id, slug, existing_ptype in chunk:
                snapshot_path = snapshot_map.get(slug)
                if not snapshot_path or not os.path.exists(snapshot_path):
                    with lock:
                        missing_snapshots += 1
                    continue

                try:
                    with open(snapshot_path, "r", encoding="utf-8", errors="replace") as f:
                        html_content = f.read()

                    soup = BeautifulSoup(html_content, "html.parser")
                    pricing_data = extract_pricing_from_soup(soup)
                    p_type = pricing_data.pricing_type
                    local_types[p_type] = local_types.get(p_type, 0) + 1

                    app_obj = db_session.get(App, app_id)
                    if app_obj:
                        app_obj.pricing_type = p_type
                        app_obj.free_trial_days = pricing_data.free_trial_days

                        if pricing_data.plans:
                            plans_dict = [p.to_dict() for p in pricing_data.plans]
                            inserted = repositories.upsert_pricing_plans(
                                db_session, app_id, slug, plans_dict
                            )
                            local_plans += len(inserted)

                        local_updated += 1
                except Exception as exc:
                    logger.debug("Error extracting pricing for %s: %s", slug, exc)

            db_session.commit()

        with lock:
            processed += len(chunk)
            updated_apps += local_updated
            plans_inserted += local_plans
            for pt, cnt in local_types.items():
                type_counts[pt] = type_counts.get(pt, 0) + cnt

            if processed % 1000 == 0 or processed >= total_apps:
                elapsed = max(time.time() - start_time, 0.1)
                rate = round(processed / elapsed * 60, 1)
                print(
                    f"Progress: {processed}/{total_apps} ({round(processed/total_apps*100, 1)}%) | "
                    f"Updated: {updated_apps:,} apps | Plans: {plans_inserted:,} | Rate: {rate} apps/min"
                )

        return {"updated": local_updated, "plans": local_plans}

    # Split into chunks of batch_size
    chunks = [all_apps[i : i + batch_size] for i in range(0, len(all_apps), batch_size)]

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_worker_chunk, c) for c in chunks]
        for f in as_completed(futures):
            f.result()

    elapsed_total = max(time.time() - start_time, 0.1)

    with get_db() as final_session:
        total_plans_in_db = final_session.scalar(select(func.count(AppPricingPlan.id))) or 0
        apps_with_pricing = final_session.scalar(select(func.count(App.id)).where(App.pricing_type != None)) or 0
        apps_missing_pricing = final_session.scalar(select(func.count(App.id)).where(App.pricing_type == None)) or 0

    print("\n" + "=" * 76)
    print("OFFLINE PRICING BACKFILL COMPLETED")
    print("=" * 76)
    print(f"Total Apps Processed       : {processed:,}")
    print(f"Apps Updated with Pricing  : {updated_apps:,} ({apps_with_pricing:,} populated)")
    print(f"Apps Missing Pricing       : {apps_missing_pricing:,}")
    print(f"Total Pricing Plans in DB  : {total_plans_in_db:,}")
    print(f"Total Elapsed Time         : {elapsed_total:.2f}s ({round(processed/elapsed_total*60, 1)} apps/min)")
    print("-" * 76)
    print("Pricing Model Breakdown:")
    for pt, count in sorted(type_counts.items()):
        print(f"  - {pt:<20}: {count:,}")
    print("=" * 76 + "\n")

    return {
        "total_apps": total_apps,
        "updated_apps": updated_apps,
        "apps_with_pricing": apps_with_pricing,
        "apps_missing_pricing": apps_missing_pricing,
        "total_plans_in_db": total_plans_in_db,
        "type_counts": type_counts,
        "elapsed_seconds": elapsed_total,
    }


if __name__ == "__main__":
    run_pricing_backfill()
