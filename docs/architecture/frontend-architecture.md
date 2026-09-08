# AppScout Frontend Architecture

The AppScout frontend is a modern single-page web application built with **React 19**, **TypeScript**, and **Vite 8**, styled with custom design tokens and **Tailwind CSS**.

---

## 1. Application Layout & Navigation

The root layout in [`frontend/src/App.tsx`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/frontend/src/App.tsx) provides a responsive two-column dashboard:

```text
┌─────────────────┬────────────────────────────────────────────────────────┐
│ AppScout        │ Top Header: Current Page Title + Global Quick Nav      │
│                 ├────────────────────────────────────────────────────────┤
│ ❖ Home          │                                                        │
│ ❖ Overview      │ Active View Container                                  │
│ ❖ App Explorer  │ (Wrapped in React ErrorBoundary)                       │
│ ❖ App Categories│                                                        │
│ ❖ App Pricing   │                                                        │
│ ❖ App Reviews   │                                                        │
│                 │                                                        │
└─────────────────┴────────────────────────────────────────────────────────┘
  Shared Global AppDetailModal (mounted on root, accessible from all views)
```

* **Active View State**: Controlled via `activeView` (`home`, `overview`, `apps`, `categories`, `pricing`, `reviews`).
* **Cross-View Interactivity**:
  * Clicking an app row or card in any view opens the `AppDetailModal`.
  * Clicking *"View all reviews (N)"* inside the modal navigates to the **App Reviews** view pre-filtered to that application slug.
  * Clicking *"Explore all apps in Explorer"* in Category Intelligence navigates to the **App Explorer** pre-filtered to that category.

---

## 2. Views Breakdown

### 2.1 Home View ([`HomeView.tsx`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/frontend/src/views/HomeView.tsx))
* Introduces platform value proposition and highlights the 21,502 canonical app database.
* Provides direct quick-action cards to dive into Explorer, Categories, Pricing, and Reviews.

### 2.2 Overview View ([`OverviewView.tsx`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/frontend/src/views/OverviewView.tsx))
* Top KPIs: Total Active Apps, Categories, Pricing Plans, Stored Reviews, and Market Average Rating.
* **Review Availability & Evidence Section**: Proportional visual distribution bar showing:
  * Public Reviews Available ($38.8\%$) vs Zero Public Reviews ($61.2\%$).
  * Stored Reviews in Database ($738,101$ across $8,235$ apps).
  * Uncollected Discrepancy Apps ($104$ apps / $0.5\%$).
* Pricing model distribution and rating breakdown bar charts.

### 2.3 App Explorer View ([`AppExplorerView.tsx`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/frontend/src/views/AppExplorerView.tsx))
* Fast, debounced search across app names, developers, and descriptions.
* Multi-facet filtering: Category dropdown (166 items), Pricing Model (Paid, Freemium, Free, Unknown), Minimum Rating, Minimum Reviews, and Free Trial toggle.
* Pagination and sort order controls (`reviews`, `rating`, `name`, `newest`).

### 2.4 Category Intelligence View ([`CategoryIntelligenceView.tsx`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/frontend/src/views/CategoryIntelligenceView.tsx))
* **Single-Card Interface**: State A (category directory list) seamlessly transitions into State B (in-depth category intelligence) within the same unified card.
* Displays App Density, Average Star Rating, Average Reviews, Commercial Breakdown, and Review Evidence Distribution (Sufficient, Limited, Unreviewed).
* **Evidence-Backed Ranking Tabs**:
  * Most-Reviewed (sorted by review count).
  * Highest-Rated ($\ge 4.8$ rating, $\ge 20$ reviews).
  * Lowest-Rated ($< 4.0$ rating, $\ge 10$ reviews).
* **Ranking Count Dropdown**: `Show: Top 10`, `Top 20`, `Top 30`, `Top 50`.

### 2.5 Pricing Intelligence View ([`PricingIntelligenceView.tsx`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/frontend/src/views/PricingIntelligenceView.tsx))
* Monetization analytics across 42,326 structured plan tiers.
* Median paid price ($21.00/mo), average price ($66.89/mo), and 25th/75th percentiles.
* Searchable and filterable plan explorer table with billing cadence filters.

### 2.6 Reviews Explorer View ([`ReviewsExplorerView.tsx`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/frontend/src/views/ReviewsExplorerView.tsx))
* Interactive rating filters (5★, 4★, 3★, 2★, 1★).
* Full-text search over review body content.
* Expandable review cards with 280-character truncation and merchant location badges.

---

## 3. Global Components

* **`AppDetailModal.tsx`**: Deep modal showing developer info, Shopify App Store links, official descriptions, category tags, structured pricing tiers, and recent merchant reviews. Implements strict three-state review coverage logic (Cases A, B, and C).
* **`Badge.tsx`**: Standardized badges for pricing types (`free`, `freemium`, `paid`, `unknown`) and rating badges showing star counts and review numbers.
* **`KPICard.tsx`**: Metric presentation widget with icons, values, descriptions, and trend tags.
* **`StatusStates.tsx`**: `LoadingState` spinner, `ErrorState` with retry button, and `InfoTooltip` with hover explanation popovers.
* **`ErrorBoundary.tsx`**: React error boundary catching render exceptions without crashing the shell.

---

## 4. API Client & State Management

* **Client**: Centralized typed HTTP wrapper around the browser's native `fetch()` API in [`frontend/src/api/client.ts`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/frontend/src/api/client.ts).
* **Base URL**: Uses relative `/api` by default (automatically proxied by Vite in development to `http://127.0.0.1:8000`), or `VITE_API_URL` when explicitly configured in `frontend/.env`.
* **State Management**: Local state via `useState` and `useCallback` hooks. Deep detail calls are lazily fetched on user interaction.
* **Loading State Priority**: Views strictly evaluate:
  ```tsx
  {loading ? (
    <LoadingState message="..." />
  ) : error ? (
    <ErrorState message={error} onRetry={loadData} />
  ) : items.length > 0 ? (
    <RenderItems items={items} />
  ) : (
    <EmptyState />
  )}
  ```
  This eliminates layout flicker and premature empty states during network operations.
