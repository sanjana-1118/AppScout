"""
experiment/reviews/verify_reviews.py
-----------------------------------
PostgreSQL Integrity & Data Quality Auditor for Shopify Merchant Reviews.
"""

from __future__ import annotations

from sqlalchemy import func, select

from experiment.db.database import get_db
from experiment.db.models import App
from experiment.reviews.models import Review, ReviewCollectionItem, ReviewCollectionRun


def verify_reviews_dataset() -> dict:
    print("\n" + "=" * 76)
    print("APPSCOUT — MERCHANT REVIEW INTELLIGENCE DATASET AUDIT")
    print("=" * 76)

    with get_db() as session:
        total_reviews = session.scalar(select(func.count(Review.id))) or 0
        total_runs = session.scalar(select(func.count(ReviewCollectionRun.id))) or 0
        total_audit_items = session.scalar(select(func.count(ReviewCollectionItem.id))) or 0

        # Unique apps with reviews
        distinct_apps_with_reviews = session.scalar(
            select(func.count(func.distinct(Review.app_slug)))
        ) or 0

        # Integrity Checks
        dup_fingerprints = session.execute(
            select(Review.review_fingerprint, func.count(Review.id))
            .where(Review.review_fingerprint != None)
            .group_by(Review.review_fingerprint)
            .having(func.count(Review.id) > 1)
        ).all()

        orphan_reviews = session.execute(
            select(Review)
            .outerjoin(App, Review.app_id == App.id)
            .where(App.id == None)
        ).all()

        invalid_ratings = session.execute(
            select(Review).where((Review.rating < 1) | (Review.rating > 5))
        ).all()

        null_body = session.execute(
            select(Review).where((Review.body == None) | (Review.body == ""))
        ).all()

        null_slug = session.execute(
            select(Review).where(Review.app_slug == None)
        ).all()

        # Rating Distribution
        rating_dist = dict(
            session.execute(
                select(Review.rating, func.count(Review.id))
                .group_by(Review.rating)
                .order_by(Review.rating.asc())
            ).all()
        )

        avg_rating = session.scalar(select(func.avg(Review.rating))) or 0.0

        # Field Fill Rates
        all_revs = session.scalars(select(Review)).all()
        n = max(len(all_revs), 1)
        fill_reviewer = sum(1 for r in all_revs if r.reviewer_name)
        fill_location = sum(1 for r in all_revs if r.reviewer_location)
        fill_time_spent = sum(1 for r in all_revs if r.time_spent_using_app)
        fill_date = sum(1 for r in all_revs if r.review_date)

    integrity_passed = (
        len(dup_fingerprints) == 0
        and len(orphan_reviews) == 0
        and len(invalid_ratings) == 0
        and len(null_body) == 0
        and len(null_slug) == 0
    )

    print(f"Total Merchant Reviews in DB  : {total_reviews:,}")
    print(f"Distinct Apps with Reviews    : {distinct_apps_with_reviews:,}")
    print(f"Average Review Rating         : {avg_rating:.2f} / 5.0")
    print(f"Audit Runs Executed           : {total_runs:,}")
    print(f"Audit Items Logged            : {total_audit_items:,}")
    print("-" * 76)
    print("Database Integrity Constraints:")
    print(f"  - Duplicate Review Hashes   : {len(dup_fingerprints)} (PASSED)" if len(dup_fingerprints) == 0 else f"  - Duplicate Review Hashes: {len(dup_fingerprints)} FAIL")
    print(f"  - Orphan Reviews (No App)   : {len(orphan_reviews)} (PASSED)" if len(orphan_reviews) == 0 else f"  - Orphan Reviews: {len(orphan_reviews)} FAIL")
    print(f"  - Invalid Ratings (<1 or >5): {len(invalid_ratings)} (PASSED)" if len(invalid_ratings) == 0 else f"  - Invalid Ratings: {len(invalid_ratings)} FAIL")
    print(f"  - Empty / Null Review Body  : {len(null_body)} (PASSED)" if len(null_body) == 0 else f"  - Empty Body: {len(null_body)} FAIL")
    print(f"  - Null App Slug             : {len(null_slug)} (PASSED)" if len(null_slug) == 0 else f"  - Null App Slug: {len(null_slug)} FAIL")
    print("-" * 76)
    print("Rating Distribution Breakdown:")
    for star in range(1, 6):
        count = rating_dist.get(star, 0)
        pct = round(count / max(total_reviews, 1) * 100, 1)
        bar = "#" * int(pct // 3)
        print(f"  {star} Star(s) : {count:>6,} ({pct:>5.1f}%) | {bar}")
    print("-" * 76)
    print("Review Metadata Field Fill Rates:")
    print(f"  - reviewer_name        : {fill_reviewer:,}/{total_reviews:,} ({round(fill_reviewer/n*100, 1)}%)")
    print(f"  - review_date          : {fill_date:,}/{total_reviews:,} ({round(fill_date/n*100, 1)}%)")
    print(f"  - reviewer_location    : {fill_location:,}/{total_reviews:,} ({round(fill_location/n*100, 1)}%) [Where publicly provided]")
    print(f"  - time_spent_using_app : {fill_time_spent:,}/{total_reviews:,} ({round(fill_time_spent/n*100, 1)}%) [Where publicly provided]")
    print("-" * 76)
    print(f"Review Subsystem Status       : {'100% PASSED & PRODUCTION-READY' if integrity_passed else 'INTEGRITY ISSUES FOUND'}")
    print("=" * 76 + "\n")

    return {
        "total_reviews": total_reviews,
        "distinct_apps_with_reviews": distinct_apps_with_reviews,
        "avg_rating": float(avg_rating),
        "integrity_passed": integrity_passed,
        "rating_dist": rating_dist,
    }


if __name__ == "__main__":
    verify_reviews_dataset()
