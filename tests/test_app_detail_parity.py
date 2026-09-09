"""
tests/test_app_detail_parity.py
-------------------------------
Parity test comparing the current unoptimized review query in get_app_detail
with the proposed SQL GROUP BY + LIMIT 10 query to ensure 100% data integrity
and identical response schema before applying optimizations.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, or_, desc, func
from experiment.db.database import SessionLocal
from experiment.db.models import App
from experiment.reviews.models import Review
from backend.schemas.apps import ReviewSummary, ReviewBrief


def run_original_query(db, app_obj):
    """Original unoptimized logic in backend/routers/apps.py (fetches .all() into RAM)."""
    reviews_in_db = db.scalars(
        select(Review)
        .where(or_(Review.app_id == app_obj.id, Review.app_slug == app_obj.app_slug))
        .order_by(desc(Review.id))
    ).all()

    total_revs = len(reviews_in_db)
    avg_rev_rating = None
    rating_breakdown = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    if total_revs > 0:
        avg_rev_rating = round(sum(r.rating for r in reviews_in_db) / total_revs, 2)
        for r in reviews_in_db:
            if r.rating in rating_breakdown:
                rating_breakdown[r.rating] += 1

    recent_reviews = [
        ReviewBrief(
            id=r.id,
            reviewer_name=r.reviewer_name,
            reviewer_location=r.reviewer_location,
            time_spent_using_app=r.time_spent_using_app,
            rating=r.rating,
            review_date=r.review_date,
            body=r.body,
        )
        for r in reviews_in_db[:10]
    ]

    summary = ReviewSummary(
        total_reviews_in_db=total_revs,
        average_rating_in_db=avg_rev_rating,
        rating_breakdown=rating_breakdown,
    )
    return summary, recent_reviews


def run_optimized_query(db, app_obj):
    """Proposed optimized logic using SQL GROUP BY and LIMIT 10."""
    # 1. Star rating distribution and aggregates computed in SQL
    rating_counts = db.execute(
        select(Review.rating, func.count(Review.id))
        .where(or_(Review.app_id == app_obj.id, Review.app_slug == app_obj.app_slug))
        .group_by(Review.rating)
    ).all()

    rating_breakdown = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for star, cnt in rating_counts:
        if star in rating_breakdown:
            rating_breakdown[star] = cnt

    total_revs = sum(rating_breakdown.values())
    avg_rev_rating = (
        round(sum(star * cnt for star, cnt in rating_breakdown.items()) / total_revs, 2)
        if total_revs > 0
        else None
    )

    # 2. Only fetch the 10 recent reviews requested
    recent_objs = db.scalars(
        select(Review)
        .where(or_(Review.app_id == app_obj.id, Review.app_slug == app_obj.app_slug))
        .order_by(desc(Review.id))
        .limit(10)
    ).all()

    recent_reviews = [
        ReviewBrief(
            id=r.id,
            reviewer_name=r.reviewer_name,
            reviewer_location=r.reviewer_location,
            time_spent_using_app=r.time_spent_using_app,
            rating=r.rating,
            review_date=r.review_date,
            body=r.body,
        )
        for r in recent_objs
    ]

    summary = ReviewSummary(
        total_reviews_in_db=total_revs,
        average_rating_in_db=avg_rev_rating,
        rating_breakdown=rating_breakdown,
    )
    return summary, recent_reviews


def test_app_detail_review_query_parity():
    """Verify that both queries produce 100% identical outputs for rated apps."""
    db = SessionLocal()
    try:
        test_slugs = ["17track", "1clickproduct", "1clickreferral"]
        for slug in test_slugs:
            print(f"Testing parity for app '{slug}'...", flush=True)
            app_obj = db.scalar(select(App).where(App.app_slug == slug))
            assert app_obj is not None, f"App '{slug}' not found in database"

            orig_summary, orig_recent = run_original_query(db, app_obj)
            opt_summary, opt_recent = run_optimized_query(db, app_obj)

            # Assert ReviewSummary parity
            assert orig_summary.total_reviews_in_db == opt_summary.total_reviews_in_db, (
                f"Mismatch in total_reviews_in_db for {slug}: {orig_summary.total_reviews_in_db} vs {opt_summary.total_reviews_in_db}"
            )
            assert orig_summary.average_rating_in_db == opt_summary.average_rating_in_db, (
                f"Mismatch in average_rating_in_db for {slug}: {orig_summary.average_rating_in_db} vs {opt_summary.average_rating_in_db}"
            )
            assert orig_summary.rating_breakdown == opt_summary.rating_breakdown, (
                f"Mismatch in rating_breakdown for {slug}"
            )

            # Assert Recent Reviews parity
            assert len(orig_recent) == len(opt_recent), (
                f"Mismatch in recent_reviews count for {slug}"
            )
            for i in range(len(orig_recent)):
                assert orig_recent[i].id == opt_recent[i].id
                assert orig_recent[i].rating == opt_recent[i].rating
                assert orig_recent[i].reviewer_name == opt_recent[i].reviewer_name
                assert orig_recent[i].review_date == opt_recent[i].review_date
                assert orig_recent[i].body == opt_recent[i].body

            print(f"  [PARITY MATCHED] App '{slug}': Total={opt_summary.total_reviews_in_db}, Avg={opt_summary.average_rating_in_db}, Breakdown={opt_summary.rating_breakdown}", flush=True)
    finally:
        db.close()


if __name__ == "__main__":
    test_app_detail_review_query_parity()
    print("\nALL REVIEW QUERY PARITY CHECKS PASSED SUCCESSFULLY!", flush=True)
