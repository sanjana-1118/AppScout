/**
 * frontend/src/api/reviews.ts
 * API calls for Merchant Reviews Explorer and sentiment analytics.
 */

import { apiClient } from './client';
import type { ReviewItem } from '../types';
import type { PaginatedResponse } from './apps';

export interface ReviewsStatsResponse {
  total_reviews: number;
  distinct_apps_covered: number;
  average_rating: number;
  rating_distribution: Record<string, number>;
}

export interface ReviewQueryParams {
  q?: string;
  app_slug?: string;
  rating?: number;
  sort_by?: 'date' | 'rating' | 'newest';
  sort_order?: 'asc' | 'desc';
  page?: number;
  limit?: number;
}

export async function fetchReviews(
  params?: ReviewQueryParams
): Promise<PaginatedResponse<ReviewItem>> {
  return apiClient<PaginatedResponse<ReviewItem>>('/reviews', undefined, params as any);
}

export async function fetchReviewsStats(): Promise<ReviewsStatsResponse> {
  return apiClient<ReviewsStatsResponse>('/reviews/stats');
}
