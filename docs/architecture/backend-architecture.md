# AppScout Backend Architecture

The AppScout backend is a high-performance, asynchronous REST API service built with **FastAPI**, **Python 3.12+**, and **SQLAlchemy 2.0+**, serving catalog data, market aggregations, statistical rankings, and review searches over an audited **PostgreSQL 18.6+** database.

---

## 1. Architectural Overview

The backend is structured around a modular, decoupled domain pattern with strict separation between configuration, routing, request/response validation, dependency injection, and data persistence:

```mermaid
graph TD
    Client["Client (React SPA / HTTP Client)"]

    subgraph EntrypointLayer ["1. Entrypoint & Middleware (backend/main.py)"]
        FastAPIApp["FastAPI Application"]
        CORS["CORSMiddleware (Allowed Origins)"]
        RootRoute["GET / (Service Metadata)"]
        FastAPIApp --> CORS
        FastAPIApp --> RootRoute
    end

    subgraph ConfigLayer ["2. Configuration (backend/config.py)"]
        Settings["Settings (Pydantic BaseSettings)"]
        EnvFile[".env Environment File"]
        EnvFile --> Settings
    end

    subgraph DependencyLayer ["3. Dependency Injection (backend/dependencies.py)"]
        DBSession["get_db_session() (Yields Scoped Session)"]
        Pagination["get_pagination() (Page & Limit Bounds)"]
    end

    subgraph RouterLayer ["4. Domain Routers (backend/routers/)"]
        RouterOverview["overview.py (/api/overview)"]
        RouterApps["apps.py (/api/apps)"]
        RouterCategories["categories.py (/api/categories)"]
        RouterPricing["pricing.py (/api/pricing)"]
        RouterReviews["reviews.py (/api/reviews)"]
        RouterCoverage["coverage.py (/api/coverage & /api/health)"]
    end

    subgraph SchemaLayer ["5. Schemas & Validation (backend/schemas/)"]
        CommonSchemas["common.py (PaginatedResponse[T])"]
        DomainSchemas["Pydantic v2 Models (Apps, Categories, Pricing, Reviews)"]
    end

    subgraph PersistenceLayer ["6. Relational Persistence (PostgreSQL)"]
        Engine["SQLAlchemy 2.0 Engine & Pool (pool_size=20)"]
        ORMModels["ORM Models (App, Category, Plan, Review)"]
        PostgreSQL[(PostgreSQL 18.6+ Database)]
        Engine --> ORMModels
        ORMModels --> PostgreSQL
    end

    Client -->|HTTP Requests| FastAPIApp
    Settings --> FastAPIApp
    FastAPIApp --> RouterLayer
    RouterLayer --> DependencyLayer
    RouterLayer --> SchemaLayer
    DependencyLayer --> Engine
    RouterLayer -->|SQLAlchemy 2.0 Select Queries| Engine
```

---

## 2. Core Modules & Responsibilities

### 2.1 Application Entrypoint (`backend/main.py`)
* **Framework Initialization**: Instantiates the primary `FastAPI(title="AppScout Backend", version="0.1.0")` application instance.
* **CORS Middleware**: Implements `CORSMiddleware` using `settings.cors_origins` (defaulting to `http://localhost:5173` and `http://127.0.0.1:5173`) to allow cross-origin requests from Vite development servers and production domains.
* **Router Mounting**: Registers all 6 domain routers under the `/api` prefix.
* **System Endpoints**: Exposes `GET /` returning service metadata and interactive OpenAPI (`/docs`) and ReDoc (`/redoc`) documentation endpoints.

### 2.2 Configuration Management (`backend/config.py`)
* Built with **Pydantic `BaseSettings`** with automatic `.env` file resolution.
* Manages runtime settings without hardcoded constants:
  * `DATABASE_URL`: PostgreSQL connection string (`postgresql+psycopg://user:pass@host:port/dbname`).
  * `DB_POOL_SIZE` (default `20`): Core connection pool size.
  * `DB_MAX_OVERFLOW` (default `30`): Maximum temporary connections permitted under peak load.
  * `DB_POOL_TIMEOUT` (default `30` seconds): Timeout before pool raises error.
  * `API_HOST` (`127.0.0.1`) and `API_PORT` (`8000`): Server binding addresses.
  * `CORS_ORIGINS`: Comma-delimited list of permitted browser origins.

