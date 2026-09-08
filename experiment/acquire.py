"""
experiment/acquire.py
---------------------
Make ONE HTTP GET request to a target URL and persist the raw response as two files:

    data/raw/<slug>_<timestamp>.html       — decoded body text, written as UTF-8
    data/raw/<slug>_<timestamp>.meta.json  — all response metadata (no body)

Design constraints (by choice, not accident):
  - Exactly one request per run.  No retry logic.
  - No headless browser.  Plain requests only.
  - No CAPTCHA bypass or rate-limit workaround.
  - Returns a RawResponse dataclass; does NOT parse the body.
  - If a previously saved response for the same URL already exists in raw_dir,
    it is loaded from disk and returned without making a new HTTP request.
  - Encoding is handled explicitly and documented in the meta file.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from .models import RawResponse

logger = logging.getLogger(__name__)

# A conservative browser-like User-Agent.  We identify as a regular browser;
# we do NOT impersonate any specific tool or claim to be a bot.
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

_DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": _DEFAULT_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------

def _slug_from_url(url: str) -> str:
    """Derive a filesystem-safe slug from a URL.

    Examples
    --------
    >>> _slug_from_url("https://apps.shopify.com/some-app?ref=xyz")
    'some-app'
    >>> _slug_from_url("https://apps.shopify.com/some-app/reviews")
    'some-app_reviews'
    >>> _slug_from_url("https://apps.shopify.com/")
    'response'
    """
    path = re.sub(r"https?://[^/]+", "", url).strip("/").split("?")[0]
    segments = [s for s in path.split("/") if s]
    if len(segments) >= 2 and segments[-1] == "reviews":
        combined = f"{segments[-2]}_reviews"
    elif segments:
        combined = segments[-1]
    else:
        combined = "response"
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", combined).strip("-") or "response"
    return slug[:64]


def _timestamp_utc() -> str:
    """Return a compact UTC timestamp string safe for filenames."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# ---------------------------------------------------------------------------
# Encoding helpers
# ---------------------------------------------------------------------------

def _decode_body(
    content: bytes,
    server_encoding: str | None,
    apparent_encoding: str | None,
) -> tuple[str, str, str, bool]:
    """Decode raw response bytes to a Python str, with explicit fallback chain.

    Encoding strategy (in order):
    1. Server-declared encoding (Content-Type charset or HTTP header).
       Tried first without replacement so any decode error is surfaced.
    2. Charset-detected encoding (charset-normalizer / chardet via requests).
       Used when server declares nothing, or when step 1 raises UnicodeDecodeError.
    3. UTF-8 (last resort).
       Used only when both of the above fail.
    4. UTF-8 with errors="replace" (absolute last resort).
       Only reached if UTF-8 strict also fails (extremely rare for HTML).

    Returns
    -------
    body_text : str
        The decoded text.
    encoding_used : str
        The encoding that successfully decoded the content.
    encoding_source : str
        One of: "server-declared", "charset-detected", "fallback-utf8",
        "fallback-utf8-with-replacements".
    had_replacements : bool
        True only when errors="replace" was used.  Signals that some bytes
        could not be decoded and were silently substituted with U+FFFD.
    """
    candidates: list[tuple[str, str]] = []

    if server_encoding:
        candidates.append((server_encoding, "server-declared"))
    if apparent_encoding and apparent_encoding != server_encoding:
        candidates.append((apparent_encoding, "charset-detected"))
    if "utf-8" not in (server_encoding or "").lower() and "utf-8" not in (apparent_encoding or "").lower():
        candidates.append(("utf-8", "fallback-utf8"))

    # Try each candidate without replacement first.
    for enc, source in candidates:
        try:
            body_text = content.decode(enc)
            return body_text, enc, source, False
        except (UnicodeDecodeError, LookupError):
            logger.debug("Strict decode failed for encoding=%s (%s), trying next", enc, source)
            continue

    # Absolute last resort: UTF-8 with replacement characters.
    logger.warning(
        "All strict decode attempts failed — falling back to UTF-8 with errors='replace'. "
        "U+FFFD replacement characters will appear where bytes could not be decoded."
    )
    body_text = content.decode("utf-8", errors="replace")
    return body_text, "utf-8", "fallback-utf8-with-replacements", True


# ---------------------------------------------------------------------------
# Reuse: find an existing saved pair for this URL
# ---------------------------------------------------------------------------

def _find_existing(
    url: str, slug: str, raw_path: Path
) -> tuple[Path, Path] | None:
    """Search raw_path for a previously saved .html + .meta.json pair for *url*.

    Matches on the exact ``requested_url`` value stored in the .meta.json file.
    Returns the pair (html_path, meta_path) for the most recent matching file,
    or None if no match is found.
    """
    # Glob for candidate HTML files that share this slug prefix.
    candidates = sorted(raw_path.glob(f"{slug}_*.html"), reverse=True)
    for html_file in candidates:
        meta_file = html_file.parent / (html_file.stem + ".meta.json")
        if not meta_file.exists():
            logger.debug("No matching .meta.json for %s — skipping", html_file.name)
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.debug("Could not read %s: %s — skipping", meta_file.name, exc)
            continue
        if meta.get("requested_url") == url:
            return html_file, meta_file
    return None


