import React, { useState, useEffect, useCallback } from 'react';
import {
  FolderTree,
  Search,
  Star,
  ArrowUpDown,
  ChevronRight,
  TrendingUp,
  Tag,
  Loader2,
  X,
} from 'lucide-react';
import type { CategoryItem, AppItem } from '../types';
import { PricingBadge, RatingBadge } from '../components/Badge';
import { InfoTooltip } from '../components/StatusStates';
import { fetchCategories, fetchCategoryDetail } from '../api/categories';
import { formatCategoryName } from '../utils/formatters';

interface CategoryIntelligenceViewProps {
  onSelectApp: (app: AppItem) => void;
}

export const CategoryIntelligenceView: React.FC<CategoryIntelligenceViewProps> = ({ onSelectApp }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [sortBy, setSortBy] = useState<'app_count' | 'name' | 'rating' | 'reviews'>('app_count');
  const [sortOrder] = useState<'desc' | 'asc'>('desc');

  // Categories list state
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const [totalCategoriesCount, setTotalCategoriesCount] = useState<number>(166);
  const [loadingCategories, setLoadingCategories] = useState(true);
  const [categoriesError, setCategoriesError] = useState<string | null>(null);

  // Selected category state
  const [selectedCategory, setSelectedCategory] = useState<CategoryItem | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
    }, 250);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Load detailed category intelligence when user clicks a category
  const loadCategoryDeepDetail = useCallback(async (cat: CategoryItem) => {
    setSelectedCategory(cat);
    try {
      setLoadingDetail(true);
      const detail = await fetchCategoryDetail(cat.slug || cat.id);
      setSelectedCategory(detail);
    } catch {
      // Keep existing category if deep detail fetch fails
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  // Fetch all 166 categories without artificial 100 cut-off
  const loadCategories = useCallback(async () => {
    try {
      setLoadingCategories(true);
      setCategoriesError(null);
      const res = await fetchCategories({
        q: debouncedSearch.trim() || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        limit: 200, // Load all 166 categories
      });
      setCategories(res.items);
      setTotalCategoriesCount(res.total);

      // Default select the first category if none selected
      if (!selectedCategory && res.items.length > 0) {
        loadCategoryDeepDetail(res.items[0]);
      }
    } catch (err: any) {
      setCategoriesError(err.message || 'Failed to load categories');
    } finally {
      setLoadingCategories(false);
    }
  }, [debouncedSearch, sortBy, sortOrder, selectedCategory, loadCategoryDeepDetail]);

  useEffect(() => {
    loadCategories();
  }, [loadCategories]);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Category Intelligence Intro Bar */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-100">
            <FolderTree className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-sm flex items-center">
              App Categories
              <InfoTooltip content="166 normalized Shopify categories organizing apps across the marketplace." />
            </h3>
            <p className="text-xs text-slate-500">
              Explore app counts, ratings, and pricing models across all 166 categories
            </p>
          </div>
        </div>

        {/* Search & Sort Controls */}
        <div className="flex items-center gap-3">
          <div className="relative w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search category name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-8 py-1.5 text-xs bg-slate-50 rounded-lg border border-slate-200 focus:outline-hidden focus:border-blue-500 text-slate-900"
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

          <div className="flex items-center gap-1.5 bg-slate-50 px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs text-slate-600">
            <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-transparent font-semibold text-slate-800 focus:outline-hidden text-xs"
            >
              <option value="app_count">App Density</option>
              <option value="rating">Highest Rated</option>
              <option value="reviews">Avg Public Reviews</option>
              <option value="name">Category Name</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Dual-Panel Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Category List (5 cols) */}
        <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between text-xs font-semibold text-slate-600">
            <span>
              {categories.length === totalCategoriesCount
                ? `All ${totalCategoriesCount} Categories`
                : `${categories.length} of ${totalCategoriesCount} Categories`}
            </span>
            <span>App Density</span>
          </div>

          {loadingCategories ? (
            <div className="p-12 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-blue-600" /> Loading categories...
            </div>
          ) : categoriesError ? (
            <div className="p-6 text-center text-xs text-red-600">
              {categoriesError}
            </div>
          ) : categories.length === 0 ? (
            <div className="p-12 text-center text-xs text-slate-400">
              No categories match your search.
            </div>
          ) : (
            <div className="divide-y divide-slate-100 max-h-[640px] overflow-y-auto">
              {categories.map((cat) => {
                const isSelected = selectedCategory?.id === cat.id;
                const cleanName = formatCategoryName(cat.name, cat.slug);
                return (
                  <div
                    key={cat.id}
                    onClick={() => loadCategoryDeepDetail(cat)}
                    className={`p-3.5 cursor-pointer transition-all flex items-center justify-between gap-3 ${
                      isSelected
                        ? 'bg-blue-50/90 border-l-4 border-blue-600 text-blue-950 font-semibold shadow-2xs'
                        : 'hover:bg-slate-50 text-slate-800'
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="text-xs font-bold truncate">{cleanName}</div>
                      <div className="flex items-center gap-2.5 text-[11px] text-slate-400 mt-0.5">
                        <span className="flex items-center gap-0.5">
                          <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
                          {cat.average_rating ? cat.average_rating.toFixed(2) : 'Unrated'}
                        </span>
                        <span>•</span>
                        <span>~{Math.round(cat.average_review_count || 0)} avg public reviews</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full font-mono font-bold ${
                          isSelected
                            ? 'bg-blue-600 text-white'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {cat.app_count.toLocaleString()}
                      </span>
                      <ChevronRight
                        className={`w-4 h-4 ${
                          isSelected ? 'text-blue-600' : 'text-slate-300'
                        }`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Category Deep-Dive (7 cols) */}
        <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6 min-h-[500px]">
          {selectedCategory ? (
            <>
              {/* Header of Selected Category */}
              <div className="border-b border-slate-100 pb-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-semibold text-blue-600 mb-1">
                    <Tag className="w-3.5 h-3.5" />
                    <span>Category Deep-Dive</span>
                  </div>
                  {loadingDetail && (
                    <span className="inline-flex items-center gap-1 text-[11px] text-blue-600 font-medium">
                      <Loader2 className="w-3 h-3 animate-spin" /> Fetching latest aggregates...
                    </span>
                  )}
                </div>
                <h3 className="text-xl font-bold text-slate-900 tracking-tight">
                  {formatCategoryName(selectedCategory.name, selectedCategory.slug)}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5 font-mono">
                  Taxonomy Slug: {selectedCategory.slug}
                </p>
              </div>

              {/* Aggregate KPI Badges */}
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 text-center">
                  <span className="text-[11px] font-bold text-slate-400 uppercase flex items-center justify-center gap-1">
                    App Density
                    <InfoTooltip content="Total active canonical applications cataloged under this specific category." />
                  </span>
                  <p className="text-2xl font-bold text-slate-900 mt-0.5 font-mono">
                    {selectedCategory.app_count.toLocaleString()}
                  </p>
                  <span className="text-[10px] text-slate-500">active applications</span>
                </div>
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 text-center">
                  <span className="text-[11px] font-bold text-slate-400 uppercase flex items-center justify-center gap-1">
                    Avg Rating
                    <InfoTooltip content="Average star rating across all rated applications in this category." />
                  </span>
                  <p className="text-2xl font-bold text-amber-600 mt-0.5 flex items-center justify-center gap-1 font-mono">
                    <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                    {selectedCategory.average_rating ? selectedCategory.average_rating.toFixed(2) : 'N/A'}
                  </p>
                  <span className="text-[10px] text-slate-500">out of 5.0 stars</span>
                </div>
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 text-center">
                  <span className="text-[11px] font-bold text-slate-400 uppercase flex items-center justify-center gap-1">
                    Avg Reviews
                    <InfoTooltip content="Average Public Shopify Review Count per app in this category listing." />
                  </span>
                  <p className="text-2xl font-bold text-slate-900 mt-0.5 font-mono">
                    {Math.round(selectedCategory.average_review_count || 0).toLocaleString()}
                  </p>
                  <span className="text-[10px] text-slate-500">public reviews per app</span>
                </div>
              </div>

              {/* Pricing Breakdown in this Category */}
              {selectedCategory.pricing_breakdown && (
                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50">
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3 flex items-center">
                    Category Commercial Breakdown
                    <InfoTooltip content="Pricing model distribution among apps cataloged in this category." />
                  </h4>
                  <div className="grid grid-cols-4 gap-2 text-center">
                    <div className="p-2.5 bg-white rounded-lg border border-slate-200/80">
                      <span className="text-[11px] text-slate-400 block font-semibold">Paid</span>
                      <span className="text-sm font-bold text-blue-600 font-mono">
                        {(selectedCategory.pricing_breakdown.paid || 0).toLocaleString()}
                      </span>
                    </div>
                    <div className="p-2.5 bg-white rounded-lg border border-slate-200/80">
                      <span className="text-[11px] text-slate-400 block font-semibold">Freemium</span>
                      <span className="text-sm font-bold text-emerald-600 font-mono">
                        {(selectedCategory.pricing_breakdown.freemium || 0).toLocaleString()}
                      </span>
                    </div>
                    <div className="p-2.5 bg-white rounded-lg border border-slate-200/80">
                      <span className="text-[11px] text-slate-400 block font-semibold">Free</span>
                      <span className="text-sm font-bold text-amber-600 font-mono">
                        {(selectedCategory.pricing_breakdown.free || 0).toLocaleString()}
                      </span>
                    </div>
                    <div className="p-2.5 bg-white rounded-lg border border-slate-200/80">
                      <span className="text-[11px] text-slate-400 block font-semibold truncate" title="Unknown / Unclassified">
                        Unknown / Unclassified
                      </span>
                      <span className="text-sm font-bold text-slate-600 font-mono">
                        {(selectedCategory.pricing_breakdown.unknown || 0).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Top Apps in this Category */}
              <div>
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-blue-600" />
                  Top Applications in Category
                  <InfoTooltip content="Applications ranked by highest Public Shopify Review Count cataloged within this specific category." />
                </h4>

                <div className="space-y-2.5">
                  {selectedCategory.top_apps && selectedCategory.top_apps.length > 0 ? (
                    selectedCategory.top_apps.map((app) => (
                      <div
                        key={app.id}
                        onClick={() => onSelectApp(app)}
                        className="p-3.5 rounded-xl border border-slate-200 bg-white hover:border-blue-300 hover:shadow-xs transition-all cursor-pointer flex items-center justify-between gap-3 group"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-sm text-slate-900 group-hover:text-blue-600 truncate">
                              {app.app_name}
                            </span>
                            <PricingBadge type={app.pricing_type} />
                          </div>
                          <p className="text-xs text-slate-500 mt-0.5 truncate">
                            {app.developer_name || 'Verified Developer'}
                          </p>
                        </div>

                        <div className="text-right shrink-0">
                          <RatingBadge
                            rating={app.average_rating}
                            reviewCount={app.review_count}
                            showReviewLabel
                          />
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="p-6 text-center border border-dashed border-slate-200 rounded-xl text-xs text-slate-400">
                      Loading top applications in this category...
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="p-16 text-center text-xs text-slate-400">
              Select any category from the left list to view category details.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
