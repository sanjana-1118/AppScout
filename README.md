# AppScout

> A market intelligence and analytics platform for the Shopify App Store, built on an audited database of 21,502 canonical applications, 166 taxonomy categories, 42,326 structured pricing tiers, and 738,101 verified merchant reviews.

---

## 1. Project Overview

**AppScout** is a full-stack eCommerce market intelligence platform designed to help developers, merchants, and market analysts navigate the Shopify App Store.

### What Problem Does AppScout Solve?
The public Shopify App Store contains over 21,000 active applications, but public listings are cluttered with extreme rating inflation (over 95% of reviews are 4 or 5 stars), unproven 1-review apps ranking artificially high, and opaque monetization models. 

AppScout solves this by collecting and normalizing empirical marketplace data into transparent, statistically defensible market signals:
* **Statistically Defensible Rankings**: Applies sample-size evidence thresholds ($\ge 20$ reviews for highest-rated, $\ge 10$ for lowest-rated) so 1-review apps never distort category leaderboards.
* **Commercial Transparency**: Unpacks 42,326 discrete pricing tiers to benchmark median prices, billing cadences, and free trial penetration across 166 categories.
* **Review Verification**: Indexes 738,101 merchant reviews with SHA-256 fingerprint deduplication, star-rating stratification, and full-text keyword search.

---

## 2. Key Features

* **Market Overview**: Executive dashboard with high-level ecosystem KPIs, review availability distribution, commercial model breakdown, and star rating distributions.
* **App Explorer**: Interactive directory covering all 21,502 applications with real-time text search, multi-facet category and pricing filters, rating boundaries, and sorting.
* **Category Intelligence**: Unified single-card workspace across all 166 categories featuring app density, average ratings, commercial breakdowns, evidence distributions, and ranked application cohorts (Most-Reviewed, Highest-Rated, Lowest-Rated) with a Top 10/20/30/50 count selector.
* **Pricing Intelligence**: Monetization analytics across 42,326 plan tiers with median price anchors ($21.00/mo), billing cadence shares, and a searchable plan explorer table.
* **Review Explorer**: Fast full-text keyword search across 738,101 merchant reviews with star rating filters, merchant location tags, and usage duration metadata.
* **App Detail Modal**: Comprehensive application profile modal presenting developer credentials, official descriptions, category tags, structured plan cards, and merchant review excerpts with transparent three-state coverage notices (Cases A, B, and C).

---

## 3. Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | React 19, TypeScript, Vite 8, Tailwind CSS, Lucide React, native `fetch()` |
| **Backend** | FastAPI, Python 3.12+, SQLAlchemy 2.0+, Pydantic v2, Uvicorn ASGI |
| **Database** | PostgreSQL 18.6+ (Neon Cloud / Local PostgreSQL) |
| **Data Collection** | Python 3.12+, `requests`, `beautifulsoup4`, JSON-LD Schema Parsers |
| **Review Processing** | SHA-256 Fingerprint Deduplication, Star Sentiment Stratification, SQL `ILIKE` Search |
| **Testing & Quality** | Oxlint, TypeScript (`tsc -b`), Python smoke and functional acceptance tests |

---

## 4. Project Structure

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
├── appscout_backup.dump             # Canonical PostgreSQL database backup (9.25 MB)
├── backend/                         # FastAPI application, routers, dependencies, and schemas
│   ├── main.py                      # Application entrypoint & CORS middleware
│   ├── config.py                    # Environment settings
│   ├── routers/                     # REST API routers (overview, apps, categories, pricing, reviews)
│   └── schemas/                     # Pydantic v2 validation models
├── docs/                            # Comprehensive technical documentation suite
│   ├── index.md                     # Documentation entrypoint & hub
│   ├── architecture/                # System, backend, frontend, data pipeline, ranking, MCP
│   ├── reference/                   # REST API reference, database schema, project structure
│   └── operations/                  # Setup, testing, troubleshooting
├── frontend/                        # React 19 Single Page Application (Vite + TypeScript)
│   ├── src/views/                   # Core dashboard views (Home, Overview, Explorer, Categories, etc.)
│   ├── src/components/              # Reusable UI widgets (AppDetailModal, Badges, Sidebar)
│   └── src/api/                     # Strongly typed native fetch() API clients
├── experiment/                      # Collection engine, database models, and review scrapers
│   ├── db/                          # SQLAlchemy database engine and ORM models
│   └── reviews/                     # Review collection runner and deduplication logic
├── data/                            # Frontier files, ingestion checkpoints, and schemas
└── tests/                           # Functional acceptance, parity, and live MCP test suites
```

---

## 5. Getting Started

### Quick Start (Local Development)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/appscout.git
   cd appscout
   ```

2. **Configure Backend & Database**:
   ```bash
   cp .env.example .env
   # Restore PostgreSQL database from appscout_backup.dump if needed
   createdb -U postgres appscout
   pg_restore -U postgres -d appscout -v appscout_backup.dump

   python -m venv .venv
   .venv\Scripts\Activate.ps1   # On Windows (or 'source .venv/bin/activate' on Unix)
   pip install -r requirements.txt
   uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```

