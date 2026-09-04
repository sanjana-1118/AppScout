"""
experiment/run_experiment.py
-----------------------------
CLI entry-point and processing engine for the Single-App Experiment pipeline.

Usage
-----
    python -m experiment.run_experiment --url <shopify-app-page-url>

Pipeline steps
--------------
1. Acquire: Fetch target URL (or reuse existing local snapshot if already acquired).
2. Inspect: Read saved snapshot, perform passive inspection, save report.
3. Extract: Extract the 8 proof-of-concept fields and record provenance.
4. Validate: Validate extracted data against sanity checks and ground_truth.json.
5. Persist: Save consolidated experiment result JSON in output/.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import acquire, extract, inspect_response, validate

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        level=level,
        stream=sys.stderr,
    )


def process_single_app(
    url: str,
    *,
    raw_dir: str | Path = "data/raw",
    output_dir: str | Path = "output",
    ground_truth_path: str | Path = "data/ground_truth.json",
    timeout: int = 30,
    verbose_print: bool = True,
) -> dict[str, Any]:
    """Execute the complete single-app pipeline: acquire -> inspect -> extract -> validate -> persist.

    Returns
    -------
    dict[str, Any]
        Structured execution result containing status, app data, extraction meta,
        validation summary, and file paths.
    """
    raw_path_dir = Path(raw_dir)
    out_path_dir = Path(output_dir)
    out_path_dir.mkdir(parents=True, exist_ok=True)

    slug = acquire._slug_from_url(url)
    existing = acquire._find_existing(url, slug, raw_path_dir)
    snapshot_reused = existing is not None

    try:
        # ── Step 1: Acquire ──────────────────────────────────────────────────
        logger.info("Pipeline Step 1 — acquire: %s", url)
        raw = acquire.fetch(
            url=url,
            raw_dir=raw_path_dir,
            timeout=timeout,
        )

        if verbose_print:
            print(f"\n[OK] HTML body file : {raw.html_path}")
            print(f"[OK] Metadata file  : {raw.meta_path}")

        # ── Step 2: Inspect ──────────────────────────────────────────────────
        logger.info("Pipeline Step 2 — inspect: %s", raw.meta_path)
        report = inspect_response.inspect_from_raw_response(raw)
        report_text = report.to_text()

        if verbose_print:
            print()
            print(report_text)

        # Save inspection report text
        meta_stem = Path(raw.meta_path).stem
        if meta_stem.endswith(".meta"):
            meta_stem = meta_stem[:-len(".meta")]

        report_filename = f"{meta_stem}_inspection.txt"
        report_file = out_path_dir / report_filename
        report_file.write_text(report_text, encoding="utf-8")

        if verbose_print:
            print(f"\n[OK] Inspection report saved to: {report_file.resolve()}")

        # ── Step 3: Extract ──────────────────────────────────────────────────
        logger.info("Pipeline Step 3 — extract: %s", raw.html_path)
        app_data, ext_meta = extract.extract_from_raw_response(raw)

        if verbose_print:
            print("\n" + "=" * 72)
            print("APPSCOUT - EXTRACTION RESULT")
            print("=" * 72)
            for field_name, val in app_data.to_dict().items():
                src = ext_meta.sources.get(field_name, "(none)")
                val_repr = repr(val)
                if isinstance(val, str) and len(val) > 70:
                    val_repr = repr(val[:67] + "...")
                print(f"  {field_name:<18} : {val_repr:<35} | source: {src}")
            print(f"  Missing fields     : {ext_meta.missing or 'none'}")
            print(f"  Warnings           : {len(ext_meta.warnings)}")
            print("=" * 72)

        # ── Step 4: Validate ─────────────────────────────────────────────────
        logger.info("Pipeline Step 4 — validate: using %s", ground_truth_path)
        validation_result = validate.validate(app_data, ground_truth_path=ground_truth_path)

        summary = validation_result.get("summary", {})
        if verbose_print:
            print("\n" + "=" * 72)
            print("APPSCOUT - VALIDATION SUMMARY")
            print("=" * 72)
            print(f"  Checked fields          : {summary.get('checked_fields', 0)}")
            print(f"  Passed fields           : {summary.get('passed_fields', 0)}")
            print(f"  Failed fields           : {summary.get('failed_fields', 0)}")
            print(f"  Not checked (GT null)   : {summary.get('not_checked_fields', [])}")
            print(f"  All checked passed      : {summary.get('all_checked_fields_passed', False)}")
            print(f"  All sanity checks pass  : {summary.get('all_sanity_checks_passed', False)}")
            print("=" * 72)

        # ── Step 5: Save Final Result JSON ───────────────────────────────────
        fetch_timestamp = None
        try:
            meta_json = json.loads(Path(raw.meta_path).read_text(encoding="utf-8"))
            fetch_timestamp = meta_json.get("fetched_at")
        except Exception:
            pass
        if not fetch_timestamp:
            fetch_timestamp = datetime.now(timezone.utc).isoformat()

        experiment_result: dict[str, Any] = {
            "target_url": raw.url,
            "fetch_timestamp": fetch_timestamp,
            "inspection_summary": dataclasses.asdict(report),
            "extracted_data": app_data.to_dict(),
            "extraction_meta": ext_meta.to_dict(),
            "validation": validation_result,
        }

        result_filename = f"{meta_stem}_experiment_result.json"
        result_file = out_path_dir / result_filename
        result_file.write_text(
            json.dumps(experiment_result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if verbose_print:
            print(f"\n[OK] Experiment result JSON saved to: {result_file.resolve()}\n")

        return {
            "url": url,
            "slug": app_data.app_slug or slug,
            "status": "success",
            "snapshot_reused": snapshot_reused,
            "http_status": raw.status_code,
            "raw_response": raw,
            "inspection_report": report,
            "app_data": app_data,
            "extraction_meta": ext_meta,
            "validation_result": validation_result,
            "fields_extracted": 8 - len(ext_meta.missing),
            "missing_fields": ext_meta.missing,
            "sanity_checks_passed": summary.get("all_sanity_checks_passed", False),
            "result_file": str(result_file.resolve()),
            "error": None,
        }

    except Exception as exc:
        logger.error("Processing failed for %s: %s", url, exc)
        if verbose_print:
            print(f"\n[ERROR] Processing failed for {url}: {exc}", file=sys.stderr)
        return {
            "url": url,
            "slug": slug,
            "status": "failed",
            "snapshot_reused": snapshot_reused,
            "http_status": None,
            "raw_response": None,
            "inspection_report": None,
            "app_data": None,
            "extraction_meta": None,
            "validation_result": None,
            "fields_extracted": 0,
            "missing_fields": [],
            "sanity_checks_passed": False,
            "result_file": None,
            "error": str(exc),
        }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m experiment.run_experiment",
        description="Run the single-app acquisition, inspection, extraction, and validation pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--url",
        required=True,
        metavar="URL",
        help="Full URL of the Shopify App Store app page to process.",
    )
    parser.add_argument(
        "--raw-dir",
        default="data/raw",
        metavar="DIR",
        help="Directory where .html and .meta.json files are saved/reused. (default: data/raw)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        metavar="DIR",
        help="Directory where inspection and experiment result files are written. (default: output)",
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
        help="HTTP request timeout in seconds if acquiring. (default: 30)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging to stderr.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry-point for the complete single-app experiment pipeline."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
            sys.stderr.reconfigure(errors="replace")
        except Exception:
            pass

    args = _parse_args(argv)
    _configure_logging(args.verbose)

    result = process_single_app(
        url=args.url,
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        ground_truth_path=args.ground_truth,
        timeout=args.timeout,
        verbose_print=True,
    )

    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
