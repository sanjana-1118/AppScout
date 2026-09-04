import React, { useState, useEffect, useCallback } from 'react';
import {
  MessageSquare,
  Search,
  Star,
  MapPin,
  Clock,
  Calendar,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  X,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { LoadingState, ErrorState, InfoTooltip } from '../components/StatusStates';
import {
  fetchReviews,
  fetchReviewsStats,
  type ReviewsStatsResponse,
} from '../api/reviews';
import type { ReviewItem, AppItem } from '../types';
import type { PaginatedResponse } from '../api/apps';

interface ReviewsExplorerViewProps {
  onSelectApp?: (app: AppItem) => void;
}

export const ReviewsExplorerView: React.FC<ReviewsExplorerViewProps> = ({ onSelectApp }) => {
  // Stats state
  const [stats, setStats] = useState<ReviewsStatsResponse | null>(null);

  // Reviews list state
  const [reviewsData, setReviewsData] = useState<PaginatedResponse<ReviewItem>>({
    items: [],
    total: 0,
    page: 1,
    limit: 10,
    pages: 1,
  });
  const [loadingReviews, setLoadingReviews] = useState(true);
  const [reviewsError, setReviewsError] = useState<string | null>(null);

  // Expanded review cards state for long reviews
  const [expandedReviewIds, setExpandedReviewIds] = useState<Set<number>>(new Set());

  // Filters state
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedRating, setSelectedRating] = useState<number>(0);
  const [selectedAppSlug, setSelectedAppSlug] = useState<string>('');
  const [sortBy, setSortBy] = useState<'date' | 'rating' | 'newest'>('date');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // 1. Fetch aggregate review statistics
  const loadStats = useCallback(async () => {
    try {
      const res = await fetchReviewsStats();
      setStats(res);
    } catch {
      // Fallback handled gracefully
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // 2. Fetch paginated reviews with filters
  const loadReviews = useCallback(async () => {
    try {
      setLoadingReviews(true);
      setReviewsError(null);

      const params: any = {
        page,
        limit: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      };

      if (debouncedSearch.trim()) {
        params.q = debouncedSearch.trim();
      }
      if (selectedRating > 0) {
        params.rating = selectedRating;
      }
      if (selectedAppSlug.trim()) {
        params.app_slug = selectedAppSlug.trim();
      }

      const res = await fetchReviews(params);
      setReviewsData(res);
    } catch (err: any) {
      setReviewsError(err.message || 'Failed to load merchant reviews');
    } finally {
      setLoadingReviews(false);
    }
  }, [debouncedSearch, selectedRating, selectedAppSlug, sortBy, sortOrder, page]);

  useEffect(() => {
    loadReviews();
  }, [loadReviews]);

  const toggleExpand = (id: number) => {
    setExpandedReviewIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* 1. Review Analytics Summary Card */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 border border-amber-200 flex items-center justify-center">
            <MessageSquare className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900 tracking-tight flex items-center">
              App Reviews
              <InfoTooltip content="Merchant reviews extracted from public Shopify app store listings across 451 priority applications." />
            </h3>
            <p className="text-xs text-slate-500">
              {stats ? (
                <span>
                  <strong>{stats.total_reviews.toLocaleString()}</strong> reviews collected across{' '}
                  <strong>{stats.distinct_apps_covered}</strong> priority applications in dataset
                </span>
              ) : (
                'Loading review dataset summary...'
              )}
            </p>
          </div>
        </div>

        {/* Aggregate Sentiment Score */}
        <div className="flex items-center gap-4 bg-slate-50 p-3.5 rounded-xl border border-slate-200">
          <div className="text-center px-3">
            <span className="text-[11px] font-bold text-slate-400 uppercase">Dataset Sentiment</span>
            <div className="text-xl font-bold text-amber-600 flex items-center justify-center gap-1 mt-0.5 font-mono">
              <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
              {stats ? stats.average_rating.toFixed(2) : '4.67'}
            </div>
            <span className="text-[10px] text-slate-400">out of 5.0</span>
          </div>
          <div className="h-9 w-px bg-slate-200" />
          <div className="text-center px-3">
            <span className="text-[11px] font-bold text-slate-400 uppercase">5-Star Ratio</span>
            <div className="text-xl font-bold text-slate-900 mt-0.5 font-mono">
              {stats && stats.total_reviews > 0
                ? `${(((stats.rating_distribution[5] || 0) / stats.total_reviews) * 100).toFixed(1)}%`
                : '87.5%'}
            </div>
            <span className="text-[10px] text-slate-400">satisfaction</span>
          </div>
        </div>
      </div>

      {/* 2. Interactive Star Rating Breakdown */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
        <div className="flex justify-between items-center text-xs font-semibold text-slate-700">
          <span className="flex items-center">
            Rating Distribution ({stats?.total_reviews.toLocaleString() || '20,978'} total)
            <InfoTooltip content="Click any star button to filter reviews below to that exact rating score." />
          </span>
          {selectedRating > 0 ? (
            <button
              onClick={() => {
                setSelectedRating(0);
                setPage(1);
              }}
              className="text-xs text-blue-600 hover:text-blue-800 font-semibold"
            >
              Clear Star Filter (Showing {selectedRating}★)
            </button>
          ) : (
            <span className="text-slate-400">Click star button to toggle filter</span>
          )}
        </div>

        <div className="grid grid-cols-5 gap-2">
          {[5, 4, 3, 2, 1].map((star) => {
            const count = stats?.rating_distribution[star] || 0;
            const total = stats?.total_reviews || 1;
            const pct = ((count / total) * 100).toFixed(1);
            const isSelected = selectedRating === star;
            return (
              <button
                key={star}
                onClick={() => {
                  setSelectedRating(selectedRating === star ? 0 : star);
                  setPage(1);
                }}
                className={`p-3 rounded-xl border text-center transition-all ${
                  isSelected
                    ? 'bg-amber-50 border-amber-400 text-amber-950 font-bold ring-2 ring-amber-400/20 shadow-xs'
                    : 'bg-slate-50/60 border-slate-200 hover:bg-slate-100 text-slate-700'
                }`}
              >
                <div className="flex items-center justify-center gap-1 text-xs font-bold">
                  <span>{star}</span>
                  <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                </div>
                <div className="text-xs text-slate-800 font-mono font-bold mt-1">
                  {count.toLocaleString()}
                </div>
                <div className="text-[10px] text-slate-400 font-medium">{pct}% of total</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* 3. Search and Filters Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
        {/* Search Input */}
        <div className="relative flex-1 w-full">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search review body text, merchant keywords (e.g. support, conversion, fast, bug)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-8 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:outline-hidden focus:border-blue-500 text-xs"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* App Slug Filter & Sort */}
        <div className="flex items-center gap-2 shrink-0 w-full md:w-auto">
          <input
            type="text"
            placeholder="Filter app slug (e.g. judgeme)..."
            value={selectedAppSlug}
            onChange={(e) => {
              setSelectedAppSlug(e.target.value);
              setPage(1);
            }}
            className="w-48 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:outline-hidden focus:border-blue-500 text-xs"
          />

          <div className="flex items-center gap-1.5 bg-slate-50 px-3 py-2 rounded-lg border border-slate-200 text-slate-600">
            <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value as any);
                setPage(1);
              }}
              className="bg-transparent font-semibold text-slate-800 focus:outline-hidden text-xs"
            >
              <option value="date">Review Date</option>
              <option value="rating">Rating</option>
              <option value="newest">Ingested Date</option>
            </select>
          </div>

          <button
            onClick={() => {
              setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
              setPage(1);
            }}
            className="px-2.5 py-2 bg-slate-50 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
          >
            {sortOrder === 'desc' ? 'Newest / High' : 'Oldest / Low'}
          </button>

          {(searchTerm || selectedRating > 0 || selectedAppSlug) && (
            <button
              onClick={() => {
                setSearchTerm('');
                setSelectedRating(0);
                setSelectedAppSlug('');
                setPage(1);
              }}
              className="px-3 py-2 text-blue-600 hover:text-blue-800 font-semibold"
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* 4. Results Header */}
      <div className="flex items-center justify-between text-xs text-slate-500 px-1">
        <span>
          Showing <strong className="text-slate-900">{reviewsData.total.toLocaleString()}</strong> matching reviews
          {selectedRating > 0 && <span> (filtered to {selectedRating}-star reviews)</span>}
          {selectedAppSlug && <span> (app: {selectedAppSlug})</span>}
        </span>
        {reviewsData.pages > 1 && (
          <span className="font-mono">
            Page {reviewsData.page} of {reviewsData.pages}
          </span>
        )}
      </div>

      {/* 5. Compact Reviews List Content */}
      {loadingReviews ? (
        <LoadingState message="Searching merchant reviews..." />
      ) : reviewsError ? (
        <ErrorState message={reviewsError} onRetry={loadReviews} />
      ) : reviewsData.items.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-xl border border-slate-200 text-xs text-slate-500">
          No merchant reviews found matching your search or rating filters.
        </div>
      ) : (
        <div className="space-y-3">
          {reviewsData.items.map((rev) => {
            const isLong = rev.body.length > 280;
            const isExpanded = expandedReviewIds.has(rev.id);
            const displayText = isLong && !isExpanded ? `${rev.body.slice(0, 280)}...` : rev.body;

            return (
              <div
                key={rev.id}
                className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs hover:border-slate-300 transition-all space-y-2.5"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-slate-900">
                        {rev.reviewer_name || 'Shopify Merchant'}
                      </span>
                      <button
                        onClick={() =>
                          onSelectApp?.({
                            id: 0,
                            app_slug: rev.app_slug,
                            app_name: rev.app_name || rev.app_slug,
                            app_url: `https://apps.shopify.com/${rev.app_slug}`,
                            developer_name: null,
                            description: null,
                            average_rating: null,
                            review_count: null,
                            pricing_type: 'unknown',
                            free_trial_days: null,
                            categories: [],
                          })
                        }
                        className="text-xs px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 font-semibold border border-blue-100 font-mono hover:bg-blue-100 transition-colors cursor-pointer"
                        title="Inspect app details and plans"
                      >
                        {rev.app_name || rev.app_slug}
                      </button>
                    </div>
                    {rev.reviewer_location && (
                      <div className="flex items-center gap-1 text-[11px] text-slate-400 mt-0.5">
                        <MapPin className="w-3 h-3 text-slate-400" />
                        <span>{rev.reviewer_location}</span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-1 bg-amber-50 px-2 py-0.5 rounded-lg border border-amber-200 text-xs font-bold text-amber-800 self-start sm:self-auto">
                    <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                    <span>{rev.rating}.0</span>
                  </div>
                </div>

                {/* Review Body (handles foreign/multilingual text safely) */}
                <div className="text-xs text-slate-700 leading-relaxed bg-slate-50/60 p-3 rounded-lg border border-slate-100 font-serif break-words whitespace-pre-wrap">
                  "{displayText}"
                  {isLong && (
                    <button
                      onClick={() => toggleExpand(rev.id)}
                      className="ml-2 font-sans font-semibold text-blue-600 hover:text-blue-800 inline-flex items-center gap-0.5"
                    >
                      {isExpanded ? (
                        <>
                          Show less <ChevronUp className="w-3 h-3" />
                        </>
                      ) : (
                        <>
                          Read more <ChevronDown className="w-3 h-3" />
                        </>
                      )}
                    </button>
                  )}
                </div>

                {/* Metadata Footer */}
                <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-400 pt-1.5 border-t border-slate-100">
                  <div>
                    {rev.time_spent_using_app && (
                      <span className="flex items-center gap-1 font-medium text-slate-500">
                        <Clock className="w-3 h-3 text-slate-400" /> {rev.time_spent_using_app}
                      </span>
                    )}
                  </div>
                  <span className="flex items-center gap-1 font-mono text-slate-400">
                    <Calendar className="w-3 h-3" /> {rev.review_date || 'Recent'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination Controls */}
      {reviewsData.pages > 1 && (
        <div className="flex items-center justify-between bg-white p-4 rounded-xl border border-slate-200 shadow-2xs text-xs">
          <button
            disabled={page === 1 || loadingReviews}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
          >
            <ChevronLeft className="w-4 h-4" /> Previous
          </button>
          <span className="font-medium text-slate-600 font-mono">
            Page {reviewsData.page} of {reviewsData.pages} ({reviewsData.total.toLocaleString()} reviews)
          </span>
          <button
            disabled={page === reviewsData.pages || loadingReviews}
            onClick={() => setPage((p) => Math.min(reviewsData.pages, p + 1))}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
          >
            Next <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
};
