import React, { useEffect, useState } from 'react';
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
} from 'lucide-react';
import type { AppItem } from '../types';
import { PricingBadge, RatingBadge } from './Badge';
import { fetchAppDetail } from '../api/apps';
import { InfoTooltip } from './StatusStates';
import { formatCategoryName } from '../utils/formatters';

interface AppDetailModalProps {
  app: AppItem | null;
  onClose: () => void;
}

export const AppDetailModal: React.FC<AppDetailModalProps> = ({ app, onClose }) => {
  const [detail, setDetail] = useState<AppItem | null>(app);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!app) {
      setDetail(null);
      return;
    }
    setDetail(app);

    // Fetch live deep detail from backend if app has a slug or id
    const loadDeepDetail = async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await fetchAppDetail(app.app_slug || app.id);
        setDetail(res);
      } catch (err: any) {
        // Fallback to currently passed summary app object if individual detail fails
        setError(err.message || 'Could not load extended detail');
      } finally {
        setLoading(false);
      }
    };

    loadDeepDetail();
  }, [app]);

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

          {/* Recent Merchant Reviews */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Star className="w-3.5 h-3.5 text-amber-500 fill-amber-400" />
                Recent Merchant Reviews
                <InfoTooltip content="Verified merchant feedback extracted for this application in the baseline review dataset." />
              </h4>
              <span className="text-xs text-slate-500">
                {currentApp.review_count?.toLocaleString() || 0} total reviews on Shopify
              </span>
            </div>

            {currentApp.recent_reviews && currentApp.recent_reviews.length > 0 ? (
              <div className="space-y-3">
                {currentApp.recent_reviews.map((rev) => (
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
                ))}
              </div>
            ) : (
              <div className="p-4 text-center rounded-lg border border-dashed border-slate-200 text-xs text-slate-400">
                No individual review text stored in the priority review sample for this application.
              </div>
            )}
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
