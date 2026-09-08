# AppScout Data Collection & Review Pipeline

This document details how AppScout discovered, scraped, validated, and ingested the Shopify App Store catalog and merchant reviews into PostgreSQL.

---

## 1. Pipeline Overview & Architecture

All application records, category taxonomies, pricing tiers, and merchant reviews originate from the public **Shopify App Store** (`apps.shopify.com`). The ingestion subsystem is implemented in Python under `experiment/` using `requests`, `beautifulsoup4`, JSON-LD schema extractors, and multi-threaded worker pools.

```text
Shopify App Store
       ↓
Category Discovery (45 Leaf Categories) + XML Sitemap
       ↓
Frontier Reconciliation (25,633 Unique Targets)
       ↓
Master App Frontier JSON (data/frontier/final_verified_master_frontier_20260829T181905Z.json)
       ↓
Concurrent Ingestion Engine (experiment/run_ingestion.py)
       ↓
Metadata Extraction (extract.py) + Pricing Extractor (extract_pricing.py)
       ↓
Validation Quality Gates (validate.py)
       ↓
PostgreSQL Persistence (apps, categories, app_categories, app_pricing_plans)
       ↓
Review Collection Engine (experiment/reviews/run_review_collection.py)
       ↓
SHA-256 Fingerprint Deduplicator (ix_reviews_fingerprint)
       ↓
PostgreSQL Persistence (reviews: 738,101 rows)
```

---

## 2. Phase 1: Catalog Discovery & Frontier Reconciliation

### 2.1 Category Discovery & Sitemap Harvesting
* Traversed 52 top-level category listings (7 root categories + 45 sub-categories) across 572 listing pages.
* Supplemented discovery with the official Shopify App Store XML sitemap.
* Parsed and deduplicated canonical application slugs into a unified master frontier of **25,633 URLs**.

### 2.2 Frontier Reconciliation Accounting
Every target in the master frontier was tracked and accounted for with 0 unaccounted targets:

$$\text{Total Frontier } (25,633) = \text{Stored Active Apps } (21,502) + \text{Validation Rejected Non-App URLs } (4,130) + \text{Redirect } (1)$$

* **21,502 Active Apps**: Valid Shopify applications committed to the `apps` table.
* **4,130 Rejected Targets**: Discovered links that were non-app collection pages, developer profile links, or delisted 404 stubs.
* **1 Redirect**: Canonical slug consolidation.

---

## 3. Phase 2: Metadata & Pricing Tier Extraction

### 3.1 Metadata Extraction
* **JSON-LD Schema Parsing**: Extracted `name`, `brand` (developer), `description`, and `aggregateRating` (`ratingValue`, `ratingCount`) from structured `<script type="application/ld+json">` tags on listing pages.
* **HTML Component Fallbacks**: Used CSS selectors as resilient fallbacks when JSON-LD blocks were absent or incomplete.

### 3.2 Pricing Tier Extraction (`experiment/extract_pricing.py`)
Parsed 42,326 discrete plan tiers across the catalog:
* **Tier Title**: e.g., `Free`, `Basic`, `Pro`, `Enterprise`.
* **Amount in USD**: Numeric price converted to float (`0.0` for free plans).
* **Billing Cadence**: Normalized to `month`, `year`, `usage_based`, `one_time`.
* **Free Trial Days**: Extracted from trial badges (e.g. `14-day free trial`).
* **Features**: Extracted from bulleted checklist items as JSON arrays.

---

## 4. Phase 3: Review Collection & Processing

Review collection is executed by [`experiment/reviews/run_review_collection.py`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/experiment/reviews/run_review_collection.py) and [`collect_reviews.py`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/experiment/reviews/collect_reviews.py):

* **Target URL Structure**: `https://apps.shopify.com/{app_slug}/reviews`
* **Pagination Mechanism**: Traverses sequential HTML pages tracking `<a rel="next">` links (`?page=N`).
* **Page Density**: Shopify strictly serves **10 reviews per page**.
* **Review Extraction**:
  * Reviewer store/author name
  * Geographic location (e.g. `United States`, `United Kingdom`, `Germany`)
  * Merchant usage duration (e.g. `About 6 months using the app`)
  * Star rating (integer `1` to `5`)
  * Published date string
  * Body text content

