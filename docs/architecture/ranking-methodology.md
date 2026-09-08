# AppScout Ranking Methodology & Market Intelligence

This document describes the ranking algorithms, statistical evidence thresholding, and market intelligence metrics implemented across AppScout.

---

## 1. The Core Problem: Why Naive Rating Rankings Fail

A naive sort by `average_rating DESC` fails on the Shopify App Store due to three empirical realities:

1. **Massive Zero-Review Tail**: **61.2%** of all active applications (13,163 out of 21,502) have **zero public reviews**.
2. **The "One-Review 5-Star" Distortion**: An unproven application with a single 5.0-star review would rank higher than an established enterprise tool with 5,000 reviews and a 4.9-star average.
3. **Severe Rating Inflation**: Over **95.3% of all reviews on Shopify are 4 or 5 stars**. The marketplace average rating across rated apps is **4.74 / 5.0**.

To provide trustworthy, defendable market signals, AppScout introduces **Evidence Thresholding** and **Three Independent Ranking Cohorts**.

---

## 2. Review Evidence Classification

Every application is classified into one of three statistically defensible evidence tiers based on sample size:

| Evidence Tier | Criteria | Active Apps Count | % of Catalog | Interpretation |
| :--- | :--- | :---: | :---: | :--- |
| **Sufficient Evidence** | `review_count >= 20` | **2,412** | 11.22% | Statistically meaningful review volume; ratings can be reliably compared. |
| **Limited Evidence** | `1 <= review_count <= 19` | **5,927** | 27.56% | Some merchant feedback exists, but sample size is too small for definitive quality ranking. |
| **Unreviewed on Shopify** | `review_count == 0` or `NULL` | **13,163** | 61.22% | Zero public merchant feedback recorded on Shopify. |

---

## 3. The Three Category Ranking Cohorts

Within each of the 166 taxonomy categories, applications are evaluated under three distinct ranking cohorts:

### 3.1 Most-Reviewed Apps (Popularity & Market Presence)
* **Goal**: Identifies market leaders and established products by merchant adoption volume.
* **Filter**: `review_count > 0` and app ID not in `UNCOLLECTED_APP_IDS`.
* **Ordering**: `review_count DESC`, then `average_rating DESC`.
* **Important Distinction**: This is a **market-presence / popularity ranking**, not a quality ranking.

### 3.2 Highest-Rated Apps (Quality Leaderboard with Evidence)
* **Goal**: Identifies the highest-quality apps backed by verified merchant feedback.
* **Filter**: `average_rating >= 4.8` **AND** `review_count >= 20`.
* **Ordering**: `average_rating DESC`, then `review_count DESC`.
* **Why $\ge 20$ Reviews?**: Prevents 1-review apps with 5.0 stars from displacing proven tools with thousands of reviews and a 4.9 average.

### 3.3 Lowest-Rated Apps (Established Low-Performance Cohort)
* **Goal**: Highlights established applications with persistent, verifiable merchant dissatisfaction.
* **Filter**: `average_rating < 4.0` **AND** `review_count >= 10`.
* **Ordering**: `average_rating ASC`, then `review_count DESC`.
* **Why $\ge 10$ Reviews?**: A brand-new app with a single 1-star review is often a user mistake or isolated bug. Requiring at least 10 reviews ensures only genuine, recurring patterns of merchant dissatisfaction are highlighted.

---

## 4. Ranking Count Selector ("Show: Top N")

Users can dynamically control how many ranking results to inspect per category via the **Show** selector:

* **Options**: `Top 10` (default), `Top 20`, `Top 30`, `Top 50`.
* **Dynamic Indicator**: When a category contains fewer qualifying apps than the selected limit (for example, only 11 apps meet the lowest-rated threshold), the UI displays only the qualifying apps without padding artificial entries:
  > *"Showing the top 11 eligible apps in this category."*
* **API Support**: `GET /api/categories/{slug}?ranking_limit={10|20|30|50}`.

---

## 5. Review Availability Semantics

AppScout strictly distinguishes between an app's public Shopify listing count and its collected database records:

| State | Condition | Display Behavior in App Detail Modal |
| :--- | :--- | :--- |
| **Case A (Stored Reviews Available)** | `stored_review_count > 0` | Displays review badge (`N stored reviews`), recent review excerpt cards, and an active **"View all reviews (N) →"** button linking to the App Reviews view with the app filter active. |
| **Case B (Public Reviews on Shopify, but Uncollected in DB)** | `review_count > 0` and `stored_review_count == 0` | Displays badge (`N public on Shopify (uncollected)`) and an amber notice: *"Public review records were not collected for this app."* No empty list and no dead links. |
| **Case C (Zero Public Reviews on Shopify)** | `review_count == 0` or `NULL` | Displays badge (`0 public reviews`) and neutral notice: *"No public reviews on Shopify. This application has zero public merchant reviews recorded on Shopify."* |

---

## 6. Pricing Intelligence Metrics

Pricing intelligence is calculated across **42,326 structured plan tiers**:

* **Commercial Model Distribution (in PostgreSQL)**:
  * **Paid**: 7,981 apps (37.1%)
  * **Freemium**: 7,775 apps (36.2%)
  * **Unknown / Unclassified**: 3,884 apps (18.1%)
  * **Free**: 1,862 apps (8.7%)
  * **Total**: 21,502 apps (100.0%)
* **Paid Tier Price Benchmarks**:
  * Median Paid Price: **$21.00 / month** (50th percentile anchor)
  * Average Paid Price: **$66.89 / month**
  * 25th Percentile: **$9.99 / month**
  * 75th Percentile: **$59.00 / month**
* **Free Trial Penetration**: **50.94%** of all applications offer a free trial period (ranging from 3 to 90 days, with 14 days being the most common).
