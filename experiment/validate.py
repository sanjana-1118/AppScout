"""
experiment/validate.py
-----------------------
Validate extracted AppData against sanity rules and optional ground truth.

Responsibilities:
  - Apply field-level sanity checks to AppData values.
  - Compare extracted values against a ground-truth JSON file where
    ground-truth values are non-null.
  - Return a plain JSON-serializable dict — no database, no HTTP, no HTML parsing.

Design constraints:
  - No network calls.
  - Does NOT import requests, BeautifulSoup, or acquire.
  - Accepts AppData (from extract.py) + path to ground_truth.json.
  - Ground-truth null fields are marked "not_checked" — never auto-failed.
  - Result is a plain dict, immediately JSON-serializable.

Validation rules per field
--------------------------
  Field           | Rule
  ----------------|-----------------------------------------------------------
  app_name        | exact string match
  app_slug        | exact string match
  app_url         | exact string match
  developer_name  | case-insensitive exact match
  description     | compare first 100 chars after stripping whitespace
  average_rating  | numeric difference <= 0.1
  review_count    | difference within 5%
  category        | case-insensitive exact match

Sanity checks
-------------
  app_name        : non-empty string, length < 200
  app_slug        : non-empty string
  app_url         : starts with "https://apps.shopify.com/"
  developer_name  : None  OR  non-empty string
  description     : None  OR  non-empty string
  average_rating  : None  OR  float in [0.0, 5.0]
  review_count    : None  OR  non-negative integer
  category        : None  OR  non-empty string
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from .models import AppData

logger = logging.getLogger(__name__)

# The complete ordered list of the 8 POC fields.
_ALL_FIELDS: list[str] = [
    "app_name",
    "app_slug",
    "app_url",
    "developer_name",
    "description",
    "average_rating",
    "review_count",
    "category",
]

# ---------------------------------------------------------------------------
# Ground-truth comparison helpers
# ---------------------------------------------------------------------------

def _compare_exact(expected: Any, actual: Any) -> bool:
    return str(expected) == str(actual)


def _compare_case_insensitive(expected: Any, actual: Any) -> bool:
    if expected is None or actual is None:
        return expected is actual
    return str(expected).strip().lower() == str(actual).strip().lower()


def _compare_description(expected: Any, actual: Any) -> bool:
    """Compare the first 100 characters after stripping whitespace."""
    if expected is None or actual is None:
        return expected is actual
    return str(expected).strip()[:100] == str(actual).strip()[:100]


def _compare_rating(expected: Any, actual: Any) -> bool:
    """Pass when |actual - expected| <= 0.1."""
    try:
        return abs(float(actual) - float(expected)) <= 0.1
    except (TypeError, ValueError):
        return False


def _compare_review_count(expected: Any, actual: Any) -> bool:
    """Pass when the absolute difference is within 5% of the expected value."""
    try:
        exp_f = float(expected)
        act_f = float(actual)
    except (TypeError, ValueError):
        return False
    if exp_f == 0:
        return act_f == 0
    return abs(act_f - exp_f) / exp_f <= 0.05


# Map each field name to its comparison function.
_COMPARATORS: dict[str, Any] = {
    "app_name":       _compare_exact,
    "app_slug":       _compare_exact,
    "app_url":        _compare_exact,
    "developer_name": _compare_case_insensitive,
    "description":    _compare_description,
    "average_rating": _compare_rating,
    "review_count":   _compare_review_count,
    "category":       _compare_case_insensitive,
}


def _load_ground_truth(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Load ground_truth.json, stripping non-field keys (e.g. _instructions)."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    # Keep only the 8 known fields; ignore meta-keys like _instructions.
    return {k: raw.get(k) for k in _ALL_FIELDS}


# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------

def _run_sanity_checks(app: AppData) -> dict[str, bool]:
    """Return a dict of check_name -> passed (bool)."""
    checks: dict[str, bool] = {}

    # app_name: non-empty string, length < 200
    checks["app_name_nonempty_string"] = (
        isinstance(app.app_name, str) and len(app.app_name.strip()) > 0
    )
    checks["app_name_length_lt_200"] = (
        isinstance(app.app_name, str) and len(app.app_name) < 200
    )

    # app_slug: non-empty string
    checks["app_slug_nonempty_string"] = (
        isinstance(app.app_slug, str) and len(app.app_slug.strip()) > 0
    )

    # app_url: starts with https://apps.shopify.com/
    checks["app_url_shopify_prefix"] = (
        isinstance(app.app_url, str)
        and app.app_url.startswith("https://apps.shopify.com/")
    )

    # developer_name: None OR non-empty string
    checks["developer_name_valid"] = (
        app.developer_name is None
        or (isinstance(app.developer_name, str) and len(app.developer_name.strip()) > 0)
    )

    # description: None OR non-empty string
    checks["description_valid"] = (
        app.description is None
        or (isinstance(app.description, str) and len(app.description.strip()) > 0)
    )

    # average_rating: None OR float in [0.0, 5.0]
    checks["average_rating_valid"] = (
        app.average_rating is None
        or (isinstance(app.average_rating, (int, float)) and 0.0 <= app.average_rating <= 5.0)
    )

    # review_count: None OR non-negative integer
    checks["review_count_valid"] = (
        app.review_count is None
        or (isinstance(app.review_count, int) and app.review_count >= 0)
    )

    # category: None OR non-empty string
    checks["category_valid"] = (
        app.category is None
        or (isinstance(app.category, str) and len(app.category.strip()) > 0)
    )

    return checks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate(
    app: AppData,
    ground_truth_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Validate extracted AppData and return a JSON-serializable result dict.

    Parameters
    ----------
    app : AppData
        The extracted data to validate.
    ground_truth_path : path-like, optional
        Path to ground_truth.json.  If None or the file does not exist,
        ground-truth comparison is skipped entirely.

    Returns
    -------
    dict
        Keys: "ground_truth_comparison", "sanity_checks", "summary".
        Fully JSON-serializable with no nested custom objects.
    """
    # ── Ground truth ─────────────────────────────────────────────────────────
    gt: dict[str, Any] = {}
    gt_available = False

    if ground_truth_path is not None:
        gt_path = Path(ground_truth_path)
        if gt_path.exists():
            gt = _load_ground_truth(gt_path)
            gt_available = True
            logger.info("Ground truth loaded from: %s", gt_path)
        else:
            logger.warning("Ground truth file not found: %s — comparison skipped", gt_path)

    # Build ground-truth comparison entries.
    gt_comparison: dict[str, dict[str, Any]] = {}
    checked = 0
    passed = 0
    failed = 0
    not_checked: list[str] = []

    for field in _ALL_FIELDS:
        actual = getattr(app, field)
        expected = gt.get(field) if gt_available else None

        if not gt_available or expected is None:
            # Ground truth absent or null — do not check, do not fail.
            gt_comparison[field] = {
                "expected": None,
                "actual": actual,
                "status": "not_checked",
            }
            not_checked.append(field)
            continue

        # Ground truth value is present — compare.
        comparator = _COMPARATORS[field]
        passed_check = comparator(expected, actual)
        status = "pass" if passed_check else "fail"

        gt_comparison[field] = {
            "expected": expected,
            "actual": actual,
            "status": status,
        }
        checked += 1
        if passed_check:
            passed += 1
        else:
            failed += 1

    # ── Sanity checks ─────────────────────────────────────────────────────────
    sanity = _run_sanity_checks(app)
    all_sanity_passed = all(sanity.values())

    # ── Summary ───────────────────────────────────────────────────────────────
    summary: dict[str, Any] = {
        "checked_fields": checked,
        "passed_fields": passed,
        "failed_fields": failed,
        "not_checked_fields": not_checked,
        "all_checked_fields_passed": (failed == 0),
        "all_sanity_checks_passed": all_sanity_passed,
    }

    result: dict[str, Any] = {
        "ground_truth_comparison": gt_comparison,
        "sanity_checks": sanity,
        "summary": summary,
    }

    logger.info(
        "Validation complete: %d checked (%d pass / %d fail), "
        "%d not_checked, sanity=%s",
        checked, passed, failed, len(not_checked),
        "ALL PASS" if all_sanity_passed else "SOME FAIL",
    )

    return result
