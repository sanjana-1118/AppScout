/**
 * frontend/src/api/pricing.ts
 * API calls for Pricing Intelligence and Plan Explorer.
 */

import { apiClient } from './client';
import type { PlanExplorerItem } from '../types';
import type { PaginatedResponse } from './apps';

export interface PricingModelStats {
  model: string;
  count: number;
  percentage: number;
}

export interface PriceAmountDistribution {
  min_price: number | null;
  max_price: number | null;
  avg_price: number | null;
  median_price: number | null;
  p25_price: number | null;
  p75_price: number | null;
}

export interface IntervalBreakdown {
  billing_interval: string;
  plan_count: number;
  percentage: number;
}

export interface FreeTrialStats {
  has_trial_count: number;
  no_trial_count: number;
  trial_percentage: number;
  popular_durations: Record<string, number>;
}

export interface PricingOverviewResponse {
  total_apps: number;
  total_pricing_plans: number;
  model_breakdown: PricingModelStats[];
  price_distribution: PriceAmountDistribution;
  interval_breakdown: IntervalBreakdown[];
  free_trial_stats: FreeTrialStats;
}

export interface PricingPlanQueryParams {
  q?: string;
  app_slug?: string;
  billing_interval?: string;
  min_price?: number;
  max_price?: number;
  has_free_trial?: boolean;
  sort_by?: 'price' | 'plan_name' | 'app' | 'newest';
  sort_order?: 'asc' | 'desc';
  page?: number;
  limit?: number;
}

export async function fetchPricingOverview(): Promise<PricingOverviewResponse> {
  return apiClient<PricingOverviewResponse>('/pricing/overview');
}

export async function fetchPricingPlans(
  params?: PricingPlanQueryParams
): Promise<PaginatedResponse<PlanExplorerItem>> {
  return apiClient<PaginatedResponse<PlanExplorerItem>>('/pricing/plans', undefined, params as any);
}
