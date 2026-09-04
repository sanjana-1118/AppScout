"""
experiment/inspect_response.py
-------------------------------
Read a saved .html + .meta.json pair and produce a human-readable InspectionReport.

Design constraints:
  - Reads *only* what was actually saved by acquire.py.
  - The HTML body is read from <slug>_<timestamp>.html (UTF-8).
  - Metadata is read from <slug>_<timestamp>.meta.json.
  - These two files are kept separate — the HTML is never re-embedded in JSON.
  - Makes zero network calls.
  - Does NOT extract structured data fields (that is Phase 2).
  - Reports only facts that can be read directly from the saved files.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from .models import InspectionReport, RawResponse

logger = logging.getLogger(__name__)


def _is_html(content_type: str) -> bool:
    """Return True when the Content-Type indicates an HTML document."""
    return "text/html" in content_type.lower()


def _is_json(content_type: str) -> bool:
    """Return True when the Content-Type indicates JSON."""
    ct = content_type.lower()
    return "application/json" in ct or "text/json" in ct


def _inspect_html(body_text: str, notes: list[str]) -> dict[str, Any]:
    """Parse HTML with BeautifulSoup and extract observable metadata.

    No data is extracted that is not directly present as HTML element text
    or attribute values.  No field is guessed or inferred.

    Returns a dict that is merged into the InspectionReport fields.
    """
    try:
        # html.parser is Python's built-in parser — no C extension required.
        soup = BeautifulSoup(body_text, "html.parser")
    except Exception as exc:
        notes.append(f"BeautifulSoup parse error: {exc}")
        soup = BeautifulSoup("", "html.parser")

    # <title>
    title_tag: str | None = None
    title_el = soup.find("title")
    if title_el:
        title_tag = title_el.get_text(strip=True) or None

    # <meta name="description">
    meta_description: str | None = None
    meta_el = soup.find("meta", attrs={"name": "description"})
    if meta_el and meta_el.get("content"):
        meta_description = str(meta_el["content"]).strip() or None

    # <link rel="canonical">
    canonical_url: str | None = None
    canonical_el = soup.find("link", attrs={"rel": "canonical"})
    if canonical_el and canonical_el.get("href"):
        canonical_url = str(canonical_el["href"]).strip() or None

    # <h1> tags
    h1_tags = [el.get_text(strip=True) for el in soup.find_all("h1") if el.get_text(strip=True)]

    # <script type="application/ld+json">
    json_ld_blocks = soup.find_all("script", attrs={"type": "application/ld+json"})
    json_ld_count = len(json_ld_blocks)

    # Total <script> elements
    script_count = len(soup.find_all("script"))

    # Observations / anomalies
    if not title_tag:
        notes.append("No <title> element found — page may be a redirect shell or error page.")
    if script_count > 50:
        notes.append(
            f"High script count ({script_count}) — page is likely JS-rendered; "
            "raw HTML may be a skeleton."
        )
    if json_ld_count > 0:
        notes.append(
            f"Found {json_ld_count} JSON-LD block(s) — structured data may be available."
        )

    # Check for common bot/challenge signals in body text (passive detection only)
    body_lower = body_text.lower()
    if "captcha" in body_lower or "cf-challenge" in body_lower:
        notes.append(
            "Body contains 'captcha' or 'cf-challenge' — server may have returned a "
            "challenge page instead of the app listing."
        )
    if "access denied" in body_lower or "403 forbidden" in body_lower:
        notes.append("Body suggests an access-denied response.")
    if "just a moment" in body_lower:
        notes.append(
            "Body contains 'just a moment' — likely a Cloudflare waiting-room page."
        )

    return {
        "title_tag": title_tag,
        "meta_description": meta_description,
        "canonical_url": canonical_url,
        "h1_tags": h1_tags,
        "json_ld_count": json_ld_count,
        "script_count": script_count,
        "inline_json_keys": [],
    }


def _inspect_json(body_text: str, notes: list[str]) -> dict[str, Any]:
    """Parse a JSON body and return the top-level keys.

    No data is extracted beyond the key names — this is for orientation only.
    """
    try:
        data = json.loads(body_text)
    except json.JSONDecodeError as exc:
        notes.append(f"Content-Type is JSON but body failed to parse: {exc}")
        return {"inline_json_keys": []}

    if isinstance(data, dict):
        return {"inline_json_keys": list(data.keys())}
    if isinstance(data, list):
        notes.append(f"JSON body is an array with {len(data)} element(s).")
        if data and isinstance(data[0], dict):
            return {"inline_json_keys": list(data[0].keys())}
    return {"inline_json_keys": []}


def inspect_from_files(
    meta_path: str | os.PathLike[str],
    html_path: str | os.PathLike[str] | None = None,
) -> InspectionReport:
    """Load a saved .meta.json + .html pair and return an InspectionReport.

    Parameters
    ----------
    meta_path : path-like
        Path to the .meta.json file written by acquire.fetch().
    html_path : path-like, optional
        Path to the .html file.  If omitted, derived automatically from
        meta_path by reading the ``html_filename`` key in the JSON.

    Returns
    -------
    InspectionReport
        A frozen dataclass summarising the observed properties.
    """
    meta_p = Path(meta_path)
    logger.info("Reading metadata: %s", meta_p)

    meta = json.loads(meta_p.read_text(encoding="utf-8"))

    # Resolve the HTML path.
    if html_path is None:
        html_filename = meta.get("html_filename")
        if html_filename:
            html_p = meta_p.parent / html_filename
        else:
            # Legacy fallback: derive from meta_path stem.
            # meta stem = "<slug>_<timestamp>.meta", html = "<slug>_<timestamp>.html"
            html_stem = meta_p.stem  # e.g. "some-app_20240101T120000Z.meta"
            if html_stem.endswith(".meta"):
                html_stem = html_stem[: -len(".meta")]
            html_p = meta_p.parent / f"{html_stem}.html"
    else:
        html_p = Path(html_path)

    logger.info("Reading HTML body: %s", html_p)

    # The .html file is always written as UTF-8 by acquire.py.
    # No need to consult the detected_encoding here — UTF-8 is the file encoding.
    body_text: str = html_p.read_text(encoding="utf-8")

    # Pull fields from meta.
    url: str = meta.get("requested_url", "")
    final_url: str = meta.get("final_url", url)
    status_code: int = int(meta.get("status_code", 0))
    headers: dict[str, str] = {
        k.lower(): v for k, v in meta.get("response_headers", {}).items()
    }
    body_bytes_length: int = int(meta.get("body_bytes_length", 0))
    elapsed_seconds: float = float(meta.get("elapsed_seconds", 0.0))
    encoding: str | None = meta.get("detected_encoding")
    redirects: list[dict] = meta.get("redirects", [])

    content_type: str = meta.get("content_type", "") or headers.get("content-type", "")
    is_html = _is_html(content_type)
    is_json = _is_json(content_type)

    notes: list[str] = []

    # Note the encoding situation.
    encoding_source = meta.get("encoding_source", "")
    had_replacements = meta.get("encoding_had_replacements", False)
    if had_replacements:
        notes.append(
            f"Encoding fallback used replacement characters (U+FFFD). "
            f"Original bytes could not be decoded as {encoding!r}. "
            f"Some content may be missing."
        )
    if encoding_source:
        notes.append(f"Encoding: {encoding!r} ({encoding_source})")

    # Note redirect chain.
    if redirects:
        for hop in redirects:
            notes.append(
                f"Redirect: HTTP {hop.get('status_code')} from {hop.get('from_url')}"
            )
    elif final_url and final_url != url:
        notes.append(f"Redirect detected: {url} \u2192 {final_url}")

    # Note non-200 status.
    if status_code != 200:
        notes.append(f"Non-200 status code: {status_code}")

    # Passive content-type observations.
    if not content_type:
        notes.append("Content-Type header is absent.")
    elif not is_html and not is_json:
        notes.append(f"Unexpected Content-Type: {content_type!r}")

    # Branch into HTML or JSON inspection.
    if is_html:
        extra = _inspect_html(body_text, notes)
    elif is_json:
        extra = _inspect_json(body_text, notes)
        extra.update(
            {
                "title_tag": None,
                "meta_description": None,
                "canonical_url": None,
                "h1_tags": [],
                "json_ld_count": 0,
                "script_count": 0,
            }
        )
    else:
        notes.append(
            "Body is neither HTML nor JSON — inspect the .html file directly."
        )
        extra = {
            "title_tag": None,
            "meta_description": None,
            "canonical_url": None,
            "h1_tags": [],
            "json_ld_count": 0,
            "script_count": 0,
            "inline_json_keys": [],
        }

    return InspectionReport(
        meta_path=str(meta_p.resolve()),
        html_path=str(html_p.resolve()),
        url=url,
        final_url=final_url,
        status_code=status_code,
        content_type=content_type,
        body_bytes_length=body_bytes_length,
        body_text_length=len(body_text),
        encoding=encoding,
        elapsed_seconds=elapsed_seconds,
        is_html=is_html,
        is_json=is_json,
        notes=notes,
        **extra,
    )


def inspect_from_raw_response(raw: RawResponse) -> InspectionReport:
    """Convenience wrapper: inspect directly from a RawResponse object.

    Reads both files from their saved paths (html_path and meta_path), keeping
    the persisted files as the authoritative record rather than re-using the
    in-memory body_text.
    """
    return inspect_from_files(
        meta_path=raw.meta_path,
        html_path=raw.html_path,
    )
