"""
experiment/models.py
--------------------
Lightweight dataclasses for Phase 1.

No ORM. No database. No external dependencies.
These are plain Python objects used to pass data between acquire and inspect.
"""

from __future__ import annotations

import dataclasses
from typing import Any


@dataclasses.dataclass(frozen=True)
class RawResponse:
    """Everything captured from a single HTTP response, before any parsing.

    Attributes
    ----------
    url : str
        The URL that was requested (before redirects).
    final_url : str
        The final URL after redirects (may differ from *url*).
    status_code : int
        HTTP status code returned by the server.
    headers : dict[str, str]
        Response headers as a plain dict (header names lowercased).
    body_text : str
        Full response body decoded to str and re-encoded as UTF-8 on disk.
        Read back from html_path so the in-memory value always matches the file.
    body_bytes_length : int
        Length of the raw decompressed response body in bytes (before decoding).
    elapsed_seconds : float
        Wall-clock time for the request/response cycle in seconds.
    encoding : str | None
        The encoding that was used to decode the raw bytes to text.
        Documented in the .meta.json file under ``detected_encoding``.
    html_path : str
        Absolute path to the saved .html file (decoded body, written as UTF-8).
    meta_path : str
        Absolute path to the saved .meta.json file (all other response metadata).
    """

    url: str
    final_url: str
    status_code: int
    headers: dict[str, str]
    body_text: str
    body_bytes_length: int
    elapsed_seconds: float
    encoding: str | None
    html_path: str
    meta_path: str


