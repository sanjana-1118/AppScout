"""
experiment/reviews/extract_reviews.py
-------------------------------------
Phase 7: Review HTML Extraction Module for Shopify App Store.

Parses server-rendered review listing pages (https://apps.shopify.com/<slug>/reviews)
and extracts structured review records with reviewer metadata, rating, date, and text.
"""

from __future__ import annotations

import dataclasses
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup


@dataclasses.dataclass
class ExtractedReview:
    """Individual parsed review item."""
    app_slug: str
    reviewer_name: str | None
    reviewer_location: str | None
    time_spent_using_app: str | None
    rating: int
    review_date: str | None
    body: str

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def extract_reviews_from_html(
    html_text: str,
    app_slug: str,
    source_url: str,
) -> tuple[list[ExtractedReview], str | None]:
    """Parse HTML and extract review items and next page link.

    Returns
    -------
    (reviews, next_page_url) : tuple[list[ExtractedReview], str | None]
    """
    soup = BeautifulSoup(html_text, "html.parser")
    review_cards = soup.find_all("div", attrs={"data-merchant-review": True})

    reviews: list[ExtractedReview] = []

    for card in review_cards:
        # 1. Rating
        rating = 5  # default fallback
        rating_el = card.find(attrs={"aria-label": re.compile(r"(\d+)\s+out of 5 stars", re.I)})
        if rating_el and rating_el.get("aria-label"):
            match = re.search(r"(\d+)\s+out of 5 stars", rating_el["aria-label"], re.I)
            if match:
                rating = int(match.group(1))

        # 2. Date
        review_date = None
        # Usually first text or div in review header
        date_pattern = re.compile(
            r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b",
            re.I,
        )
        card_text = card.get_text(" ", strip=True)
        date_match = date_pattern.search(card_text)
        if date_match:
            review_date = date_match.group(0)

        # 3. Body text
        # Review body is in p tag or data-truncate-content-container
        body_el = card.find("p") or card.find("div", attrs={"data-truncate-content-container": True})
        body_text = body_el.get_text(" ", strip=True) if body_el else ""
        # Clean up "Show more" or extra labels if present
        body_text = re.sub(r"\s+Show more$", "", body_text).strip()
        if not body_text:
            body_text = "No review content provided."

        # 4. Reviewer Store / Name & Location
        # Located in author info section
        reviewer_name = None
        reviewer_location = None
        time_spent = None

        time_match = re.search(r"(About\s+[\w\s]+using the app|Less than\s+[\w\s]+using the app)", card_text, re.I)
        if time_match:
            time_spent = time_match.group(0)

        # Look for author metadata divs
        author_divs = card.find_all("div", class_=lambda c: c and "author" in c.lower()) or card.find_all("span")
        for ad in author_divs:
            txt = ad.get_text(strip=True)
            if txt and len(txt) < 80 and txt != review_date and txt != time_spent:
                if not reviewer_name:
                    reviewer_name = txt
                elif not reviewer_location and txt != reviewer_name:
                    reviewer_location = txt

        reviews.append(
            ExtractedReview(
                app_slug=app_slug,
                reviewer_name=reviewer_name,
                reviewer_location=reviewer_location,
                time_spent_using_app=time_spent,
                rating=rating,
                review_date=review_date,
                body=body_text,
            )
        )

    # 5. Next page link
    next_page_url = None
    next_anchor = soup.find("a", attrs={"rel": "next"})
    if next_anchor and next_anchor.get("href"):
        next_page_url = urljoin(source_url, next_anchor["href"])

    return reviews, next_page_url
