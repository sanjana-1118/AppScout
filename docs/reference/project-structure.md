# AppScout Project Structure & Conventions

This document details the organization of the AppScout monorepo, explaining the responsibilities of each directory, service, and module along with core engineering conventions.

---

## 1. Monorepo Overview

```text
AppScout/
├── .agents/                         # Antigravity agent configuration and workspace plugins
│   └── plugins/appscout/            # AppScout MCP plugin (plugin.json, mcp_config.json)
├── .env.example                     # Root environment configuration template
├── .gitignore                       # Git ignore patterns (virtualenvs, builds, dumps, db)
├── mcp_config.json                  # Root Model Context Protocol (MCP) server configuration
├── mcp_server/                      # FastMCP server exposing 11 tools to AI agents
│   ├── client.py                    # Asynchronous httpx client calling FastAPI endpoints
│   ├── config.py                    # Environment settings, timeouts, and stderr logging
│   └── server.py                    # FastMCP tool registrations and stdio entrypoint
├── README.md                        # Primary project entrypoint and high-level guide
├── requirements.txt                 # Python dependencies (FastAPI, SQLAlchemy, MCP, httpx)
├── test_backend_api.py              # Automated 14-endpoint FastAPI smoke test suite
├── appscout_backup.dump             # Master PostgreSQL backup dump file (9.25 MB)
├── backend/                         # FastAPI application and REST endpoints
├── docs/                            # Categorized technical documentation suite
│   ├── index.md                     # Documentation hub
│   ├── architecture/                # System, backend, frontend, data pipeline, ranking, MCP
│   ├── reference/                   # API reference, database schema, project structure
│   └── operations/                  # Setup, testing, troubleshooting
├── frontend/                        # React 19 + TypeScript + Vite web application
├── experiment/                      # Data collection, scraping, and review processing engine
├── data/                            # Frontier files, ingestion progress, and schemas
└── tests/                           # Functional acceptance, parity, and live MCP test suites
```

---

## 2. Backend Directory (`backend/`)

The `backend/` package contains the production FastAPI application, domain routers, and Pydantic validation schemas.

```text
backend/
├── __init__.py                      # Package marker
├── config.py                        # Pydantic BaseSettings (DB URL, CORS origins, API host/port)
├── dependencies.py                  # FastAPI dependencies (DB session, pagination params)
├── main.py                          # Application entrypoint, CORS middleware, router registration
├── routers/                         # Domain-specific route controllers
│   ├── __init__.py                  # Exposes all router instances
│   ├── apps.py                      # /api/apps (listing, search, filters) & /api/apps/{slug}
│   ├── categories.py                # /api/categories & /api/categories/{slug} (with ranking limit)
│   ├── coverage.py                  # /api/coverage (internal data health) & /api/health
│   ├── overview.py                  # /api/overview (market KPIs, review availability distribution)
│   ├── pricing.py                   # /api/pricing/overview & /api/pricing/plans
│   └── reviews.py                   # /api/reviews (search, rating filters) & /api/reviews/stats
└── schemas/                         # Pydantic v2 request/response models
    ├── __init__.py                  # Package exports
    ├── apps.py                      # AppListItem, AppDetail, CategoryBadge, PricingPlanItem
    ├── categories.py                # CategoryListItem, CategoryDetail, EvidenceSummary
    ├── common.py                    # PaginatedResponse generic schema
    ├── coverage.py                  # DataCoverageReport schema
    ├── overview.py                  # OverviewResponse schema
    ├── pricing.py                   # PricingOverviewResponse, PlanExplorerItem
    └── reviews.py                   # ReviewItem, ReviewsStatsResponse
```

### Key Logic Locations
* **CORS & Root Health**: [`backend/main.py`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/backend/main.py)
* **App Detail & Stored Reviews Lookup**: [`backend/routers/apps.py`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/backend/routers/apps.py)
* **Category Rankings & Evidence Thresholds**: [`backend/routers/categories.py`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/backend/routers/categories.py)
* **Review Text Search & Rating Filters**: [`backend/routers/reviews.py`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/backend/routers/reviews.py)

