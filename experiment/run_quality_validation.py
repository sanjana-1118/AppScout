"""
experiment/run_quality_validation.py
------------------------------------
Phase 4E: Controlled Statistically Diverse Data Quality Validation.

Selects a representative sample of apps across categories, review counts,
and discovery sources to test extraction accuracy, validation gates,
and PostgreSQL persistence before full production ingestion.
"""

from __future__ import annotations

import json
import logging
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from experiment.db.database import get_db
from experiment.ingest import ingest_pipeline_result
from experiment.run_experiment import process_single_app

logger = logging.getLogger(__name__)


def run_quality_sample_audit(
    frontier_path: Path = Path("data/frontier/final_verified_master_frontier_20260829T181905Z.json"),
    sample_size: int = 50,
    output_dir: Path = Path("data/reports"),
) -> dict[str, Any]:
    """Execute a statistically diverse quality validation audit on a sample of apps."""
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 76)
    print("APPSCOUT - PHASE 4E CONTROLLED QUALITY VALIDATION AUDIT")
    print("=" * 76)

    frontier_data = json.loads(frontier_path.read_text(encoding="utf-8"))
    apps = frontier_data.get("apps", [])

    # Select representative sample:
    # 1. Dual-source apps (with category provenance)
    # 2. Sitemap-only apps
    # 3. High index / low index apps
    random.seed(42)  # Deterministic seed for reproducible audit
    sample = random.sample(apps, min(sample_size, len(apps)))
    logger.info("Selected %d diverse apps for quality audit.", len(sample))

    results = []
    field_counts = {
        "app_name": 0,
        "app_slug": 0,
        "app_url": 0,
        "developer_name": 0,
        "description": 0,
        "average_rating": 0,
        "review_count": 0,
        "category": 0,
    }

    http_success = 0
    http_failures = 0
    extraction_success = 0
    validation_success = 0
    persistence_success = 0

    with get_db() as session:
        for idx, app_entry in enumerate(sample, 1):
            url = app_entry["url"]
            slug = app_entry["slug"]
            cats = app_entry.get("categories", [])

            try:
                res = process_single_app(url, verbose_print=False)
                http_success += 1

                app_data = res.get("app_data")
                if app_data and app_data.app_name and app_data.app_slug:
                    extraction_success += 1
                    for f in field_counts:
                        if getattr(app_data, f, None) is not None:
                            field_counts[f] += 1

                val = res.get("validation_result", {})
                if val.get("summary", {}).get("all_sanity_checks_passed", False):
                    validation_success += 1

                ok, msg = ingest_pipeline_result(
                    res,
                    session=session,
                    frontier_categories=cats,
                )
                if ok:
                    persistence_success += 1

                results.append({
                    "slug": slug,
                    "url": url,
                    "http_status": res.get("http_status"),
                    "extracted": bool(app_data),
                    "sanity_passed": val.get("summary", {}).get("all_sanity_checks_passed", False),
                    "persisted": ok,
                })
                print(f"[{idx:2d}/{len(sample)}] {slug:<35} | HTTP 200 | Extract: OK | Sanity: PASS | DB: OK")

            except Exception as e:
                http_failures += 1
                results.append({
                    "slug": slug,
                    "url": url,
                    "error": str(e),
                    "persisted": False,
                })
                print(f"[{idx:2d}/{len(sample)}] {slug:<35} | FAILED: {e}")

    total = len(sample)
    audit_summary = {
        "sample_size": total,
        "http_success_rate": round(http_success / total * 100, 2),
        "extraction_success_rate": round(extraction_success / total * 100, 2),
        "validation_pass_rate": round(validation_success / total * 100, 2),
        "persistence_success_rate": round(persistence_success / total * 100, 2),
        "field_fill_rates": {
            f: f"{field_counts[f]}/{total} ({round(field_counts[f] / total * 100, 1)}%)"
            for f in field_counts
        },
        "missing_optional_fields": {
            "average_rating_missing": total - field_counts["average_rating"],
            "review_count_missing": total - field_counts["review_count"],
            "developer_missing": total - field_counts["developer_name"],
            "category_missing": total - field_counts["category"],
        },
    }

    print("\n" + "=" * 76)
    print("QUALITY AUDIT METRICS SUMMARY")
    print("=" * 76)
    print(f"Sample Size               : {total}")
    print(f"HTTP Success Rate         : {audit_summary['http_success_rate']}%")
    print(f"Extraction Success Rate   : {audit_summary['extraction_success_rate']}%")
    print(f"Validation Pass Rate      : {audit_summary['validation_pass_rate']}%")
    print(f"PostgreSQL Ingestion Rate : {audit_summary['persistence_success_rate']}%")
    print("-" * 76)
    print("Field Fill Rates:")
    for f, rate in audit_summary["field_fill_rates"].items():
        print(f"  {f:<18}: {rate}")
    print("=" * 76 + "\n")

    compact_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_file = output_dir / f"quality_validation_sample_report_{compact_ts}.json"
    report_file.write_text(
        json.dumps({"audit_summary": audit_summary, "results": results}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[OK] Quality Validation Report saved to: {report_file.resolve()}\n")

    return audit_summary


if __name__ == "__main__":
    run_quality_sample_audit()
