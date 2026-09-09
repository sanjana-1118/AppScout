"""
mcp_server/server.py
--------------------
AppScout Model Context Protocol (MCP) Server using FastMCP.
Exposes Shopify App Market Intelligence REST APIs as AI-callable tools for Antigravity.
Runs over stdio transport. Logs strictly to stderr.
"""

from __future__ import annotations

from typing import Literal, Any
from mcp.server.fastmcp import FastMCP

from mcp_server.config import SERVER_NAME, logger
from mcp_server.client import default_client

# Initialize FastMCP Server
mcp = FastMCP(
    SERVER_NAME,
    instructions=(
        "AppScout MCP Server provides access to verified Shopify App Store intelligence, "
        "covering 21,500+ canonical applications, 166 taxonomy categories, 42,000+ structured pricing "
        "plan tiers, and 738,000+ verified merchant reviews. Use these tools to query macro market "
        "statistics, search and filter apps, inspect detailed pricing models, extract category cohorts, "
        "and analyze merchant review sentiment."
    ),
)


@mcp.tool()
async def check_backend_health() -> dict[str, Any]:
    """Check the health status and PostgreSQL connectivity of the AppScout backend API.

    Returns:
        Status ('healthy' or 'degraded'), database connection state, and PostgreSQL version.
    """
    logger.info("Tool called: check_backend_health")
    return await default_client.check_health()


@mcp.tool()
async def get_market_overview() -> dict[str, Any]:
    """Retrieve macro Shopify App Store ecosystem statistics, distributions, and top apps.

    Provides high-level KPIs including total canonical apps, category counts, structured plan tiers,
    review availability, ecosystem average rating, pricing model distributions (free/freemium/paid),
    rating star breakdown, and top apps by review volume and rating.

    Returns:
        Overview dashboard containing summary KPIs, distributions, and highlighted apps.
    """
    logger.info("Tool called: get_market_overview")
    return await default_client.get_overview()


@mcp.tool()
async def search_apps(
    q: str | None = None,
    category: str | None = None,
    pricing_type: Literal["free", "freemium", "paid", "unknown"] | None = None,
    min_rating: float | None = None,
    max_rating: float | None = None,
    min_reviews: int | None = None,
    max_reviews: int | None = None,
    has_free_trial: bool | None = None,
    sort_by: Literal["reviews", "rating", "name", "newest", "pricing"] = "reviews",
    sort_order: Literal["asc", "desc"] = "desc",
    page: int = 1,
    limit: int = 10,
) -> dict[str, Any]:
    """Search, filter, and paginate through canonical Shopify applications.

    Allows filtering by keyword, taxonomy category, pricing model, rating range, review count range,
    and free trial availability.

    Args:
        q: Search keyword matching app name, developer, description, or slug.
        category: Filter by specific category slug (e.g., 'marketing-and-conversion').
        pricing_type: Filter by pricing model ('free', 'freemium', 'paid', or 'unknown').
        min_rating: Minimum average star rating (1.0 to 5.0).
        max_rating: Maximum average star rating (1.0 to 5.0).
        min_reviews: Minimum merchant review count (e.g., 20 for statistical confidence).
        max_reviews: Maximum merchant review count.
        has_free_trial: True for apps offering a free trial, False for none.
        sort_by: Field to sort by ('reviews', 'rating', 'name', 'newest', 'pricing'). Default 'reviews'.
        sort_order: Sort direction ('asc' or 'desc'). Default 'desc'.
        page: Page number (1-indexed). Default 1.
        limit: Number of apps per page (1 to 100). Default 10 for token economy.

    Returns:
        Paginated list of applications with metadata, badges, and review counts.
    """
    logger.info("Tool called: search_apps (q=%s, category=%s, page=%s, limit=%s)", q, category, page, limit)
    params = {
        "q": q,
        "category": category,
        "pricing_type": pricing_type,
        "min_rating": min_rating,
        "max_rating": max_rating,
        "min_reviews": min_reviews,
        "max_reviews": max_reviews,
        "has_free_trial": has_free_trial,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "page": max(1, page),
        "limit": min(100, max(1, limit)),
    }
    return await default_client.list_apps(params)


