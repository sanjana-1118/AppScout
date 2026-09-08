"""
test_backend_api.py
-------------------
Comprehensive test suite verifying all AppScout FastAPI endpoints against real PostgreSQL data.
"""

from __future__ import annotations

import sys
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_root_endpoint():
    print("\n[TEST] GET / (Root)")
    res = client.get("/")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert "endpoints" in data
    print("  -> OK:", data["name"], data["version"])


def test_health_endpoint():
    print("\n[TEST] GET /api/health")
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True
    print("  -> OK: DB Connected, Version:", data["postgres_version"][:40], "...")


def test_overview_endpoint():
    print("\n[TEST] GET /api/overview")
    res = client.get("/api/overview")
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data
    assert "total_apps" in data["summary"]
    total_apps_val = data["summary"]["total_apps"]["value"]
    assert total_apps_val == 21502, f"Expected 21502 apps, got {total_apps_val}"
    assert len(data["top_categories"]) > 0
    assert len(data["top_reviewed_apps"]) > 0
    print(f"  -> OK: {total_apps_val:,} apps, {len(data['top_categories'])} top categories returned")


def test_apps_endpoints():
    print("\n[TEST] GET /api/apps (List & Filter)")
    # Default list
    res = client.get("/api/apps?page=1&limit=5")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 21502
    assert len(data["items"]) == 5
    first_app = data["items"][0]
    print(f"  -> OK: Paginated list (total={data['total']:,}), first app='{first_app['app_slug']}'")

    # Search query
    print("\n[TEST] GET /api/apps?q=reviews&limit=3")
    res_search = client.get("/api/apps?q=reviews&limit=3")
    assert res_search.status_code == 200
    data_search = res_search.json()
    assert data_search["total"] > 0
    print(f"  -> OK: Search for 'reviews' found {data_search['total']:,} matches")

    # Filter by pricing_type and free trial
    print("\n[TEST] GET /api/apps?pricing_type=freemium&has_free_trial=true&limit=3")
    res_filter = client.get("/api/apps?pricing_type=freemium&has_free_trial=true&limit=3")
    assert res_filter.status_code == 200
    data_filter = res_filter.json()
    assert data_filter["total"] > 0
    for it in data_filter["items"]:
        assert it["pricing_type"] == "freemium"
        assert it["free_trial_days"] is not None and it["free_trial_days"] > 0
    print(f"  -> OK: Filtered freemium apps with trial ({data_filter['total']:,} matches)")

    # Detail view
    slug = first_app["app_slug"]
    print(f"\n[TEST] GET /api/apps/{slug} (Detail)")
    res_detail = client.get(f"/api/apps/{slug}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["app_slug"] == slug
    assert "categories" in detail
    assert "pricing_plans" in detail
    assert "review_summary" in detail
    print(f"  -> OK: Detail loaded for '{slug}' with {len(detail['pricing_plans'])} plans and {len(detail['categories'])} categories")


def test_categories_endpoints():
    print("\n[TEST] GET /api/categories")
    res = client.get("/api/categories?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 166
    first_cat = data["items"][0]
    print(f"  -> OK: 166 categories, top='{first_cat['name']}' ({first_cat['app_count']:,} apps)")

    cat_slug = first_cat["slug"]
    print(f"\n[TEST] GET /api/categories/{cat_slug} (Detail)")
    res_cat_detail = client.get(f"/api/categories/{cat_slug}")
    assert res_cat_detail.status_code == 200
    cat_data = res_cat_detail.json()
    assert cat_data["slug"] == cat_slug
    assert "top_apps" in cat_data
    assert len(cat_data["top_apps"]) > 0
    print(f"  -> OK: Category detail '{cat_slug}' loaded with {len(cat_data['top_apps'])} top apps")


def test_pricing_endpoints():
    print("\n[TEST] GET /api/pricing/overview")
    res = client.get("/api/pricing/overview")
    assert res.status_code == 200
    data = res.json()
    assert data["total_pricing_plans"] == 42326
    assert len(data["model_breakdown"]) >= 4
    print(f"  -> OK: Pricing overview has {data['total_pricing_plans']:,} plans, median price=${data['price_distribution']['median_price']}")

    print("\n[TEST] GET /api/pricing/plans?billing_interval=monthly&limit=5")
    res_plans = client.get("/api/pricing/plans?billing_interval=monthly&limit=5")
    assert res_plans.status_code == 200
    data_plans = res_plans.json()
    assert data_plans["total"] > 0
    print(f"  -> OK: Monthly plans count={data_plans['total']:,}")


def test_reviews_endpoints():
    print("\n[TEST] GET /api/reviews/stats")
    res_stats = client.get("/api/reviews/stats")
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["total_reviews"] > 0
    assert stats["distinct_apps_covered"] > 0
    print(f"  -> OK: {stats['total_reviews']:,} reviews across {stats['distinct_apps_covered']:,} apps, avg={stats['average_rating']} stars")

    print("\n[TEST] GET /api/reviews?rating=5&limit=5")
    res_revs = client.get("/api/reviews?rating=5&limit=5")
    assert res_revs.status_code == 200
    data_revs = res_revs.json()
    assert data_revs["total"] > 0
    for r in data_revs["items"]:
        assert r["rating"] == 5
    print(f"  -> OK: 5-star reviews explorer ({data_revs['total']:,} total 5-star reviews)")


def test_coverage_endpoint():
    print("\n[TEST] GET /api/coverage")
    res = client.get("/api/coverage")
    assert res.status_code == 200
    cov = res.json()
    assert cov["master_frontier_total"] == 25633
    assert cov["canonical_apps_in_db"] == 21502
    assert cov["unaccounted_apps"] == 0
    assert cov["pricing_coverage_percentage"] == 100.0
    assert cov["integrity_status"]["all_checks_passed"] is True
    print("  -> OK: Data coverage verified. 100% pricing coverage, 0 unaccounted apps, integrity: PASSED")


def run_all_tests():
    print("=" * 76)
    print("APPSCOUT FASTAPI BACKEND VERIFICATION TEST SUITE")
    print("=" * 76)
    try:
        test_root_endpoint()
        test_health_endpoint()
        test_overview_endpoint()
        test_apps_endpoints()
        test_categories_endpoints()
        test_pricing_endpoints()
        test_reviews_endpoints()
        test_coverage_endpoint()
        print("\n" + "=" * 76)
        print("ALL FASTAPI BACKEND TESTS PASSED SUCCESSFULLY!")
        print("=" * 76)
    except AssertionError as e:
        print(f"\n[FAIL] Test assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected test exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
