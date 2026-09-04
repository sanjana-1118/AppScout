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
    max_reviews: int = 50,
    delay: float = 1.0,
    raw_dir: str | Path = "data/raw",
    timeout: int = 30,
) -> tuple[int, int, int, str]:
    """Collect up to max_reviews for an app, traversing pagination as needed.

    Returns
    -------
    (reviews_saved, duplicate_reviews, pages_scraped, status) : tuple[int, int, int, str]
    """
    app = session.scalars(select(App).where(App.app_slug == app_slug)).first()
    app_id = app.id if app else None

    current_url: str | None = f"https://apps.shopify.com/{app_slug}/reviews"
    pages_scraped = 0
    reviews_saved = 0
    duplicate_reviews = 0
    max_pages = max(1, (max_reviews + 9) // 10 + 1)  # ~10 reviews per page

    while current_url and reviews_saved < max_reviews and pages_scraped < max_pages:
        try:
            logger.info("Fetching review page [%d]: %s", pages_scraped + 1, current_url)
            raw = acquire.fetch(current_url, raw_dir=raw_dir, timeout=timeout)
            pages_scraped += 1

            extracted_reviews, next_page = extract_reviews_from_html(
                raw.body_text,
                app_slug=app_slug,
                source_url=raw.url,
            )

            if not extracted_reviews:
                logger.debug("No reviews found on page %s for %s", current_url, app_slug)
                break

            for r in extracted_reviews:
                if reviews_saved >= max_reviews:
                    break

                fp = compute_review_fingerprint(
                    app_slug=app_slug,
                    reviewer_name=r.reviewer_name,
                    review_date=r.review_date,
                    rating=r.rating,
                    body=r.body,
                )

                # Check if fingerprint already exists in DB
                existing = session.scalars(
                    select(Review.id).where(Review.review_fingerprint == fp)
                ).first()

                if existing is not None:
                    duplicate_reviews += 1
                    continue

                review_orm = Review(
                    app_id=app_id,
                    app_slug=app_slug,
                    review_fingerprint=fp,
                    reviewer_name=r.reviewer_name,
                    reviewer_location=r.reviewer_location,
                    time_spent_using_app=r.time_spent_using_app,
                    rating=r.rating,
                    review_date=r.review_date,
                    body=r.body,
                )
                session.add(review_orm)
                reviews_saved += 1

            session.flush()

            if next_page and reviews_saved < max_reviews:
                current_url = next_page
                if delay > 0:
                    time.sleep(delay)
            else:
                break

        except Exception as exc:
            err_msg = str(exc)
            if "404" in err_msg:
                logger.info("App %s has no reviews page (HTTP 404)", app_slug)
                return reviews_saved, duplicate_reviews, pages_scraped, "not_found"
            logger.warning("Error collecting reviews for %s on %s: %s", app_slug, current_url, exc)
            return reviews_saved, duplicate_reviews, pages_scraped, f"error: {exc}"

    return reviews_saved, duplicate_reviews, pages_scraped, "success"
