"""
experiment/auto_finalizer.py
----------------------------
Non-disruptive Background Finalization Watcher for AppScout.

Monitors the active main ingestion process and database state.
As soon as the master frontier ingestion finishes (unprocessed == 0 or ingestion completed),
it automatically executes the full master orchestration workflow:
  1. Offline Pricing Backfill (100% of collected apps)
  2. Pricing Verification & Plan Tiers Audit
  3. Review Intelligence Audit
  4. Database Integrity Audit
  5. Completion Gate Checks (0 un-enriched apps, 0 unaccounted apps)
  6. Generation of Final Report and Technical Documentation
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from experiment.db.database import get_db
from experiment.db.models import App, IngestionItem
from experiment.master_orchestrator import run_completion_workflow
from experiment.inspect_state import is_process_running

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("experiment.auto_finalizer")


def check_unprocessed_count(frontier_path: Path) -> int:
    """Check number of unprocessed frontier apps from PostgreSQL."""
    try:
        frontier_data = json.loads(frontier_path.read_text(encoding="utf-8"))
        frontier_apps = frontier_data.get("apps", [])
        frontier_total = len(frontier_apps)
        frontier_slugs = {a.get("slug") for a in frontier_apps if a.get("slug")}

        with get_db() as session:
            db_slugs = set(session.scalars(select(App.app_slug)).all())
            items_slugs = set(session.scalars(select(IngestionItem.app_slug)).all())

        accounted = frontier_slugs.intersection(db_slugs.union(items_slugs))
        return max(frontier_total - len(accounted), 0)
    except Exception as exc:
        logger.warning("Error calculating unprocessed count: %s", exc)
        return 999999


def monitor_and_finalize(
    poll_interval: int = 45,
    frontier_file: str | Path = "data/frontier/final_verified_master_frontier_20260829T181905Z.json",
) -> None:
    frontier_path = Path(frontier_file)
    print("\n" + "=" * 76)
    print("APPSCOUT — AUTOMATED COMPLETION WATCHER ACTIVE")
    print("=" * 76)
    print(f"Monitoring Frontier Source : {frontier_path.name}")
    print(f"Polling Interval           : {poll_interval}s")
    print("Waiting for main ingestion to reach terminal state (unprocessed == 0)...")
    print("=" * 76 + "\n")

    while True:
        unprocessed = check_unprocessed_count(frontier_path)
        is_active = is_process_running()

        ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        print(f"[{ts}] Ingestion Process: {'RUNNING' if is_active else 'IDLE'} | Remaining Unprocessed: {unprocessed:,} apps")

        if unprocessed == 0 and not is_active:
            print("\n" + "!" * 76)
            print("[TRIGGER ACTIVATED] Master Frontier Ingestion Complete (Unprocessed == 0)!")
            print("Executing Full Master Finalization Workflow...")
            print("!" * 76 + "\n")

            try:
                run_completion_workflow()
                print("\n[SUCCESS] Master Finalization Workflow Finished Successfully!")
            except Exception as e:
                logger.error("Error executing completion workflow: %s", e)

            break

        time.sleep(poll_interval)


if __name__ == "__main__":
    from sqlalchemy import select
    monitor_and_finalize()
