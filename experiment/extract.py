"""
experiment/extract.py
---------------------
Extract the 8 proof-of-concept fields from a saved Shopify App Store HTML snapshot.

Design constraints:
  - Reads ONLY local files.  No network calls.  Does NOT import requests.
  - Accepts the file paths produced by acquire.py (html_path, meta_path).
  - Uses BeautifulSoup with the built-in html.parser (no lxml required).
  - Every extracted field is accompanied by a provenance label in ExtractionMeta.sources.
  - Fields that cannot be extracted are left as None and listed in ExtractionMeta.missing.
  - No guessing, no fallback invention, no framework.

Extraction sources (discovered from the saved Judge.me snapshot):

  Field             | Primary source
  ------------------|----------------------------------------------------------
  app_name          | JSON-LD SoftwareApplication.name
  app_slug          | Canonical URL path last segment
  app_url           | <link rel="canonical"> href
  developer_name    | JSON-LD SoftwareApplication.brand
  description       | JSON-LD SoftwareApplication.description
  average_rating    | JSON-LD SoftwareApplication.aggregateRating.ratingValue
  review_count      | JSON-LD SoftwareApplication.aggregateRating.ratingCount
  category          | <a href=".../categories/...?...surface_type=app_details">
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .extract_pricing import extract_pricing_from_soup
from .models import AppData, ExtractionMeta, RawResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_json_ld(soup: BeautifulSoup, warnings: list[str]) -> dict[str, Any]:
    """Find and parse the first <script type="application/ld+json"> block.

    Returns the parsed dict, or an empty dict if the block is absent or
    malformed.  Appends a warning instead of raising.
    """
    tag = soup.find("script", attrs={"type": "application/ld+json"})
    if tag is None:
        warnings.append("No <script type='application/ld+json'> block found.")
        return {}
    raw = (tag.string or "").strip()
    if not raw:
        warnings.append("JSON-LD <script> block is present but empty.")
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        warnings.append(f"JSON-LD parse error: {exc}")
        return {}
    if not isinstance(data, dict):
        warnings.append(f"JSON-LD root is not an object (got {type(data).__name__}).")
        return {}
    return data


def _slug_from_url(url: str) -> str | None:
    """Return the last non-empty path segment of a URL as the app slug.

    Example:
        https://apps.shopify.com/judgeme  ->  "judgeme"
        https://apps.shopify.com/         ->  None
    """
    try:
        path = urlparse(url).path.strip("/")
        if not path:
            return None
        segment = path.split("/")[-1]
        return segment or None
    except Exception:
        return None


def _coerce_float(value: Any, field: str, warnings: list[str]) -> float | None:
    """Safely coerce a value to float, recording a warning on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        warnings.append(
            f"Could not coerce {field}={value!r} to float — left as None."
        )
        return None


