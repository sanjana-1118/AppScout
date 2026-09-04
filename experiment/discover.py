"""
experiment/discover.py
----------------------
Automated App URL Discovery from a Shopify App Store listing or category page.

Phase 2A: Discovers, normalizes, filters, and deduplicates Shopify App Store
app listing URLs from a single listing/category page snapshot.

Design constraints:
  - Reuses existing acquire.py for single-request snapshot acquisition and offline reuse.
  - No crawling, no pagination, no database, no concurrency.
  - URL normalization: converts to https://apps.shopify.com/<app-slug>, removes queries and fragments.
  - Robust non-app link filtering (excludes categories, stories, auth, navigation, and external links).
  - Deduplicates URLs while strictly preserving discovery order.
  - Saves discovery result to data/discovered/<slug>_<timestamp>.json.
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
from .models import DiscoveryResult, RawResponse

logger = logging.getLogger(__name__)

# Base domain for official Shopify App Store
SHOPIFY_APP_STORE_DOMAIN = "apps.shopify.com"

# Known non-app top-level path segments on apps.shopify.com
RESERVED_NON_APP_SLUGS = {
    "",
    "about",
    "admin",
    "apps",
    "categories",
    "collections",
    "help",
    "legal",
    "login",
    "oauth",
    "partner",
    "partners",
    "pricing",
    "search",
    "services",
    "signup",
    "sitemap",
    "stories",
}


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        level=level,
        stream=sys.stderr,
    )


def extract_app_urls_from_html(
    html_text: str,
    base_url: str = f"https://{SHOPIFY_APP_STORE_DOMAIN}",
) -> tuple[list[str], int, int]:
    """Parse HTML and discover normalized, deduplicated app listing URLs.

    Parameters
    ----------
    html_text : str
        The raw HTML of the listing/category page.
    base_url : str
        Base URL for resolving relative links.

    Returns
    -------
    unique_urls : list[str]
        Deduplicated list of absolute app URLs (e.g. "https://apps.shopify.com/judgeme").
    duplicate_count : int
        Number of duplicate app links encountered.
    filtered_count : int
        Number of non-app links filtered out.
    """
    soup = BeautifulSoup(html_text, "html.parser")

    discovered_urls: list[str] = []
    filtered_count = 0
    duplicate_count = 0
    seen_urls: set[str] = set()

    for a_tag in soup.find_all("a", href=True):
        raw_href = a_tag["href"].strip()
        if not raw_href:
            continue

        full_url = urljoin(base_url, raw_href)
        parsed = urlparse(full_url)

        # 1. Domain filter: must be apps.shopify.com
        if parsed.netloc.lower() != SHOPIFY_APP_STORE_DOMAIN:
            filtered_count += 1
            continue

        # 2. Path normalization: extract path segments without leading/trailing slashes
        clean_path = parsed.path.strip("/")
        segments = [s for s in clean_path.split("/") if s]

        # 3. Structure filter: an app listing URL has exactly one path segment (the slug)
        if len(segments) != 1:
            filtered_count += 1
            continue

        slug = segments[0].strip()
        slug_lower = slug.lower()

        # 4. Reserved slug filter: ignore non-app pages (categories, stories, search, etc.)
        if slug_lower in RESERVED_NON_APP_SLUGS:
            filtered_count += 1
            continue

        # Basic slug format check (alphanumeric with hyphens/underscores)
        if not re.match(r"^[a-zA-Z0-9_-]+$", slug):
            filtered_count += 1
            continue

        # 5. Normalized canonical app listing URL (no query parameters, no fragments)
        normalized_url = f"https://{SHOPIFY_APP_STORE_DOMAIN}/{slug}"

        # 6. Deduplication preserving discovery order
        if normalized_url in seen_urls:
            duplicate_count += 1
            continue

        seen_urls.add(normalized_url)
        discovered_urls.append(normalized_url)

    return discovered_urls, duplicate_count, filtered_count


def discover_from_raw_response(
    raw: RawResponse,
    *,
    output_dir: str | Path = "data/discovered",
) -> DiscoveryResult:
    """Discover app URLs from a saved RawResponse and persist the result.

    Parameters
    ----------
    raw : RawResponse
        The raw response snapshot from acquire.py.
    output_dir : path-like
        Directory where discovered URL JSON will be saved.

    Returns
    -------
    DiscoveryResult
        Structured dataclass containing discovered URLs and metadata.
    """
    html_path = Path(raw.html_path)
    html_text = html_path.read_text(encoding="utf-8")

    urls, dup_count, filt_count = extract_app_urls_from_html(
        html_text=html_text,
        base_url=raw.url,
    )

    fetch_timestamp = None
    if raw.meta_path and Path(raw.meta_path).exists():
        try:
            meta_json = json.loads(Path(raw.meta_path).read_text(encoding="utf-8"))
            fetch_timestamp = meta_json.get("fetched_at")
        except Exception:
            pass
    if not fetch_timestamp:
        fetch_timestamp = datetime.now(timezone.utc).isoformat()

    result = DiscoveryResult(
        source_url=raw.url,
        fetch_timestamp=fetch_timestamp,
        discovered_count=len(urls),
        urls=urls,
        html_path=str(raw.html_path),
        meta_path=str(raw.meta_path) if raw.meta_path else None,
        duplicate_count=dup_count,
        filtered_count=filt_count,
    )

    # Save discovery result JSON
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    meta_stem = Path(raw.meta_path).stem if raw.meta_path else "discovery"
    if meta_stem.endswith(".meta"):
        meta_stem = meta_stem[:-len(".meta")]

    save_path = out_dir / f"{meta_stem}_discovered.json"
    save_path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Discovery result saved to: %s", save_path.resolve())

    return result


def discover_from_url(
    url: str,
    *,
    raw_dir: str | Path = "data/raw",
    output_dir: str | Path = "data/discovered",
    timeout: int = 30,
) -> DiscoveryResult:
    """Acquire (or reuse) a category listing page and discover app URLs."""
    raw = acquire.fetch(url, raw_dir=raw_dir, timeout=timeout)
    return discover_from_raw_response(raw, output_dir=output_dir)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m experiment.discover",
        description="Phase 2A: Automatically discover app listing URLs from a Shopify App Store listing page.",
    )
    parser.add_argument(
        "--url",
        required=True,
        metavar="URL",
        help="Shopify App Store category or listing page URL.",
    )
    parser.add_argument(
        "--raw-dir",
        default="data/raw",
        metavar="DIR",
        help="Directory to save/reuse raw HTML snapshots. (default: data/raw)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/discovered",
        metavar="DIR",
        help="Directory where discovery results are written. (default: data/discovered)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        metavar="SECONDS",
        help="HTTP request timeout in seconds. (default: 30)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry-point for automated app URL discovery."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
            sys.stderr.reconfigure(errors="replace")
        except Exception:
            pass

    args = _parse_args(argv)
    _configure_logging(args.verbose)

    logger.info("Phase 2A Discovery: processing %s", args.url)

    try:
        result = discover_from_url(
            url=args.url,
            raw_dir=args.raw_dir,
            output_dir=args.output_dir,
            timeout=args.timeout,
        )
    except Exception as exc:
        logger.error("Discovery failed: %s", exc)
        print(f"\n[ERROR] Discovery failed: {exc}", file=sys.stderr)
        return 1

    out_dir = Path(args.output_dir)
    meta_stem = Path(result.meta_path).stem if result.meta_path else "discovery"
    if meta_stem.endswith(".meta"):
        meta_stem = meta_stem[:-len(".meta")]
    saved_file = out_dir / f"{meta_stem}_discovered.json"

    print("\n" + "=" * 72)
    print("APPSCOUT - PHASE 2A APP URL DISCOVERY")
    print("=" * 72)
    print(f"Source URL          : {result.source_url}")
    print(f"HTML Snapshot       : {result.html_path}")
    print(f"Metadata Snapshot   : {result.meta_path}")
    print(f"Fetch Timestamp     : {result.fetch_timestamp}")
    print(f"App URLs Discovered : {result.discovered_count}")
    print(f"Duplicates Removed  : {result.duplicate_count}")
    print(f"Non-App Links Filter: {result.filtered_count}")
    print("-" * 72)
    print("DISCOVERED APP LISTING URLS (Sample First 10):")
    print("-" * 72)
    for i, u in enumerate(result.urls[:10], 1):
        print(f"  {i:2d}. {u}")
    if result.discovered_count > 10:
        print(f"  ... and {result.discovered_count - 10} more URLs")
    print("=" * 72)
    print(f"\n[OK] Discovered URLs saved to: {saved_file.resolve()}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
