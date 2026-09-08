/**
 * frontend/src/types.ts
 * TypeScript domain models for AppScout.
 */

export interface CategoryBadge {
  id: number;
  slug: string;
  name: string;
}

export interface PricingPlan {
  id: number;
  plan_name: string;
  price_amount: number | null;
  currency: string;
  billing_interval: string;
  free_trial_days: number | null;
  features: string[] | string | null;
}

export interface ReviewItem {
  id: number;
  app_slug: string;
  app_name: string;
  reviewer_name: string;
  reviewer_location?: string | null;
  time_spent_using_app?: string | null;
  rating: number;
  review_date: string;
  body: string;
}

export interface ReviewSummary {
  total_reviews_in_db: number;
  average_rating_in_db?: number | null;
  rating_breakdown?: Record<number, number>;
}

export interface AppItem {
  id: number;
  app_slug: string;
  app_name: string;
  app_url: string;
  developer_name?: string | null;
  description?: string | null;
  average_rating: number | null;
  review_count?: number | null;
  pricing_type: string;
  free_trial_days: number | null;
  categories: CategoryBadge[];
  pricing_plans?: PricingPlan[];
  review_summary?: ReviewSummary;
  recent_reviews?: ReviewItem[];
  has_stored_reviews?: boolean;
  stored_review_count?: number;
}

export interface EvidenceSummary {
  sufficient_count: number;
  limited_count: number;
  unreviewed_count: number;
}

export interface CategoryItem {
  id: number;
  slug: string;
  name: string;
  app_count: number;
  average_rating: number | null;
  average_review_count: number | null;
  pricing_breakdown?: Record<string, number>;
  evidence_summary?: EvidenceSummary;
  most_reviewed_apps?: AppItem[];
  highest_rated_apps?: AppItem[];
  lowest_rated_apps?: AppItem[];
  top_apps?: AppItem[];
}

export interface PlanExplorerItem {
  id: number;
  app_id: number;
  app_slug: string;
  app_name: string;
  plan_name: string;
  price_amount: number | null;
  currency: string;
  billing_interval: string;
  free_trial_days: number | null;
  features: string[] | null;
}
