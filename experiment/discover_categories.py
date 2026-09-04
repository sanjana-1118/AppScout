"""
experiment/discover_categories.py
---------------------------------
Phase 2E: Category Taxonomy Discovery Module for Shopify App Store.

Discovers, classifies, normalizes, and deduplicates Shopify App Store
category URLs from server-rendered directory and navigation structures.

Design constraints:
  - Systematically extracts category URLs from page HTML.
  - Distinguishes top-level root categories from crawlable leaf subcategories.
  - Reuses existing acquire.py snapshot mechanism (0 network requests if cached).
  - Preserves discovery order.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from . import acquire

logger = logging.getLogger(__name__)

SHOPIFY_APP_STORE_BASE = "https://apps.shopify.com"

# The 7 canonical root/parent category slugs on Shopify App Store
TOP_LEVEL_ROOT_SLUGS = {
    "finding-products",
    "marketing-and-conversion",
    "orders-and-shipping",
    "sales-channels",
    "selling-products",
    "store-design",
    "store-management",
}


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        level=level,
        stream=sys.stderr,
    )


def extract_categories_from_html(
    html_text: str,
    source_url: str = SHOPIFY_APP_STORE_BASE,
) -> list[dict[str, Any]]:
    """Parse HTML and discover normalized category metadata records.

    Parameters
    ----------
    html_text : str
        The raw HTML containing category navigation or directory links.
    source_url : str
        The URL the HTML was fetched from (used for resolving relative links).

    Returns
    -------
    list[dict[str, Any]]
        Ordered list of discovered category dictionaries.
    """
    soup = BeautifulSoup(html_text, "html.parser")

    category_map: dict[str, dict[str, Any]] = {}

    for a in soup.find_all("a", href=True):
        raw_href = a["href"].strip()
        if not raw_href or "/categories/" not in raw_href:
            continue

        full_url = urljoin(source_url, raw_href)
        parsed = urlparse(full_url)

        if parsed.netloc.lower() != "apps.shopify.com":
            continue

        clean_path = parsed.path.strip("/")
        if not clean_path.startswith("categories/"):
            continue

        category_slug = clean_path[len("categories/"):].rstrip("/all").strip("/")
        if not category_slug or not re.match(r"^[a-zA-Z0-9_-]+$", category_slug):
            continue

        normalized_url = f"https://apps.shopify.com/categories/{category_slug}"

        label = a.get_text(strip=True)
        if not label or len(label) > 120:
            label = category_slug.replace("-", " ").capitalize()

        is_root = category_slug in TOP_LEVEL_ROOT_SLUGS
        category_type = "root" if is_root else "leaf"
        # Leaf subcategories are the primary crawlable listing targets
        is_crawlable = not is_root

        if normalized_url not in category_map:
            category_map[normalized_url] = {
                "url": normalized_url,
                "slug": category_slug,
                "label": label,
                "type": category_type,
                "crawlable": is_crawlable,
                "discovered_from": source_url,
            }

    return list(category_map.values())


def discover_category_taxonomy(
    source_url: str = SHOPIFY_APP_STORE_BASE,
    *,
    deep: bool = True,
    raw_dir: str | Path = "data/raw",
    output_dir: str | Path = "data/discovered/categories",
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """Discover the full category taxonomy by acquiring directory & root page snapshots.

    Parameters
    ----------
    source_url : str
        URL of the page containing the category directory (default: App Store homepage).
    deep : bool
        If True, also acquires the 7 root category pages to discover all subcategories.
    raw_dir : path-like
        Directory where raw snapshots are stored/reused.
    output_dir : path-like
        Directory where taxonomy JSON will be saved.
    timeout : int
        HTTP socket timeout.

    Returns
    -------
    list[dict[str, Any]]
        List of all discovered category records.
    """
    raw = acquire.fetch(source_url, raw_dir=raw_dir, timeout=timeout)
    categories = extract_categories_from_html(raw.body_text, source_url=raw.url)

    if deep:
        cat_map: dict[str, dict[str, Any]] = {c["slug"]: c for c in categories}
        root_slugs = [c["slug"] for c in categories if c["type"] == "root"]
        for r_slug in root_slugs:
            r_url = f"{SHOPIFY_APP_STORE_BASE}/categories/{r_slug}"
            try:
                r_raw = acquire.fetch(r_url, raw_dir=raw_dir, timeout=timeout)
                sub_cats = extract_categories_from_html(r_raw.body_text, source_url=r_raw.url)
                for sc in sub_cats:
                    if sc["slug"] not in cat_map:
                        cat_map[sc["slug"]] = sc
            except Exception as exc:
                logger.warning("Could not fetch subcategories for root %s: %s", r_slug, exc)

        categories = list(cat_map.values())

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    compact_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    taxonomy_file = out_path / f"category_taxonomy_{compact_ts}.json"

    taxonomy_payload = {
        "source_url": source_url,
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "total_categories": len(categories),
        "root_count": sum(1 for c in categories if c["type"] == "root"),
        "leaf_count": sum(1 for c in categories if c["type"] == "leaf"),
        "crawlable_count": sum(1 for c in categories if c["crawlable"]),
        "categories": categories,
    }

    taxonomy_file.write_text(
        json.dumps(taxonomy_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Category taxonomy saved to: %s", taxonomy_file.resolve())

    return categories


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m experiment.discover_categories",
        description="Phase 2E: Discover Shopify App Store category taxonomy and crawlable leaf categories.",
    )
    parser.add_argument(
        "--source-url",
        default=SHOPIFY_APP_STORE_BASE,
        metavar="URL",
        help="Shopify App Store directory page URL. (default: https://apps.shopify.com)",
    )
    parser.add_argument(
        "--raw-dir",
        default="data/raw",
        metavar="DIR",
        help="Directory where raw snapshots are stored/reused. (default: data/raw)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/discovered/categories",
        metavar="DIR",
        help="Directory where taxonomy JSON is saved. (default: data/discovered/categories)",
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
    """CLI entry-point for category taxonomy discovery."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
            sys.stderr.reconfigure(errors="replace")
        except Exception:
            pass

    args = _parse_args(argv)
    _configure_logging(args.verbose)

    try:
        cats = discover_category_taxonomy(
            source_url=args.source_url,
            raw_dir=args.raw_dir,
            output_dir=args.output_dir,
            timeout=args.timeout,
        )

        root_cats = [c for c in cats if c["type"] == "root"]
        leaf_cats = [c for c in cats if c["type"] == "leaf"]

        print("\n" + "=" * 76)
        print("APPSCOUT - CATEGORY TAXONOMY DISCOVERY")
        print("=" * 76)
        print(f"Source URL               : {args.source_url}")
        print(f"Total Categories Found   : {len(cats)}")
        print(f"Root Categories          : {len(root_cats)}")
        print(f"Crawlable Leaf Categories: {len(leaf_cats)}")
        print("-" * 76)
        print("ROOT CATEGORIES (7 Primary Taxonomies):")
        print("-" * 76)
        for i, c in enumerate(root_cats, 1):
            print(f"  {i:2d}. {c['slug']:<30} | {c['url']}")
        print("-" * 76)
        print("CRAWLABLE LEAF SUBCATEGORIES:")
        print("-" * 76)
        for i, c in enumerate(leaf_cats, 1):
            print(f"  {i:2d}. {c['slug']:<50} | {c['label']}")
        print("=" * 76 + "\n")
        return 0

    except Exception as exc:
        logger.error("Category taxonomy discovery failed: %s", exc)
        print(f"\n[ERROR] Category taxonomy discovery failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