@mcp.tool()
async def get_app_details(slug_or_id: str) -> dict[str, Any]:
    """Retrieve full 360-degree intelligence profile for a specific Shopify application.

    Fetches complete app details including description, developer info, taxonomy categories,
    structured pricing plan tiers (prices, billing intervals, features), stored review summary
    statistics, and recent verified merchant reviews.

    Args:
        slug_or_id: The unique Shopify app slug (e.g., 'judgeme', 'klaviyo') or integer app ID.

    Returns:
        Comprehensive app profile, pricing cards, and recent merchant review excerpts.
    """
    logger.info("Tool called: get_app_details (slug_or_id=%s)", slug_or_id)
    return await default_client.get_app_detail(slug_or_id.strip())


@mcp.tool()
async def get_categories(
    q: str | None = None,
    sort_by: Literal["app_count", "name", "rating", "reviews"] = "app_count",
    sort_order: Literal["asc", "desc"] = "desc",
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """Browse normalized Shopify taxonomy categories enriched with app counts and aggregate ratings.

    Args:
        q: Optional search query filtering category name or slug.
        sort_by: Field to sort by ('app_count', 'name', 'rating', 'reviews'). Default 'app_count'.
        sort_order: Sort direction ('asc' or 'desc'). Default 'desc'.
        page: Page number (1-indexed). Default 1.
        limit: Categories per page (1 to 200). Default 20.

    Returns:
        Paginated list of taxonomy categories with app volume and mean category ratings.
    """
    logger.info("Tool called: get_categories (q=%s, page=%s, limit=%s)", q, page, limit)
    params = {
        "q": q,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "page": max(1, page),
        "limit": min(200, max(1, limit)),
    }
    return await default_client.list_categories(params)


@mcp.tool()
async def get_category_intelligence(
    slug_or_id: str,
    ranking_limit: int = 10,
) -> dict[str, Any]:
    """Retrieve deep-dive category intelligence, pricing distributions, and competitive ranking cohorts.

    Returns category-level metrics (mean rating, total apps), pricing model breakdown within the niche,
    evidence availability, and 3 distinct competitive cohorts:
    1. Most-Reviewed Apps (sorted by review volume)
    2. Highest-Rated Apps (rating >= 4.8 and reviews >= 20)
    3. Lowest-Rated Apps (rating < 4.0 and reviews >= 10)

    Args:
        slug_or_id: Category slug (e.g., 'marketing-and-conversion') or integer ID.
        ranking_limit: Max apps to include per cohort (10 to 100). Default 10 for token economy.

    Returns:
        Category profile with pricing breakdown and ranked app cohorts.
    """
    logger.info("Tool called: get_category_intelligence (slug_or_id=%s, limit=%s)", slug_or_id, ranking_limit)
    clamped_limit = min(100, max(10, ranking_limit))
    return await default_client.get_category_detail(slug_or_id.strip(), ranking_limit=clamped_limit)


@mcp.tool()
async def get_pricing_overview() -> dict[str, Any]:
    """Retrieve macro pricing intelligence across all 42,300+ plan tiers in the Shopify App Store.

    Computes price distributions across paid tiers (min, max, average, median, 25th percentile, 75th percentile),
    billing interval breakdown (monthly vs annual shares), free trial adoption rate (50.9% penetration),
    and popular trial duration frequencies (e.g. 7-day, 14-day trials).

    Returns:
        Ecosystem pricing intelligence report and statistical percentiles.
    """
    logger.info("Tool called: get_pricing_overview")
    return await default_client.get_pricing_overview()


@mcp.tool()
async def search_pricing_plans(
    q: str | None = None,
    app_slug: str | None = None,
    billing_interval: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    has_free_trial: bool | None = None,
    sort_by: Literal["price", "plan_name", "app", "newest"] = "price",
    sort_order: Literal["asc", "desc"] = "asc",
    page: int = 1,
    limit: int = 10,
) -> dict[str, Any]:
    """Search and filter through all 42,300+ individual pricing plan tiers.

    Allows querying specific plan names, feature bullet keywords, parent app slugs, billing intervals,
    and price amount ranges.

    Args:
        q: Search keyword matching plan name, features text, or parent app name/slug.
        app_slug: Filter plans belonging to a specific app slug (e.g., 'klaviyo').
        billing_interval: Filter by interval ('monthly', 'annual', etc.).
        min_price: Minimum price amount in USD.
        max_price: Maximum price amount in USD.
        has_free_trial: True to filter plans offering free trial.
        sort_by: Sort field ('price', 'plan_name', 'app', 'newest'). Default 'price'.
        sort_order: Sort direction ('asc' or 'desc'). Default 'asc'.
        page: Page number (1-indexed). Default 1.
        limit: Number of plan tiers per page (1 to 50). Default 10.

    Returns:
        Paginated list of pricing plan tiers with price amounts, intervals, and features.
    """
    logger.info("Tool called: search_pricing_plans (q=%s, app_slug=%s, page=%s)", q, app_slug, page)
    params = {
        "q": q,
        "app_slug": app_slug,
        "billing_interval": billing_interval,
        "min_price": min_price,
        "max_price": max_price,
        "has_free_trial": has_free_trial,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "page": max(1, page),
        "limit": min(50, max(1, limit)),
    }
    return await default_client.list_pricing_plans(params)


@mcp.tool()
async def search_reviews(
    q: str | None = None,
    app_slug: str | None = None,
    rating: int | None = None,
    sort_by: Literal["date", "rating", "newest"] = "date",
    sort_order: Literal["asc", "desc"] = "desc",
    page: int = 1,
    limit: int = 10,
) -> dict[str, Any]:
    """Search, filter, and inspect verified Shopify merchant reviews (738,000+ dataset).

    Enables sentiment analysis, feature request analysis, and merchant complaint discovery
    by searching review text body, filtering by exact star rating (1 to 5), or scoping to a specific app.

    Args:
        q: Search keyword in review body text or reviewer name.
        app_slug: Scopes reviews to a specific application slug (e.g., 'judgeme').
        rating: Exact star rating filter (integer from 1 to 5).
        sort_by: Sort field ('date', 'rating', 'newest'). Default 'date'.
        sort_order: Sort direction ('asc' or 'desc'). Default 'desc'.
        page: Page number (1-indexed). Default 1.
        limit: Number of reviews per page (1 to 50). Default 10.

    Returns:
        Paginated list of verified merchant reviews with rating, date, and review body.
    """
    logger.info("Tool called: search_reviews (q=%s, app_slug=%s, rating=%s)", q, app_slug, rating)
    params = {
        "q": q,
        "app_slug": app_slug,
        "rating": rating,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "page": max(1, page),
        "limit": min(50, max(1, limit)),
    }
    return await default_client.list_reviews(params)


@mcp.tool()
async def get_review_stats() -> dict[str, Any]:
    """Retrieve global merchant review telemetry and star rating distribution.

    Provides dataset-wide metrics including total verified reviews (738,101), distinct apps covered (8,235),
    ecosystem-wide mean review rating (4.8 / 5.0), and the exact count distribution from 1-star to 5-star reviews.

    Returns:
        Review dataset telemetry and star rating breakdown.
    """
    logger.info("Tool called: get_review_stats")
    return await default_client.get_review_stats()


@mcp.tool()
async def get_data_coverage() -> dict[str, Any]:
    """Retrieve data pipeline reconciliation accounting, field fill rates, and database integrity status.

    Verifies the complete frontier reconciliation (25,633 target = 21,502 canonical + 4,130 inactive,
    with 0 unaccounted apps), 100.0% pricing coverage, field population rates, and data integrity checks
    (no duplicate slugs, no duplicate URLs, no duplicate reviews, no orphan reviews).

    Returns:
        Reconciliation metrics, fill rate percentages, and integrity check flags.
    """
    logger.info("Tool called: get_data_coverage")
    return await default_client.get_coverage()


def main():
    """Main execution entrypoint running the AppScout FastMCP server over stdio."""
    logger.info("Starting AppScout MCP Server (stdio transport)...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
