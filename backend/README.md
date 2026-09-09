# AppScout Backend

The **AppScout Backend** is a high-performance asynchronous REST API service built with **FastAPI**, **Python 3.12+**, and **SQLAlchemy 2.0+**. It serves catalog queries, market analytics, category rankings, and review explorations over an audited PostgreSQL database.

---

## 1. Key Responsibilities

* **Catalog Serving**: Fast paginated queries with text search, rating, pricing, and category filters.
* **Category Intelligence**: Computes category-level metrics (app density, commercial breakdown, review evidence distributions).
* **Defensible Rankings**: Evaluates Most-Reviewed, Highest-Rated ($\ge 4.8$ rating, $\ge 20$ reviews), and Lowest-Rated ($< 4.0$ rating, $\ge 10$ reviews) cohorts.
* **Review Explorer**: Full-text keyword searches across 738,101 stored merchant reviews.
* **Connection Pooling**: Manages database sessions safely via FastAPI dependencies.

---

## 2. Getting Started

### Prerequisites
* Python `3.12+`
* PostgreSQL `18.6+` (or a cloud PostgreSQL instance)

### Installation
From the project root:

```bash
# Windows
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running the API Server
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

* **Interactive OpenAPI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc Schema Browser**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### Running Automated Smoke Tests
```bash
python test_backend_api.py
```

---

## 3. Configuration

Configured via environment variables (or `.env` at root):

* `DATABASE_URL`: PostgreSQL connection string (`postgresql+psycopg://user:pass@host:port/dbname`).
* `API_HOST`: Bind address (default `127.0.0.1` or `0.0.0.0`).
* `API_PORT`: Bind port (default `8000`).
* `CORS_ORIGINS`: Comma-separated allowed CORS origins.

---

## 4. Model Context Protocol (MCP) Server

AppScout includes a native **FastMCP** server in `mcp_server/` that exposes 11 market intelligence tools to AI agents like Google Antigravity over `stdio`:

```bash
# Start MCP server over stdio (Windows)
.venv\Scripts\python -m mcp_server.server

# Start MCP server over stdio (Linux / macOS)
.venv/bin/python -m mcp_server.server
```

The MCP server communicates with this FastAPI backend as its single source of truth via asynchronous `httpx` HTTP requests (`http://127.0.0.1:8000`), with zero direct database queries and zero data duplication.

---

## 5. Documentation

For detailed backend reference, schemas, and database ERD:
* [Backend Architecture Guide](../docs/architecture/backend-architecture.md)
* [MCP Server Architecture Guide](../docs/architecture/mcp-architecture.md)
* [API Reference](../docs/reference/api-reference.md)
* [Database Schema](../docs/reference/database-schema.md)
* [Ranking & Intelligence Methodology](../docs/architecture/ranking-methodology.md)
* [System Architecture](../docs/architecture/system-architecture.md)
