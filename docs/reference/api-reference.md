# AppScout API Reference

The AppScout backend exposes a RESTful API via FastAPI under `/api`. All responses are formatted as JSON and standard HTTP status codes are utilized (`200 OK`, `404 Not Found`, `422 Unprocessable Entity`, `500 Internal Server Error`).

---

## 1. System Endpoints

### `GET /`
Returns service health metadata and direct links to documentation and primary domain routes.

* **Response**: `200 OK`
```json
{
  "name": "AppScout Backend",
  "version": "0.1.0",
  "description": "API backend for Shopify App Store Intelligence Platform",
  "docs_url": "/docs",
  "redoc_url": "/redoc",
  "endpoints": {
    "overview": "/api/overview",
    "apps": "/api/apps",
    "categories": "/api/categories",
    "pricing": "/api/pricing/overview",
    "reviews": "/api/reviews",
    "coverage": "/api/coverage",
    "health": "/api/health"
  }
}
```

### `GET /api/health`
Lightweight system health check verifying database reachability.

* **Response**: `200 OK`
```json
{
  "status": "healthy",
  "database": "connected"
}
```

---

## 2. Overview Endpoints

### `GET /api/overview`
Aggregates high-level marketplace indicators, pricing models, rating distributions, and review availability data.

* **Response**: `200 OK`
```json
{
  "summary": {
    "total_apps": { "label": "Total Active Apps", "value": 21502 },
    "total_categories": { "label": "Taxonomy Categories", "value": 166 },
    "total_pricing_plans": { "label": "Structured Plan Tiers", "value": 42326 },
    "total_reviews": { "label": "Merchant Reviews In DB", "value": 738101 },
    "average_rating": { "label": "Market Average Rating", "value": 4.74 }
  },
  "pricing_distribution": {
    "paid": 7981,
    "freemium": 7775,
    "unknown": 3884,
    "free": 1862
  },
  "rating_distribution": {
    "1": 0,
    "2": 107,
    "3": 575,
    "4": 2644,
    "5": 5013
  },
  "review_availability": {
    "total_active_apps": 21502,
    "apps_with_public_reviews": 8339,
    "apps_with_no_public_reviews": 13163,
    "total_stored_reviews": 738101,
    "apps_with_stored_reviews": 8235,
    "uncollected_apps_count": 104
  }
}
```

---

## 3. Application Endpoints

### `GET /api/apps`
Paginates, searches, and filters the canonical Shopify application catalog.

* **Query Parameters**:
  * `page` (int, default: `1`): 1-indexed page number.
  * `limit` (int, default: `20`, max: `100`): Items per page.
  * `q` (string, optional): Full-text substring search matching app name, developer, or description.
  * `category` (string, optional): Filter by exact category slug.
  * `pricing_type` (string, optional): One of `free`, `freemium`, `paid`, `unknown`.
  * `min_rating` (float, optional): Filter apps with `average_rating >= min_rating`.
  * `min_reviews` (int, optional): Filter apps with `review_count >= min_reviews`.
  * `has_free_trial` (bool, optional): Filter apps offering `free_trial_days > 0`.
  * `sort_by` (string, default: `reviews`): One of `reviews`, `rating`, `name`, `newest`.
  * `sort_order` (string, default: `desc`): `asc` or `desc`.

* **Response**: `200 OK` (PaginatedResponse[AppListItem])
```json
{
  "items": [
    {
      "id": 102,
      "app_slug": "microsoft-clarity",
      "app_name": "Microsoft Clarity",
      "app_url": "https://apps.shopify.com/microsoft-clarity",
      "developer_name": "Microsoft Corporation",
      "description": "Understand your customers with heatmaps and session recordings.",
      "average_rating": 4.9,
      "review_count": 2093,
      "pricing_type": "free",
      "free_trial_days": null,
      "categories": [
        { "id": 14, "slug": "store-management-operations-analytics", "name": "Analytics" }
      ]
    }
  ],
  "total": 21502,
  "page": 1,
  "limit": 20,
  "pages": 1076
}
```

### `GET /api/apps/{app_slug}`
Retrieves extended application profile details including parsed structured pricing plans and recent merchant review excerpts.

* **Path Parameters**:
  * `app_slug` (string, required): Canonical slug or integer ID.
* **Response**: `200 OK` (AppDetail)
```json
{
  "id": 102,
  "app_slug": "microsoft-clarity",
  "app_name": "Microsoft Clarity",
  "app_url": "https://apps.shopify.com/microsoft-clarity",
  "developer_name": "Microsoft Corporation",
  "description": "Understand your customers with heatmaps and session recordings.",
  "average_rating": 4.9,
  "review_count": 2093,
  "pricing_type": "free",
  "free_trial_days": null,
  "categories": [
    { "id": 14, "slug": "store-management-operations-analytics", "name": "Analytics" }
  ],
  "pricing_plans": [],
  "stored_review_count": 2093,
  "recent_reviews": [
    {
      "id": 91823,
      "reviewer_name": "Modern Retail Store",
      "reviewer_location": "United States",
      "time_spent_using_app": "About 6 months using the app",
      "rating": 5,
      "review_date": "August 28, 2026",
      "body": "Incredible insights for optimizing checkout flows!"
    }
  ]
}
```
* **Error**: `404 Not Found` if the app slug does not exist in the database.

