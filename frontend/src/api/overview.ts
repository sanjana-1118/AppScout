/**
 * frontend/src/api/overview.ts
 * API calls for Home / Ecosystem Overview.
 */

import { apiClient } from './client';
import type { AppItem, CategoryItem } from '../types';

export interface StatCardData {
  label: string;
  value: number | string;
  formatted: string;
  description?: string;
}

export interface ReviewAvailability {
  total_active_apps: number;
  apps_with_public_reviews: number;
  apps_with_no_public_reviews: number;
  total_stored_reviews: number;
  apps_with_stored_reviews: number;
  uncollected_apps_count: number;
}

export interface OverviewResponse {
  summary: {
    total_apps: StatCardData;
    total_categories: StatCardData;
    total_pricing_plans: StatCardData;
    total_reviews: StatCardData;
    average_rating: StatCardData;
  };
  review_availability: ReviewAvailability;
  pricing_distribution: Record<string, number>;
  rating_distribution: Record<string, number>;
  top_categories: CategoryItem[];
  top_reviewed_apps: AppItem[];
  top_rated_apps: AppItem[];
}

export async function fetchOverview(): Promise<OverviewResponse> {
  return apiClient<OverviewResponse>('/overview');
}