---

## 3. Frontend Directory (`frontend/`)

The `frontend/` package is an independent React 19 single-page application built with Vite and TypeScript.

```text
frontend/
├── index.html                       # HTML entrypoint
├── package.json                     # Node.js dependencies and lifecycle scripts
├── tsconfig.json                    # TypeScript compiler configuration
├── vite.config.ts                   # Vite bundler configuration & local API proxy setup
├── tailwind.config.js               # Tailwind CSS theme tokens
├── src/
│   ├── main.tsx                     # React DOM entrypoint
│   ├── App.tsx                      # Root application layout, navigation state, modal mounting
│   ├── types.ts                     # Shared TypeScript interfaces (AppItem, CategoryItem, ReviewItem)
│   ├── api/                         # Strongly typed API client functions (native fetch)
│   │   ├── client.ts                # Generic fetch wrapper with baseUrl and query serializing
│   │   ├── apps.ts                  # fetchApps, fetchAppDetail
│   │   ├── categories.ts            # fetchCategories, fetchCategoryDetail
│   │   ├── overview.ts              # fetchOverview
│   │   ├── pricing.ts               # fetchPricingOverview, fetchPricingPlans
│   │   └── reviews.ts               # fetchReviews, fetchReviewsStats
│   ├── components/                  # Reusable UI widgets
│   │   ├── AppDetailModal.tsx       # Full app profile, pricing plans, and merchant review cards
│   │   ├── Badge.tsx                # RatingBadge and PricingBadge
│   │   ├── ErrorBoundary.tsx        # React component error containment
│   │   ├── Header.tsx               # Top navigation bar
│   │   ├── KPICard.tsx              # Metric presentation card with trend indicators
│   │   ├── Sidebar.tsx              # Left navigation sidebar
│   │   └── StatusStates.tsx         # LoadingState, ErrorState, InfoTooltip
│   ├── utils/                       # Presentation formatters
│   │   ├── formatters.ts            # Currency formatting, category name cleanups, pricing types
│   │   └── deduplicateCategories.ts # Category badge deduplication logic
│   └── views/                       # Six primary application views
│       ├── HomeView.tsx             # Platform landing and ecosystem highlights
│       ├── OverviewView.tsx         # High-level market KPIs and review availability breakdown
│       ├── AppExplorerView.tsx      # Full catalog search, pricing/rating filters, pagination
│       ├── CategoryIntelligenceView.tsx # Unified single-card category workspace & rankings
│       ├── PricingIntelligenceView.tsx  # Monetization analytics and plan explorer table
│       └── ReviewsExplorerView.tsx  # 738k review explorer with rating and keyword filters
```

---

## 4. Data Collection & Experiment Directory (`experiment/`)

The `experiment/` directory houses the crawling, HTML extraction, validation, and database ingestion pipeline used to build and maintain AppScout's dataset.

```text
experiment/
├── acquire.py                       # HTTP client with retry logic, polite delays, and snapshot caching
├── discover_categories.py           # Discovers canonical category sitemaps and entrypoints
├── build_frontier.py                # Traverses listing pages and builds master URL frontier
├── extract.py                       # Extracts JSON-LD metadata and HTML cards from app snapshots
├── extract_pricing.py               # Parses structured pricing plan cards into discrete tiers
├── validate.py                      # Enforces validation quality gates prior to database writes
├── run_ingestion.py                 # Multi-threaded orchestrator for catalog ingestion
├── db/                              # Core database definitions
│   ├── database.py                  # SQLAlchemy engine, sessionmaker, and connection tests
│   └── models.py                    # SQLAlchemy ORM models (App, Category, AppCategory, PricingPlan)
└── reviews/                         # Dedicated review collection subsystem
    ├── collect_reviews.py           # Per-app review pagination traversal and SHA-256 fingerprinting
    ├── extract_reviews.py           # BeautifulSoup parser for merchant review cards
    ├── models.py                    # Review, ReviewCollectionRun, ReviewCollectionItem ORM models
    ├── run_review_collection.py     # Production crawler with Adaptive Concurrency Controller
    └── verify_reviews.py            # Review dataset integrity and deduplication checks
```

