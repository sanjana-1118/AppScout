"""
tests/test_functional_acceptance.py
Comprehensive Functional Acceptance Test Suite across all six AppScout views.
Verifies endpoints, queries, filters, sorting, pagination, empty states, and error handling.
"""

import sys
import json
import urllib.request
import urllib.parse

BASE_URL = "http://127.0.0.1:8000"

def fetch_json(endpoint: str):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, headers={"User-Agent": "AppScoutFunctionalTester"})
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

def test_view_1_overview():
    print("\n=== TEST VIEW 1: OVERVIEW ===")
    status, data = fetch_json("/api/overview")
    assert status == 200, f"Expected 200, got {status}"
    
    # 1. Summary KPIs
    assert data["summary"]["total_apps"]["value"] == 21502
    assert data["summary"]["total_categories"]["value"] == 166
    assert data["summary"]["total_pricing_plans"]["value"] == 42326
    assert data["summary"]["total_reviews"]["value"] == 20978
    
    # 2. Top reviewed apps
    top_apps = data["top_reviewed_apps"]
    assert len(top_apps) == 5
    assert top_apps[0]["app_slug"] == "judgeme"
    assert top_apps[0]["review_count"] == 44288
    assert top_apps[1]["app_slug"] == "tiktok"
    assert top_apps[1]["review_count"] == 15468
    # Ensure descending order
    for i in range(len(top_apps) - 1):
        assert top_apps[i]["review_count"] >= top_apps[i+1]["review_count"]
    
    # 3. Top rated apps (>= 50 reviews)
    top_rated = data["top_rated_apps"]
    assert len(top_rated) == 5
    for app in top_rated:
        assert app["average_rating"] is not None and app["average_rating"] > 0
        assert app["review_count"] >= 50
    
    # 4. Pricing distribution
    dist = data["pricing_distribution"]
    assert dist["paid"] == 7981
    assert dist["freemium"] == 7775
    assert dist["unknown"] == 3884
    assert dist["free"] == 1862
    assert sum(dist.values()) == 21502
    print("  [PASS] Overview KPIs, Top Reviewed Apps, Top Rated Apps, and Pricing Distribution verified.")

def test_view_2_app_explorer():
    print("\n=== TEST VIEW 2: APP EXPLORER ===")
    # 1. Base query
    status, data = fetch_json("/api/apps?page=1&limit=10&sort_by=reviews&sort_order=desc")
    assert status == 200
    assert data["total"] == 21502
    assert len(data["items"]) == 10
    assert data["items"][0]["app_slug"] == "judgeme"
    
    # 2. Search query (search for 'loox')
    status, data = fetch_json("/api/apps?q=loox&page=1&limit=10")
    assert status == 200
    assert data["total"] >= 1
    assert any(app["app_slug"] == "loox" for app in data["items"])
    
    # 3. Filter by pricing_type (freemium)
    status, data = fetch_json("/api/apps?pricing_type=freemium&page=1&limit=10")
    assert status == 200
    assert data["total"] == 7775
    for app in data["items"]:
        assert app["pricing_type"] == "freemium"
        
    # 4. Filter by category
    status, data = fetch_json("/api/apps?category=marketing-and-conversion-marketing-email-marketing&page=1&limit=10")
    assert status == 200
    assert data["total"] > 0
    
    # 5. Pagination test
    status, p1 = fetch_json("/api/apps?page=1&limit=5&sort_by=reviews&sort_order=desc")
    status, p2 = fetch_json("/api/apps?page=2&limit=5&sort_by=reviews&sort_order=desc")
    assert p1["items"][0]["id"] != p2["items"][0]["id"]
    
    # 6. Empty state test
    status, empty_data = fetch_json("/api/apps?q=xyznonexistentappterm12345")
    assert status == 200
    assert empty_data["total"] == 0
    assert len(empty_data["items"]) == 0
    
    # 7. App details modal endpoint
    status, app_detail = fetch_json("/api/apps/judgeme")
    assert status == 200
    assert app_detail["app_slug"] == "judgeme"
    assert app_detail["app_name"] == "Judge.me Product Reviews App"
    assert len(app_detail["pricing_plans"]) >= 2
    assert len(app_detail["recent_reviews"]) >= 1
    print("  [PASS] App Explorer Search, Pricing Filter, Category Filter, Pagination, Empty State, and App Detail Modal verified.")

def test_view_3_category_intelligence():
    print("\n=== TEST VIEW 3: CATEGORY INTELLIGENCE ===")
    # 1. All 166 categories loaded
    status, data = fetch_json("/api/categories?limit=200")
    assert status == 200
    assert data["total"] == 166
    assert len(data["items"]) == 166
    
    # 2. Search category
    status, search_data = fetch_json("/api/categories?q=shipping&limit=100")
    assert status == 200
    assert search_data["total"] > 0
    for cat in search_data["items"]:
        assert "shipping" in cat["name"].lower() or "shipping" in cat["slug"].lower()
        
    # 3. Category deep dive details
    status, cat_detail = fetch_json("/api/categories/orders-and-shipping-shipping-solutions-shipping")
    assert status == 200
    assert cat_detail["app_count"] == 742
    assert cat_detail["average_rating"] is not None
    assert cat_detail["pricing_breakdown"] is not None
    assert "paid" in cat_detail["pricing_breakdown"]
    assert len(cat_detail["top_apps"]) > 0
    print("  [PASS] Category Intelligence 166 categories, Category Search, and Category Deep-Dive verified.")

