/**
 * frontend/src/api/client.ts
 * Base HTTP client for communicating with the AppScout FastAPI backend.
 */

// Uses VITE_API_URL if configured, otherwise defaults to relative /api (handled by Vite proxy in dev or reverse proxy in prod)
const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') || '/api';

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export async function apiClient<T>(
  endpoint: string,
  options?: RequestInit,
  params?: Record<string, string | number | boolean | null | undefined>
): Promise<T> {
  let url = `${API_BASE}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let errorData: any = null;
    try {
      errorData = await response.json();
    } catch {
      // response wasn't JSON
    }
    const message =
      errorData?.detail || `API request failed with status ${response.status} (${response.statusText})`;
    throw new ApiError(message, response.status, errorData);
  }

  return (await response.json()) as T;
}