---

## 5. Tests Directory (`tests/`)

The `tests/` directory contains functional verification suites:

```text
tests/
├── test_functional_acceptance.py    # Multi-step functional verification of catalog consistency
└── test_e2e_workflows.py            # End-to-end API response validation
```

---

## 6. Data Directory (`data/`)

The `data/` directory stores offline datasets, ingestion checkpoints, and canonical frontiers:

```text
data/
├── frontier/                        # Master URL targets and reconciliation files
│   └── final_verified_master_frontier_20260829T181905Z.json  # Canonical 25,633-target master frontier (6.16 MB)
├── discovered/                      # Raw category sitemaps and leaf discovery lists
├── ingestion/                       # Ingestion batch progress checkpoints
├── raw/                             # Cached HTML app profile snapshots
├── reports/                         # Offline audit summaries
└── reviews/                         # Review crawling progress logs
```

---

## 7. Root Support Files & Tooling

* **`requirements.txt`**: Minimal, locked Python dependencies:
  * `requests==2.32.3` & `beautifulsoup4==4.12.3`: HTTP scraping and HTML/JSON-LD parsing.
  * `fastapi>=0.115.0`, `uvicorn>=0.30.0`, `pydantic>=2.9.0`: ASGI API server and validation.
  * `sqlalchemy>=2.0.0`, `psycopg[binary]>=3.1.0`, `python-dotenv>=1.0.0`: PostgreSQL 18.6+ ORM and connection pooling.
* **`test_backend_api.py`**: Automated 14-endpoint FastAPI smoke test suite verifying status codes, response schemas, and database connectivity.
* **`tests/test_mcp_server.py`**: MCP unit and parity test suite verifying tool registration, bounds enforcement, stderr isolation, and endpoint parity.
* **`tests/test_live_mcp_integration.py`**: 14-step live stdio JSON-RPC test suite executing actual MCP client sessions against the running server.
* **`tests/test_app_detail_parity.py`**: Exact parity verification suite comparing SQL review aggregation against full ORM loads.
* **`mcp_config.json`**: Standard MCP server configuration file for IDE and client discovery.
* **`.agents/plugins/appscout/`**: Antigravity workspace plugin registering the AppScout MCP server.
* **`appscout_backup.dump`**: Master PostgreSQL backup in custom archive format (`-Fc`, 9.25 MB) containing all 21,502 applications, 166 categories, 42,326 plans, and 738,101 reviews.
* **`.env.example`**: Template for database URLs, pool parameters, API binding, and CORS configuration.
* **`scratch/`**: Ad-hoc diagnostic and data validation scripts used during development.
* **`output/`**: Local offline data exports and HTML snapshot caches (untracked in Git).

---

## 8. Engineering Conventions

### 8.1 Backend & Database (SQLAlchemy 2.0)
* Always use SQLAlchemy 2.0 `select()` statements with scalar execution:
  ```python
  stmt = select(App).where(App.app_slug == slug)
  app = db.scalars(stmt).first()
  ```
* Avoid legacy 1.x `db.query(App).filter(...)` constructs.
* Explicitly annotate all Pydantic response models using `response_model=...` on FastAPI routes.
* Wrap all database operations inside the `get_db_session` dependency to guarantee proper session closing and connection release.

### 8.2 Frontend & TypeScript
* Maintain strict TypeScript types in [`frontend/src/types.ts`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/frontend/src/types.ts). Avoid using `any`.
* All API calls must reside inside [`frontend/src/api/`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/frontend/src/api/) with typed request parameters and responses.
* When loading remote data in views, always adhere to the loading hierarchy:
  ```tsx
  {loading ? (
    <LoadingState message="..." />
  ) : error ? (
    <ErrorState message={error} onRetry={loadData} />
  ) : items.length > 0 ? (
    <RenderItems items={items} />
  ) : (
    <EmptyState />
  )}
  ```
* Use Tailwind utility classes with consistent SaaS color tokens (`slate-*`, `blue-*`, `emerald-*`, `amber-*`).