---

## 4. Category Intelligence Endpoints

### `GET /api/categories`
Lists all 166 normalized Shopify categories with active application density and average ratings.

* **Query Parameters**:
  * `q` (string, optional): Substring filter for category name or slug.
  * `sort_by` (string, default: `app_count`): One of `app_count`, `name`, `rating`, `reviews`.
  * `sort_order` (string, default: `desc`): `asc` or `desc`.
  * `page` (int, default: `1`), `limit` (int, default: `50`, max: `200`).

* **Response**: `200 OK` (PaginatedResponse[CategoryListItem])

### `GET /api/categories/{category_slug}`
Fetches in-depth category intelligence, including commercial breakdowns, evidence distributions, and ranked application cohorts.

* **Path Parameters**:
  * `category_slug` (string, required): e.g. `store-management-operations-analytics`.
* **Query Parameters**:
  * `ranking_limit` (int, default: `10`, range: `10` to `100`): Maximum apps returned per ranking cohort.
* **Response**: `200 OK` (CategoryDetail)
```json
{
  "id": 14,
  "slug": "store-management-operations-analytics",
  "name": "Analytics",
  "app_count": 1327,
  "average_rating": 4.68,
  "average_review_count": 52.4,
  "evidence_summary": {
    "sufficient_count": 109,
    "limited_count": 339,
    "unreviewed_count": 879
  },
  "pricing_breakdown": {
    "paid": 312,
    "freemium": 520,
    "free": 380,
    "unknown": 115
  },
  "most_reviewed_apps": [ ... ],
  "highest_rated_apps": [ ... ],
  "lowest_rated_apps": [ ... ]
}
```

---

## 5. Pricing Intelligence Endpoints

### `GET /api/pricing/overview`
Provides aggregate pricing analytics computed across 42,326 structured plan tiers.

* **Response**: `200 OK`
```json
{
  "total_plans": 42326,
  "total_apps": 21502,
  "pricing_model_counts": {
    "paid": 7981,
    "freemium": 7775,
    "unknown": 3884,
    "free": 1862
  },
  "price_distribution": {
    "median_price": 21.0,
    "average_price": 66.89,
    "min_price": 0.0,
    "max_price": 10000.0,
    "p25": 9.99,
    "p75": 59.0
  },
  "billing_intervals": { "monthly": 27480, "annual": 765, "usage_based": 340, "one_time": 45 },
  "free_trial_summary": { "plans_with_trial": 21560, "trial_penetration_pct": 50.94 }
}
```

### `GET /api/pricing/plans`
Searchable and filterable table of individual plan tiers.

* **Query Parameters**:
  * `q` (string, optional): Plan name or app name search.
  * `billing_interval` (string, optional): e.g. `monthly`, `annual`.
  * `has_free_trial` (bool, optional).
  * `sort_by` (string, default: `price`): `price`, `plan_name`, `app`, `newest`.
  * `page` (int, default: `1`), `limit` (int, default: `20`).

---

## 6. Review Explorer Endpoints

### `GET /api/reviews`
Searches and filters the 738,101 stored merchant review records.

* **Query Parameters**:
  * `q` (string, optional): Keyword search matching body text, reviewer name, or app slug.
  * `app_slug` (string, optional): Filter reviews belonging to a specific app.
  * `rating` (int, optional, 1-5): Filter by exact star rating.
  * `sort_by` (string, default: `date`): `date`, `rating`, `newest`.
  * `sort_order` (string, default: `desc`).
  * `page` (int, default: `1`), `limit` (int, default: `10`).

### `GET /api/reviews/stats`
Returns total review counts, distinct applications covered, average rating, and star distribution.

* **Response**: `200 OK`
```json
{
  "total_reviews": 738101,
  "distinct_apps_covered": 8235,
  "average_rating": 4.8,
  "rating_distribution": {
    "1": 21948,
    "2": 5092,
    "3": 7519,
    "4": 29081,
    "5": 674461
  }
}
```

---

## 7. Data Coverage & Health

### `GET /api/coverage`
Internal health and catalog reconciliation report showing frontier verification metrics.

* **Response**: `200 OK`
```json
{
  "active_apps_in_db": 21502,
  "frontier_urls_accounted": 25633,
  "stored_reviews": 738101,
  "uncollected_discrepancy_apps": 104,
  "status": "verified"
}
```