@dataclasses.dataclass(frozen=True)
class InspectionReport:
    """Summary produced by inspect_response, derived from a RawResponse.

    All fields describe *observed* properties of the raw response.
    No fields are invented or assumed.

    Attributes
    ----------
    meta_path : str
        Absolute path to the .meta.json file that was inspected.
    html_path : str
        Absolute path to the .html file whose body was inspected.
    url : str
        The URL that was requested.
    final_url : str
        The final URL after any redirects.
    status_code : int
        HTTP status code.
    content_type : str
        Value of the Content-Type header (empty string if absent).
    body_bytes_length : int
        Size of the response body in bytes.
    body_text_length : int
        Length of the decoded body text in characters.
    encoding : str | None
        Declared encoding.
    elapsed_seconds : float
        Round-trip time in seconds.
    is_html : bool
        True when Content-Type indicates HTML.
    is_json : bool
        True when Content-Type indicates JSON.
    title_tag : str | None
        Text content of the HTML <title> element, or None if not found /
        not applicable.
    meta_description : str | None
        Content attribute of <meta name="description">, or None.
    canonical_url : str | None
        href of <link rel="canonical">, or None.
    h1_tags : list[str]
        Text of all <h1> elements found (empty list if none).
    json_ld_count : int
        Number of <script type="application/ld+json"> blocks found.
    script_count : int
        Total number of <script> elements in the document.
    inline_json_keys : list[str]
        Top-level keys found in the *first* JSON response body (if is_json).
    notes : list[str]
        Free-form observations added during inspection (anomalies, redirects,
        unexpected content types, etc.).
    """

    meta_path: str
    html_path: str
    url: str
    final_url: str
    status_code: int
    content_type: str
    body_bytes_length: int
    body_text_length: int
    encoding: str | None
    elapsed_seconds: float
    is_html: bool
    is_json: bool
    title_tag: str | None
    meta_description: str | None
    canonical_url: str | None
    h1_tags: list[str]
    json_ld_count: int
    script_count: int
    inline_json_keys: list[str]
    notes: list[str]

    def to_text(self) -> str:
        """Render the report as a human-readable plain-text block."""
        lines: list[str] = [
            "=" * 72,
            "APPSCOUT - PHASE 1 INSPECTION REPORT",
            "=" * 72,
            f"Meta file        : {self.meta_path}",
            f"HTML file        : {self.html_path}",
            f"Requested URL    : {self.url}",
            f"Final URL        : {self.final_url}",
            f"Status code      : {self.status_code}",
            f"Content-Type     : {self.content_type or '(not set)'}",
            f"Encoding         : {self.encoding or '(not declared)'}",
            f"Body size        : {self.body_bytes_length:,} bytes / "
            f"{self.body_text_length:,} chars",
            f"Elapsed          : {self.elapsed_seconds:.3f}s",
            f"Is HTML          : {self.is_html}",
            f"Is JSON          : {self.is_json}",
            "-" * 72,
            "HTML metadata",
            "-" * 72,
            f"<title>          : {self.title_tag or '(not found)'}",
            f"meta description : {self.meta_description or '(not found)'}",
            f"canonical URL    : {self.canonical_url or '(not found)'}",
            f"<h1> tags ({len(self.h1_tags):2d})  : "
            + (", ".join(repr(h) for h in self.h1_tags) or "(none)"),
            f"JSON-LD blocks   : {self.json_ld_count}",
            f"<script> count   : {self.script_count}",
        ]

        if self.is_json and self.inline_json_keys:
            lines += [
                "-" * 72,
                "JSON top-level keys",
                "-" * 72,
                "  " + ", ".join(self.inline_json_keys),
            ]

        if self.notes:
            lines += [
                "-" * 72,
                "Notes / observations",
                "-" * 72,
            ]
            for note in self.notes:
                lines.append(f"  • {note}")

        lines.append("=" * 72)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Extraction output models (added for extract.py)
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class AppData:
    """The 8 proof-of-concept fields extracted from one Shopify App Store page.

    All fields default to None so that a partially-extracted result is still a
    valid object.  No field is invented or guessed — None means not found.

    Attributes
    ----------
    app_name : str | None
    app_slug : str | None
        Derived from the canonical URL path segment.
    app_url : str | None
        Canonical URL (from <link rel="canonical"> or meta/og:url).
    developer_name : str | None
    description : str | None
    average_rating : float | None
    review_count : int | None
    category : str | None
        Shopify-specific human-readable category label (NOT schema.org applicationCategory).
    """

    app_name: str | None = None
    app_slug: str | None = None
    app_url: str | None = None
    developer_name: str | None = None
    description: str | None = None
    average_rating: float | None = None
    review_count: int | None = None
    category: str | None = None
    pricing_type: str | None = None
    free_trial_days: int | None = None
    pricing_plans: list[dict[str, Any]] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class ExtractionMeta:
    """Provenance and quality metadata for one extraction run.

    Attributes
    ----------
    html_path : str
        Absolute path to the .html file that was parsed.
    meta_path : str
        Absolute path to the .meta.json file that was read.
    sources : dict[str, str]
        Maps each field name to a short description of the extraction source.
        Example: {"app_name": "json_ld.name", "category": "app_specific_category_anchor"}
    missing : list[str]
        Field names that could not be extracted (value is None in AppData).
    warnings : list[str]
        Non-fatal issues encountered during extraction (e.g. JSON-LD parse errors,
        type coercion failures, unexpected structure).
    """

    html_path: str
    meta_path: str
    sources: dict[str, str] = dataclasses.field(default_factory=dict)
    missing: list[str] = dataclasses.field(default_factory=list)
    warnings: list[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# ---------------------------------------------------------------------------
# Discovery output models (added for discover.py)
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class DiscoveryResult:
    """Discovered app URLs and metadata from a Shopify App Store listing/category page.

    Attributes
    ----------
    source_url : str
        The listing/category page URL that was processed.
    fetch_timestamp : str
        ISO 8601 UTC timestamp of acquisition.
    discovered_count : int
        Number of unique valid app URLs discovered.
    urls : list[str]
        Deduplicated list of absolute, normalized app listing URLs.
    html_path : str | None
        Path to the HTML snapshot used.
    meta_path : str | None
        Path to the metadata snapshot used.
    duplicate_count : int
        Number of duplicate app links encountered and deduplicated.
    filtered_count : int
        Number of non-app links filtered out.
    """

    source_url: str
    fetch_timestamp: str
    discovered_count: int
    urls: list[str]
    html_path: str | None = None
    meta_path: str | None = None
    duplicate_count: int = 0
    filtered_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# ---------------------------------------------------------------------------
# Category Traversal output models (added for traverse_category.py)
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class CategoryTraversalResult:
    """Complete pagination traversal result for one Shopify App Store category.

    Attributes
    ----------
    category_url : str
        The initial category landing page URL.
    category_slug : str
        The slug identifying this category.
    traversal_timestamp : str
        ISO 8601 UTC timestamp of traversal completion.
    pages_processed : int
        Number of pagination pages traversed.
    page_urls : list[str]
        List of all pagination page URLs visited in order.
    app_urls : list[str]
        Deduplicated master list of app listing URLs discovered.
    total_urls_encountered : int
        Total app link occurrences across all pages before deduplication.
    unique_app_urls : int
        Count of unique app listing URLs.
    duplicates_removed : int
        Number of duplicate app listings across pages removed.
    snapshots_reused : int
        Number of pages loaded from existing local raw snapshots.
    new_http_requests : int
        Number of pages fetched via live HTTP GET requests.
    delay_seconds : float
        Configured delay between new network requests.
    stopped_reason : str
        Reason traversal stopped ("no_next_page", "max_pages_reached", "loop_detected", "error").
    """

    category_url: str
    category_slug: str
    traversal_timestamp: str
    pages_processed: int
    page_urls: list[str]
    app_urls: list[str]
    total_urls_encountered: int
    unique_app_urls: int
    duplicates_removed: int
    snapshots_reused: int
    new_http_requests: int
    delay_seconds: float
    stopped_reason: str

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# ---------------------------------------------------------------------------
# Master Frontier output models (added for build_frontier.py)
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class FrontierAppEntry:
    """An app URL and its category provenance in the Master Frontier."""

    url: str
    slug: str
    categories: list[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class MasterFrontierResult:
    """Consolidated Master App URL Frontier across multiple categories.

    Attributes
    ----------
    created_at : str
        ISO 8601 UTC timestamp of creation.
    categories_processed : list[dict[str, Any]]
        Per-category metrics (slug, url, pages_processed, apps_discovered, status).
    summary : dict[str, Any]
        Aggregated summary metrics.
    apps : list[dict[str, Any]]
        List of unique app entries with category provenance.
    """

    created_at: str
    categories_processed: list[dict[str, Any]]
    summary: dict[str, Any]
    apps: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)
