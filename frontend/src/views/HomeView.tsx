import React from 'react';
import {
  LayoutDashboard,
  Search,
  FolderTree,
  DollarSign,
  MessageSquare,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import type { ActiveView } from '../components/Sidebar';

interface HomeViewProps {
  onNavigateToView: (view: ActiveView) => void;
}

export const HomeView: React.FC<HomeViewProps> = ({ onNavigateToView }) => {
  return (
    <div className="space-y-8 p-8 max-w-7xl mx-auto">
      {/* 1. Hero Section */}
      <section className="bg-gradient-to-br from-white via-slate-50 to-blue-50/50 border border-slate-200 rounded-2xl p-8 lg:p-12 shadow-xs relative overflow-hidden">
        <div className="relative z-10 max-w-3xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 shadow-xs">
            <Sparkles className="w-3.5 h-3.5 text-blue-600" />
            Shopify App Explorer
          </div>

          <h1 className="text-3xl lg:text-4xl font-extrabold text-slate-900 tracking-tight leading-tight">
            Welcome to AppScout
          </h1>

          <p className="text-lg text-slate-700 font-medium leading-relaxed">
            Explore the Shopify app market through collected app information, categories, pricing, and merchant reviews.
          </p>

          <p className="text-sm text-slate-500 leading-normal">
            Understand the market, explore the data, and discover insights.
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-4">
            <button
              onClick={() => onNavigateToView('overview')}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm shadow-sm shadow-blue-500/20 transition-all cursor-pointer"
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Explore Dashboard</span>
              <ArrowRight className="w-4 h-4 ml-0.5" />
            </button>

            <button
              onClick={() => onNavigateToView('apps')}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-white hover:bg-slate-50 text-slate-700 font-semibold text-sm border border-slate-300 shadow-xs transition-all cursor-pointer"
            >
              <Search className="w-4 h-4 text-slate-500" />
              <span>Explore Apps</span>
            </button>
          </div>
        </div>
      </section>

      {/* 2. What Can You Do With AppScout? */}
      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            What Can You Do with AppScout?
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Explore focused areas to analyze apps, categories, commercial pricing models, and merchant feedback.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* Card 1: Explore Apps */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 hover:shadow-sm hover:border-blue-300 transition-all flex flex-col justify-between group">
            <div className="space-y-3">
              <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center border border-blue-100">
                <Search className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900">Explore Apps</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Search and inspect individual Shopify apps.
              </p>
            </div>
            <div className="pt-5 mt-auto">
              <button
                onClick={() => onNavigateToView('apps')}
                className="inline-flex items-center gap-1.5 text-sm font-semibold text-blue-600 hover:text-blue-700 group-hover:gap-2 transition-all cursor-pointer"
              >
                <span>Explore Apps</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Card 2: App Categories */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 hover:shadow-sm hover:border-indigo-300 transition-all flex flex-col justify-between group">
            <div className="space-y-3">
              <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center border border-indigo-100">
                <FolderTree className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900">App Categories</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Explore how apps are organized across the Shopify app market.
              </p>
            </div>
            <div className="pt-5 mt-auto">
              <button
                onClick={() => onNavigateToView('categories')}
                className="inline-flex items-center gap-1.5 text-sm font-semibold text-indigo-600 hover:text-indigo-700 group-hover:gap-2 transition-all cursor-pointer"
              >
                <span>Explore Categories</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Card 3: App Pricing */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 hover:shadow-sm hover:border-emerald-300 transition-all flex flex-col justify-between group">
            <div className="space-y-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-100">
                <DollarSign className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900">App Pricing</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Understand pricing models and plan structures.
              </p>
            </div>
            <div className="pt-5 mt-auto">
              <button
                onClick={() => onNavigateToView('pricing')}
                className="inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-600 hover:text-emerald-700 group-hover:gap-2 transition-all cursor-pointer"
              >
                <span>Explore Pricing</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Card 4: App Reviews */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 hover:shadow-sm hover:border-amber-300 transition-all flex flex-col justify-between group">
            <div className="space-y-3">
              <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center border border-amber-100">
                <MessageSquare className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900">App Reviews</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Read collected merchant review text and understand review coverage.
              </p>
            </div>
            <div className="pt-5 mt-auto">
              <button
                onClick={() => onNavigateToView('reviews')}
                className="inline-flex items-center gap-1.5 text-sm font-semibold text-amber-700 hover:text-amber-800 group-hover:gap-2 transition-all cursor-pointer"
              >
                <span>Explore Reviews</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
