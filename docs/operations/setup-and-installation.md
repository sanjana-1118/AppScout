# AppScout Setup & Installation Guide

This guide walks through setting up, configuring, and running the AppScout monorepo in a local development environment, including restoring the canonical dataset from the provided database backup.

---

## 1. Prerequisites

Ensure the following tools are installed on your machine:

* **Python**: Version `3.12` or newer.
* **Node.js**: Version `20.x` or newer (with `npm` version 10+).
* **PostgreSQL**: Version `18.6` or newer (or access to a serverless PostgreSQL instance such as Neon Cloud).
* **Git**: Modern release.

---

## 2. Repository Cloning & Environment Setup

Clone the repository to your local workspace:

```bash
git clone https://github.com/your-org/appscout.git
cd appscout
```

### 2.1 Backend Environment Configuration

Copy the example environment file at the root:

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and configure your database connection string and optional server settings:

```ini
# PostgreSQL Database Connection
# Format: postgresql+psycopg://<user>:<password>@<host>:<port>/<dbname>
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/appscout

# Optional Connection Pool Settings
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_TIMEOUT=30

# API Host & Port
API_HOST=127.0.0.1
API_PORT=8000

# CORS Allowed Origins (comma-separated list of origins)
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

---

## 3. Database Restoration (`appscout_backup.dump`)

AppScout provides a complete, audited PostgreSQL backup file at the root: **[`appscout_backup.dump`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/appscout_backup.dump)** (9.25 MB). This archive contains all 21,502 applications, 166 categories, 42,326 pricing tiers, and 738,101 deduplicated reviews.

### 3.1 Create Local Database
Using `psql` or PostgreSQL command line tools:

```bash
# Create database
createdb -U postgres appscout
```

### 3.2 Restore from Backup File
The dump file is formatted in PostgreSQL custom archive format (`-Fc` with binary `PGDMP` header), rather than plain text SQL. 

* **Use `pg_restore`**: 
  ```bash
  pg_restore -U postgres -d appscout -v appscout_backup.dump
  ```
* **Do NOT use `psql`**: Running `psql -U postgres -d appscout -f appscout_backup.dump` or piping `psql < appscout_backup.dump` will fail with binary syntax errors because plain `psql` only accepts plain-text `.sql` scripts. `pg_restore` is specifically designed to extract and rebuild tables, schemas, and indexes from custom archive dumps.

*(If prompted, enter your PostgreSQL superuser password).*

### 3.3 Verify Row Counts
Confirm that all tables were populated properly:

```bash
psql -U postgres -d appscout -c "
SELECT 'apps' AS table_name, count(*) FROM apps
UNION ALL
SELECT 'categories', count(*) FROM categories
UNION ALL
SELECT 'app_categories', count(*) FROM app_categories
UNION ALL
SELECT 'app_pricing_plans', count(*) FROM app_pricing_plans
UNION ALL
SELECT 'reviews', count(*) FROM reviews;
"
```

Expected row counts:
* `apps`: **21,502**
* `categories`: **166**
* `app_categories`: **32,587**
* `app_pricing_plans`: **42,326**
* `reviews`: **738,101**

---

## 4. Backend Setup

### 4.1 Create and Activate Virtual Environment

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 4.2 Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4.3 Verify Database Connection & Run Smoke Tests

Verify that your PostgreSQL database is reachable and the FastAPI routes respond correctly:

```bash
python test_backend_api.py
```

All 14 endpoints should pass with HTTP 200 OK.

### 4.4 Start the FastAPI Server

Launch the development server with auto-reload:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

* **Interactive OpenAPI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
* **Root Health Check**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## 5. Frontend Setup

### 5.1 Install Node Dependencies

Open a second terminal, navigate into the `frontend/` directory, and install packages:

```bash
cd frontend
npm install
```

### 5.2 Frontend Environment Variables (Optional)

By default, Vite proxies `/api` requests to `http://127.0.0.1:8000`. If you deploy the frontend separately or point to a remote server, configure `frontend/.env`:

```ini
VITE_API_URL=http://127.0.0.1:8000/api
```

### 5.3 Run the Development Server

```bash
npm run dev
```

* **Frontend URL**: [http://localhost:5173](http://localhost:5173)

---

## 6. First-Run Verification Checklist

1. Open [http://127.0.0.1:8000/api/overview](http://127.0.0.1:8000/api/overview) in your browser. You should receive HTTP 200 with marketplace KPIs.
2. Open [http://localhost:5173](http://localhost:5173). The Home page should load smoothly with metrics and sidebar navigation.
3. Click into **App Explorer** and test search query `"Klaviyo"` or filter by Category.
4. Click into **App Categories**, select a category (e.g. *Store management - Operations - Analytics*), and verify rankings and review evidence distributions.
5. Click an app row to open the **App Detail Modal**; verify structured plans and review excerpts display cleanly.
