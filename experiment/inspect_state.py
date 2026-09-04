"""
experiment/inspect_state.py
---------------------------
AppScout: Live Ingestion Progress & Database State Auditor.

Reads directly from the live PostgreSQL database, checkpoint file, and Master Frontier JSON
to compute real-time deduplicated progress, throughput, and estimated time remaining.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from experiment.db.database import get_db
from experiment.db.models import App, Category, AppCategory, IngestionItem, IngestionRun


def is_process_running() -> bool:
    """Check whether a python process running run_ingestion is currently active."""
    try:
        if sys.platform == "win32":
            # Use PowerShell / tasklist to check for python running run_ingestion
            cmd = 'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*run_ingestion*" } | Select-Object -ExpandProperty ProcessId'
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=5,
            )
            pids = [p.strip() for p in out.stdout.strip().splitlines() if p.strip()]
            return len(pids) > 0
    except Exception:
        pass
    return False


def inspect_live_state() -> dict[str, Any]:
    """Calculate and display real-time live progress metrics."""
    # 1. Load Final Verified Master Frontier
    frontier_path = Path("data/frontier/final_verified_master_frontier_20260829T181905Z.json")
    if not frontier_path.exists():
        # Fallback search
        files = list(Path("data/frontier").glob("final_verified_master_frontier_*.json"))
        if files:
            files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            frontier_path = files[0]

    frontier_total = 25633
    frontier_slugs: list[str] = []
    if frontier_path.exists():
        try:
            frontier_data = json.loads(frontier_path.read_text(encoding="utf-8"))
            apps_list = frontier_data.get("apps", [])
            frontier_total = len(apps_list)
            for a in apps_list:
                if isinstance(a, dict) and a.get("slug"):
                    frontier_slugs.append(a["slug"])
                elif isinstance(a, str):
                    frontier_slugs.append(a.split("/")[-1])
        except Exception:
            pass

    frontier_slug_set = set(frontier_slugs)

    # 2. Load Checkpoint File
    checkpoint_path = Path("data/ingestion/_ingestion_progress.json")
    checkpoint_data: dict[str, Any] = {}
    if checkpoint_path.exists():
        try:
            checkpoint_data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 3. Query PostgreSQL Live State
    with get_db() as session:
        canonical_apps_count = session.scalar(select(func.count(App.id))) or 0
        db_canonical_slugs = set(session.scalars(select(App.app_slug)).all())

        # Query all ingestion items ordered by id ascending so latest state per slug is known
        audit_rows = session.execute(
            select(
                IngestionItem.app_slug,
                IngestionItem.status,
                IngestionItem.error_message,
                IngestionItem.created_at,
            ).order_by(IngestionItem.id.asc())
        ).all()

    # Map the latest terminal status per unique app slug
    latest_item_status: dict[str, tuple[str, str | None]] = {}
    earliest_item_time = None
    latest_item_time = None

    for row in audit_rows:
        slug = row[0]
        st = row[1]
        err = row[2]
        created = row[3]
        latest_item_status[slug] = (st, err)

        if earliest_item_time is None or (created and created < earliest_item_time):
            earliest_item_time = created
        if latest_item_time is None or (created and created > latest_item_time):
            latest_item_time = created

    # 4. Accurate Deduplicated Frontier Accounting
    # Categorize every unique slug in the frontier
    count_stored = 0
    count_skipped = 0
    count_validation_failed = 0
    count_not_found = 0
    count_persistent_failures = 0

    accounted_slugs = set()

    for slug in frontier_slug_set:
        if slug in db_canonical_slugs:
            count_stored += 1
            accounted_slugs.add(slug)
        elif slug in latest_item_status:
            st, err = latest_item_status[slug]
            err_str = (err or "").lower()

            if st in ("skipped", "skipped_fresh"):
                count_skipped += 1
                accounted_slugs.add(slug)
            elif st == "not_found" or "404" in err_str or "delisted" in err_str:
                count_not_found += 1
                accounted_slugs.add(slug)
            elif st == "validation_failed":
                count_validation_failed += 1
                accounted_slugs.add(slug)
            elif st in ("failed", "network_failed", "rate_limited", "unexpected_error"):
                count_persistent_failures += 1
                accounted_slugs.add(slug)

    total_accounted = len(accounted_slugs)
    remaining_apps = max(frontier_total - total_accounted, 0)
    completion_percentage = (total_accounted / frontier_total * 100.0) if frontier_total > 0 else 0.0

    # 5. Process Detection & Throughput Estimation
    process_active = is_process_running()
    
    # Check if checkpoint was updated recently (within last 3 minutes)
    checkpoint_last_str = checkpoint_data.get("last_updated_at")
    checkpoint_is_fresh = False
    if checkpoint_last_str:
        try:
            last_dt = datetime.fromisoformat(checkpoint_last_str)
            now_dt = datetime.now(timezone.utc)
            if (now_dt - last_dt).total_seconds() < 180:
                checkpoint_is_fresh = True
        except Exception:
            pass

    is_running = process_active or checkpoint_is_fresh
    ingestion_status = "COMPLETED" if remaining_apps == 0 else ("RUNNING" if is_running else "IDLE / PAUSED")

    # Real-Time Rolling Throughput Calculation (Last 100 items)
    throughput_per_min = 0.0
    est_hours = 0
    est_mins = 0

    if is_running:
        with get_db() as s:
            recent_timestamps = s.execute(
                select(IngestionItem.created_at)
                .order_by(IngestionItem.id.desc())
                .limit(100)
            ).scalars().all()

        if len(recent_timestamps) >= 10:
            window_sec = (recent_timestamps[0] - recent_timestamps[-1]).total_seconds()
            if window_sec > 0:
                throughput_per_min = round((len(recent_timestamps) / window_sec) * 60.0, 1)
                if throughput_per_min > 0:
                    est_total_mins = remaining_apps / throughput_per_min
                    est_hours = int(est_total_mins // 60)
                    est_mins = int(est_total_mins % 60)

    # 6. Format and Print Required Output
    print("\n" + "=" * 52)
    print("APPSCOUT DATA COLLECTION LIVE PROGRESS")
    print("=" * 52)
    print(f"\nTotal Frontier Apps        : {frontier_total:,}")
    print(f"Processed / Accounted Apps : {total_accounted:,}")
    print(f"Remaining Apps             : {remaining_apps:,}")
    print(f"Completion Percentage      : {completion_percentage:.2f}%")
    print(f"\nSuccessfully Stored        : {count_stored:,}")
    print(f"Skipped Fresh              : {count_skipped:,}")
    print(f"Validation Failed          : {count_validation_failed:,}")
    print(f"Not Found / Delisted       : {count_not_found:,}")
    print(f"Persistent Failures        : {count_persistent_failures:,}")
    print(f"\nCanonical Apps in Database : {canonical_apps_count:,}")
    print(f"\nIngestion Status           : {ingestion_status}")
    if throughput_per_min > 0:
        print(f"Current Throughput         : {throughput_per_min:.1f} apps/minute")
    else:
        print("Current Throughput         : -- apps/minute")

    if remaining_apps > 0 and est_hours + est_mins > 0:
        print(f"Estimated Time Remaining   : {est_hours} hours {est_mins} minutes")
    elif remaining_apps == 0:
        print("Estimated Time Remaining   : 0 hours 0 minutes (Completed)")
    else:
        print("Estimated Time Remaining   : Calculating...")
    print("\n" + "=" * 52 + "\n")

    return {
        "frontier_total": frontier_total,
        "processed_accounted": total_accounted,
        "remaining": remaining_apps,
        "completion_percentage": completion_percentage,
        "stored": count_stored,
        "skipped_fresh": count_skipped,
        "validation_failed": count_validation_failed,
        "not_found": count_not_found,
        "persistent_failures": count_persistent_failures,
        "canonical_apps_in_db": canonical_apps_count,
        "ingestion_status": ingestion_status,
        "throughput_per_min": throughput_per_min,
        "est_remaining_hours": est_hours,
        "est_remaining_mins": est_mins,
    }


if __name__ == "__main__":
    inspect_live_state()
