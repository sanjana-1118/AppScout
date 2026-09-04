# AppScout — Shopify App Market Intelligence Platform

AppScout is a comprehensive market intelligence platform for the Shopify App Store. Built on a verified, real-world database of **21,502 canonical applications**, **166 taxonomy categories**, and **42,326 structured pricing tiers**, AppScout empowers merchants, developers, and eCommerce researchers to analyze market saturation, pricing strategies, and merchant sentiment with complete data transparency.

---

## Key Highlights & Ecosystem Metrics

- **Total Active Shopify Apps:** 21,502 canonical applications stored in PostgreSQL.
- **Taxonomy Categories:** 166 normalized Shopify App Store categories.
- **Structured Pricing Plans:** 42,326 parsed plan tiers (32,658 positive paid tiers + 9,668 zero-dollar free tiers).
- **Merchant Review Intelligence:** 20,978 verified merchant reviews across 451 priority applications.
- **Ecosystem Rating Distribution:** 8,339 rated apps (38.78% with $\ge 1$ review; 4.74 / 5.0 average) and 13,163 unreviewed apps (61.22%).
- **Pricing Benchmarks (Paid Tiers):** Median: **$21.00/mo**, Average: **$66.89/mo**, 25th Percentile: **$9.99/mo**, 75th Percentile: **$59.00/mo**.
- **100% Data Accounting:** 25,633 discovered frontier URLs reconciled with 0 unaccounted apps ($21,502\text{ active} + 4,130\text{ rejected} + 1\text{ redirect} = 25,633$).

---

## Dashboard Views

AppScout features seven dedicated views built with a clean SaaS aesthetic:

1. **Home:** Product introduction, core value proposition, key platform stats, and quick navigation cards.
2. **Overview:** Executive market summary, high-level KPIs, top reviewed market leaders (e.g. Judge.me, TikTok, Shopify Flow), and commercial pricing breakdown.
3. **App Explorer:** Interactive app catalog with real-time text search, pricing model filters (Free, Freemium, Paid, Unknown), category filters, pagination, and an in-depth App Detail modal displaying full descriptions, plans, and reviews.
4. **App Categories:** Complete 166-category taxonomy browser with app density counts, average review counts, and category deep-dives.
5. **App Pricing:** Pricing intelligence dashboard featuring tier distributions, billing frequency breakdowns (monthly, annual), free trial penetration (50.94%), and searchable plan explorer.
6. **App Reviews:** Merchant review explorer with 1-star to 5-star rating filters, keyword search, merchant location metadata, and review cards.
7. **Data Coverage:** Data transparency and audit page providing proof of frontier reconciliation, field fill rates, and PostgreSQL database health.

---

## Technology Stack

