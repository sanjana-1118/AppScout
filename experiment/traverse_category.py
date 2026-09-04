"""
experiment/traverse_category.py
-------------------------------
Phase 2D: Category Pagination Traverser for Shopify App Store.

Sequentially traverses all pagination pages of a single Shopify App Store
category by following standard HTML <a rel="next"> links until the end of
the category is reached or a loop/safety limit is encountered.

Design constraints:
  - Follows actual rel="next" links (never hardcodes page numbers or bounds).
  - Uses existing acquire.py for single-request snapshot storage and 100% offline reuse.
  - Applies polite delay ONLY between live network requests (never on reused snapshots).
  - Maintains category-wide ordered deduplication across all visited pages.
  - Implements loop safety: tracks visited URLs and stops if a repeat URL is detected.
  - Persists complete category discovery output to data/discovered/categories/.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from . import acquire, discover
from .models import CategoryTraversalResult

logger = logging.getLogger(__name__)

SHOPIFY_APP_STORE_BASE = "https://apps.shopify.com"


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        level=level,
        stream=sys.stderr,
    )


def find_next_page_url(html_text: str, current_url: str = SHOPIFY_APP_STORE_BASE) -> str | None:
    """Find the next pagination page URL by inspecting rel='next' anchor tags.

    Parameters
    ----------
    html_text : str
        The raw HTML content of the current category page.
    current_url : str
        The current page URL for relative URL resolution.

    Returns
    -------
    str | None
        Normalized absolute URL for the next page, or None if no rel='next' exists.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    rel_next_tag = soup.find("a", attrs={"rel": lambda r: r and "next" in r})
    if rel_next_tag and rel_next_tag.get("href"):
        raw_href = rel_next_tag["href"].strip()
        if raw_href:
            return urljoin(current_url, raw_href)
    return None


