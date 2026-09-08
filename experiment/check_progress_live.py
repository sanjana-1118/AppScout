import json
from pathlib import Path
from experiment.db.database import get_engine
from sqlalchemy import text

progress_path = Path('data/reviews/_review_collection_progress.json')
if progress_path.exists():
    with open(progress_path, 'r', encoding='utf-8') as f:
        prog = json.load(f)
    print(f"PROGRESS JSON:")
    print(f"  total_completed_apps: {prog.get('total_completed_apps')}")
    print(f"  run_id: {prog.get('run_id')}")
    print(f"  last_updated_at: {prog.get('last_updated_at')}")
    print(f"  completed_in_this_batch: {prog.get('completed_in_this_batch')}")
    print(f"  total_reviews_collected_in_batch: {prog.get('total_reviews_collected_in_batch')}")
    print(f"  failed_apps_count: {prog.get('failed_apps_count')}")

engine = get_engine()
with engine.connect() as conn:
    total_rev = conn.execute(text("SELECT count(*) FROM reviews")).scalar()
    distinct_rev = conn.execute(text("SELECT count(DISTINCT review_fingerprint) FROM reviews")).scalar()
    apps_with_reviews = conn.execute(text("SELECT count(DISTINCT app_id) FROM reviews")).scalar()
    eligible_apps = conn.execute(text("SELECT count(*) FROM apps WHERE review_count > 0")).scalar()
    
    # Calculate exact reachable reviews remaining
    remaining_stats = conn.execute(text("""
        WITH completed_slugs AS (
            -- completed in progress file or apps with >= review_count
            SELECT a.id
            FROM apps a
            JOIN reviews r ON a.id = r.app_id
            WHERE a.review_count > 0
            GROUP BY a.id, a.review_count
            HAVING count(r.id) >= a.review_count
        ),
        app_rev_counts AS (
            SELECT a.id, a.app_slug, a.review_count, count(r.id) as in_db
            FROM apps a
            LEFT JOIN reviews r ON a.id = r.app_id
            WHERE a.review_count > 0 AND a.id NOT IN (SELECT id FROM completed_slugs)
            GROUP BY a.id, a.app_slug, a.review_count
        )
        SELECT 
            count(*) as remaining_apps_count,
            sum(review_count) as raw_remaining_revs,
            sum(LEAST(review_count, 10000) - in_db) as net_reachable_remaining
        FROM app_rev_counts
    """)).mappings().first()
    
    print(f"DATABASE COUNTS:")
    print(f"  total reviews: {total_rev:,}")
    print(f"  distinct fingerprints: {distinct_rev:,}")
    print(f"  apps with reviews in DB: {apps_with_reviews:,}")
    print(f"  eligible apps: {eligible_apps:,}")
    if remaining_stats:
        print(f"REMAINING WORK:")
        print(f"  remaining apps without full reviews: {remaining_stats['remaining_apps_count']:,}")
        print(f"  net reachable reviews remaining: {remaining_stats['net_reachable_remaining']:,}")
