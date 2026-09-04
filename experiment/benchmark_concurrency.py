"""
experiment/benchmark_concurrency.py
-----------------------------------
Phase A: Short controlled benchmark across 8, 12, 16 workers
to find the fastest stable concurrency configuration.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from experiment.run_ingestion import run_ingestion_batch

logger = logging.getLogger(__name__)


def run_benchmark_matrix() -> dict[str, Any]:
    print("\n" + "=" * 76)
    print("APPSCOUT - PHASE A CONCURRENCY & THROUGHPUT BENCHMARK MATRIX")
    print("=" * 76)

    test_configs = [
        {"workers": 8, "delay": 0.3, "batch_size": 40},
        {"workers": 12, "delay": 0.2, "batch_size": 40},
        {"workers": 16, "delay": 0.15, "batch_size": 40},
    ]

    results = []

    for cfg in test_configs:
        w = cfg["workers"]
        d = cfg["delay"]
        n = cfg["batch_size"]

        print(f"\n--- Testing Configuration: {w} Workers | Delay: {d}s | Sample: {n} Apps ---")
        t0 = time.time()
        
        try:
            summary = run_ingestion_batch(
                limit=n,
                workers=w,
                delay=d,
                report_interval=20,
                force=False,
            )
            elapsed = max(time.time() - t0, 0.1)
            apps_min = round((n / elapsed) * 60, 1)
            metrics = summary.get("metrics", {})
            rate_limited = metrics.get("rate_limited_429", 0)
            success_count = metrics.get("apps_succeeded_in_db", 0) + metrics.get("apps_skipped_fresh", 0)

            res = {
                "workers": w,
                "delay": d,
                "batch_size": n,
                "elapsed_seconds": round(elapsed, 2),
                "throughput_apps_per_min": apps_min,
                "rate_limited_count": rate_limited,
                "success_count": success_count,
                "status": "STABLE" if rate_limited == 0 else "THROTTLED",
            }
            results.append(res)
            print(f"Result: {apps_min} apps/min | Rate-Limited: {rate_limited} | Status: {res['status']}")

        except Exception as e:
            print(f"Config failed with error: {e}")
            results.append({
                "workers": w,
                "delay": d,
                "error": str(e),
                "status": "FAILED",
            })

    # Pick best stable configuration
    stable_results = [r for r in results if r.get("status") == "STABLE"]
    best_config = max(stable_results, key=lambda x: x.get("throughput_apps_per_min", 0)) if stable_results else results[0]

    benchmark_summary = {
        "benchmark_timestamp": datetime.now(timezone.utc).isoformat(),
        "matrix_results": results,
        "selected_optimal_config": best_config,
    }

    out_file = Path("data/reports/concurrency_benchmark_report.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(benchmark_summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 76)
    print("BENCHMARK MATRIX COMPLETED")
    print("=" * 76)
    print(f"Optimal Configuration: {best_config.get('workers')} Workers @ {best_config.get('delay')}s delay")
    print(f"Estimated Peak Stable Throughput: {best_config.get('throughput_apps_per_min')} apps/min")
    print("=" * 76 + "\n")

    return benchmark_summary


if __name__ == "__main__":
    run_benchmark_matrix()
