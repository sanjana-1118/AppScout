/**
 * frontend/src/api/coverage.ts
 * API calls for Data Coverage, Pipeline Health, and Database Verification.
 */

import { apiClient } from './client';

export interface FieldFillRate {
  field_name: string;
  populated_count: number;
  total_count: number;
  fill_percentage: number;
}

export interface IngestionRunSummary {
  id: number;
  started_at: string | null;
  completed_at: string | null;
  status: string;
  apps_requested: number;
  apps_processed: number;
  apps_succeeded: number;
  apps_failed: number;
  apps_skipped: number;
}

export interface DataCoverageResponse {
  master_frontier_total: number;
  canonical_apps_in_db: number;
  rejected_inactive_apps: number;
  unaccounted_apps: number;
  reconciliation_status: string;
  total_categories: number;
  total_app_category_links: number;
  total_pricing_plans: number;
  apps_with_pricing: number;
  pricing_coverage_percentage: number;
  total_merchant_reviews: number;
  priority_apps_with_reviews: number;
  field_fill_rates: FieldFillRate[];
  recent_ingestion_runs: IngestionRunSummary[];
  integrity_status: Record<string, boolean>;
}

export interface HealthResponse {
  status: string;
  database_connected: boolean;
  postgres_version: string | null;
  timestamp: string;
}

export async function fetchDataCoverage(): Promise<DataCoverageResponse> {
  return apiClient<DataCoverageResponse>('/coverage');
}

export async function fetchHealth(): Promise<HealthResponse> {
  return apiClient<HealthResponse>('/health');
}
