/**
 * frontend/src/api/categories.ts
 * API calls for Category Taxonomy Intelligence.
 */

import { apiClient } from './client';
import type { CategoryItem } from '../types';
import type { PaginatedResponse } from './apps';

export interface CategoryQueryParams {
  q?: string;
  sort_by?: 'app_count' | 'name' | 'rating' | 'reviews';
  sort_order?: 'asc' | 'desc';
  page?: number;
  limit?: number;
}

export async function fetchCategories(
  params?: CategoryQueryParams
): Promise<PaginatedResponse<CategoryItem>> {
  return apiClient<PaginatedResponse<CategoryItem>>('/categories', undefined, params as any);
}

export async function fetchCategoryDetail(slugOrId: string | number): Promise<CategoryItem> {
  return apiClient<CategoryItem>(`/categories/${slugOrId}`);
}
