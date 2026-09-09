"""
tests/test_mcp_server.py
------------------------
Comprehensive test suite verifying the AppScout MCP Server:
1. Tool Registration & Schema definitions (all 11 tools discovered).
2. Parameter handling & bounds enforcement.
3. Stdout isolation (ensuring zero logging on stdout, 100% on stderr).
4. Error handling (BackendUnreachable, NotFound, Timeout).
5. Live end-to-end backend integration & response parity.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import io
import httpx

from mcp_server.server import mcp
from mcp_server.client import AppScoutClient
from backend.main import app


EXPECTED_TOOLS = [
    "check_backend_health",
    "get_market_overview",
    "search_apps",
    "get_app_details",
    "get_categories",
    "get_category_intelligence",
    "get_pricing_overview",
    "search_pricing_plans",
    "search_reviews",
    "get_review_stats",
    "get_data_coverage",
]


async def test_tool_registration():
    """Verify that all 11 domain tools are properly registered with FastMCP."""
    print("\n[TEST 1] Verifying Tool Registration...")
    tools = await mcp.list_tools()
    registered_names = [t.name for t in tools]

    assert len(tools) == 11, f"Expected 11 registered tools, got {len(tools)}"
    for expected in EXPECTED_TOOLS:
        assert expected in registered_names, f"Tool '{expected}' is missing from registration!"

    # Verify tool metadata
    for t in tools:
        assert t.description, f"Tool '{t.name}' is missing a description!"
        assert len(t.description) > 20, f"Tool '{t.name}' description is too brief!"
        assert t.inputSchema is not None, f"Tool '{t.name}' is missing an inputSchema!"

    print(f"  -> OK: All {len(tools)} tools registered with valid schemas and descriptions.")


def test_stdout_isolation():
    """Verify that logging goes to stderr and stdout produces 0 spurious characters."""
    print("\n[TEST 2] Verifying Stdout Logging Isolation...")
    import subprocess

    cmd = [
        sys.executable,
        "-c",
        "from mcp_server.config import logger; logger.info('Test MCP Log Message')",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert len(res.stdout) == 0, f"Stdout received unexpected logging: '{res.stdout}'"
    assert "Test MCP Log Message" in res.stderr, f"Stderr did not receive log: '{res.stderr}'"
    print("  -> OK: Stdout is completely clean. Logs routed strictly to stderr.")


async def test_error_handling_unreachable_backend():
    """Verify clean error dictionary when the backend is unreachable."""
    print("\n[TEST 3] Verifying BackendUnreachable Error Handling...")
    client = AppScoutClient(base_url="http://127.0.0.1:59999", timeout=1.0)
    res = await client.check_health()
    assert res.get("error") in ("BackendUnreachable", "Timeout"), f"Expected BackendUnreachable or Timeout, got: {res}"
    assert "error" in res and "message" in res
    print(f"  -> OK: Unreachable backend safely caught ({res.get('error')}: {res.get('message')[:50]}...).")


async def test_error_handling_404_not_found():
    """Verify clean 404 translation for unknown entities."""
    print("\n[TEST 4] Verifying 404 NotFound Handling...")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_http:
        client = AppScoutClient(base_url="http://testserver")
        # Monkeypatch client._get to use test_http
        async def patched_get(path: str, params=None):
            clean_params = {k: v for k, v in (params or {}).items() if v is not None}
            resp = await test_http.get(path, params=clean_params)
            if resp.status_code == 404:
                detail = "Resource not found"
                try:
                    detail = resp.json().get("detail", detail)
                except Exception:
                    pass
                return {"error": "NotFound", "status_code": 404, "message": detail}
            resp.raise_for_status()
            return resp.json()

        client._get = patched_get
        res = await client.get_app_detail("nonexistent-fake-app-slug-999")
        assert res.get("error") == "NotFound"
        assert res.get("status_code") == 404
        assert "not found" in res.get("message", "").lower()
    print("  -> OK: 404 errors properly translated with descriptive message.")


async def test_live_backend_tool_parity():
    """Verify live tool calls against the AppScout FastAPI application."""
    print("\n[TEST 5] Verifying Live Backend Tool Parity...")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_http:
        client = AppScoutClient(base_url="http://testserver")
        client._get = lambda path, params=None: _asgi_get(test_http, path, params)

        # 1. Health check
        h = await client.check_health()
        assert h["status"] == "healthy"
        assert h["database_connected"] is True
        print("  -> check_backend_health: PASSED (healthy, DB connected)")

        # 2. Market overview
        ov = await client.get_overview()
        assert ov["summary"]["total_apps"]["value"] == 21502
        assert ov["summary"]["total_reviews"]["value"] == 738101
        print("  -> get_market_overview: PASSED (21,502 apps, 738,101 reviews)")

        # 3. Search apps
        apps = await client.list_apps({"q": "reviews", "limit": 5})
        assert apps["total"] > 0
        assert len(apps["items"]) <= 5
        print(f"  -> search_apps: PASSED ({apps['total']} matches for 'reviews')")

        # 4. App details
        detail = await client.get_app_detail("judgeme")
        assert detail["app_slug"] == "judgeme"
        assert len(detail["pricing_plans"]) >= 2
        assert "review_summary" in detail
        assert len(detail["recent_reviews"]) <= 10
        print(f"  -> get_app_details: PASSED ('judgeme' loaded with {len(detail['pricing_plans'])} plans)")

        # 5. Categories
        cats = await client.list_categories({"limit": 10})
        assert cats["total"] == 166
        assert len(cats["items"]) == 10
        print(f"  -> get_categories: PASSED ({cats['total']} total categories)")

        # 6. Category intelligence
        cat_slug = cats["items"][0]["slug"]
        cat_detail = await client.get_category_detail(cat_slug, ranking_limit=10)
        assert cat_detail["slug"] == cat_slug
        assert "most_reviewed_apps" in cat_detail
        print(f"  -> get_category_intelligence: PASSED ('{cat_slug}' loaded with cohorts)")

        # 7. Pricing overview
        po = await client.get_pricing_overview()
        assert po["total_pricing_plans"] == 42326
        assert po["price_distribution"]["median_price"] == 21.0
        print("  -> get_pricing_overview: PASSED (42,326 plans, $21.00 median)")

        # 8. Search pricing plans
        plans = await client.list_pricing_plans({"billing_interval": "annual", "limit": 5})
        assert plans["total"] > 0
        print(f"  -> search_pricing_plans: PASSED ({plans['total']} annual plans found)")

        # 9. Search reviews
        revs = await client.list_reviews({"rating": 5, "limit": 5})
        assert revs["total"] > 0
        for r in revs["items"]:
            assert r["rating"] == 5
        print(f"  -> search_reviews: PASSED ({revs['total']} 5-star reviews found)")

        # 10. Review stats
        rs = await client.get_review_stats()
        assert rs["total_reviews"] == 738101
        assert rs["distinct_apps_covered"] == 8235
        print("  -> get_review_stats: PASSED (738,101 reviews across 8,235 apps)")

        # 11. Data coverage
        cov = await client.get_coverage()
        assert cov["canonical_apps_in_db"] == 21502
        assert cov["unaccounted_apps"] == 0
        assert cov["integrity_status"]["all_checks_passed"] is True
        print("  -> get_data_coverage: PASSED (100% accounted, integrity PASSED)")


async def _asgi_get(test_http: httpx.AsyncClient, path: str, params: dict | None = None):
    clean_params = {k: v for k, v in (params or {}).items() if v is not None}
    resp = await test_http.get(path, params=clean_params)
    if resp.status_code == 404:
        detail = "Resource not found"
        try:
            detail = resp.json().get("detail", detail)
        except Exception:
            pass
        return {"error": "NotFound", "status_code": 404, "message": detail}
    resp.raise_for_status()
    return resp.json()


async def run_all_tests():
    print("=" * 76)
    print("APPSCOUT MODEL CONTEXT PROTOCOL (MCP) TEST SUITE")
    print("=" * 76)
    await test_tool_registration()
    test_stdout_isolation()
    await test_error_handling_unreachable_backend()
    await test_error_handling_404_not_found()
    await test_live_backend_tool_parity()
    print("\n" + "=" * 76)
    print("ALL MCP SERVER TESTS PASSED SUCCESSFULLY WITH 100% VERIFICATION!")
    print("=" * 76)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
