# AppScout — Authoritative Metric Definitions & Data Dictionary

This document serves as the **single source of truth** for all metrics across the six views of the AppScout dashboard.

---

## Metric Definition & Source Mapping Table

| Metric Name | Source Table & Column | Query / Calculation | Denominator / Population | Display Unit | Intended Meaning & User Context |
|---|---|---|---|---|---|
| **Total Shopify Apps** | `apps.id` | `SELECT COUNT(id) FROM apps` | Total active apps universe | Integer (`21,502`) | Total canonical active Shopify applications stored, validated, and reconciled in AppScout's PostgreSQL database. |
| **Taxonomy Categories** | `categories.id` | `SELECT COUNT(id) FROM categories` | Normalized taxonomy universe | Integer (`166`) | Normalized app categories across the Shopify App Store taxonomy tree. |
| **Structured Pricing Plans** | `app_pricing_plans.id` | `SELECT COUNT(id) FROM app_pricing_plans` | Extracted plan tiers universe | Integer (`42,326`) | Total individual plan tiers extracted and parsed into price, interval, and feature sets across stored apps. |
| **Merchant Reviews (Collected)** | `reviews.id` | `SELECT COUNT(id) FROM reviews` | Scraped review bodies universe | Integer (`20,978`) | Verified merchant review bodies scraped from public Shopify app pages for 451 priority applications in the baseline review dataset. |
| **Apps with Collected Reviews** | `reviews.app_slug` | `SELECT COUNT(DISTINCT app_slug) FROM reviews` | Apps in `reviews` table | Integer (`451`) | Priority applications for which full individual review text, merchant locations, and timestamps were extracted. |
| **Ecosystem Avg Rating** | `apps.average_rating` | `SELECT AVG(average_rating) FROM apps WHERE average_rating > 0` | Rated canonical apps (`8,339`) | Score out of `5.0` (`4.74 / 5.0`) | Average star rating calculated across all 8,339 rated Shopify applications in the database. (Unreviewed apps have no public rating on Shopify). |
| **Dataset Sentiment** | `reviews.rating` | `SELECT AVG(rating) FROM reviews` | Collected review bodies (`20,978`) | Score out of `5.0` (`4.67 / 5.0`) | Mean star rating across all 20,978 individual merchant review bodies collected in the Reviews Explorer. |
| **Public Shopify Review Count** | `apps.review_count` | Public count on Shopify listing | Individual application | Integer | Total public reviews displayed on Shopify's official App Store listing for that app (e.g. Judge.me has 44,288 public reviews). |
| **Rated Apps Count & Fill Rate** | `apps.average_rating` | `SELECT COUNT(*) FROM apps WHERE average_rating > 0` | All canonical apps (`21,502`) | Count & Percentage (`8,339` / `38.78%`) | Canonical apps with at least 1 public review on Shopify. The remaining 13,163 apps (61.22%) have 0 reviews and are unrated. |
| **Review Count Field Fill Rate** | `apps.review_count` | `SELECT COUNT(*) FROM apps WHERE review_count IS NOT NULL` | All canonical apps (`21,502`) | Count & Percentage (`21,476` / `99.88%`) | Canonical apps with a populated review_count column in PostgreSQL (8,339 apps with review_count > 0, and 13,137 with review_count = 0). |
| **Commercial Pricing Models** | `apps.pricing_type` | `COUNT(*) GROUP BY pricing_type` | All canonical apps (`21,502`) | Counts & Percentages | Primary commercialization model: Paid (`7,981` / 37.12%), Freemium (`7,775` / 36.16%), Unknown / Unclassified (`3,884` / 18.06%), Free (`1,862` / 8.66%). |
| **Free Trial Penetration** | `apps.free_trial_days` | `SELECT COUNT(*) FROM apps WHERE free_trial_days > 0` | All canonical apps (`21,502`) | Count & Percentage (`10,953` / `50.94%`) | Percentage of all 21,502 canonical apps that offer a free trial period ($\ge 1$ day). |
| **Paid Tier Median Price** | `app_pricing_plans.price_amount` | `percentile_cont(0.50) WHERE price_amount > 0` | Positive paid tiers (`32,658`) | USD (`$21.00`) | The middle price point across all positive paid tiers (50% cost less than $21.00, 50% cost more). |
| **Paid Tier Average Price** | `app_pricing_plans.price_amount` | `AVG(price_amount) WHERE price_amount > 0` | Positive paid tiers (`32,658`) | USD (`$66.89`) | Arithmetic mean price of positive paid tiers ($66.89), influenced by high enterprise/plus tiers (up to $5,000/mo). |
| **Paid Tier 25th / 75th Percentiles**| `app_pricing_plans.price_amount` | `percentile_cont(0.25, 0.75) WHERE price_amount > 0` | Positive paid tiers (`32,658`) | USD (`$9.99` / `$59.00`) | 25th percentile ($9.99, entry merchant tier) and 75th percentile ($59.00, established growth tier). |
| **Billing Intervals** | `app_pricing_plans.billing_interval`| `COUNT(*) GROUP BY billing_interval` | All pricing tiers (`42,326`) | Counts & Percentages | Monthly (`41,154` / 97.23%), Annual (`890` / 2.10%), Usage / Other (`282` / 0.67%). |
| **Master Frontier Reconciliation** | Frontier vs Stored vs Rejected | $21,502\text{ stored} + 4,130\text{ rejected} + 1\text{ redirect} = 25,633$ | Master frontier (`25,633`) | Equations & Zero Unaccounted | Mathematical audit proving 100% of discovered URLs from category trees and XML sitemaps are reconciled. |
| **Category App Density** | `app_categories.app_id` | `SELECT COUNT(app_id) GROUP BY category_id` | Category specific | Integer count | Number of active canonical Shopify apps indexed under that specific category. |
| **Category Avg Public Reviews** | `apps.review_count` | `AVG(apps.review_count) in category` | Apps in category | Float | Average public Shopify review count per app in that category. |