def _load_existing(html_path: Path, meta_path: Path) -> RawResponse:
    """Reconstruct a RawResponse from a previously saved file pair."""
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    # The .html file is always written as UTF-8 (see fetch()), so read as UTF-8.
    body_text = html_path.read_text(encoding="utf-8")

    return RawResponse(
        url=meta["requested_url"],
        final_url=meta["final_url"],
        status_code=meta["status_code"],
        headers={k.lower(): v for k, v in meta["response_headers"].items()},
        body_text=body_text,
        body_bytes_length=meta["body_bytes_length"],
        elapsed_seconds=meta["elapsed_seconds"],
        encoding=meta["detected_encoding"],
        html_path=str(html_path.resolve()),
        meta_path=str(meta_path.resolve()),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_thread_local = threading.local()


def _get_session() -> requests.Session:
    """Return a thread-local requests.Session for persistent HTTP connection reuse."""
    if not hasattr(_thread_local, "session"):
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=0,
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        _thread_local.session = session
    return _thread_local.session


def fetch(
    url: str,
    *,
    raw_dir: str | os.PathLike[str] | None = "data/raw",
    timeout: int = 30,
) -> RawResponse:
    """Make one HTTP GET request and optionally save the raw response as two files.

    If raw_dir is None, the response is decoded in memory and returned directly
    without performing filesystem glob searches or writing files to disk.

    If raw_dir is a path and a previously saved response for *url* already exists,
    the saved files are loaded and returned without making a new HTTP request.
    """
    raw_path = Path(raw_dir) if raw_dir else None
    if raw_path:
        raw_path.mkdir(parents=True, exist_ok=True)
        slug = _slug_from_url(url)
        existing = _find_existing(url, slug, raw_path)
        if existing:
            html_file, meta_file = existing
            logger.info("Reusing existing saved response for %s → %s", url, html_file.name)
            return _load_existing(html_file, meta_file)

    logger.info("Requesting URL: %s", url)

    http_session = _get_session()
    response = http_session.get(
        url,
        headers=_DEFAULT_HEADERS,
        timeout=timeout,
        allow_redirects=True,
    )

    if response.status_code == 429:
        logger.warning("HTTP 429 Too Many Requests encountered for %s", url)
        response.raise_for_status()

    logger.info(
        "Response received: HTTP %d | %.3fs | %d bytes",
        response.status_code,
        response.elapsed.total_seconds(),
        len(response.content),
    )

    body_text, encoding_used, encoding_source, had_replacements = _decode_body(
        content=response.content,
        server_encoding=response.encoding,
        apparent_encoding=response.apparent_encoding,
    )
    if had_replacements:
        logger.warning(
            "Body contains U+FFFD replacement characters — some bytes could not "
            "be decoded."
        )

    html_path_str = ""
    meta_path_str = ""

    if raw_path:
        slug = _slug_from_url(url)
        redirects: list[dict[str, Any]] = [
            {"from_url": r.url, "status_code": r.status_code}
            for r in response.history
        ]
        timestamp = _timestamp_utc()
        stem = f"{slug}_{timestamp}"
        html_path = raw_path / f"{stem}.html"
        meta_path = raw_path / f"{stem}.meta.json"

        html_path.write_text(body_text, encoding="utf-8")
        logger.info("HTML body saved to: %s", html_path.resolve())

        meta: dict[str, Any] = {
            "experiment_version": "phase1",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "requested_url": url,
            "final_url": response.url,
            "status_code": response.status_code,
            "content_type": response.headers.get("Content-Type", ""),
            "detected_encoding": encoding_used,
            "encoding_source": encoding_source,
            "encoding_had_replacements": had_replacements,
            "body_bytes_length": len(response.content),
            "elapsed_seconds": response.elapsed.total_seconds(),
            "redirects": redirects,
            "response_headers": dict(response.headers),
            "html_filename": html_path.name,
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Metadata saved to: %s", meta_path.resolve())
        html_path_str = str(html_path.resolve())
        meta_path_str = str(meta_path.resolve())

    return RawResponse(
        url=url,
        final_url=response.url,
        status_code=response.status_code,
        headers={k.lower(): v for k, v in response.headers.items()},
        body_text=body_text,
        body_bytes_length=len(response.content),
        elapsed_seconds=response.elapsed.total_seconds(),
        encoding=encoding_used,
        html_path=html_path_str,
        meta_path=meta_path_str,
    )
