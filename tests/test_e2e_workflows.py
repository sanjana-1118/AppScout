"""
tests/test_e2e_workflows.py
Automated end-to-end verification script for AppScout.
Tests all workflows specified in section 6D, 5E, 3A-B, and single source of truth.
"""

import json
import urllib.request

def req(url: str):
    request = urllib.request.Request(url, headers={'User-Agent': 'AppScoutTestRunner'})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode('utf-8'))

def test_single_source_of_truth():
    print("--- 1. Testing Single Source of Truth Metrics ---")
    ov = req('http://127.0.0.1:8000/api/overview')
    assert ov['summary']['total_apps']['value'] == 21502, "Total apps must be 21502"
    assert ov['summary']['total_categories']['value'] == 166, "Categories must be 166"
    assert ov['summary']['total_pricing_plans']['value'] == 42326, "Plans must be 42326"
    assert ov['summary']['total_reviews']['value'] == 20978, "Reviews must be 20978"
    assert ov['pricing_distribution']['paid'] == 7981
    assert ov['pricing_distribution']['freemium'] == 7775
    assert ov['pricing_distribution']['unknown'] == 3884
    assert ov['pricing_distribution']['free'] == 1862
    print("  [OK] Overview metrics match single source of truth.")

    cov = req('http://127.0.0.1:8000/api/coverage')
    assert cov['master_frontier_total'] == 25633
    assert cov['canonical_apps_in_db'] == 21502
    assert cov['rejected_inactive_apps'] == 4130
    assert cov['unaccounted_apps'] == 0
    assert cov['integrity_status']['all_checks_passed'] is True
    print("  [OK] Data coverage reconciliation matches 25,633 = 21,502 + 4,130 + 1 (0 unaccounted).")

    pricing = req('http://127.0.0.1:8000/api/pricing/overview')
    assert pricing['free_trial_stats']['has_trial_count'] == 10953
    assert pricing['free_trial_stats']['trial_percentage'] == 50.94
    assert pricing['price_distribution']['median_price'] == 21.0
    assert pricing['price_distribution']['avg_price'] == 66.89
    assert pricing['price_distribution']['p25_price'] == 9.99
    assert pricing['price_distribution']['p75_price'] == 59.0
    print("  [OK] Pricing metrics match $21.00 median, $66.89 avg, 50.94% free trial penetration.")

def test_combined_reviews_workflow():
    print("\n--- 2. Testing Combined Reviews Workflow (Section 6D) ---")
    # Step 1: Search for 'support'
    s1 = req('http://127.0.0.1:8000/api/reviews?q=support&page=1&limit=10')
    print(f"  Step 1: Search 'support' -> {s1['total']} matching reviews")
    assert s1['total'] > 0

    # Step 2: Select 5-star reviews
    s2 = req('http://127.0.0.1:8000/api/reviews?q=support&rating=5&page=1&limit=10')
    print(f"  Step 2: 'support' + 5-star -> {s2['total']} matching reviews")
    assert s2['total'] <= s1['total']

    # Step 3: Filter by app slug 'judgeme'
    s3 = req('http://127.0.0.1:8000/api/reviews?q=support&rating=5&app_slug=judgeme&page=1&limit=10')
    print(f"  Step 3: 'support' + 5-star + 'judgeme' -> {s3['total']} matching reviews")
    assert s3['total'] > 0
    for r in s3['items']:
        assert r['app_slug'] == 'judgeme'
        assert r['rating'] == 5

    # Step 4: Move to next page
    s4 = req('http://127.0.0.1:8000/api/reviews?q=support&rating=5&app_slug=judgeme&page=2&limit=10')
    print(f"  Step 4: Page 2 -> {len(s4['items'])} items, page={s4['page']}, total={s4['total']}")
    assert s4['total'] == s3['total']
    assert s4['page'] == 2

    # Step 5: Clear star filter
    s5 = req('http://127.0.0.1:8000/api/reviews?q=support&app_slug=judgeme&page=1&limit=10')
    print(f"  Step 5: Cleared star filter -> {s5['total']} matching reviews")
    assert s5['total'] >= s3['total']

    # Step 6: Clear search & slug -> restore full dataset
    s6 = req('http://127.0.0.1:8000/api/reviews?page=1&limit=10')
    print(f"  Step 6: Fully cleared -> {s6['total']} total reviews restored")
    assert s6['total'] == 20978
    print("  [OK] Reviews combined workflow passed.")

def test_plan_explorer_workflow():
    print("\n--- 3. Testing Plan Explorer Workflow (Section 5E) ---")
    p1 = req('http://127.0.0.1:8000/api/pricing/plans?page=1&limit=10')
    assert p1['total'] == 42326

    # Test annual filter
    p2 = req('http://127.0.0.1:8000/api/pricing/plans?billing_interval=annual&page=1&limit=10')
    assert p2['total'] == 492
    for item in p2['items']:
        assert item['billing_interval'] == 'annual'

    # Test free trial filter
    p3 = req('http://127.0.0.1:8000/api/pricing/plans?has_free_trial=true&page=1&limit=10')
    assert p3['total'] > 0
    for item in p3['items']:
        assert item['free_trial_days'] is not None and item['free_trial_days'] > 0

    # Test price sorting
    p_asc = req('http://127.0.0.1:8000/api/pricing/plans?q=pro&page=1&limit=10&sort_by=price&sort_order=asc')
    p_desc = req('http://127.0.0.1:8000/api/pricing/plans?q=pro&page=1&limit=10&sort_by=price&sort_order=desc')
    print(f"  Search 'pro' asc lowest: ${p_asc['items'][0]['price_amount']} | desc highest: ${p_desc['items'][0]['price_amount']}")
    assert p_desc['items'][0]['price_amount'] >= p_asc['items'][0]['price_amount']
    print("  [OK] Plan Explorer workflow passed.")

def test_categories_loading():
    print("\n--- 4. Testing Categories Loading (Section 4A) ---")
    cats = req('http://127.0.0.1:8000/api/categories?limit=200')
    print(f"  Total categories returned in 1 call: {len(cats['items'])} of {cats['total']}")
    assert cats['total'] == 166
    assert len(cats['items']) == 166, "All 166 categories must be returned"
    print("  [OK] All 166 categories loaded successfully without 100 limit cut-off.")

if __name__ == '__main__':
    test_single_source_of_truth()
    test_combined_reviews_workflow()
    test_plan_explorer_workflow()
    test_categories_loading()
    print("\nALL VERIFICATION TESTS COMPLETED SUCCESSFULLY WITH 0 FAILURES!")