### 4.1 Idempotent Deduplication (SHA-256 Fingerprinting)
To prevent duplicate reviews across overlapping crawling runs, every review is hashed into a 64-character hexadecimal SHA-256 fingerprint:

$$\text{Fingerprint} = \text{SHA256}(\text{app\_slug} + \text{reviewer\_name} + \text{review\_date} + \text{rating} + \text{body}[:180])$$

* **Unique Index**: Stored under `reviews.review_fingerprint` with a unique database index (`ix_reviews_fingerprint`).
* **In-Memory Hash Pre-loading**: Prior to crawling an app, existing fingerprints are pre-loaded into a Python `set()`. New reviews are checked against this set in memory, eliminating redundant database write attempts and query overhead.
* **Audit Verification**: Database audits confirmed **0 duplicate fingerprinted reviews** across all 738,101 rows.

### 4.2 Shopify 1,000-Page Ceiling Constraint
During bulk crawling, an architectural constraint on Shopify's public web servers was discovered:

> **Shopify Public Web Constraint**:  
> Shopify strictly caps web pagination at **page 1,000** (10 reviews $\times$ 1,000 pages = 10,000 reviews max).  
> Any request for `?page=1001` returns **HTTP 404 Not Found**, regardless of the total review count displayed on the listing header.

Three high-volume market leaders reached this ceiling:

| App Slug | App Name | Reviews Stored in AppScout | Store Display Count | Public Web Coverage |
| :--- | :--- | :---: | :---: | :---: |
| `judgeme` | Judge.me Product Reviews App | **10,038** | 44,288 | 22.7% (1,000 pages collected) |
| `tiktok` | TikTok | **10,018** | 15,468 | 64.8% (1,000 pages collected) |
| `flow` | Shopify Flow | **10,019** | 12,377 | 80.9% (1,000 pages collected) |

For all other apps with reviews ($\le 10,000$), AppScout collected **100% of available reviews**.

### 4.3 The 104 Uncollected Apps Audit
A discrepancy between public catalog counts (8,339 apps with `review_count > 0`) and stored review records (8,235 apps with stored reviews) was investigated across all 104 affected applications:

* **22 Apps**: Delisted from the Shopify App Store (HTTP 404 on app profile).
* **79 Apps**: Active on Shopify, but their review endpoint explicitly returned `"Overall rating: 0"` and `"No reviews yet"`. The catalog count of `1` was a stale search-index caching discrepancy on Shopify's servers.
* **3 Apps** (`amojo-product-image-translator`, `fast-conversion-bar`, `codverify-1`): Published their first review on Shopify after the crawler batch run.

These apps are explicitly tracked in `UNCOLLECTED_APP_IDS` in [`backend/routers/categories.py`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/backend/routers/categories.py) and handled transparently in the user interface.

---

## 5. Validation Quality Gate

Before writing any record into PostgreSQL, data objects must pass validation in [`experiment/validate.py`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/experiment/validate.py):

* **Slug Format**: Lowercase alphanumeric slug with hyphens; must match canonical URL path.
* **Title & URL Integrity**: `app_name` and `app_url` must be non-empty strings.
* **Rating Boundaries**: `average_rating` must be between `1.0` and `5.0` or `None` (for unreviewed apps).
* **Review Count Non-negativity**: `review_count >= 0`.
* **Pricing Type Validation**: Normalized to `free`, `freemium`, `paid`, or `unknown`.

---

## 6. Checkpointing & Fault Tolerance

* **Atomic Progress Tracking**: The runner updates progress checkpoints upon every batch commit.
* **Resumability**: If network connections disconnect or the process is interrupted, the runner resumes from the exact uncommitted item without re-fetching already processed apps.
* **Polite Rate Delays**: Configured with default delays between requests and randomized exponential backoff (25s–45s) upon encountering HTTP 429 rate limit responses.
