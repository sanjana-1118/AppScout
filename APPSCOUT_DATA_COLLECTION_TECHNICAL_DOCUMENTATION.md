# APPSCOUT — DATA COLLECTION TECHNICAL DOCUMENTATION

**Version**: 1.0.0 (Production Release)  
**Project**: AppScout (Shopify App Market Intelligence Platform)  
**Database**: PostgreSQL 18.6 (`localhost:5432/appscout`)  

---

## 1. Architecture & Pipeline Overview

```text
Shopify App Store
       ↓
Category Discovery (45 Leaf Categories) + XML Sitemap (25,608 Apps)
       ↓
Frontier Reconciliation (25,633 Unique Canonical Apps)
       ↓
Master App Frontier JSON (data/frontier/)
       ↓
Concurrent Ingestion Engine (run_ingestion.py)
       ↓
Raw HTML Snapshot Caching (data/raw/)
       ↓
Metadata Extraction (extract.py) + Pricing Extractor (extract_pricing.py)
       ↓
Validation Quality Gates (validate.py)
       ↓
PostgreSQL Persistence (apps, categories, app_categories, app_pricing_plans)
       ↓
Review Intelligence Subsystem (collect_reviews.py -> reviews)
       ↓
Failure Reconciliation & Database Integrity Audits
```

---

## 2. Database Models & Relationships

1. **`apps`**: Canonical Shopify application entities (`app_slug`, `app_name`, `app_url`, `developer_name`, `description`, `average_rating`, `review_count`, `pricing_type`, `free_trial_days`).
2. **`categories`**: Normalized category records (`slug`, `name`).
3. **`app_categories`**: Many-to-many junction table mapping applications to categories.
4. **`app_pricing_plans`**: Structured plan tiers (`app_id`, `plan_name`, `price_amount`, `currency`, `billing_interval`, `free_trial_days`, `features`).
5. **`reviews`**: Merchant reviews (`app_id`, `app_slug`, `review_fingerprint`, `reviewer_name`, `reviewer_location`, `time_spent_using_app`, `rating`, `review_date`, `body`).
6. **`ingestion_runs` / `ingestion_items`**: Telemetry and per-app audit tracking.

---

## 3. Key CLI Reproduction Commands

```powershell
# Inspect Live Database & Ingestion Progress
python -m experiment.inspect_state

# Run Full Offline Pricing Backfill Across Snapshots
python -m experiment.backfill_pricing

# Verify Pricing Metadata
python -m experiment.verify_pricing

# Run Review Collection Across Priority Apps
python -m experiment.reviews.run_review_collection --limit 500 --reviews-per-app 50 --workers 4

# Verify Review Dataset Integrity
python -m experiment.reviews.verify_reviews

# Run Master Completion Pipeline
python -m experiment.master_orchestrator
```