def _coerce_int(value: Any, field: str, warnings: list[str]) -> int | None:
    """Safely coerce a value to int, recording a warning on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        warnings.append(
            f"Could not coerce {field}={value!r} to int — left as None."
        )
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_from_files(
    html_path: str | os.PathLike[str],
    meta_path: str | os.PathLike[str],
) -> tuple[AppData, ExtractionMeta]:
    """Extract the 8 proof-of-concept fields from a saved .html + .meta.json pair.

    Parameters
    ----------
    html_path : path-like
        Absolute path to the .html file written by acquire.fetch().
    meta_path : path-like
        Absolute path to the .meta.json file written by acquire.fetch().

    Returns
    -------
    (AppData, ExtractionMeta)
        AppData holds the extracted field values.
        ExtractionMeta records provenance, missing fields, and any warnings.

    No network calls are made.  Both files must already exist on disk.
    """
    html_p = Path(html_path)
    meta_p = Path(meta_path)

    logger.info("Extracting from HTML : %s", html_p)
    logger.info("Extracting from meta : %s", meta_p)

    # The .html file is always written as UTF-8 by acquire.py.
    html_text = html_p.read_text(encoding="utf-8")
    meta = json.loads(meta_p.read_text(encoding="utf-8"))

    soup = BeautifulSoup(html_text, "html.parser")

    sources: dict[str, str] = {}
    warnings: list[str] = []

    # ── 1. Parse JSON-LD ────────────────────────────────────────────────────
    ld = _parse_json_ld(soup, warnings)
    aggregate_rating: dict[str, Any] = {}
    if ld:
        aggregate_rating = ld.get("aggregateRating") or {}
        if not isinstance(aggregate_rating, dict):
            warnings.append(
                f"aggregateRating is not an object (got {type(aggregate_rating).__name__})"
                " — rating fields left as None."
            )
            aggregate_rating = {}

    # ── 2. Canonical URL ─────────────────────────────────────────────────────
    canonical_url: str | None = None
    canonical_el = soup.find("link", attrs={"rel": "canonical"})
    if canonical_el and canonical_el.get("href"):
        canonical_url = str(canonical_el["href"]).strip() or None

    # ── 3. Extract each field ────────────────────────────────────────────────

    # app_url
    app_url: str | None = canonical_url
    if app_url:
        sources["app_url"] = "canonical_link"
    else:
        # Fallback: og:url meta tag
        og_url_el = soup.find("meta", attrs={"property": "og:url"})
        if og_url_el and og_url_el.get("content"):
            app_url = str(og_url_el["content"]).strip() or None
            if app_url:
                sources["app_url"] = "og:url_meta"
        if not app_url:
            # Last resort: final_url from the meta file (no tracking params)
            app_url = meta.get("final_url") or meta.get("requested_url") or None
            if app_url:
                sources["app_url"] = "meta_json.final_url"

    # app_slug  — derived from canonical/final URL, not invented
    app_slug: str | None = _slug_from_url(app_url) if app_url else None
    if app_slug:
        sources["app_slug"] = "canonical_url_path"

    # app_name  — JSON-LD.name with h1, og:title, and title tag fallbacks
    app_name: str | None = ld.get("name") or None
    if app_name:
        sources["app_name"] = "json_ld.name"
    else:
        h1_tag = soup.find("h1")
        if h1_tag and h1_tag.get_text(strip=True):
            app_name = h1_tag.get_text(strip=True)
            sources["app_name"] = "html_h1"
        else:
            og_title = soup.find("meta", attrs={"property": "og:title"})
            if og_title and og_title.get("content"):
                t_val = str(og_title["content"]).split("|")[0].split("- Shopify")[0].strip()
                if t_val:
                    app_name = t_val
                    sources["app_name"] = "og_title_meta"
            elif soup.title and soup.title.get_text(strip=True):
                t_val = soup.title.get_text(strip=True).split("|")[0].split("- Shopify")[0].strip()
                if t_val and "page not found" not in t_val.lower() and "404" not in t_val.lower():
                    app_name = t_val
                    sources["app_name"] = "html_title"

    # developer_name  — JSON-LD.brand with partner link fallback
    developer_name: str | None = ld.get("brand") or None
    if developer_name:
        sources["developer_name"] = "json_ld.brand"
    else:
        partner_link = soup.find("a", href=lambda h: h and "/partners/" in h)
        if partner_link and partner_link.get_text(strip=True):
            developer_name = partner_link.get_text(strip=True)
            sources["developer_name"] = "partner_link_anchor"

    # description  — JSON-LD.description with meta description fallback
    description: str | None = ld.get("description") or None
    if description:
        sources["description"] = "json_ld.description"
    else:
        og_desc = soup.find("meta", attrs={"property": "og:description"}) or soup.find("meta", attrs={"name": "description"})
        if og_desc and og_desc.get("content"):
            d_val = str(og_desc["content"]).strip()
            if d_val and len(d_val) > 10:
                description = d_val
                sources["description"] = "meta_description"

    # average_rating  — JSON-LD.aggregateRating.ratingValue
    _rv = aggregate_rating.get("ratingValue")
    average_rating: float | None = _coerce_float(_rv, "ratingValue", warnings) if _rv is not None else None
    if average_rating is not None:
        sources["average_rating"] = "json_ld.aggregateRating.ratingValue"

    # review_count  — JSON-LD.aggregateRating.ratingCount
    _rc = aggregate_rating.get("ratingCount")
    review_count: int | None = _coerce_int(_rc, "ratingCount", warnings) if _rc is not None else None
    if review_count is not None:
        sources["review_count"] = "json_ld.aggregateRating.ratingCount"

    # category  — app-specific category anchor (surface_type=app_details)
    # Primary: <a href containing /categories/ AND surface_type=app_details>
    # Fallback: <a href containing /categories/> (excluding navbar blocks) with slug derivation
    category: str | None = None
    cat_anchor = soup.find(
        "a",
        href=lambda h: (
            h is not None
            and "/categories/" in h
            and "surface_type=app_details" in h
        ),
    )
    if cat_anchor:
        text = cat_anchor.get_text(strip=True)
        if text:
            category = text
            sources["category"] = "app_specific_category_anchor"

    # Fallback if primary anchor not found
    if category is None:
        fallback_anchor = soup.find(
            "a",
            href=lambda h: (
                h is not None
                and "/categories/" in h
                and "navbar" not in h
            ),
        )
        if fallback_anchor and fallback_anchor.get("href"):
            href = fallback_anchor["href"]
            fb_text = fallback_anchor.get_text(strip=True)
            if fb_text and len(fb_text) < 60 and "\n" not in fb_text:
                category = fb_text
            else:
                cat_path = urlparse(href).path.strip("/").split("/")
                if len(cat_path) >= 2 and cat_path[0] == "categories":
                    slug = cat_path[-1]
                    if slug:
                        category = slug.replace("-", " ").replace("_", " ").strip().capitalize()

            if category:
                sources["category"] = "category_url_fallback"
                warnings.append("Category extracted using fallback strategy (category_url_fallback).")

    if category is None:
        warnings.append("Category could not be extracted.")

    # ── 4. Pricing & Plans Extraction ────────────────────────────────────────
    pricing_data = extract_pricing_from_soup(soup)
    sources["pricing"] = "shopify_pricing_cards"

    # ── 5. Record missing fields ─────────────────────────────────────────────
    all_fields = [
        "app_name", "app_slug", "app_url", "developer_name",
        "description", "average_rating", "review_count", "category",
    ]
    field_values = {
        "app_name": app_name,
        "app_slug": app_slug,
        "app_url": app_url,
        "developer_name": developer_name,
        "description": description,
        "average_rating": average_rating,
        "review_count": review_count,
        "category": category,
    }
    missing = [f for f in all_fields if field_values[f] is None]

    # ── 6. Assemble result objects ───────────────────────────────────────────
    app_data = AppData(
        app_name=app_name,
        app_slug=app_slug,
        app_url=app_url,
        developer_name=developer_name,
        description=description,
        average_rating=average_rating,
        review_count=review_count,
        category=category,
        pricing_type=pricing_data.pricing_type,
        free_trial_days=pricing_data.free_trial_days,
        pricing_plans=[p.to_dict() for p in pricing_data.plans],
    )

    extraction_meta = ExtractionMeta(
        html_path=str(html_p.resolve()),
        meta_path=str(meta_p.resolve()),
        sources=sources,
        missing=missing,
        warnings=warnings,
    )

    logger.info(
        "Extraction complete: %d/%d fields extracted, %d missing, %d warning(s)",
        len(all_fields) - len(missing),
        len(all_fields),
        len(missing),
        len(warnings),
    )

    return app_data, extraction_meta


def extract_from_raw_response(raw: RawResponse) -> tuple[AppData, ExtractionMeta]:
    """Convenience wrapper: extract from a RawResponse produced by acquire.fetch().

    Reads from the saved files (raw.html_path, raw.meta_path) — not from the
    in-memory body_text — so the saved file is always the authoritative source.
    """
    return extract_from_files(
        html_path=raw.html_path,
        meta_path=raw.meta_path,
    )