def traverse_category(
    category_url: str,
    *,
    max_pages: int | None = None,
    delay: float = 1.5,
    raw_dir: str | Path = "data/raw",
    output_dir: str | Path = "data/discovered/categories",
    timeout: int = 30,
) -> CategoryTraversalResult:
    """Traverse all pagination pages of a category and compile a deduplicated app list.

    Parameters
    ----------
    category_url : str
        The starting category landing page URL.
    max_pages : int | None
        Optional safety limit on the number of pages to traverse.
    delay : float
        Polite delay in seconds between NEW live HTTP GET requests.
    raw_dir : path-like
        Directory where raw page snapshots are saved/reused.
    output_dir : path-like
        Directory where complete category discovery JSON will be written.
    timeout : int
        HTTP socket timeout in seconds.

    Returns
    -------
    CategoryTraversalResult
        Structured dataclass with all traversal metrics and the master app URL list.
    """
    raw_path_dir = Path(raw_dir)
    raw_path_dir.mkdir(parents=True, exist_ok=True)

    out_path_dir = Path(output_dir)
    out_path_dir.mkdir(parents=True, exist_ok=True)

    category_slug = acquire._slug_from_url(category_url)

    visited_pages: set[str] = set()
    page_urls: list[str] = []
    seen_app_urls: set[str] = set()
    master_app_urls: list[str] = []

    total_urls_encountered = 0
    duplicates_removed = 0
    snapshots_reused = 0
    new_http_requests = 0
    stopped_reason = "unknown"

    current_url: str | None = category_url

    print("\n" + "=" * 76)
    print("APPSCOUT - PHASE 2D CATEGORY PAGINATION TRAVERSER")
    print("=" * 76)
    print(f"Target Category     : {category_url}")
    print(f"Category Slug       : {category_slug}")
    print(f"Max Pages Limit     : {max_pages if max_pages is not None else 'Unlimited (Follow rel=next)'}")
    print(f"Polite Delay        : {delay}s (applied only on new HTTP requests)")
    print("=" * 76 + "\n")

    page_num = 0

    while current_url:
        page_num += 1

        # ── Loop & Limit Safety Checks ───────────────────────────────────────
        if current_url in visited_pages:
            logger.warning("Pagination loop detected at URL: %s", current_url)
            stopped_reason = "loop_detected"
            break

        if max_pages is not None and len(page_urls) >= max_pages:
            logger.info("Safety limit reached: %d pages processed", max_pages)
            stopped_reason = "max_pages_reached"
            break

        visited_pages.add(current_url)
        page_urls.append(current_url)

        # ── Check Snapshot Reuse ─────────────────────────────────────────────
        page_slug = acquire._slug_from_url(current_url)
        existing = acquire._find_existing(current_url, page_slug, raw_path_dir)
        is_reused = existing is not None

        if is_reused:
            snapshots_reused += 1
            reuse_label = "REUSED SNAPSHOT"
        else:
            new_http_requests += 1
            reuse_label = "NEW HTTP GET"

        logger.info("Page [%d]: %s (%s)", page_num, current_url, reuse_label)

        # ── Acquire Page ─────────────────────────────────────────────────────
        try:
            raw = acquire.fetch(current_url, raw_dir=raw_path_dir, timeout=timeout)
        except Exception as exc:
            logger.error("Failed to acquire page %s: %s", current_url, exc)
            stopped_reason = f"acquisition_error: {exc}"
            break

        # ── Extract App URLs from Page HTML ──────────────────────────────────
        page_apps, page_dups, page_filts = discover.extract_app_urls_from_html(
            raw.body_text,
            base_url=current_url,
        )

        total_urls_encountered += len(page_apps) + page_dups

        new_apps_on_page = 0
        for app_url in page_apps:
            if app_url not in seen_app_urls:
                seen_app_urls.add(app_url)
                master_app_urls.append(app_url)
                new_apps_on_page += 1
            else:
                duplicates_removed += 1

        print(
            f"  Page {page_num:2d} | {reuse_label:<15} | "
            f"Apps on page: {len(page_apps):2d} (New: {new_apps_on_page:2d}) | "
            f"Total unique so far: {len(master_app_urls):3d}"
        )

        # ── Inspect Next Page Anchor ─────────────────────────────────────────
        next_url = find_next_page_url(raw.body_text, current_url)

        if not next_url:
            logger.info("No rel='next' anchor found on page %d. Reached end of category.", page_num)
            stopped_reason = "no_next_page"
            break

        if next_url in visited_pages:
            logger.warning("rel='next' points to already visited page (%s). Stopping loop.", next_url)
            stopped_reason = "loop_detected"
            break

        # ── Polite Delay (only after live network request) ───────────────────
        if not is_reused and delay > 0:
            logger.debug("Sleeping %ss before next request...", delay)
            time.sleep(delay)

        current_url = next_url

    # ── Consolidate and Save Result ──────────────────────────────────────────
    traversal_timestamp = datetime.now(timezone.utc).isoformat()
    compact_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    result = CategoryTraversalResult(
        category_url=category_url,
        category_slug=category_slug,
        traversal_timestamp=traversal_timestamp,
        pages_processed=len(page_urls),
        page_urls=page_urls,
        app_urls=master_app_urls,
        total_urls_encountered=total_urls_encountered,
        unique_app_urls=len(master_app_urls),
        duplicates_removed=duplicates_removed,
        snapshots_reused=snapshots_reused,
        new_http_requests=new_http_requests,
        delay_seconds=delay,
        stopped_reason=stopped_reason,
    )

    out_filename = f"{category_slug}_{compact_ts}_complete_discovery.json"
    out_file_path = out_path_dir / out_filename
    out_file_path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Category traversal result saved to: %s", out_file_path.resolve())

    print("\n" + "=" * 76)
    print("APPSCOUT - CATEGORY TRAVERSAL SUMMARY")
    print("=" * 76)
    print(f"Category Slug               : {result.category_slug}")
    print(f"Pages Processed             : {result.pages_processed}")
    print(f"Total App URLs Encountered  : {result.total_urls_encountered}")
    print(f"Total Unique Apps Discovered: {result.unique_app_urls}")
    print(f"Cross-Page Duplicates Pruned: {result.duplicates_removed}")
    print(f"Snapshots Reused            : {result.snapshots_reused}")
    print(f"New HTTP Requests Made      : {result.new_http_requests}")
    print(f"Stopped Reason              : {result.stopped_reason}")
    print("=" * 76)
    print(f"\n[OK] Complete category discovery JSON saved to:\n  {out_file_path.resolve()}\n")

    return result


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m experiment.traverse_category",
        description="Phase 2D: Sequentially traverse all pagination pages of a Shopify App Store category.",
    )
    parser.add_argument(
        "--url",
        required=True,
        metavar="URL",
        help="Shopify App Store category landing page URL.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        metavar="N",
        help="Optional safety limit on maximum pages to traverse. (default: None - follow rel=next to end)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        metavar="SECONDS",
        help="Polite delay between new live HTTP requests in seconds. (default: 1.5)",
    )
    parser.add_argument(
        "--raw-dir",
        default="data/raw",
        metavar="DIR",
        help="Directory where raw snapshots are saved/reused. (default: data/raw)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/discovered/categories",
        metavar="DIR",
        help="Directory where category discovery result JSON is saved. (default: data/discovered/categories)",
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
    """CLI entry-point for category pagination traversal."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
            sys.stderr.reconfigure(errors="replace")
        except Exception:
            pass

    args = _parse_args(argv)
    _configure_logging(args.verbose)

    try:
        res = traverse_category(
            category_url=args.url,
            max_pages=args.max_pages,
            delay=args.delay,
            raw_dir=args.raw_dir,
            output_dir=args.output_dir,
            timeout=args.timeout,
        )
        return 0
    except Exception as exc:
        logger.error("Category traversal failed: %s", exc)
        print(f"\n[ERROR] Category traversal failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
