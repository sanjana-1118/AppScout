import React from 'react';
import {
  Home,
  LayoutDashboard,
  Search,
  FolderTree,
  DollarSign,
  MessageSquare,
} from 'lucide-react';
import { AppScoutLogo } from './AppScoutLogo';

export type ActiveView =
  | 'home'
  | 'overview'
  | 'apps'
  | 'categories'
  | 'pricing'
  | 'reviews';

interface SidebarProps {
  activeView: ActiveView;
  onSelectView: (view: ActiveView) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeView, onSelectView }) => {
  const navItems = [
    {
      id: 'home' as ActiveView,
      label: 'Home',
      icon: Home,
      description: 'Welcome & introduction',
    },
    {
      id: 'overview' as ActiveView,
      label: 'Overview',
      icon: LayoutDashboard,
      description: 'Market snapshot & KPIs',
    },
    {
      id: 'apps' as ActiveView,
      label: 'App Explorer',
      icon: Search,
      description: 'Search & filter 21k+ apps',
    },
    {
      id: 'categories' as ActiveView,
      label: 'App Categories',
      icon: FolderTree,
      description: '166 app categories',
    },
    {
      id: 'pricing' as ActiveView,
      label: 'App Pricing',
      icon: DollarSign,
      description: 'Plans & pricing models',
    },
    {
      id: 'reviews' as ActiveView,
      label: 'App Reviews',
      icon: MessageSquare,
      description: '738k merchant reviews',
    },
  ];

  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col h-screen sticky top-0 select-none z-20">
      {/* Brand Header */}
      <div
        onClick={() => onSelectView('home')}
        className="p-5 border-b border-slate-100 flex items-center gap-3 cursor-pointer group"
        title="Go to Home"
      >
        <AppScoutLogo size={36} />
        <div>
          <h1 className="text-base font-bold text-slate-900 tracking-tight group-hover:text-blue-600 transition-colors">
            AppScout
          </h1>
          <p className="text-xs text-slate-400">Shopify App Insights</p>
        </div>
      </div>

      {/* Navigation List */}
      <div className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Workspace Views
          </p>
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectView(item.id)}
              className={`w-full text-left flex items-start gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                isActive
                  ? 'bg-blue-50/80 text-blue-700 font-semibold shadow-xs border border-blue-100'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <Icon
                className={`w-4 h-4 mt-0.5 shrink-0 ${
                  isActive ? 'text-blue-600' : 'text-slate-400'
                }`}
              />
              <div className="flex-1 min-w-0">
                <div className="leading-tight">{item.label}</div>
                <div
                  className={`text-[11px] truncate mt-0.5 ${
                    isActive ? 'text-blue-600/80 font-normal' : 'text-slate-400'
                  }`}
                >
                  {item.description}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
};
