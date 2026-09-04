import React, { useState, useEffect, useCallback } from 'react';
import {
  DollarSign,
  Search,
  Clock,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { KPICard } from '../components/KPICard';
import { LoadingState, ErrorState, InfoTooltip } from '../components/StatusStates';
import {
  fetchPricingOverview,
  fetchPricingPlans,
  type PricingOverviewResponse,
} from '../api/pricing';
import { formatPricingType } from '../utils/formatters';
import type { PlanExplorerItem, AppItem } from '../types';
import type { PaginatedResponse } from '../api/apps';

interface PricingIntelligenceViewProps {
  onSelectApp?: (app: AppItem) => void;
}

export const PricingIntelligenceView: React.FC<PricingIntelligenceViewProps> = ({ onSelectApp }) => {
  // Overview state
  const [overview, setOverview] = useState<PricingOverviewResponse | null>(null);
  const [loadingOverview, setLoadingOverview] = useState(true);
  const [overviewError, setOverviewError] = useState<string | null>(null);

  // Plans explorer state
  const [plansData, setPlansData] = useState<PaginatedResponse<PlanExplorerItem>>({
    items: [],
    total: 0,
    page: 1,
    limit: 10,
    pages: 1,
  });
  const [loadingPlans, setLoadingPlans] = useState(true);
  const [plansError, setPlansError] = useState<string | null>(null);

  // Filters state
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [intervalFilter, setIntervalFilter] = useState<string>('all');
  const [freeTrialOnly, setFreeTrialOnly] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<'price' | 'plan_name' | 'app' | 'newest'>('price');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
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

  // 1. Fetch overview statistics
  const loadOverview = async () => {
    try {
      setLoadingOverview(true);
      setOverviewError(null);
      const res = await fetchPricingOverview();
      setOverview(res);
    } catch (err: any) {
      setOverviewError(err.message || 'Failed to load pricing overview');
    } finally {
      setLoadingOverview(false);
    }
  };

  useEffect(() => {
    loadOverview();
  }, []);

  // 2. Fetch plans table with current filters & pagination
  const loadPlans = useCallback(async () => {
    try {
      setLoadingPlans(true);
      setPlansError(null);

      const params: any = {
        page,
        limit: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      };

      if (debouncedSearch.trim()) {
        params.q = debouncedSearch.trim();
      }
      if (intervalFilter !== 'all') {
        params.billing_interval = intervalFilter;
      }
      if (freeTrialOnly) {
        params.has_free_trial = true;
      }

      const res = await fetchPricingPlans(params);
      setPlansData(res);
    } catch (err: any) {
      setPlansError(err.message || 'Failed to load pricing plans');
    } finally {
      setLoadingPlans(false);
    }
  }, [debouncedSearch, intervalFilter, freeTrialOnly, sortBy, sortOrder, page]);

  useEffect(() => {
    loadPlans();
  }, [loadPlans]);

  if (loadingOverview && !overview) {
    return <LoadingState message="Calculating monetization statistics across 42,326 plan tiers..." />;
  }

  if (overviewError && !overview) {
    return (
      <ErrorState
        title="Could not load app pricing"
        message={overviewError}
        onRetry={loadOverview}
      />
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* 1. Pricing KPI Metrics */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-emerald-600" />
            App Pricing Overview
            <InfoTooltip content="Calculated across all 42,326 structured pricing plan tiers." />
          </h3>
          <span className="text-xs font-mono font-medium text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded border border-emerald-200">
            ● 42,326 Plans Analyzed
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <KPICard
            label="Median Tier Price"
            value={overview ? `$${overview.price_distribution.median_price?.toFixed(2)}` : '$21.00'}
            description="50th percentile paid plan"
            trend="Core Market Anchor"
            icon={DollarSign}
            variant="emerald"
          />
          <KPICard
            label="Average Tier Price"
            value={overview ? `$${overview.price_distribution.avg_price?.toFixed(2)}` : '$66.89'}
            description="Pulled by enterprise/plus tiers"
            variant="default"
          />
          <KPICard
            label="25th Percentile"
            value={overview ? `$${overview.price_distribution.p25_price?.toFixed(2)}` : '$9.99'}
            description="Entry-level merchant plan"
            variant="accent"
          />
          <KPICard
            label="75th Percentile"
            value={overview ? `$${overview.price_distribution.p75_price?.toFixed(2)}` : '$59.00'}
            description="Established merchant tier"
            variant="indigo"
          />
          <KPICard
            label="Free Trial Penetration"
            value={overview ? `${overview.free_trial_stats.trial_percentage}%` : '50.94%'}
            description={`${overview?.free_trial_stats.has_trial_count.toLocaleString() || '10,953'} of 21,502 apps offer trial`}
            trend="14-day standard"
            icon={Clock}
            variant="amber"
          />
        </div>
      </div>

      {/* 2. Analytical Charts: Monetization Breakdown, Billing Intervals & Free Trials */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Commercial Model Distribution */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h4 className="text-sm font-bold text-slate-900 mb-1 flex items-center">
            Commercial Model Mix
            <InfoTooltip content="Primary pricing model distribution categorized across all 21,502 canonical Shopify apps. Denominator: 21,502 total apps." />
          </h4>
          <p className="text-xs text-slate-500 mb-4">Breakdown across 21,502 Shopify apps</p>

          <div className="space-y-3">
            {overview?.model_breakdown.map((m) => {
              const { label, dotColor } = formatPricingType(m.model);
              return (
                <div key={m.model} className="space-y-1 text-xs">
                  <div className="flex justify-between font-medium">
                    <span className="text-slate-700">{label}</span>
                    <span className="text-slate-500 font-mono">
                      {m.count.toLocaleString()} ({m.percentage}%)
                    </span>
                  </div>
                  <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${m.percentage}%`, backgroundColor: dotColor }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Billing Interval Breakdown */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h4 className="text-sm font-bold text-slate-900 mb-1 flex items-center">
            Billing Interval Cadence
            <InfoTooltip content="Frequency of subscription billing across all 42,326 individual plan tiers in the dataset." />
          </h4>
          <p className="text-xs text-slate-500 mb-4">Recurring contract models</p>

          <div className="space-y-3">
            {overview?.interval_breakdown.map((item) => {
              const labelMap: Record<string, { title: string; desc: string }> = {
                monthly: {
                  title: 'Monthly Subscription',
                  desc: 'Predominant billing standard across the Shopify merchant app market.',
                },
                annual: {
                  title: 'Annual Commitment',
                  desc: 'Annual commitment plans offering upfront volume discounts.',
                },
                one_time: {
                  title: 'One-Time Charge',
                  desc: 'Single fixed payment for lifetime access or setup.',
                },
                usage_based: {
                  title: 'Usage / Variable',
                  desc: 'Variable or usage-based metered billing tier.',
                },
              };
              const meta = labelMap[item.billing_interval] || {
                title: `${item.billing_interval.charAt(0).toUpperCase() + item.billing_interval.slice(1)} Cadence`,
                desc: 'Alternative billing interval schedule.',
              };
              return (
                <div
                  key={item.billing_interval}
                  className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs"
                >
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-slate-800">{meta.title}</span>
                    <span className="font-mono font-bold text-blue-700">
                      {item.plan_count.toLocaleString()} ({item.percentage}%)
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">{meta.desc}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Free Trial Length Analysis */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h4 className="text-sm font-bold text-slate-900 mb-1 flex items-center">
            Free Trial Duration Analysis
            <InfoTooltip content="Distribution of free trial lengths offered by apps that include trial onboarding (10,953 apps with trial). Denominator: 10,953 trial-enabled apps." />
          </h4>
          <p className="text-xs text-slate-500 mb-4">
            Trial durations across {overview?.free_trial_stats.has_trial_count.toLocaleString() || '10,953'} trial apps
          </p>

          <div className="space-y-2.5">
            {overview?.free_trial_stats.popular_durations &&
              Object.entries(overview.free_trial_stats.popular_durations).map(([days, count]) => {
                const totalTrialApps = overview.free_trial_stats.has_trial_count || 1;
                const pct = ((Number(count) / totalTrialApps) * 100).toFixed(1);
                return (
                  <div
                    key={days}
                    className="flex items-center justify-between p-2.5 rounded-lg border border-slate-100 bg-slate-50/60 text-xs"
                  >
                    <div>
                      <span className="font-bold text-slate-800">{days}-Day Free Trial</span>
                      <span className="text-[11px] text-slate-400 block font-mono">
                        {Number(count).toLocaleString()} applications
                      </span>
                    </div>
                    <span className="font-mono font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 text-[11px]">
                      {pct}%
                    </span>
                  </div>
                );
              })}
          </div>
          <p className="text-[11px] text-slate-400 mt-3 pt-2 border-t border-slate-100">
            * Note: Remaining 10,549 apps (49.06%) offer no free trial period.
          </p>
        </div>
      </div>

      {/* 3. Plan Explorer Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h4 className="text-sm font-bold text-slate-900 flex items-center">
              Plan Explorer
              <InfoTooltip content="Interactive search and filter table across all 42,326 structured plan tiers extracted from the Shopify App Store." />
            </h4>
            <p className="text-xs text-slate-500">
              Showing {plansData.total.toLocaleString()} plan tiers in dataset
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs">
            {/* Search */}
            <div className="relative w-64">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search plan, app name, features..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:outline-hidden focus:border-blue-500 text-xs"
              />
            </div>

            {/* Interval Filter */}
            <select
              value={intervalFilter}
              onChange={(e) => {
                setIntervalFilter(e.target.value);
                setPage(1);
              }}
              className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 focus:outline-hidden text-xs"
            >
              <option value="all">All Intervals</option>
              <option value="monthly">Monthly</option>
              <option value="annual">Annual</option>
              <option value="one_time">One-Time</option>
              <option value="usage_based">Usage-Based</option>
            </select>

            {/* Trial Checkbox */}
            <label className="flex items-center gap-1.5 cursor-pointer bg-slate-50 px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs text-slate-700">
              <input
                type="checkbox"
                checked={freeTrialOnly}
                onChange={(e) => {
                  setFreeTrialOnly(e.target.checked);
                  setPage(1);
                }}
                className="rounded text-blue-600 focus:ring-0"
              />
              <span>With Free Trial</span>
            </label>

            {/* Sort */}
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value as any);
                setPage(1);
              }}
              className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 focus:outline-hidden text-xs"
            >
              <option value="price">Price Amount</option>
              <option value="plan_name">Plan Name</option>
              <option value="app">Parent App</option>
            </select>

            <button
              onClick={() => {
                setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                setPage(1);
              }}
              className="px-2 py-1.5 bg-slate-50 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
            >
              {sortOrder === 'asc' ? 'Low → High' : 'High → Low'}
            </button>
          </div>
        </div>

        {/* Table Content */}
        {loadingPlans ? (
          <div className="p-12 text-center text-xs text-slate-500">
            Loading pricing plans...
          </div>
        ) : plansError ? (
          <div className="p-6 text-center text-xs text-red-600">
            {plansError}
          </div>
        ) : plansData.items.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-400">
            No pricing plans found matching your search.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50/75 border-b border-slate-200 text-slate-600 font-semibold">
                  <th className="py-3 px-4">Plan Name</th>
                  <th className="py-3 px-4">Parent Application</th>
                  <th className="py-3 px-4">Price (USD)</th>
                  <th className="py-3 px-4">Billing Cadence</th>
                  <th className="py-3 px-4">Free Trial</th>
                  <th className="py-3 px-4">Features & Inclusions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {plansData.items.map((plan) => {
                  // Normalize plan name capitalization (e.g. FREE -> Free)
                  const cleanPlanName =
                    plan.plan_name?.toUpperCase() === 'FREE'
                      ? 'Free'
                      : plan.plan_name;

                  return (
                    <tr key={plan.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3.5 px-4 font-bold text-slate-900">{cleanPlanName}</td>
                      <td className="py-3.5 px-4 font-medium">
                        <button
                          onClick={() =>
                            onSelectApp?.({
                              id: plan.app_id,
                              app_slug: plan.app_slug,
                              app_name: plan.app_name,
                              app_url: `https://apps.shopify.com/${plan.app_slug}`,
                              developer_name: null,
                              description: null,
                              average_rating: null,
                              review_count: null,
                              pricing_type: 'unknown',
                              free_trial_days: plan.free_trial_days,
                              categories: [],
                            })
                          }
                          className="text-blue-600 hover:text-blue-800 hover:underline font-semibold text-left cursor-pointer transition-colors"
                        >
                          {plan.app_name}
                        </button>
                      </td>
                      <td className="py-3.5 px-4 font-mono font-bold text-slate-900">
                        {plan.price_amount !== null && plan.price_amount > 0
                          ? `$${plan.price_amount.toFixed(2)}`
                          : 'Free tier'}
                      </td>
                      <td className="py-3.5 px-4 text-slate-500 capitalize">
                        {plan.billing_interval?.replace('_', ' ') || 'monthly'}
                      </td>
                      <td className="py-3.5 px-4">
                        {plan.free_trial_days ? (
                          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            {plan.free_trial_days} days
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-slate-600 max-w-xs">
                        <div
                          className="truncate"
                          title={
                            Array.isArray(plan.features)
                              ? plan.features.join(' • ')
                              : String(plan.features || '')
                          }
                        >
                          {Array.isArray(plan.features)
                            ? plan.features.join(' • ')
                            : typeof plan.features === 'string'
                            ? plan.features
                            : 'Standard feature set'}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Controls */}
        {plansData.pages > 1 && (
          <div className="flex items-center justify-between bg-white p-4 border-t border-slate-100 text-xs">
            <button
              disabled={page === 1 || loadingPlans}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" /> Previous
            </button>
            <span className="font-medium text-slate-600">
              Page {plansData.page} of {plansData.pages} ({plansData.total.toLocaleString()} plans)
            </span>
            <button
              disabled={page === plansData.pages || loadingPlans}
              onClick={() => setPage((p) => Math.min(plansData.pages, p + 1))}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
            >
              Next <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
