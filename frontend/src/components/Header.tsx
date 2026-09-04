import React from 'react';
import { Search } from 'lucide-react';
import { AppScoutLogo } from './AppScoutLogo';
import type { ActiveView } from './Sidebar';

interface HeaderProps {
  currentPageTitle: string;
  onNavigateToView?: (view: ActiveView) => void;
  actions?: React.ReactNode;
}

export const Header: React.FC<HeaderProps> = ({
  currentPageTitle,
  onNavigateToView,
  actions,
}) => {
  return (
    <header className="bg-white border-b border-slate-200 px-6 py-3 sticky top-0 z-10 select-none">
      <div className="flex items-center justify-between gap-4">
        {/* Left: AppScout Logo + Brand + Current View */}
        <div className="flex items-center gap-3">
          <div
            onClick={() => onNavigateToView?.('home')}
            className="flex items-center gap-2.5 cursor-pointer group"
            title="Go to Home"
          >
            <AppScoutLogo size={28} />
            <span className="font-bold text-base text-slate-900 tracking-tight group-hover:text-blue-600 transition-colors">
              AppScout
            </span>
          </div>

          <span className="text-slate-300 font-light hidden sm:inline">/</span>

          <span className="text-sm font-semibold text-slate-700 hidden sm:inline">
            {currentPageTitle}
          </span>
        </div>

        {/* Right: Only useful actions */}
        <div className="flex items-center gap-3">
          {actions}

          {/* Quick Jump to App Explorer */}
          <button
            onClick={() => onNavigateToView?.('apps')}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-xs text-slate-500 hover:text-slate-800 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg transition-colors cursor-pointer"
            title="Search apps in App Explorer"
          >
            <Search className="w-3.5 h-3.5 text-slate-400" />
            <span className="hidden sm:inline">Search apps...</span>
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
