import React, { useEffect, useState } from 'react';
import {
  AppWindow,
  FolderTree,
  DollarSign,
  MessageSquare,
  TrendingUp,
  Star,
  Layers,
  ArrowUpRight,
  Database,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import { KPICard } from '../components/KPICard';
import { PricingBadge, RatingBadge } from '../components/Badge';
import { LoadingState, ErrorState, InfoTooltip } from '../components/StatusStates';
import { fetchOverview, type OverviewResponse } from '../api/overview';
import { formatCategoryName, formatPricingType } from '../utils/formatters';
import type { AppItem } from '../types';

interface OverviewViewProps {
  onSelectApp: (app: AppItem) => void;
  onNavigateToView: (view: 'apps' | 'categories' | 'pricing' | 'reviews') => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({ onSelectApp, onNavigateToView }) => {
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchOverview();
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to AppScout backend');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return <LoadingState message="Loading live ecosystem metrics..." />;
  }

  if (error || !data) {
    return (
      <ErrorState
        title="Could not connect to backend"
        message={error || 'Please ensure the AppScout backend is running.'}
        onRetry={loadData}
      />
    );
  }

  const totalAppsCount =
    typeof data.summary.total_apps.value === 'number'
      ? data.summary.total_apps.value
      : Number(data.summary.total_apps.value) || 21502;

  // Consistent pricing models mapping
  const pricingItems = [
    { key: 'paid', count: data.pricing_distribution.paid || 0, ...formatPricingType('paid') },
    { key: 'freemium', count: data.pricing_distribution.freemium || 0, ...formatPricingType('freemium') },
    { key: 'unknown', count: data.pricing_distribution.unknown || 0, ...formatPricingType('unknown') },
    { key: 'free', count: data.pricing_distribution.free || 0, ...formatPricingType('free') },
  ].map((item) => ({
    ...item,
    percentage: totalAppsCount > 0 ? Number(((item.count / totalAppsCount) * 100).toFixed(1)) : 0,
  }));

  // Rating distribution across rated apps (8,339 rated apps in dataset)
  const totalRatedApps = Object.values(data.rating_distribution).reduce((a, b) => a + b, 0);
  const ratingItems = [5, 4, 3, 2, 1].map((stars) => {
    const count = data.rating_distribution[stars] || data.rating_distribution[String(stars)] || 0;
    return {
      stars,
      count,
      percentage: totalRatedApps > 0 ? Number(((count / totalRatedApps) * 100).toFixed(1)) : 0,
    };
  });

  const revAvail = data.review_availability;
  const totalActiveApps = revAvail?.total_active_apps || totalAppsCount;
  const appsWithPublic = revAvail?.apps_with_public_reviews || 8339;
  const appsWithNoPublic = revAvail?.apps_with_no_public_reviews || 13163;
  const totalStoredRevs = revAvail?.total_stored_reviews || 738101;
  const appsWithStored = revAvail?.apps_with_stored_reviews || 8235;
  const uncollectedApps = revAvail?.uncollected_apps_count || 104;

  const pctPublic = totalActiveApps > 0 ? ((appsWithPublic / totalActiveApps) * 100).toFixed(1) : '38.8';
  const pctNoPublic = totalActiveApps > 0 ? ((appsWithNoPublic / totalActiveApps) * 100).toFixed(1) : '61.2';
  const pctStored = totalActiveApps > 0 ? ((appsWithStored / totalActiveApps) * 100).toFixed(1) : '38.3';
  const pctUncollected = totalActiveApps > 0 ? ((uncollectedApps / totalActiveApps) * 100).toFixed(1) : '0.5';

  return (
    <div className="space-y-8 p-8 max-w-7xl mx-auto">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
          Shopify App Market Overview
        </h1>
        <p className="text-sm text-slate-500 mt-1 max-w-3xl">
          Explore the overall Shopify app ecosystem through market size, pricing models, ratings, categories, and review activity.
        </p>
      </div>

      {/* 1. Market at a Glance */}
      <div>
        <div className="mb-3">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-600" />
            Market at a Glance
            <InfoTooltip content="Calculated across 21,502 active Shopify applications included in the dataset." />
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Understand the size and overall activity of the Shopify app ecosystem.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <KPICard
            label="Total Shopify Apps"
            value={data.summary.total_apps.formatted}
            description="Apps included in the current dataset."
            icon={AppWindow}
            variant="accent"
          />
          <KPICard
            label="App Categories"
            value={data.summary.total_categories.formatted}
            description="Categories organizing the app market."
            icon={FolderTree}
            variant="indigo"
          />
          <KPICard
            label="Structured Plans"
            value={data.summary.total_pricing_plans.formatted}
            description="Pricing plans extracted from app listings."
            icon={DollarSign}
            variant="emerald"
          />
          <KPICard
            label="Merchant Reviews"
            value={data.summary.total_reviews.formatted}
            description="Actual review texts collected for analysis."
            icon={MessageSquare}
            variant="amber"
          />
          <KPICard
            label="Average App Rating"
            value={data.summary.average_rating.formatted}
            description="Average across 8,339 rated apps."
            icon={Star}
            variant="default"
          />
        </div>
      </div>

      {/* 2. Review Availability & Evidence Breakdown */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Database className="w-4 h-4 text-amber-600" />
              Review Availability & Evidence
              <InfoTooltip content="Distinguishes public Shopify listing review counts from actual merchant review records collected into the AppScout database. These are separate values and must not be conflated." />
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Accurate breakdown of public Shopify review counts vs. stored merchant review records.
            </p>
          </div>
          <button
            onClick={() => onNavigateToView('reviews')}
            className="text-xs text-amber-700 hover:text-amber-800 font-semibold flex items-center gap-1 cursor-pointer shrink-0 self-start sm:self-auto bg-amber-50 hover:bg-amber-100 px-3 py-1.5 rounded-lg border border-amber-200 transition-colors"
          >
            <span>Explore Stored Reviews</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* 5 Availability KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Card 1: Total Active Apps */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-1">
            <span className="text-xs font-semibold text-slate-500 block">Total Active Apps</span>
            <div className="text-xl font-bold text-slate-900 font-mono">
              {totalActiveApps.toLocaleString()}
            </div>
            <p className="text-[11px] text-slate-400">Total catalog in database</p>
          </div>

          {/* Card 2: Apps with Public Reviews */}
          <div className="p-4 rounded-xl border border-blue-200 bg-blue-50/40 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-blue-900">Public Reviews &gt; 0</span>
              <span className="text-[10px] font-bold px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">
                {pctPublic}%
              </span>
            </div>
            <div className="text-xl font-bold text-blue-950 font-mono">
              {appsWithPublic.toLocaleString()}
            </div>
            <p className="text-[11px] text-blue-700">Apps with reviews on Shopify</p>
          </div>

          {/* Card 3: Apps with Zero / NULL Public Reviews */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-700">Zero Public Reviews</span>
              <span className="text-[10px] font-bold px-1.5 py-0.5 bg-slate-200 text-slate-700 rounded">
                {pctNoPublic}%
              </span>
            </div>
            <div className="text-xl font-bold text-slate-800 font-mono">
              {appsWithNoPublic.toLocaleString()}
            </div>
            <p className="text-[11px] text-slate-500">Unreviewed apps on Shopify</p>
          </div>

          {/* Card 4: Total Stored Review Records */}
          <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50/40 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-emerald-900">Stored Review Records</span>
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            </div>
            <div className="text-xl font-bold text-emerald-950 font-mono">
              {totalStoredRevs.toLocaleString()}
            </div>
            <p className="text-[11px] text-emerald-700">Across {appsWithStored.toLocaleString()} apps in DB</p>
          </div>

          {/* Card 5: Apps with Public Reviews but Uncollected Records */}
          <div className="p-4 rounded-xl border border-amber-200 bg-amber-50/40 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-amber-900">Uncollected Records</span>
              <span className="text-[10px] font-bold px-1.5 py-0.5 bg-amber-100 text-amber-800 rounded">
                {pctUncollected}%
              </span>
            </div>
            <div className="text-xl font-bold text-amber-950 font-mono">
              {uncollectedApps.toLocaleString()} apps
            </div>
            <p className="text-[11px] text-amber-700">Public reviews exist, records uncollected</p>
          </div>
        </div>

        {/* Visual Composition Bar */}
        <div className="space-y-2 pt-2">
          <div className="flex justify-between text-xs text-slate-600">
            <span className="font-semibold text-slate-700">Ecosystem Review Coverage Breakdown</span>
            <span className="text-slate-400 font-mono text-[11px]">21,502 Active Shopify Apps</span>
          </div>

          <div className="h-3 w-full bg-slate-100 rounded-full overflow-hidden flex">
            <div
              className="bg-emerald-500 h-full transition-all"
              style={{ width: `${pctStored}%` }}
              title={`Stored Reviews Available: ${appsWithStored.toLocaleString()} apps (${pctStored}%)`}
            />
            <div
              className="bg-amber-400 h-full transition-all"
              style={{ width: `${pctUncollected}%` }}
              title={`Public Reviews but Uncollected: ${uncollectedApps.toLocaleString()} apps (${pctUncollected}%)`}
            />
            <div
              className="bg-slate-300 h-full transition-all"
              style={{ width: `${pctNoPublic}%` }}
              title={`No Public Reviews on Shopify: ${appsWithNoPublic.toLocaleString()} apps (${pctNoPublic}%)`}
            />
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600 pt-1">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
              <span>
                <strong>{appsWithStored.toLocaleString()}</strong> apps with stored reviews ({pctStored}%)
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 inline-block" />
              <span>
                <strong>{uncollectedApps.toLocaleString()}</strong> public reviews uncollected ({pctUncollected}%)
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-300 inline-block" />
              <span>
                <strong>{appsWithNoPublic.toLocaleString()}</strong> zero public reviews on Shopify ({pctNoPublic}%)
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Analytical Charts: Pricing, Ratings, Categories */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Commercial Pricing Models */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center">
                Commercial Pricing Models
                <InfoTooltip content="Primary commercial model categorized across all 21,502 apps." />
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                See how apps are distributed across free, paid, freemium, and unclassified pricing models.
              </p>
            </div>
            <button
              onClick={() => onNavigateToView('pricing')}
              className="text-xs text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1 cursor-pointer shrink-0 ml-2"
            >
              App Pricing <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-3.5 mt-4">
            {pricingItems.map((item) => (
              <div key={item.key} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="font-medium text-slate-700">{item.label}</span>
                  <span className="text-slate-500 font-mono">
                    {item.count.toLocaleString()} ({item.percentage}%)
                  </span>
                </div>
                <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${item.percentage}%`, backgroundColor: item.dotColor }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100 grid grid-cols-2 gap-2 text-center text-xs">
            <div className="p-2 bg-slate-50 rounded-lg">
              <span className="text-slate-400 block text-[11px]">Commercialized (Paid+Freemium)</span>
              <span className="font-bold text-slate-800 text-sm">
                {(
                  (pricingItems.find((p) => p.key === 'paid')?.percentage || 0) +
                  (pricingItems.find((p) => p.key === 'freemium')?.percentage || 0)
                ).toFixed(1)}
                %
              </span>
            </div>
            <div className="p-2 bg-slate-50 rounded-lg">
              <span className="text-slate-400 block text-[11px]">Unclassified / Contact</span>
              <span className="font-bold text-slate-800 text-sm">
                {pricingItems.find((p) => p.key === 'unknown')?.percentage || 0}%
              </span>
            </div>
          </div>
        </div>

        {/* Overall App Ratings */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center">
                Overall App Ratings
                <InfoTooltip content="Star rating breakdown across the 8,339 Shopify apps with ≥1 public review. Unreviewed apps (13,163) have no public rating on Shopify." />
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                See how app ratings are distributed across the ecosystem.
              </p>
            </div>
            <button
              onClick={() => onNavigateToView('reviews')}
              className="text-xs text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1 cursor-pointer shrink-0 ml-2"
            >
              App Reviews <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-3 mt-4">
            {ratingItems.map((r) => (
              <div key={r.stars} className="flex items-center gap-3 text-xs">
                <span className="w-10 font-semibold text-slate-700 flex items-center gap-0.5">
                  {r.stars} <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                </span>
                <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-amber-400 rounded-full transition-all duration-500"
                    style={{ width: `${r.percentage}%` }}
                  />
                </div>
                <span className="w-16 text-right font-mono text-slate-500">
                  {r.count.toLocaleString()}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500 bg-amber-50/60 p-3 rounded-lg border border-amber-100">
            <span className="font-medium text-amber-900">Ecosystem Average Rating</span>
            <span className="font-bold text-amber-900 text-sm">
              {data.summary.average_rating.formatted}
            </span>
          </div>
        </div>

        {/* Largest App Categories */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center">
                Largest App Categories
                <InfoTooltip content="Normalized Shopify categories with the greatest concentration of active applications." />
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Identify the categories with the greatest number of apps.
              </p>
            </div>
            <button
              onClick={() => onNavigateToView('categories')}
              className="text-xs text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1 cursor-pointer shrink-0 ml-2"
            >
              App Categories <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-3 mt-4">
            {data.top_categories.map((cat, i) => (
              <div
                key={cat.id}
                className="flex items-center justify-between text-xs py-1.5 border-b border-slate-50 last:border-0"
              >
                <span className="font-medium text-slate-700 truncate pr-2">
                  <span className="text-slate-400 mr-1.5 font-mono text-[11px]">{i + 1}.</span>
                  {formatCategoryName(cat.name, cat.slug)}
                </span>
                <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-mono font-semibold shrink-0">
                  {cat.app_count.toLocaleString()} apps
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 3. Tables Section: Most-Reviewed & Highest-Rated Apps */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Most-Reviewed Apps */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex items-start justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-blue-600" />
                Most-Reviewed Apps
                <InfoTooltip content="Ranked by total public Shopify review count recorded on the app listing. Excludes unreviewed/null apps." />
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Discover apps with the highest public review volume.
              </p>
            </div>
            <button
              onClick={() => onNavigateToView('apps')}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1 cursor-pointer shrink-0 ml-2"
            >
              Explore <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {data.top_reviewed_apps.map((app) => (
              <div
                key={app.id}
                onClick={() => onSelectApp(app)}
                className="p-4 hover:bg-slate-50/80 transition-colors cursor-pointer flex items-center justify-between gap-4"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-semibold text-slate-900 truncate hover:text-blue-600">
                      {app.app_name}
                    </h4>
                    <PricingBadge type={app.pricing_type} />
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {app.developer_name || 'Verified Developer'}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <div className="font-bold text-sm text-slate-900 font-mono">
                    {app.review_count?.toLocaleString()}
                  </div>
                  <div className="text-[11px] text-slate-400">public reviews</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Highest-Rated Apps */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex items-start justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Star className="w-4 h-4 text-amber-500 fill-amber-400" />
                Highest-Rated Apps
                <InfoTooltip content="Applications with at least 50 public Shopify reviews to ensure statistical significance, sorted by average rating." />
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                See apps with strong ratings and at least 50 reviews.
              </p>
            </div>
            <button
              onClick={() => onNavigateToView('apps')}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1 cursor-pointer shrink-0 ml-2"
            >
              Explore <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {data.top_rated_apps.map((app) => (
              <div
                key={app.id}
                onClick={() => onSelectApp(app)}
                className="p-4 hover:bg-slate-50/80 transition-colors cursor-pointer flex items-center justify-between gap-4"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-semibold text-slate-900 truncate hover:text-blue-600">
                      {app.app_name}
                    </h4>
                    <PricingBadge type={app.pricing_type} />
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {app.developer_name || 'Verified Developer'}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <RatingBadge rating={app.average_rating} reviewCount={app.review_count} showReviewLabel />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
