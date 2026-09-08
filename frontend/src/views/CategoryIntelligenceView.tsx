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
  ArrowRight,
  ArrowLeft,
  ShieldCheck,
  Award,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import type { CategoryItem, AppItem } from '../types';
import { PricingBadge, RatingBadge } from '../components/Badge';
import { InfoTooltip } from '../components/StatusStates';
import { fetchCategories, fetchCategoryDetail } from '../api/categories';
import { formatCategoryName } from '../utils/formatters';

interface CategoryIntelligenceViewProps {
  onSelectApp: (app: AppItem) => void;
  onExploreCategory?: (categorySlug: string) => void;
}

export const CategoryIntelligenceView: React.FC<CategoryIntelligenceViewProps> = ({
  onSelectApp,
  onExploreCategory,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [sortBy, setSortBy] = useState<'app_count' | 'name' | 'rating' | 'reviews'>('app_count');
  const [sortOrder] = useState<'desc' | 'asc'>('desc');

  // Categories list state
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const [totalCategoriesCount, setTotalCategoriesCount] = useState<number>(166);
  const [loadingCategories, setLoadingCategories] = useState(true);
  const [categoriesError, setCategoriesError] = useState<string | null>(null);

  // Selected category state (null = State A: Category list; not null = State B: Selected category)
  const [selectedCategory, setSelectedCategory] = useState<CategoryItem | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Active ranking tab: 'most_reviewed' | 'highest_rated' | 'lowest_rated'
  const [activeRankingTab, setActiveRankingTab] = useState<'most_reviewed' | 'highest_rated' | 'lowest_rated'>('most_reviewed');

  // Ranking count selector: Top 10 (default), Top 20, Top 30, Top 50
  const [rankingLimit, setRankingLimit] = useState<number>(10);

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
      const detail = await fetchCategoryDetail(cat.slug || cat.id, 50);
      setSelectedCategory(detail);
    } catch {
      // Keep existing category if deep detail fetch fails
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  // Fetch all 166 categories without artificial cut-off
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
    } catch (err: any) {
      setCategoriesError(err.message || 'Failed to load categories');
    } finally {
      setLoadingCategories(false);
    }
  }, [debouncedSearch, sortBy, sortOrder]);

  useEffect(() => {
    loadCategories();
  }, [loadCategories]);

  // Helper for rendering review evidence badge
  const renderEvidenceBadge = (reviewCount?: number | null) => {
    const count = reviewCount ?? 0;
    if (count >= 20) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <ShieldCheck className="w-3 h-3 text-emerald-600" />
          Sufficient Evidence
        </span>
      );
    } else if (count >= 1) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
          <HelpCircle className="w-3 h-3 text-amber-600" />
          Limited Evidence
        </span>
      );
    } else {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
          Unreviewed on Shopify
        </span>
      );
    }
  };

  // Determine which apps list to show based on active ranking tab
  const getTabApps = () => {
    if (!selectedCategory) return [];
    if (activeRankingTab === 'most_reviewed') {
      return selectedCategory.most_reviewed_apps || selectedCategory.top_apps || [];
    }
    if (activeRankingTab === 'highest_rated') {
      return selectedCategory.highest_rated_apps || [];
    }
    if (activeRankingTab === 'lowest_rated') {
      return selectedCategory.lowest_rated_apps || [];
    }
    return [];
  };

  const currentTabApps = getTabApps();
  const displayedApps = currentTabApps.slice(0, rankingLimit);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Single Unified Categories Container */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {!selectedCategory ? (
          /* =========================================================================
             STATE A: CATEGORY LIST
             ========================================================================= */
          <div className="p-6 space-y-6">
            {/* Header & Controls */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-100">
              <div className="flex items-center gap-3.5">
                <div className="p-3 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100/80 shrink-0">
                  <FolderTree className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-slate-900 flex items-center gap-1.5">
                    App Categories
                    <InfoTooltip content="166 normalized Shopify categories organizing apps across the marketplace." />
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Explore app counts, ratings, pricing models, and market intelligence across all 166 categories
                  </p>
                </div>
              </div>

              {/* Search & Sort Controls */}
              <div className="flex items-center gap-3 flex-wrap sm:flex-nowrap">
                <div className="relative w-full sm:w-64">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Search category name..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-9 pr-8 py-2 text-xs bg-slate-50 rounded-xl border border-slate-200 focus:outline-hidden focus:border-blue-500 text-slate-900 transition-colors"
                  />
                  {searchTerm && (
                    <button
                      onClick={() => setSearchTerm('')}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                <div className="flex items-center gap-1.5 bg-slate-50 px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-600 shrink-0">
                  <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as any)}
                    className="bg-transparent font-semibold text-slate-800 focus:outline-hidden text-xs cursor-pointer"
                  >
                    <option value="app_count">App Density</option>
                    <option value="rating">Highest Rated</option>
                    <option value="reviews">Avg Public Reviews</option>
                    <option value="name">Category Name</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Sub-header counter & guide */}
            <div className="flex items-center justify-between text-xs text-slate-500 px-1">
              <span className="font-semibold text-slate-700">
                {categories.length === totalCategoriesCount
                  ? `All ${totalCategoriesCount} Categories`
                  : `${categories.length} of ${totalCategoriesCount} Categories`}
              </span>
              <span className="hidden sm:inline text-slate-400">
                Click any category to inspect category intelligence and app rankings
              </span>
            </div>

            {/* Categories List */}
            {loadingCategories ? (
              <div className="p-16 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-blue-600" /> Loading category directory...
              </div>
            ) : categoriesError ? (
              <div className="p-8 text-center text-xs text-red-600">
                {categoriesError}
              </div>
            ) : categories.length === 0 ? (
              <div className="p-16 text-center text-xs text-slate-400">
                No categories match your search.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[720px] overflow-y-auto pr-1">
                {categories.map((cat) => {
                  const cleanName = formatCategoryName(cat.name, cat.slug);
                  return (
                    <div
                      key={cat.id}
                      onClick={() => loadCategoryDeepDetail(cat)}
                      className="p-4 rounded-xl border border-slate-200/80 bg-white hover:border-blue-300 hover:bg-blue-50/30 hover:shadow-xs transition-all cursor-pointer flex items-center justify-between gap-4 group"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-bold text-slate-900 group-hover:text-blue-600 truncate transition-colors">
                          {cleanName}
                        </div>
                        <div className="flex items-center gap-2.5 text-xs text-slate-400 mt-1">
                          <span className="flex items-center gap-1 font-semibold text-slate-700">
                            <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                            {cat.average_rating ? cat.average_rating.toFixed(2) : 'Unrated'}
                          </span>
                          <span>•</span>
                          <span>~{Math.round(cat.average_review_count || 0)} avg reviews</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2.5 shrink-0">
                        <span className="text-xs px-2.5 py-1 rounded-lg font-mono font-bold bg-slate-100 text-slate-700 group-hover:bg-blue-100 group-hover:text-blue-800 transition-colors">
                          {cat.app_count.toLocaleString()} apps
                        </span>
                        <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all" />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ) : (
          /* =========================================================================
             STATE B: SELECTED CATEGORY (Replaces list in the exact same card)
             ========================================================================= */
          <div className="p-6 space-y-6">
            {/* Back to Categories Bar & Actions */}
            <div className="flex items-center justify-between pb-5 border-b border-slate-100 gap-4 flex-wrap">
              <button
                onClick={() => setSelectedCategory(null)}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border border-slate-200 bg-slate-50 text-xs font-bold text-slate-700 hover:bg-slate-100 hover:text-slate-900 hover:border-slate-300 transition-all cursor-pointer shadow-2xs group"
              >
                <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
                <span>Back to Categories</span>
              </button>

              <div className="flex items-center gap-3">
                {loadingDetail && (
                  <span className="inline-flex items-center gap-1 text-[11px] text-blue-600 font-medium">
                    <Loader2 className="w-3 h-3 animate-spin" /> Fetching category intelligence...
                  </span>
                )}
                <button
                  onClick={() => onExploreCategory?.(selectedCategory.slug)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-50 text-blue-700 hover:bg-blue-100 hover:text-blue-800 rounded-xl text-xs font-semibold transition-all border border-blue-200 cursor-pointer shadow-2xs group"
                  title={`Explore all ${selectedCategory.app_count} apps in App Explorer`}
                >
                  <span>Explore all apps in Explorer</span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                </button>
              </div>
            </div>

            {/* Selected Category Header & Short Overview */}
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-semibold text-blue-600">
                <Tag className="w-3.5 h-3.5" />
                <span>Category Intelligence</span>
              </div>
              <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
                {formatCategoryName(selectedCategory.name, selectedCategory.slug)}
              </h2>
              <p className="text-xs text-slate-500">
                Official Shopify taxonomy category cataloging {selectedCategory.app_count.toLocaleString()} active applications across the ecosystem. Taxonomy slug: <span className="font-mono text-slate-700 font-medium">{selectedCategory.slug}</span>
              </p>
            </div>

            {/* Aggregate KPI Badges */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="p-4 bg-slate-50/80 rounded-xl border border-slate-200/80 text-center">
                <span className="text-[11px] font-bold text-slate-400 uppercase flex items-center justify-center gap-1">
                  App Density
                  <InfoTooltip content="Total active canonical applications cataloged under this specific category." />
                </span>
                <p className="text-2xl font-bold text-slate-900 mt-1 font-mono">
                  {selectedCategory.app_count.toLocaleString()}
                </p>
                <span className="text-[10px] text-slate-500">active applications</span>
              </div>
              <div className="p-4 bg-slate-50/80 rounded-xl border border-slate-200/80 text-center">
                <span className="text-[11px] font-bold text-slate-400 uppercase flex items-center justify-center gap-1">
                  Avg Rating
                  <InfoTooltip content="Average star rating across all rated applications in this category." />
                </span>
                <p className="text-2xl font-bold text-amber-600 mt-1 flex items-center justify-center gap-1 font-mono">
                  <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                  {selectedCategory.average_rating ? selectedCategory.average_rating.toFixed(2) : 'N/A'}
                </p>
                <span className="text-[10px] text-slate-500">out of 5.0 stars</span>
              </div>
              <div className="p-4 bg-slate-50/80 rounded-xl border border-slate-200/80 text-center">
                <span className="text-[11px] font-bold text-slate-400 uppercase flex items-center justify-center gap-1">
                  Avg Reviews
                  <InfoTooltip content="Average Public Shopify Review Count per app in this category listing." />
                </span>
                <p className="text-2xl font-bold text-slate-900 mt-1 font-mono">
                  {Math.round(selectedCategory.average_review_count || 0).toLocaleString()}
                </p>
                <span className="text-[10px] text-slate-500">public reviews per app</span>
              </div>
            </div>

            {/* Review Evidence Distribution */}
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center">
                  Review Evidence Distribution
                  <InfoTooltip content="Breakdown of apps by public review volume: Sufficient (>=20 reviews), Limited (1-19 reviews), and Unreviewed (0 reviews)." />
                </h4>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-center">
                <div className="p-3 bg-white rounded-lg border border-emerald-100">
                  <span className="text-[11px] font-semibold text-emerald-700 block">Sufficient Evidence</span>
                  <span className="text-base font-bold text-slate-900 font-mono">
                    {(selectedCategory.evidence_summary?.sufficient_count ?? 0).toLocaleString()}
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">
                    &ge; 20 reviews ({selectedCategory.app_count > 0 ? `${(((selectedCategory.evidence_summary?.sufficient_count ?? 0) / selectedCategory.app_count) * 100).toFixed(1)}%` : '0%'})
                  </span>
                </div>
                <div className="p-3 bg-white rounded-lg border border-amber-100">
                  <span className="text-[11px] font-semibold text-amber-700 block">Limited Evidence</span>
                  <span className="text-base font-bold text-slate-900 font-mono">
                    {(selectedCategory.evidence_summary?.limited_count ?? 0).toLocaleString()}
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">
                    1–19 reviews ({selectedCategory.app_count > 0 ? `${(((selectedCategory.evidence_summary?.limited_count ?? 0) / selectedCategory.app_count) * 100).toFixed(1)}%` : '0%'})
                  </span>
                </div>
                <div className="p-3 bg-white rounded-lg border border-slate-200">
                  <span className="text-[11px] font-semibold text-slate-600 block">Unreviewed on Shopify</span>
                  <span className="text-base font-bold text-slate-900 font-mono">
                    {(selectedCategory.evidence_summary?.unreviewed_count ?? 0).toLocaleString()}
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">
                    0 reviews ({selectedCategory.app_count > 0 ? `${(((selectedCategory.evidence_summary?.unreviewed_count ?? 0) / selectedCategory.app_count) * 100).toFixed(1)}%` : '0%'})
                  </span>
                </div>
              </div>
            </div>

            {/* Pricing Breakdown in this Category */}
            {selectedCategory.pricing_breakdown && (
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50">
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3 flex items-center">
                  Category Commercial Breakdown
                  <InfoTooltip content="Pricing model distribution among apps cataloged in this category." />
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
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
                      Unknown
                    </span>
                    <span className="text-sm font-bold text-slate-600 font-mono">
                      {(selectedCategory.pricing_breakdown.unknown || 0).toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* App Comparison Tabs */}
            <div className="space-y-4 pt-2">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-200 pb-2 gap-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <button
                    onClick={() => setActiveRankingTab('most_reviewed')}
                    className={`px-3 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                      activeRankingTab === 'most_reviewed'
                        ? 'bg-blue-600 text-white shadow-xs'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    <TrendingUp className="w-3.5 h-3.5" />
                    <span>Most-Reviewed</span>
                    <span
                      className={`ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                        activeRankingTab === 'most_reviewed'
                          ? 'bg-blue-700 text-white'
                          : 'bg-slate-200 text-slate-700'
                      }`}
                    >
                      {Math.min(rankingLimit, (selectedCategory.most_reviewed_apps || selectedCategory.top_apps || []).length)}
                    </span>
                  </button>

                  <button
                    onClick={() => setActiveRankingTab('highest_rated')}
                    className={`px-3 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                      activeRankingTab === 'highest_rated'
                        ? 'bg-emerald-600 text-white shadow-xs'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    <Award className="w-3.5 h-3.5" />
                    <span>Highest-Rated</span>
                    <span
                      className={`ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                        activeRankingTab === 'highest_rated'
                          ? 'bg-emerald-700 text-white'
                          : 'bg-slate-200 text-slate-700'
                      }`}
                    >
                      {Math.min(rankingLimit, (selectedCategory.highest_rated_apps || []).length)}
                    </span>
                  </button>

                  <button
                    onClick={() => setActiveRankingTab('lowest_rated')}
                    className={`px-3 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                      activeRankingTab === 'lowest_rated'
                        ? 'bg-amber-600 text-white shadow-xs'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>Lowest-Rated</span>
                    <span
                      className={`ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                        activeRankingTab === 'lowest_rated'
                          ? 'bg-amber-700 text-white'
                          : 'bg-slate-200 text-slate-700'
                      }`}
                    >
                      {Math.min(rankingLimit, (selectedCategory.lowest_rated_apps || []).length)}
                    </span>
                  </button>
                </div>

                {/* Show Ranking Count Dropdown */}
                <div className="flex items-center gap-2 shrink-0">
                  <label htmlFor="ranking-limit-select" className="text-xs font-semibold text-slate-600">
                    Show:
                  </label>
                  <select
                    id="ranking-limit-select"
                    value={rankingLimit}
                    onChange={(e) => setRankingLimit(Number(e.target.value))}
                    className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-800 focus:outline-hidden focus:border-blue-500 cursor-pointer shadow-2xs"
                  >
                    <option value={10}>Top 10</option>
                    <option value={20}>Top 20</option>
                    <option value={30}>Top 30</option>
                    <option value={50}>Top 50</option>
                  </select>
                </div>
              </div>

              {/* Tab Context Explanation Callouts */}
              {activeRankingTab === 'most_reviewed' && (
                <div className="p-3 bg-blue-50/70 border border-blue-200/80 rounded-xl text-xs text-blue-900 flex items-start gap-2.5">
                  <TrendingUp className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold block">Market-Presence Ranking</span>
                    <span className="text-blue-800 text-[11px]">
                      Shows established apps with the highest public review volume. This is a <strong>market-presence/popularity ranking, not a quality ranking</strong>.
                    </span>
                  </div>
                </div>
              )}

              {activeRankingTab === 'highest_rated' && (
                <div className="p-3 bg-emerald-50/70 border border-emerald-200/80 rounded-xl text-xs text-emerald-900 flex items-start gap-2.5">
                  <Award className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold block">Highest-Rated Evidence Cohort</span>
                    <span className="text-emerald-800 text-[11px]">
                      Apps with ratings of 4.8 or higher and at least 20 public reviews. Sorted by rating descending, then review count descending.
                    </span>
                  </div>
                </div>
              )}

              {activeRankingTab === 'lowest_rated' && (
                <div className="p-3 bg-amber-50/70 border border-amber-200/80 rounded-xl text-xs text-amber-900 flex items-start gap-2.5">
                  <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold block">Lowest-Rated Established Cohort</span>
                    <span className="text-amber-800 text-[11px]">
                      Apps with ratings below 4.0 and at least 10 public reviews. Sorted by rating ascending, then review count descending.
                    </span>
                  </div>
                </div>
              )}

              {/* Dynamic ranking count status indicator */}
              {displayedApps.length > 0 && (
                <div className="text-xs text-slate-500 font-medium px-1">
                  Showing the top {displayedApps.length} eligible apps in this category.
                </div>
              )}

              {/* Apps List / Empty States */}
              <div className="space-y-2.5">
                {displayedApps.length > 0 ? (
                  <>
                    {displayedApps.map((app, index) => (
                      <div
                        key={app.id}
                        onClick={() => onSelectApp(app)}
                        className="p-3.5 rounded-xl border border-slate-200 bg-white hover:border-blue-300 hover:shadow-xs transition-all cursor-pointer flex items-center justify-between gap-3 group"
                      >
                        <div className="flex items-center gap-3 min-w-0 flex-1">
                          <span className="w-6 text-center font-mono font-bold text-xs text-slate-400 group-hover:text-blue-600">
                            #{index + 1}
                          </span>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-bold text-sm text-slate-900 group-hover:text-blue-600 truncate">
                                {app.app_name}
                              </span>
                              <PricingBadge type={app.pricing_type} />
                              {renderEvidenceBadge(app.review_count)}
                              {app.free_trial_days && app.free_trial_days > 0 ? (
                                <span className="text-[10px] font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md">
                                  {app.free_trial_days}d trial
                                </span>
                              ) : null}
                            </div>
                            <p className="text-xs text-slate-500 mt-0.5 truncate">
                              {app.developer_name || 'Verified Developer'}
                            </p>
                          </div>
                        </div>

                        <div className="text-right shrink-0">
                          <RatingBadge
                            rating={app.average_rating}
                            reviewCount={app.review_count}
                            showReviewLabel
                          />
                        </div>
                      </div>
                    ))}
                    <div className="pt-2 text-center text-xs text-slate-400 font-medium">
                      Showing the top {displayedApps.length} eligible apps in this category.
                    </div>
                  </>
                ) : (
                  <div className="p-8 text-center border border-dashed border-slate-200 rounded-xl text-xs bg-slate-50/50">
                    {activeRankingTab === 'highest_rated' ? (
                      <div>
                        <Award className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                        <p className="font-semibold text-slate-700">
                          No highest-rated apps meet the current evidence threshold in this category.
                        </p>
                        <p className="text-[11px] text-slate-400 mt-1">
                          Requires a rating of 4.8+ and at least 20 public reviews.
                        </p>
                      </div>
                    ) : activeRankingTab === 'lowest_rated' ? (
                      <div>
                        <AlertCircle className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                        <p className="font-semibold text-slate-700">
                          No established low-rated apps identified in this category.
                        </p>
                        <p className="text-[11px] text-slate-400 mt-1">
                          Requires a rating below 4.0 and at least 10 public reviews.
                        </p>
                      </div>
                    ) : (
                      <div>
                        <TrendingUp className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                        <p className="font-semibold text-slate-700">
                          No reviewed applications found in this category.
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

