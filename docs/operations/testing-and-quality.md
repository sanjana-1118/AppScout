# AppScout Testing & Quality Assurance

This document details the automated test suites, quality checks, and verification procedures for AppScout.

---

## 1. Overview of Test Suites

The AppScout quality assurance framework verifies end-to-end correctness across the database, backend REST API, and frontend Single Page Application:

| Suite | Scope | Target | Command |
| :--- | :--- | :--- | :--- |
| **Backend Smoke Tests** | 14 REST Endpoints | FastAPI + PostgreSQL | `python test_backend_api.py` |
| **Functional Acceptance** | Business Logic & Consistency | Data & Categorization | `python tests/test_functional_acceptance.py` |
| **End-to-End Workflows** | Deep Workflow Validation | API Serialization | `python tests/test_e2e_workflows.py` |
| **Frontend Linter** | Static Code Analysis | React / TypeScript | `cd frontend && npm run lint` |
| **Production Build** | Typecheck & Asset Bundling | TypeScript compiler (`tsc -b`) | `cd frontend && npm run build` |

---

## 2. Backend Automated Smoke Tests (`test_backend_api.py`)

The root test script tests all 14 API routes against the running or local database instance, ensuring that status codes, response schemas, and headers are valid.

### Running the Suite
```bash
# Windows
.venv\Scripts\Activate.ps1
python test_backend_api.py

# macOS / Linux
source .venv/bin/activate
python test_backend_api.py
```

### Endpoints Verified
1. `GET /` — Root service metadata and navigation links.
2. `GET /api/overview` — Executive marketplace KPIs, review availability, pricing model distribution.
3. `GET /api/apps` — Default app catalog listing with pagination.
4. `GET /api/apps?q=Klaviyo` — Text search matching.
5. `GET /api/apps?pricing_type=free` — Pricing model filtering.
6. `GET /api/apps/{app_slug}` — Deep app detail profile with pricing plans and recent review excerpts.
7. `GET /api/categories` — Taxonomy category density listing.
8. `GET /api/categories/{category_slug}` — Category intelligence, evidence summary, and ranked cohorts.
9. `GET /api/categories/{category_slug}?ranking_limit=20` — Dynamic ranking cohort limit selector.
10. `GET /api/pricing/overview` — Pricing tier distribution, price percentiles, and trial penetration.
11. `GET /api/pricing/plans` — Searchable pricing plan tiers table.
12. `GET /api/reviews` — Merchant review keyword and star rating search.
13. `GET /api/reviews/stats` — Review dataset aggregations and star distribution.
14. `GET /api/coverage` — Internal catalog reconciliation and frontier verification.

---

## 3. Functional Acceptance & E2E Suites

### 3.1 Functional Acceptance (`tests/test_functional_acceptance.py`)
Validates catalog consistency, category relationships, pricing intervals, and statistical rating bounds:

```bash
python tests/test_functional_acceptance.py
```

### 3.2 End-to-End Workflows (`tests/test_e2e_workflows.py`)
Simulates user journeys across search, category deep-dives, pricing explorations, and review filters:

```bash
python tests/test_e2e_workflows.py
```

---

## 4. Frontend Code Quality & Build Checks

### 4.1 Oxlint Linting
AppScout uses **Oxlint** for static analysis across all React components, views, and utilities:

```bash
cd frontend
npm run lint
```

*Expected output*: `0 errors` across all 29 TypeScript files.

### 4.2 Production Typecheck & Compilation
Validates strict TypeScript types using `tsc -b` and bundles production assets into `frontend/dist/`:

```bash
cd frontend
npm run build
```

*Expected output*: Zero type errors, successfully compiled production bundle.