### 2.3 Dependency Injection (`backend/dependencies.py`)
FastAPI dependency injection guarantees clean resource management and parameter normalization:

* **`get_db_session`**:
  ```python
  def get_db_session() -> Generator[Session, None, None]:
      db = SessionLocal()
      try:
          yield db
      finally:
          db.close()
  ```
  Guarantees that database sessions and pooled TCP connections are released immediately upon route completion, eliminating connection leaks.
* **`get_pagination`**: Extracts and validates `page` (default: 1) and `limit` (default: 20, capped at 100), returning clean offsets and limits for SQL queries.

---

## 3. Domain Routers (`backend/routers/`)

The backend divides API responsibilities into 6 focused routers:

| Router | Prefix / Endpoints | Responsibility |
| :--- | :--- | :--- |
| **`overview.py`** | `GET /api/overview` | Computes ecosystem summary KPIs, review availability breakdown, commercial model counts, rating distributions, and highlighted apps. |
| **`apps.py`** | `GET /api/apps`<br>`GET /api/apps/{app_slug}` | Paginated catalog queries with text search, multi-facet filtering (categories, pricing, rating, trial), and deep detail profiles with structured plan tiers and recent reviews. |
| **`categories.py`** | `GET /api/categories`<br>`GET /api/categories/{slug}` | Category density listing, evidence distribution summaries, and three statistical ranking cohorts (Most-Reviewed, Highest-Rated, Lowest-Rated) with dynamic Top N limit selection. |
| **`pricing.py`** | `GET /api/pricing/overview`<br>`GET /api/pricing/plans` | Monetization analytics across 42,326 plan tiers with median price anchors, price percentiles, billing cadences, and a searchable plan explorer table. |
| **`reviews.py`** | `GET /api/reviews`<br>`GET /api/reviews/stats` | Full-text substring search across 738,101 reviews via SQL `ILIKE`, rating filters, and global review sentiment distributions. |
| **`coverage.py`** | `GET /api/coverage`<br>`GET /api/health` | Internal data reconciliation reporting (frontier vs database) and lightweight health checks. |

---

## 4. Schemas & Serialization (`backend/schemas/`)

AppScout enforces strict request validation and response serialization using **Pydantic v2**:

* **`common.py`**: Generic `PaginatedResponse[T]` schema returning standard pagination metadata:
  ```json
  { "items": [ ... ], "total": 21502, "page": 1, "limit": 20, "pages": 1076 }
  ```
* **Domain Response Models**:
  * `AppListItem` & `AppDetail`: Strongly typed application profiles with category badges and nested plan tiers.
  * `CategoryListItem` & `CategoryDetail`: Taxonomy density, evidence distributions, and ranked cohorts.
  * `PricingOverviewResponse` & `PlanExplorerItem`: Pricing benchmarks, distributions, and plan features.
  * `ReviewItem` & `ReviewsStatsResponse`: Sanitized merchant review records and rating counts.

---

## 5. Database Interaction & Query Standards

The backend directly interfaces with SQLAlchemy 2.0 ORM models defined in `experiment/db/models.py` and `experiment/reviews/models.py`:

### Modern SQLAlchemy 2.0 Select Syntax
All queries use explicit `select()` statements with scalar execution rather than legacy 1.x session query syntax:

```python
# Modern 2.0 Standard in AppScout
stmt = (
    select(App)
    .where(App.pricing_type == "freemium")
    .order_by(desc(App.review_count))
    .offset(offset)
    .limit(limit)
)
results = db.scalars(stmt).all()
```

### Connection Pool Configuration
* **Engine**: `create_engine(DATABASE_URL, pool_size=20, max_overflow=30, pool_timeout=30, pool_recycle=1800)`
* **Recycle**: Automatically recycles connections older than 30 minutes (1800 seconds) to prevent stale serverless connections (essential for Neon Cloud).
