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
  recent_reviews?: ReviewItem[];
}

export interface CategoryItem {
  id: number;
  slug: string;
  name: string;
  app_count: number;
  average_rating: number | null;
  average_review_count: number | null;
  pricing_breakdown?: Record<string, number>;
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
