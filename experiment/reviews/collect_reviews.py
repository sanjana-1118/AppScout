"""
experiment/reviews/collect_reviews.py
-------------------------------------
Production-grade Shopify App Review Collector & Deduplication Engine.

Features:
- Deterministic pagination traversal using <a rel="next">.
- Cap collection at latest N reviews (e.g. 50 reviews per app).
- SHA-256 review fingerprinting for strict idempotent deduplication.
- Robust error handling, polite rate delays, and transactional persistence.
"""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from experiment import acquire
from experiment.db.models import App
from .extract_reviews import extract_reviews_from_html
from .models import Review

logger = logging.getLogger("experiment.reviews.collect_reviews")


def compute_review_fingerprint(
    app_slug: str,
    reviewer_name: str | None,
    review_date: str | None,
    rating: int,
    body: str,
) -> str:
    """Generate deterministic SHA-256 fingerprint for a review to prevent duplicates."""
    raw_key = f"{app_slug}:{reviewer_name or ''}:{review_date or ''}:{rating}:{body[:180].strip()}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def collect_reviews_for_app(
    app_slug: str,
    *,
    session: Session,
    max_reviews: int | None = None,
    delay: float = 1.0,
    raw_dir: str | Path | None = None,
    timeout: int = 30,
    max_retries: int = 3,
    on_page_success: Any = None,
    on_error: Any = None,
) -> tuple[int, int, int, str]:
    """Collect reviews for an app, traversing pagination as needed.

    If max_reviews is None, traverses all available pages until next_page is None.
    If max_reviews is an int, caps collection once max_reviews reviews have been saved.

    Returns
    -------
    (reviews_saved, duplicate_reviews, pages_scraped, status) : tuple[int, int, int, str]
    """
    app = session.scalars(select(App).where(App.app_slug == app_slug)).first()
    app_id = app.id if app else None

    # In-memory pre-load of all existing fingerprints for this app to eliminate DB round-trip latency
    existing_fps: set[str] = set(
        session.scalars(
            select(Review.review_fingerprint).where(Review.app_slug == app_slug)
        ).all()
    )

    current_url: str | None = f"https://apps.shopify.com/{app_slug}/reviews"
    pages_scraped = 0
    reviews_saved = 0
    duplicate_reviews = 0
    max_pages = max(1, (max_reviews + 9) // 10 + 1) if max_reviews is not None else None
    last_page_reached = False

    while current_url and (max_reviews is None or reviews_saved < max_reviews) and (max_pages is None or pages_scraped < max_pages):
        try:
            logger.info("Fetching review page [%d]: %s", pages_scraped + 1, current_url)

            # Retry loop with exponential backoff for transient network / Shopify hiccups
            raw = None
            for attempt in range(1, max_retries + 1):
                try:
                    raw = acquire.fetch(current_url, raw_dir=raw_dir, timeout=timeout)
                    break
                except Exception as req_exc:
                    err_str = str(req_exc)
                    if "404" in err_str:
                        if pages_scraped >= 1000:
                            logger.info("[SHOPIFY LIMIT] App %s reached Shopify public 1,000-page ceiling (%d reviews collected). Marked as capped_shopify_limit.", app_slug, reviews_saved)
                            return reviews_saved, duplicate_reviews, pages_scraped, "capped_shopify_limit"
                        logger.info("App %s returned 404 on %s", app_slug, current_url)
                        return reviews_saved, duplicate_reviews, pages_scraped, "not_found"
                    if attempt >= max_retries:
                        if on_error:
                            on_error(err_str)
                        raise req_exc
                    if "429" in err_str:
                        if on_error:
                            on_error(err_str)
                        import random
                        backoff = 25.0 + random.uniform(5.0, 20.0) + attempt * 5.0  # 30s-45s spread to prevent thundering herd
                    else:
                        backoff = attempt * 2.0
                    logger.warning("Retry %d/%d for %s on %s after %.1fs: %s", attempt, max_retries, app_slug, current_url, backoff, req_exc)
                    time.sleep(backoff)

            pages_scraped += 1

            extracted_reviews, next_page = extract_reviews_from_html(
                raw.body_text,
                app_slug=app_slug,
                source_url=raw.url,
            )

            if not extracted_reviews:
                logger.debug("No reviews found on page %s for %s", current_url, app_slug)
                last_page_reached = True
                break

            page_saved = 0
            for r in extracted_reviews:
                if max_reviews is not None and reviews_saved >= max_reviews:
                    break

                fp = compute_review_fingerprint(
                    app_slug=app_slug,
                    reviewer_name=r.reviewer_name,
                    review_date=r.review_date,
                    rating=r.rating,
                    body=r.body,
                )

                # High-speed in-memory deduplication check
                if fp in existing_fps:
                    duplicate_reviews += 1
                    continue

                review_orm = Review(
                    app_id=app_id,
                    app_slug=app_slug,
                    review_fingerprint=fp,
                    reviewer_name=r.reviewer_name[:250] if r.reviewer_name else None,
                    reviewer_location=r.reviewer_location[:250] if r.reviewer_location else None,
                    time_spent_using_app=r.time_spent_using_app[:250] if r.time_spent_using_app else None,
                    rating=r.rating,
                    review_date=r.review_date,
                    body=r.body,
                )
                session.add(review_orm)
                existing_fps.add(fp)
                reviews_saved += 1
                page_saved += 1

            # Batch commit every 5 pages or when reaching the final page to reduce trans-continental latency
            if pages_scraped % 5 == 0 or not next_page:
                session.commit()

            if on_page_success:
                on_page_success(page_saved)

            if next_page and (max_reviews is None or reviews_saved < max_reviews):
                current_url = next_page
                if delay > 0:
                    import random
                    time.sleep(delay * random.uniform(0.8, 1.2))
            else:
                if not next_page:
                    last_page_reached = True
                break

        except Exception as exc:
            session.rollback()
            err_msg = str(exc)
            if "404" in err_msg:
                if pages_scraped >= 1000:
                    logger.info("[SHOPIFY LIMIT] App %s reached Shopify public 1,000-page ceiling (%d reviews collected). Marked as capped_shopify_limit.", app_slug, reviews_saved)
                    return reviews_saved, duplicate_reviews, pages_scraped, "capped_shopify_limit"
                logger.info("App %s has no reviews page (HTTP 404)", app_slug)
                return reviews_saved, duplicate_reviews, pages_scraped, "not_found"
            logger.warning("Error collecting reviews for %s on %s: %s", app_slug, current_url, exc)
            return reviews_saved, duplicate_reviews, pages_scraped, f"error: {exc}"

    status = "completed" if last_page_reached else "capped"
    return reviews_saved, duplicate_reviews, pages_scraped, status