3. **Configure & Launch Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Access the Application**:
   * Frontend: [http://localhost:5173](http://localhost:5173)
   * Backend API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

For comprehensive setup steps, prerequisites, and environment variable details, see the **[Setup Guide](docs/operations/setup-and-installation.md)**.

---

## 6. Model Context Protocol (MCP) Server for AI Agents

AppScout includes a native **FastMCP** server in `mcp_server/` that exposes verified Shopify App Store intelligence to AI agents such as **Google Antigravity** over the standard `stdio` JSON-RPC transport.

### Architecture Flow
```text
Antigravity AI Agent <--> stdio JSON-RPC <--> FastMCP (mcp_server) <--> httpx <--> FastAPI (/api/...) <--> PostgreSQL
```

* **Single Source of Truth**: The MCP server never touches the database directly; it delegates all requests to the FastAPI backend over HTTP (`http://127.0.0.1:8000`).
* **Zero Mocks**: Every tool call returns live, verified PostgreSQL marketplace data.
* **Stream Safety**: Logging routes strictly to `stderr` so standard output remains pristine JSON-RPC.

### The 11 AI-Callable Tools
1. `check_backend_health` — Diagnostic check of backend and PostgreSQL connectivity.
2. `get_market_overview` — Macro KPIs: 21.5k apps, 738k reviews, commercial distributions.
3. `search_apps` — Multi-facet app filtering (keyword, category, rating, reviews, pricing).
4. `get_app_details` — 360-degree app profile, pricing plans, and merchant reviews.
5. `get_categories` — 166 taxonomy categories with app volume and mean ratings.
6. `get_category_intelligence` — Category analytics and competitive ranking cohorts.
7. `get_pricing_overview` — Monetization analytics across 42.3k discrete plan tiers.
8. `search_pricing_plans` — Search individual plan tiers by features and price range.
9. `search_reviews` — Search 738k verified reviews by sentiment, star rating, and keyword.
10. `get_review_stats` — Review dataset telemetry and star rating distribution.
11. `get_data_coverage` — Frontier reconciliation, field fill rates, and integrity flags.

### Starting the Server
```bash
# Windows
.venv\Scripts\python -m mcp_server.server

# Linux / macOS
.venv/bin/python -m mcp_server.server
```

### Antigravity Connection
Antigravity automatically discovers and connects to the server via the project's root [`mcp_config.json`](mcp_config.json) or workspace plugin [`.agents/plugins/appscout/mcp_config.json`](.agents/plugins/appscout/mcp_config.json):

```json
{
  "mcpServers": {
    "appscout": {
      "command": ".venv/Scripts/python.exe",
      "args": ["-m", "mcp_server.server"],
      "env": {
        "APPSCOUT_API_BASE_URL": "http://127.0.0.1:8000"
      }
    }
  }
}
```
*(On Linux/macOS, replace `"command"` with `".venv/bin/python"`).*

### Example Natural Language Questions Answered by MCP
* *"What is the overall size of the Shopify app ecosystem?"* &rarr; `get_market_overview()`
* *"Which are the largest app categories?"* &rarr; `get_categories(sort_by="app_count", limit=10)`
* *"Find highly rated apps with more than 1,000 reviews."* &rarr; `search_apps(min_rating=4.5, min_reviews=1000)`
* *"What pricing models are most common?"* &rarr; `get_pricing_overview()`
* *"Show me the details of Judge.me."* &rarr; `get_app_details(slug_or_id="judgeme")`

> [!NOTE]
> **ChatGPT Connection Status**: The AppScout MCP server currently targets local agent hosts using `stdio` (such as Google Antigravity). OpenAI ChatGPT Actions / Custom GPTs require an external HTTPS reverse proxy, SSE transport, and OAuth authentication, which are **not configured yet**.

---

## 7. Technical Documentation Suite

Complete documentation is organized in the [`docs/`](docs/) directory:

### Architecture & Design
* **[System Architecture](docs/architecture/system-architecture.md)** — High-level topology, component interactions, and data flow.
* **[Backend Architecture](docs/architecture/backend-architecture.md)** — FastAPI service architecture, domain routers, dependency injection, and SQLAlchemy 2.0 ORM patterns.
* **[Frontend Architecture](docs/architecture/frontend-architecture.md)** — React 19 layout, state management, and modal lifecycle.
* **[Data Pipeline](docs/architecture/data-pipeline.md)** — Catalog crawling, frontier accounting, and review scraping engine.
* **[Ranking Methodology](docs/architecture/ranking-methodology.md)** — Statistical evidence thresholds and category ranking cohorts.
* **[MCP Server Architecture](docs/architecture/mcp-architecture.md)** — FastMCP service architecture, 11 tool specifications, Antigravity integration, and ChatGPT status.

### Reference
* **[API Reference](docs/reference/api-reference.md)** — Complete endpoint paths, query parameters, and response structures.
* **[Database Schema](docs/reference/database-schema.md)** — Relational tables, ER diagram, foreign keys, and indexes.
* **[Project Structure & Conventions](docs/reference/project-structure.md)** — Detailed file roadmap and development conventions.

### Operations
* **[Setup & Installation](docs/operations/setup-and-installation.md)** — Step-by-step local installation and database restore.
* **[Testing & Quality Assurance](docs/operations/testing-and-quality.md)** — Automated smoke tests, acceptance tests, linting, and build.
* **[Troubleshooting Guide](docs/operations/troubleshooting.md)** — Common operational, database, and network fixes.

---

## 7. Current Implementation Status

AppScout is currently in active production-ready status. The backend REST service serves all 14 domain endpoints backed by PostgreSQL, and the React frontend builds with zero TypeScript or lint errors. Data coverage accounts for 100% of discovered frontier applications (21,502 active apps, 166 taxonomy categories, 42,326 pricing plans, and 738,101 deduplicated reviews).