def test_view_4_pricing_intelligence():
    print("\n=== TEST VIEW 4: PRICING INTELLIGENCE ===")
    # 1. Pricing overview
    status, data = fetch_json("/api/pricing/overview")
    assert status == 200
    assert data["total_pricing_plans"] == 42326
    assert data["price_distribution"]["median_price"] == 21.0
    assert data["price_distribution"]["avg_price"] == 66.89
    assert data["price_distribution"]["p25_price"] == 9.99
    assert data["price_distribution"]["p75_price"] == 59.0
    assert data["free_trial_stats"]["trial_percentage"] == 50.94
    assert data["free_trial_stats"]["has_trial_count"] == 10953
    
    # 2. Plan explorer base
    status, plans = fetch_json("/api/pricing/plans?page=1&limit=10")
    assert status == 200
    assert plans["total"] == 42326
    
    # 3. Interval filtering
    status, annual_plans = fetch_json("/api/pricing/plans?billing_interval=annual&page=1&limit=10")
    assert status == 200
    assert annual_plans["total"] == 492
    for p in annual_plans["items"]:
        assert p["billing_interval"] == "annual"
        
    # 4. Free trial filter
    status, trial_plans = fetch_json("/api/pricing/plans?has_free_trial=true&page=1&limit=10")
    assert status == 200
    assert trial_plans["total"] > 0
    for p in trial_plans["items"]:
        assert p["free_trial_days"] is not None and p["free_trial_days"] > 0
        
    # 5. Price sorting
    status, asc_plans = fetch_json("/api/pricing/plans?sort_by=price&sort_order=asc&page=1&limit=5")
    status, desc_plans = fetch_json("/api/pricing/plans?sort_by=price&sort_order=desc&page=1&limit=5")
    assert asc_plans["items"][0]["price_amount"] <= desc_plans["items"][0]["price_amount"]
    print("  [PASS] Pricing Overview, Plan Explorer, Interval Filter, Trial Filter, and Price Sorting verified.")

def test_view_5_reviews_explorer():
    print("\n=== TEST VIEW 5: REVIEWS EXPLORER ===")
    # 1. Stats
    status, stats = fetch_json("/api/reviews/stats")
    assert status == 200
    assert stats["total_reviews"] == 20978
    assert stats["distinct_apps_covered"] == 451
    assert stats["average_rating"] == 4.67
    assert sum(stats["rating_distribution"].values()) == 20978
    
    # 2. Star filter (5 stars)
    status, r5 = fetch_json("/api/reviews?rating=5&page=1&limit=10")
    assert status == 200
    assert r5["total"] == stats["rating_distribution"]["5"]
    for r in r5["items"]:
        assert r["rating"] == 5
        
    # 3. Text search ('support')
    status, r_sup = fetch_json("/api/reviews?q=support&page=1&limit=10")
    assert status == 200
    assert r_sup["total"] > 0
    
    # 4. App slug filter
    status, r_judge = fetch_json("/api/reviews?app_slug=judgeme&page=1&limit=10")
    assert status == 200
    assert r_judge["total"] > 0
    for r in r_judge["items"]:
        assert r["app_slug"] == "judgeme"
        
    # 5. Combined filter & pagination
    status, r_comb_p1 = fetch_json("/api/reviews?q=support&rating=5&app_slug=judgeme&page=1&limit=10")
    status, r_comb_p2 = fetch_json("/api/reviews?q=support&rating=5&app_slug=judgeme&page=2&limit=10")
    assert r_comb_p1["total"] == r_comb_p2["total"]
    assert r_comb_p1["items"][0]["id"] != r_comb_p2["items"][0]["id"]
    print("  [PASS] Reviews Stats, Star Filters, Text Search, App Slug Filter, and Combined Pagination verified.")

def test_view_6_data_coverage():
    print("\n=== TEST VIEW 6: DATA COVERAGE & HEALTH ===")
    # 1. Coverage reconciliation
    status, cov = fetch_json("/api/coverage")
    assert status == 200
    assert cov["master_frontier_total"] == 25633
    assert cov["canonical_apps_in_db"] == 21502
    assert cov["rejected_inactive_apps"] == 4130
    assert cov["unaccounted_apps"] == 0
    assert cov["reconciliation_status"] == "COMPLETE (100.0% Accounted)"
    
    # 2. Field fill rates
    rates = {f["field_name"]: f for f in cov["field_fill_rates"]}
    assert rates["average_rating"]["populated_count"] == 8339
    assert rates["average_rating"]["fill_percentage"] == 38.78
    assert rates["review_count"]["populated_count"] == 21476
    assert rates["review_count"]["fill_percentage"] == 99.88
    
    # 3. Integrity status
    assert cov["integrity_status"]["all_checks_passed"] is True
    assert cov["integrity_status"]["no_duplicate_slugs"] is True
    assert cov["integrity_status"]["no_orphan_reviews"] is True
    
    # 4. Health endpoint
    status, hlth = fetch_json("/api/health")
    assert status == 200
    assert hlth["status"] == "healthy"
    assert hlth["database_connected"] is True
    print("  [PASS] Data Coverage Frontier Reconciliation, Field Fill Rates, Integrity Checks, and Health Endpoint verified.")

if __name__ == "__main__":
    print("RUNNING APPSCOUT FULL FUNCTIONAL ACCEPTANCE SUITE...")
    test_view_1_overview()
    test_view_2_app_explorer()
    test_view_3_category_intelligence()
    test_view_4_pricing_intelligence()
    test_view_5_reviews_explorer()
    test_view_6_data_coverage()
    print("\n>>> ALL 6 VIEWS PASSED 100% OF FUNCTIONAL ACCEPTANCE TESTS! <<<")
