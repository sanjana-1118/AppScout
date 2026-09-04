/**
 * frontend/src/api/apps.ts
 * API calls for App Explorer and App Details.
 */

import { apiClient } from './client';
import type { AppItem } from '../types';

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface AppQueryParams {
  q?: string;
  category?: string;
  pricing_type?: string;
  min_rating?: number;
  max_rating?: number;
  min_reviews?: number;
  max_reviews?: number;
  has_free_trial?: boolean;
  sort_by?: 'reviews' | 'rating' | 'name' | 'newest' | 'pricing';
  sort_order?: 'asc' | 'desc';
  page?: number;
  limit?: number;
}

export async function fetchApps(params?: AppQueryParams): Promise<PaginatedResponse<AppItem>> {
  return apiClient<PaginatedResponse<AppItem>>('/apps', undefined, params as any);
}

export async function fetchAppDetail(slugOrId: string | number): Promise<AppItem> {
  return apiClient<AppItem>(`/apps/${slugOrId}`);
}