---

## Discrepancies Resolved

1. **Top Reviewed Apps Bug Fixed**:
   - Issue: `desc(App.review_count)` in PostgreSQL places `NULLS FIRST` by default, causing 5 apps with `NULL` reviews to appear at the top.
   - Fix: Query must use `App.review_count.desc().nullslast()`. Real top reviewed apps are Judge.me (44,288 reviews), TikTok (15,468), Shopify Flow (12,377), Loox (9,119), and Shop (8,604).
2. **Review Count (21,476 vs 20,978) Clarified**:
   - `21,476` is the number of apps where the `review_count` attribute is populated in PostgreSQL (8,339 apps have reviews > 0, 13,137 have reviews = 0).
   - `20,978` is the total number of scraped merchant review bodies stored in the `reviews` table across 451 priority apps.
3. **Rated Apps (9,095 vs 8,339) Clarified**:
   - Exactly **8,339** apps (38.78%) have public ratings > 0 and reviews > 0.
   - The number 9,095 was an outdated mock placeholder; the database ground truth is **8,339**.
4. **Free Trial Penetration (31.4% vs 50.94%) Clarified**:
   - Exactly **10,953 apps (50.94%)** out of all 21,502 canonical apps have `free_trial_days > 0`.
   - 31.4% was a mock placeholder; the database ground truth is **50.94%**.
5. **Pricing Model Labeling (Custom / Enterprise vs Unknown)**:
   - Database value is literally `'unknown'` for 3,884 apps where pricing was not explicitly classified as free, freemium, or paid.
   - Consistent label across all pages: `Unknown / Unclassified` (explaining that these apps have custom pricing, unlisted plans, or are developer-contact tiers).
6. **Category Count Limit (100 vs 166)**:
   - Backend `PaginationParams` had a default `le=100`. For categories, we allow `limit=250` so all 166 categories load seamlessly into the searchable list.
7. **Paid Plan Tiers Discrepancy (38,046 vs 32,658)**:
   - **Discrepancy Cause**: The earlier figure of `38,046` was an estimated calculation of non-free app tiers from preliminary exploratory notes.
   - **Exact SQL Ground Truth**:
     - `SELECT count(*) FROM app_pricing_plans WHERE price_amount > 0` = **`32,658`** positive-price tiers (77.16%).
     - `SELECT count(*) FROM app_pricing_plans WHERE price_amount = 0` = **`9,668`** free tiers (22.84%), which belong to Free plans and Free tiers within Freemium apps (e.g. Judge.me's Forever Free tier, Klaviyo's Free plan).
     - Total structured plans in database = **`42,326`** (`32,658 + 9,668 = 42,326`, with exactly 0 NULL prices).
   - **Impact on Metrics**: All paid-tier pricing benchmarks (Median `$21.00`, Average `$66.89`, 25th percentile `$9.99`, 75th percentile `$59.00`) are calculated strictly using `WHERE price_amount > 0` across the **32,658** positive-price tiers. Including the 9,668 zero-dollar free tiers would distort paid subscription price distributions.
