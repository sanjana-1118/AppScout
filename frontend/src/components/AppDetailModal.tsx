import React, { useEffect, useState, useCallback } from 'react';
import {
  X,
  ExternalLink,
  Star,
  Check,
  Calendar,
  MapPin,
  Clock,
  DollarSign,
  Tag,
  Loader2,
  AlertCircle,
  MessageSquare,
  ArrowRight,
} from 'lucide-react';
import type { AppItem } from '../types';
import { PricingBadge, RatingBadge } from './Badge';
import { fetchAppDetail } from '../api/apps';
import { InfoTooltip } from './StatusStates';
import { formatCategoryName } from '../utils/formatters';

interface AppDetailModalProps {
  app: AppItem | null;
  onClose: () => void;
  onViewAllReviews?: (appSlug: string) => void;
}

export const AppDetailModal: React.FC<AppDetailModalProps> = ({
  app,
  onClose,
  onViewAllReviews,
}) => {
  const [detail, setDetail] = useState<AppItem | null>(app);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDeepDetail = useCallback(async (appToLoad: AppItem) => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchAppDetail(appToLoad.app_slug || appToLoad.id);
      setDetail(res);
    } catch (err: any) {
      setError(err.message || 'Could not load extended detail');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!app) {
      setDetail(null);
      return;
    }
    setDetail(app);
    loadDeepDetail(app);
  }, [app, loadDeepDetail]);

  if (!app) return null;

  const currentApp = detail || app;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 overflow-y-auto">
      <div
        className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden my-auto animate-in fade-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="p-6 border-b border-slate-100 flex items-start justify-between gap-4 bg-slate-50/50">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2 mb-1.5">
              <h3 className="text-xl font-bold text-slate-900 tracking-tight">{currentApp.app_name}</h3>
              <PricingBadge type={currentApp.pricing_type} />
              {currentApp.free_trial_days && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {currentApp.free_trial_days}-Day Free Trial
                </span>
              )}
              {loading && (
                <span className="inline-flex items-center gap-1 text-[11px] text-blue-600 font-medium">
                  <Loader2 className="w-3 h-3 animate-spin" /> Loading app details...
                </span>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
              <span>
                Developer: <strong className="text-slate-700">{currentApp.developer_name || 'Verified Partner'}</strong>
              </span>
              <span>•</span>
              <RatingBadge rating={currentApp.average_rating} reviewCount={currentApp.review_count} />
              <span>•</span>
              <a
                href={currentApp.app_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 font-semibold"
              >
                Shopify App Store <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Description */}
          <div>
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center">
              Application Overview & Capabilities
              <InfoTooltip content="Official description extracted from the canonical Shopify App Store listing." />
            </h4>
            <p className="text-sm text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-200/60">
              {currentApp.description || 'No detailed description provided by the developer.'}
            </p>
          </div>

          {/* Categories */}
          {currentApp.categories && currentApp.categories.length > 0 && (
            <div>
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Tag className="w-3.5 h-3.5 text-blue-600" />
                Taxonomy Classifications
                <InfoTooltip content="Categories under which this app is listed in the official Shopify directory." />
              </h4>
              <div className="flex flex-wrap gap-2">
                {currentApp.categories.map((cat) => (
                  <span
                    key={cat.id}
                    className="px-3 py-1 rounded-lg text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200"
                  >
                    {formatCategoryName(cat.name, cat.slug)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Pricing Plans */}
          <div>
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <DollarSign className="w-3.5 h-3.5 text-emerald-600" />
              Structured Pricing Plans ({currentApp.pricing_plans?.length || 0})
              <InfoTooltip content="Structured plan tiers parsed into price amount, billing interval, and features." />
            </h4>

            {currentApp.pricing_plans && currentApp.pricing_plans.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {currentApp.pricing_plans.map((plan) => (
                  <div
                    key={plan.id}
                    className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs hover:border-blue-200 transition-all"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <h5 className="font-bold text-slate-900 text-sm">{plan.plan_name}</h5>
                      <span className="text-xs font-mono font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded">
                        {plan.price_amount !== null && plan.price_amount > 0
                          ? `$${plan.price_amount.toFixed(2)} / ${plan.billing_interval || 'month'}`
                          : 'Free'}
                      </span>
                    </div>

                    {plan.free_trial_days && (
                      <p className="text-[11px] text-emerald-600 font-semibold mb-2">
                        Includes {plan.free_trial_days} days trial
                      </p>
                    )}

                    {plan.features && (
                      <ul className="mt-3 space-y-1.5 text-xs text-slate-600">
                        {Array.isArray(plan.features) ? (
                          plan.features.map((feat, idx) => (
                            <li key={idx} className="flex items-start gap-1.5">
                              <Check className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                              <span>{feat}</span>
                            </li>
                          ))
                        ) : (
                          <li className="flex items-start gap-1.5">
                            <Check className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                            <span>{String(plan.features)}</span>
                          </li>
                        )}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-4 text-center rounded-lg border border-dashed border-slate-200 text-xs text-slate-400">
                No individual plan tiers specified (Usage-based, contact developer, or Free app).
              </div>
            )}
          </div>

          {/* Merchant Reviews & Coverage */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Star className="w-3.5 h-3.5 text-amber-500 fill-amber-400" />
                Merchant Reviews
                <InfoTooltip content="Verified merchant feedback extracted for this application in the review dataset." />
              </h4>
              <span className="text-xs text-slate-500 font-mono">
                {(() => {
                  if (loading && detail?.stored_review_count === undefined) {
                    return 'Checking review coverage...';
                  }
                  const storedCount = detail?.stored_review_count ?? detail?.review_summary?.total_reviews_in_db ?? (currentApp.stored_review_count || 0);
                  const publicCount = currentApp.review_count ?? 0;
                  const hasStored = storedCount > 0;
                  if (hasStored) {
                    return `${storedCount.toLocaleString()} stored reviews`;
                  }
                  if (publicCount > 0) {
                    return `${publicCount.toLocaleString()} public on Shopify (uncollected)`;
                  }
                  return '0 public reviews';
                })()}
              </span>
            </div>

            {(() => {
              if (loading && !detail?.recent_reviews && !detail?.stored_review_count) {
                return (
                  <div className="p-6 text-center text-xs text-slate-500 flex items-center justify-center gap-2 border border-slate-100 rounded-xl bg-slate-50/50">
                    <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                    <span>Loading reviews and coverage...</span>
                  </div>
                );
              }

              if (error && !detail?.recent_reviews && !detail?.stored_review_count) {
                return (
                  <div className="p-4 rounded-xl border border-red-200 bg-red-50/70 text-xs text-red-800 space-y-2 text-center">
                    <AlertCircle className="w-4 h-4 text-red-500 mx-auto" />
                    <p className="font-semibold">Failed to load review records</p>
                    <p className="text-[11px] text-red-600">{error}</p>
                    <button
                      onClick={() => app && loadDeepDetail(app)}
                      className="px-3 py-1 bg-red-600 text-white rounded-md text-xs font-semibold hover:bg-red-700 transition-colors cursor-pointer"
                    >
                      Retry
                    </button>
                  </div>
                );
              }

              const storedCount = detail?.stored_review_count ?? detail?.review_summary?.total_reviews_in_db ?? (currentApp.stored_review_count || 0);
              const publicCount = currentApp.review_count ?? 0;
              const hasStoredReviews = storedCount > 0;

              // Case A: Stored reviews available
              if (hasStoredReviews) {
                return (
                  <div className="space-y-3">
                    {currentApp.recent_reviews && currentApp.recent_reviews.length > 0 ? (
                      currentApp.recent_reviews.map((rev) => (
                        <div
                          key={rev.id}
                          className="p-4 rounded-xl border border-slate-200 bg-slate-50/40 text-xs space-y-2"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-slate-900">{rev.reviewer_name || 'Shopify Merchant'}</span>
                              {rev.reviewer_location && (
                                <span className="text-slate-400 flex items-center gap-0.5 text-[11px]">
                                  <MapPin className="w-3 h-3" /> {rev.reviewer_location}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-1 font-semibold text-amber-600">
                              <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                              <span>{rev.rating}.0</span>
                            </div>
                          </div>

                          <p className="text-slate-700 leading-relaxed italic">"{rev.body}"</p>

                          <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-100">
                            {rev.time_spent_using_app && (
                              <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3" /> {rev.time_spent_using_app}
                              </span>
                            )}
                            <span className="flex items-center gap-1">
                              <Calendar className="w-3 h-3" /> {rev.review_date || 'Recent'}
                            </span>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="p-4 text-center rounded-lg border border-dashed border-slate-200 text-xs text-slate-400">
                        Reviews exist in the database, but individual sample excerpts are unavailable.
                      </div>
                    )}

                    {/* View All Reviews in App Reviews Flow */}
                    <div className="pt-2">
                      <button
                        onClick={() => {
                          onClose();
                          onViewAllReviews?.(currentApp.app_slug);
                        }}
                        className="w-full py-2.5 px-4 rounded-xl border border-blue-200 bg-blue-50/90 hover:bg-blue-100 text-blue-700 font-semibold text-xs flex items-center justify-center gap-1.5 transition-all shadow-2xs cursor-pointer group"
                      >
                        <MessageSquare className="w-3.5 h-3.5 text-blue-600" />
                        <span>View all reviews ({storedCount.toLocaleString()})</span>
                        <ArrowRight className="w-3.5 h-3.5 ml-0.5 group-hover:translate-x-0.5 transition-transform" />
                      </button>
                    </div>
                  </div>
                );
              }

              // Case B: Public reviews exist on Shopify, but records were not collected
              if (publicCount > 0) {
                return (
                  <div className="p-4 rounded-xl border border-amber-200 bg-amber-50/70 text-xs text-amber-900 space-y-2">
                    <div className="flex items-center gap-1.5 font-bold text-amber-950">
                      <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                      <span>Review Coverage Notice</span>
                    </div>
                    <p className="font-semibold text-amber-950">
                      Public review records were not collected for this app.
                    </p>
                    <p className="text-amber-800 text-[11px] leading-relaxed">
                      This app has {publicCount.toLocaleString()} public reviews on the Shopify App Store, but individual review records were not collected and are not available in AppScout's dataset.
                    </p>
                  </div>
                );
              }

              // Case C: Genuinely zero public Shopify reviews
              return (
                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 text-xs text-slate-600 space-y-1">
                  <p className="font-semibold text-slate-800">No public reviews on Shopify.</p>
                  <p className="text-slate-500 text-[11px]">This application has zero public merchant reviews recorded on Shopify.</p>
                </div>
              );
            })()}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-100 bg-slate-50/60 flex items-center justify-between text-xs text-slate-500">
          <span className="font-mono text-slate-400">Canonical Slug: {currentApp.app_slug}</span>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-900 text-white rounded-lg font-medium hover:bg-slate-800 transition-colors shadow-xs"
          >
            Close Details
          </button>
        </div>
      </div>
    </div>
  );
};
