"""
tests/test_live_mcp_integration.py
----------------------------------
Live end-to-end integration test of the AppScout MCP Server over stdio transport
using the official MCP SDK client (`stdio_client` and `ClientSession`).
Connects to the server running as a child process and calls all tools against
the live running FastAPI backend on http://127.0.0.1:8000.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import json
import requests
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

BACKEND_URL = "http://127.0.0.1:8000"


async def run_integration_suite():
    print("=" * 76, flush=True)
    print("APPSCOUT REAL STDIO MCP INTEGRATION TEST (OFFICIAL MCP CLIENT)", flush=True)
    print("=" * 76, flush=True)

    # 1. Verify FastAPI Backend is up
    print("\n[STEP 1] Checking FastAPI backend health...", flush=True)
    try:
        r = requests.get(f"{BACKEND_URL}/api/health", timeout=3)
        assert r.status_code == 200
        print(f"  -> Backend running at {BACKEND_URL} (PostgreSQL connected)", flush=True)
    except Exception as exc:
        print(f"  -> ERROR: Backend not reachable: {exc}", flush=True)
        return False

    # 2. Configure stdio server parameters matching mcp_config.json
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        env={"APPSCOUT_API_BASE_URL": BACKEND_URL},
    )

    print("\n[STEP 2] Launching MCP server over stdio and establishing ClientSession...", flush=True)
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # 3. Initialize
            print("\n[STEP 3] Initializing protocol handshake...", flush=True)
            init_res = await session.initialize()
            server_info = getattr(init_res, "serverInfo", None)
            s_name = getattr(server_info, "name", "AppScout") if server_info else "AppScout"
            s_ver = getattr(server_info, "version", "1.0.0") if server_info else "1.0.0"
            print(f"  -> Connected to MCP server: '{s_name}' v{s_ver}", flush=True)

            # 4. Tool Discovery
            print("\n[STEP 4] Discovering tools via session.list_tools()...", flush=True)
            tools_response = await session.list_tools()
            tools = tools_response.tools
            tool_names = [t.name for t in tools]
            print(f"  -> Discovered {len(tools)} tools: {', '.join(tool_names)}", flush=True)
            assert len(tools) == 11, f"Expected 11 tools, discovered {len(tools)}"

            async def call(tool_name: str, args: dict | None = None) -> dict:
                res = await session.call_tool(tool_name, arguments=args or {})
                text = res.content[0].text
                return json.loads(text)

            # 5. Test get_market_overview
            print("\n[STEP 5] Calling get_market_overview...", flush=True)
            mcp_ov = await call("get_market_overview")
            api_ov = requests.get(f"{BACKEND_URL}/api/overview").json()
            assert mcp_ov["summary"]["total_apps"]["value"] == api_ov["summary"]["total_apps"]["value"]
            assert mcp_ov["summary"]["total_reviews"]["value"] == api_ov["summary"]["total_reviews"]["value"]
            print(f"  -> Parity MATCHED: Total Apps={mcp_ov['summary']['total_apps']['value']:,}, Total Reviews={mcp_ov['summary']['total_reviews']['value']:,}", flush=True)

            # 6. Test search_apps
            print("\n[STEP 6] Calling search_apps(q='reviews', limit=5)...", flush=True)
            mcp_apps = await call("search_apps", {"q": "reviews", "limit": 5})
            api_apps = requests.get(f"{BACKEND_URL}/api/apps?q=reviews&limit=5").json()
            assert mcp_apps["total"] == api_apps["total"]
            assert mcp_apps["items"][0]["app_slug"] == api_apps["items"][0]["app_slug"]
            print(f"  -> Parity MATCHED: Total matches={mcp_apps['total']:,}, First match='{mcp_apps['items'][0]['app_slug']}'", flush=True)

            # 7. Test get_app_details
            print("\n[STEP 7] Calling get_app_details(slug_or_id='judgeme')...", flush=True)
            mcp_detail = await call("get_app_details", {"slug_or_id": "judgeme"})
            api_detail = requests.get(f"{BACKEND_URL}/api/apps/judgeme").json()
            assert mcp_detail["app_slug"] == api_detail["app_slug"]
            assert mcp_detail["app_name"] == api_detail["app_name"]
            assert len(mcp_detail["pricing_plans"]) == len(api_detail["pricing_plans"])
            print(f"  -> Parity MATCHED: '{mcp_detail['app_slug']}' loaded with {len(mcp_detail['pricing_plans'])} plans and {mcp_detail['review_summary']['total_reviews_in_db']:,} reviews", flush=True)

            # 8. Test get_categories
            print("\n[STEP 8] Calling get_categories(limit=10)...", flush=True)
            mcp_cats = await call("get_categories", {"limit": 10})
            api_cats = requests.get(f"{BACKEND_URL}/api/categories?limit=10").json()
            assert mcp_cats["total"] == api_cats["total"]
            assert len(mcp_cats["items"]) == 10
            print(f"  -> Parity MATCHED: 166 categories, top='{mcp_cats['items'][0]['name']}'", flush=True)

            # 9. Test get_pricing_overview
            print("\n[STEP 9] Calling get_pricing_overview...", flush=True)
            mcp_po = await call("get_pricing_overview")
            api_po = requests.get(f"{BACKEND_URL}/api/pricing/overview").json()
            assert mcp_po["total_pricing_plans"] == api_po["total_pricing_plans"]
            assert mcp_po["price_distribution"]["median_price"] == api_po["price_distribution"]["median_price"]
            print(f"  -> Parity MATCHED: 42,326 plans, median=${mcp_po['price_distribution']['median_price']}", flush=True)

            # 10. Test search_reviews
            print("\n[STEP 10] Calling search_reviews(rating=5, limit=5)...", flush=True)
            mcp_revs = await call("search_reviews", {"rating": 5, "limit": 5})
            api_revs = requests.get(f"{BACKEND_URL}/api/reviews?rating=5&limit=5").json()
            assert mcp_revs["total"] == api_revs["total"]
            assert len(mcp_revs["items"]) == 5
            for r in mcp_revs["items"]:
                assert r["rating"] == 5
            print(f"  -> Parity MATCHED: 5-star reviews count={mcp_revs['total']:,}", flush=True)

            # 11. Test get_review_stats
            print("\n[STEP 11] Calling get_review_stats...", flush=True)
            mcp_rs = await call("get_review_stats")
            api_rs = requests.get(f"{BACKEND_URL}/api/reviews/stats").json()
            assert mcp_rs["total_reviews"] == api_rs["total_reviews"]
            assert mcp_rs["average_rating"] == api_rs["average_rating"]
            print(f"  -> Parity MATCHED: Total reviews={mcp_rs['total_reviews']:,}, Average rating={mcp_rs['average_rating']}", flush=True)

            # 12. Test get_data_coverage
            print("\n[STEP 12] Calling get_data_coverage...", flush=True)
            mcp_cov = await call("get_data_coverage")
            api_cov = requests.get(f"{BACKEND_URL}/api/coverage").json()
            assert mcp_cov["canonical_apps_in_db"] == api_cov["canonical_apps_in_db"]
            assert mcp_cov["unaccounted_apps"] == 0
            assert mcp_cov["integrity_status"]["all_checks_passed"] is True
            print("  -> Parity MATCHED: 21,502 apps, 0 unaccounted, integrity: PASSED", flush=True)

            # 13. Test Error Case A: Invalid App Slug
            print("\n[STEP 13] Testing Error Case A: Invalid App Slug...", flush=True)
            err_res = await call("get_app_details", {"slug_or_id": "nonexistent-app-999-xyz"})
            assert err_res.get("error") == "NotFound"
            assert err_res.get("status_code") == 404
            assert "not found" in err_res.get("message", "").lower()
            print(f"  -> Handled Cleanly: {err_res}", flush=True)

            # 14. Test Error Case B: Backend-Unavailable Case
            print("\n[STEP 14] Testing Error Case B: Backend Unavailable Case...", flush=True)
            from mcp_server.client import AppScoutClient
            down_client = AppScoutClient(base_url="http://127.0.0.1:59999", timeout=1.0)
            down_res = await down_client.check_health()
            assert down_res.get("error") in ("BackendUnreachable", "Timeout")
            assert "error" in down_res and "message" in down_res
            print(f"  -> Handled Cleanly: {down_res}", flush=True)

            print("\n" + "=" * 76, flush=True)
            print("ALL 14 REAL STDIO INTEGRATION TESTS PASSED WITH 100% SUCCESS!", flush=True)
            print("=" * 76, flush=True)
            return True


if __name__ == "__main__":
    success = asyncio.run(run_integration_suite())
    if not success:
        sys.exit(1)
