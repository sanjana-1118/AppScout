import React, { useState, useEffect, useCallback } from 'react';
import {
  Search,
  Filter,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  SlidersHorizontal,
  X,
} from 'lucide-react';
import type { AppItem, CategoryItem } from '../types';
import { PricingBadge, RatingBadge } from '../components/Badge';
import { LoadingState, ErrorState, InfoTooltip } from '../components/StatusStates';
import { fetchApps, type PaginatedResponse } from '../api/apps';
import { fetchCategories } from '../api/categories';
import {
  formatCategoryName,
  deduplicateAppCategories,
} from '../utils/formatters';

interface AppExplorerViewProps {
  onSelectApp: (app: AppItem) => void;
}

export const AppExplorerView: React.FC<AppExplorerViewProps> = ({ onSelectApp }) => {
  // Query parameters state
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedPricing, setSelectedPricing] = useState<string>('all');
  const [selectedMinRating, setSelectedMinRating] = useState<number>(0);
  const [selectedMinReviews, setSelectedMinReviews] = useState<number>(0);
  const [hasFreeTrialOnly, setHasFreeTrialOnly] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<'reviews' | 'rating' | 'name' | 'newest'>('reviews');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');
  const [page, setPage] = useState(1);
  const pageSize = 12;

  // Data states
  const [appsData, setAppsData] = useState<PaginatedResponse<AppItem> | null>(null);
  const [categoriesList, setCategoriesList] = useState<CategoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchTerm);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Load available categories for dropdown (load all 166)
  useEffect(() => {
    const loadCategories = async () => {
      try {
        const res = await fetchCategories({ limit: 200 });
        setCategoriesList(res.items);
      } catch (err) {
        console.error('Failed to load categories for dropdown', err);
      }
    };
    loadCategories();
  }, []);

  // Fetch apps from live FastAPI backend
  const loadApps = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params: any = {
        page,
        limit: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      };

      if (debouncedQuery.trim()) {
        params.q = debouncedQuery.trim();
      }
      if (selectedCategory !== 'all') {
        params.category = selectedCategory;
      }
      if (selectedPricing !== 'all') {
        params.pricing_type = selectedPricing;
      }
      if (selectedMinRating > 0) {
        params.min_rating = selectedMinRating;
      }
      if (selectedMinReviews > 0) {
        params.min_reviews = selectedMinReviews;
      }
      if (hasFreeTrialOnly) {
        params.has_free_trial = true;
      }

      const res = await fetchApps(params);
      setAppsData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load apps');
    } finally {
      setLoading(false);
    }
  }, [
    debouncedQuery,
    selectedCategory,
    selectedPricing,
    selectedMinRating,
    selectedMinReviews,
    hasFreeTrialOnly,
    sortBy,
    sortOrder,
    page,
  ]);

  useEffect(() => {
    loadApps();
  }, [loadApps]);

  const resetFilters = () => {
    setSearchTerm('');
    setSelectedCategory('all');
    setSelectedPricing('all');
    setSelectedMinRating(0);
    setSelectedMinReviews(0);
    setHasFreeTrialOnly(false);
    setSortBy('reviews');
    setSortOrder('desc');
    setPage(1);
  };

  const hasActiveFilters =
    searchTerm !== '' ||
    selectedCategory !== 'all' ||
    selectedPricing !== 'all' ||
    selectedMinRating > 0 ||
    selectedMinReviews > 0 ||
    hasFreeTrialOnly;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Search and Filters Bar */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row items-center gap-3">
          {/* Search Box */}
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search across 21k+ apps by name, developer, description (e.g. Klaviyo, reviews, inventory)..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 text-sm bg-slate-50 rounded-lg border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 focus:bg-white transition-all text-slate-900"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Sort Controls */}
          <div className="flex items-center gap-2 shrink-0 w-full md:w-auto">
            <div className="flex items-center gap-1.5 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 text-xs text-slate-600">
              <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
              <span>Sort:</span>
              <select
                value={sortBy}
                onChange={(e) => {
                  setSortBy(e.target.value as any);
                  setPage(1);
                }}
                className="bg-transparent font-semibold text-slate-900 focus:outline-hidden"
              >
                <option value="reviews">Public Review Count</option>
                <option value="rating">Average Rating</option>
                <option value="name">App Name</option>
                <option value="newest">Recently Discovered</option>
              </select>
            </div>
            <button
              onClick={() => {
                setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
                setPage(1);
              }}
              className="px-2.5 py-2 bg-slate-50 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
            >
              {sortOrder === 'desc' ? 'High → Low' : 'Low → High'}
            </button>
          </div>
        </div>

        {/* Filter Chips Bar */}
        <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-slate-100 text-xs">
          <div className="flex items-center gap-1 text-slate-500 font-semibold">
            <Filter className="w-3.5 h-3.5" />
            <span>Filters:</span>
          </div>

          {/* Category Filter */}
          <select
            value={selectedCategory}
            onChange={(e) => {
              setSelectedCategory(e.target.value);
              setPage(1);
            }}
            className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 focus:outline-hidden focus:border-blue-500 max-w-xs truncate"
          >
            <option value="all">All Categories ({categoriesList.length || 166})</option>
            {categoriesList.map((cat) => (
              <option key={cat.slug} value={cat.slug}>
                {formatCategoryName(cat.name, cat.slug)} ({cat.app_count})
              </option>
            ))}
          </select>

          {/* Pricing Model Filter */}
          <select
            value={selectedPricing}
            onChange={(e) => {
              setSelectedPricing(e.target.value);
              setPage(1);
            }}
            className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 focus:outline-hidden focus:border-blue-500"
          >
            <option value="all">All Pricing Models</option>
            <option value="paid">Paid</option>
            <option value="freemium">Freemium</option>
            <option value="free">Free</option>
            <option value="unknown">Unknown / Unclassified</option>
          </select>

          {/* Minimum Rating */}
          <select
            value={selectedMinRating}
            onChange={(e) => {
              setSelectedMinRating(Number(e.target.value));
              setPage(1);
            }}
            className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 focus:outline-hidden focus:border-blue-500"
          >
            <option value={0}>Any Rating</option>
            <option value={4.8}>★ 4.8 & above</option>
            <option value={4.5}>★ 4.5 & above</option>
            <option value={4.0}>★ 4.0 & above</option>
          </select>

          {/* Minimum Reviews */}
          <select
            value={selectedMinReviews}
            onChange={(e) => {
              setSelectedMinReviews(Number(e.target.value));
              setPage(1);
            }}
            className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 focus:outline-hidden focus:border-blue-500"
          >
            <option value={0}>Any Review Count</option>
            <option value={50}>50+ Reviews</option>
            <option value={500}>500+ Reviews</option>
            <option value={1000}>1,000+ Reviews</option>
            <option value={5000}>5,000+ Reviews</option>
          </select>

          {/* Free Trial Toggle */}
          <label className="flex items-center gap-1.5 cursor-pointer bg-slate-50 px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 transition-colors">
            <input
              type="checkbox"
              checked={hasFreeTrialOnly}
              onChange={(e) => {
                setHasFreeTrialOnly(e.target.checked);
                setPage(1);
              }}
              className="rounded text-blue-600 focus:ring-0"
            />
            <span className="text-slate-700 font-medium">Free Trial Only</span>
          </label>

          {/* Reset Filters */}
          {hasActiveFilters && (
            <button
              onClick={resetFilters}
              className="text-blue-600 hover:text-blue-800 font-semibold ml-auto flex items-center gap-1"
            >
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* Results Header */}
      <div className="flex items-center justify-between text-xs text-slate-500 px-1">
        <span>
          Showing <strong className="text-slate-900">{appsData?.total.toLocaleString() || 0}</strong> matching applications
          {' '}(across 21,502 Shopify apps)
          <InfoTooltip content="Each record represents a Shopify application in the dataset. Review counts reflect public Shopify listing reviews." />
        </span>
        {appsData && appsData.pages > 1 && (
          <span className="font-mono">
            Page {appsData.page} of {appsData.pages}
          </span>
        )}
      </div>

      {/* Content Area - Compact Card Layout */}
      {loading ? (
        <LoadingState message="Searching apps with current filters..." />
      ) : error ? (
        <ErrorState message={error} onRetry={loadApps} />
      ) : appsData && appsData.items.length > 0 ? (
        <div className="space-y-3">
          {appsData.items.map((app) => {
            const cleanCategories = deduplicateAppCategories(app.categories);
            return (
              <div
                key={app.id}
                onClick={() => onSelectApp(app)}
                className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs hover:border-blue-300 hover:shadow-xs transition-all cursor-pointer group"
              >
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <h4 className="text-sm font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                        {app.app_name}
                      </h4>
                      <PricingBadge type={app.pricing_type} />
                      {app.free_trial_days && (
                        <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">
                          {app.free_trial_days}-Day Trial
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-slate-500 mb-1.5">
                      Developer: <strong className="text-slate-700">{app.developer_name || 'Verified Developer'}</strong>
                    </p>

                    {app.description ? (
                      <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                        {app.description}
                      </p>
                    ) : (
                      <p className="text-xs text-slate-400 italic">No description available</p>
                    )}

                    {/* Deduplicated & Cleaned Category Badges */}
                    {cleanCategories.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 mt-2">
                        {cleanCategories.map((cat) => (
                          <span
                            key={cat.id}
                            className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-600 group-hover:bg-blue-50 group-hover:text-blue-700 transition-colors"
                          >
                            {cat.displayName}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Stats & Actions Side */}
                  <div className="flex md:flex-col items-center md:items-end justify-between shrink-0 pt-2 md:pt-0 border-t md:border-t-0 border-slate-100 gap-2">
                    <div className="text-right">
                      <RatingBadge
                        rating={app.average_rating}
                        reviewCount={app.review_count}
                        showReviewLabel
                      />
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectApp(app);
                      }}
                      className="px-3 py-1.5 bg-slate-100 group-hover:bg-blue-600 group-hover:text-white rounded-lg text-xs font-semibold text-slate-700 transition-all shadow-2xs"
                    >
                      Inspect Plans & Reviews →
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="p-12 text-center bg-white rounded-xl border border-slate-200">
          <SlidersHorizontal className="w-8 h-8 text-slate-300 mx-auto mb-3" />
          <h4 className="font-bold text-slate-700 text-sm">No applications found</h4>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            No applications match your current search and filter combination in the database.
          </p>
          <button
            onClick={resetFilters}
            className="mt-4 px-4 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 transition-colors"
          >
            Clear Filters
          </button>
        </div>
      )}

      {/* Pagination Controls */}
      {appsData && appsData.pages > 1 && (
        <div className="flex items-center justify-between bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <button
            disabled={page === 1 || loading}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4" /> Previous
          </button>
          <span className="text-xs font-medium text-slate-600">
            Page {appsData.page} of {appsData.pages} ({appsData.total.toLocaleString()} apps)
          </span>
          <button
            disabled={page === appsData.pages || loading}
            onClick={() => setPage((p) => Math.min(appsData.pages, p + 1))}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Next <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
};