### Backend & Data Pipeline
- **Language:** Python 3.12+
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous REST API)
- **Database:** [PostgreSQL 18.6](https://www.postgresql.org/) (Relational database with connection pooling)
- **ORM & Validation:** SQLAlchemy 2.0+ & Pydantic v2
- **Data Scraping & Extraction:** `httpx`, `BeautifulSoup4`, JSON-LD structured schemas, and fallback CSS selectors

### Frontend Web Application
- **Library:** [React 19](https://react.dev/)
- **Language:** [TypeScript](https://www.typescriptlang.org/)
- **Bundler & Tooling:** [Vite 8](https://vitejs.dev/)
- **Styling:** Vanilla CSS design tokens with Tailwind CSS utility classes
- **Icons:** Lucide React

---

## Project Structure

```text
AppScout/
├── backend/
│   ├── main.py                  # FastAPI application entrypoint & CORS middleware
│   ├── config.py                # Environment configuration (Database URL, CORS origins)
│   ├── database.py              # SQLAlchemy engine & session management
│   ├── dependencies.py          # Query parameters & pagination dependencies
│   ├── models/                  # SQLAlchemy ORM models (App, Category, Plan, Review)
│   ├── schemas/                 # Pydantic validation schemas
│   └── routers/                 # API endpoint routers
│       ├── overview.py          # /api/overview
│       ├── apps.py              # /api/apps, /api/apps/{slug}
│       ├── categories.py        # /api/categories, /api/categories/{slug}
│       ├── pricing.py           # /api/pricing/overview, /api/pricing/plans
│       ├── reviews.py           # /api/reviews/stats, /api/reviews
│       └── coverage.py          # /api/coverage, /api/health
├── frontend/
│   ├── src/
│   │   ├── api/                 # Centralized API clients (apps, categories, pricing, reviews)
│   │   ├── components/          # Reusable UI components (Header, Sidebar, Modals, ErrorBoundary)
│   │   ├── views/               # Seven core dashboard views
│   │   │   ├── HomeView.tsx
│   │   │   ├── OverviewView.tsx
│   │   │   ├── AppExplorerView.tsx
│   │   │   ├── CategoryIntelligenceView.tsx
│   │   │   ├── PricingIntelligenceView.tsx
│   │   │   ├── ReviewsExplorerView.tsx
│   │   │   └── DataCoverageView.tsx
│   │   ├── utils/               # Formatting utilities (currency, categories, pricing types)
│   │   ├── App.tsx              # Main layout, view switching & error boundaries
│   │   └── index.css            # Global design system & SaaS themes
│   ├── .env.example             # Frontend environment variable documentation
│   └── package.json             # Frontend dependencies & scripts
├── data/                        # Verified master frontier & collection schemas
├── tests/                       # Automated functional acceptance test suites
├── test_backend_api.py          # 14-endpoint FastAPI test suite
├── METRIC_DEFINITIONS.md        # Single source of truth for all calculations
├── requirements.txt             # Python backend dependencies
└── .env.example                 # Root environment variable documentation
```

---

## Getting Started

### 1. Prerequisites
- **Python 3.12+**
- **Node.js 20+** & **npm**
- **PostgreSQL 18.6+** installed and running locally

---

### 2. Backend Setup

1. **Create and activate a Python virtual environment:**
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .venv\Scripts\Activate.ps1

   # macOS / Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   Copy `.env.example` to `.env` and verify your database connection:
   ```ini
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/appscout
   API_HOST=127.0.0.1
   API_PORT=8000
   CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
   ```

4. **Start the FastAPI backend server:**
   ```bash
   uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   *The API will be available at `http://127.0.0.1:8000`. Interactive documentation is available at `http://127.0.0.1:8000/docs`.*

---

### 3. Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install Node packages:**
   ```bash
   npm install
   ```

3. **Configure environment variables (optional):**
   Copy `.env.example` to `.env` if pointing to an external backend URL:
   ```ini
   VITE_API_URL=http://127.0.0.1:8000/api
   ```
   *(If left empty, requests automatically default to `/api`, which is proxied by Vite in development.)*

4. **Start the development server:**
   ```bash
   npm run dev
   ```
   *Open `http://localhost:5173` in your browser to view the dashboard.*

---

## Testing & Verification

AppScout includes comprehensive automated verification suites to ensure backend reliability, query accuracy, and zero compilation errors:

1. **Backend API Test Suite (14 Endpoints):**
   ```bash
   python test_backend_api.py
   ```
   *Verifies database connectivity, search endpoints, pagination, category trees, and coverage health.*

2. **Full Functional Acceptance Suite:**
   ```bash
   python tests/test_functional_acceptance.py
   ```
   *Verifies metric definitions, mathematical reconciliation balance, empty states, and filter logic across all six data views.*

3. **Frontend Production Compilation:**
   ```bash
   cd frontend && npm run build
   ```
   *Runs TypeScript compilation (`tsc -b`) and Vite production bundle generation.*

4. **Frontend Code Quality & Linter:**
   ```bash
   cd frontend && npm run lint
   ```
   *Runs Oxlint checks across all TypeScript and React files.*

---

## Current Project Status & Roadmap

| Stage / Feature | Status | Notes |
|---|---|---|
| **Phase 1: Data Collection & Ingestion** | **Completed** | 25,633 frontier targets crawled, 21,502 apps persisted in PostgreSQL. |
| **Phase 2: Full-Stack Platform & Stabilization** | **Completed** | FastAPI backend, React SaaS dashboard (7 views), zero errors verified. |
| **Pre-Deployment Hardening & Auditing** | **Completed** | Dynamic API endpoints, CORS configuration, React ErrorBoundary, clean UI. |
| **Live Online Deployment** | **Pending** | Awaiting web hosting setup to publish live on the internet with a public link. |
| **Phase 3: App Ranking Methodology** | **Pending** | To be designed and evaluated following live deployment. |

---

## License

This project is developed for academic and market intelligence research purposes. All data collected originates from publicly available listings on the Shopify App Store.
