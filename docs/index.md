# AppScout Documentation Hub

Welcome to the technical documentation for **AppScout**, a market intelligence and analytics platform for the Shopify App Store. Built upon an audited, canonical dataset of **21,502 applications**, **166 taxonomy categories**, **42,326 structured pricing tiers**, and **738,101 merchant reviews**, AppScout provides transparent, statistically defensible market signals for eCommerce merchants, developers, and analysts.

This documentation suite is organized according to the **Diátaxis framework** into three core functional categories: **Architecture & Explanation**, **Technical Reference**, and **Operations & How-To**.

---

## Documentation Directory

### 1. Architecture & Explanation
Understanding-oriented design guides covering system topology, data acquisition, statistical models, and frontend state:

| Guide | Description |
| :--- | :--- |
| **[System Architecture](architecture/system-architecture.md)** | Full-stack topology, component responsibilities, end-to-end data flow, and external service boundaries. |
| **[Data Pipeline](architecture/data-pipeline.md)** | Complete data acquisition story: leaf-category discovery, XML sitemaps, 25.6k frontier accounting, review scraping, Shopify 1,000-page limit, and SHA-256 deduplication. |
| **[Ranking Methodology](architecture/ranking-methodology.md)** | Statistical evidence thresholding, rating inflation analysis, three category ranking cohorts, and review availability semantics (Cases A, B, C). |
| **[Frontend Architecture](architecture/frontend-architecture.md)** | React 19 Single Page Application structure, single-card category workspace, global modal mount pattern, and native `fetch` client. |

---

### 2. Technical Reference
Exhaustive, information-oriented specifications:

| Guide | Description |
| :--- | :--- |
| **[REST API Reference](reference/api-reference.md)** | Complete specification of all 14 REST endpoints across the 6 domain routers, parameters, schemas, and live database JSON responses. |
| **[Database Schema](reference/database-schema.md)** | PostgreSQL Entity-Relationship Diagram (ERD), table specifications (`apps`, `categories`, `app_categories`, `app_pricing_plans`, `reviews`), constraints, indexes, and connection pool configurations. |
| **[Project Structure & Conventions](reference/project-structure.md)** | Monorepo directory tree, module responsibilities, SQLAlchemy 2.0 select standards, and TypeScript conventions. |

---

### 3. Operations & How-To
Actionable, task-oriented workflows for running, verifying, and maintaining the application:

| Guide | Description |
| :--- | :--- |
| **[Setup & Installation](operations/setup-and-installation.md)** | Local environment installation, `.env` configuration, **database restoration from `appscout_backup.dump`**, and running dev servers. |
| **[Testing & Quality Assurance](operations/testing-and-quality.md)** | Automated 14-endpoint backend smoke tests, functional acceptance suite, end-to-end tests, Oxlint linting, and production builds. |
| **[Troubleshooting Guide](operations/troubleshooting.md)** | Concrete diagnosis and resolution playbooks for database connections, pool limits, zombie port 8000 processes, and CORS errors. |

---

## Technical Stack Summary

* **Frontend**: React 19, TypeScript, Vite 8, Tailwind CSS, Lucide React, native `fetch()`
* **Backend**: FastAPI, Python 3.12+, SQLAlchemy 2.0+, Pydantic v2, Uvicorn ASGI
* **Database**: PostgreSQL 18.6+ (compatible with Neon Cloud serverless and local PostgreSQL)
* **Data Ingestion**: Python 3.12+, `requests`, `beautifulsoup4`, SHA-256 fingerprint deduplication
