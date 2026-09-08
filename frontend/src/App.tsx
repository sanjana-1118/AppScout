import { useState } from 'react';
import { Sidebar, type ActiveView } from './components/Sidebar';
import { Header } from './components/Header';
import { HomeView } from './views/HomeView';
import { OverviewView } from './views/OverviewView';
import { AppExplorerView } from './views/AppExplorerView';
import { CategoryIntelligenceView } from './views/CategoryIntelligenceView';
import { PricingIntelligenceView } from './views/PricingIntelligenceView';
import { ReviewsExplorerView } from './views/ReviewsExplorerView';
import { AppDetailModal } from './components/AppDetailModal';
import { ErrorBoundary } from './components/ErrorBoundary';
import type { AppItem } from './types';

export function App() {
  const [activeView, setActiveView] = useState<ActiveView>('home');
  const [selectedApp, setSelectedApp] = useState<AppItem | null>(null);
  const [selectedCategorySlug, setSelectedCategorySlug] = useState<string | null>(null);
  const [selectedReviewAppSlug, setSelectedReviewAppSlug] = useState<string | null>(null);

  const viewMetadata: Record<ActiveView, { title: string }> = {
    home: { title: 'Home' },
    overview: { title: 'Overview' },
    apps: { title: 'App Explorer' },
    categories: { title: 'App Categories' },
    pricing: { title: 'App Pricing' },
    reviews: { title: 'App Reviews' },
  };

  const currentMeta = viewMetadata[activeView];

  return (
    <div className="flex min-h-screen bg-slate-50 font-sans text-slate-900">
      {/* Persistent Left Sidebar */}
      <Sidebar activeView={activeView} onSelectView={setActiveView} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <Header
          currentPageTitle={currentMeta.title}
          onNavigateToView={setActiveView}
        />

        <main className="flex-1 pb-16">
          <ErrorBoundary>
            {activeView === 'home' && (
              <HomeView onNavigateToView={setActiveView} />
            )}

            {activeView === 'overview' && (
              <OverviewView
                onSelectApp={setSelectedApp}
                onNavigateToView={setActiveView}
              />
            )}

            {activeView === 'apps' && (
              <AppExplorerView
                onSelectApp={setSelectedApp}
                initialCategorySlug={selectedCategorySlug || undefined}
                onClearInitialCategorySlug={() => setSelectedCategorySlug(null)}
              />
            )}

            {activeView === 'categories' && (
              <CategoryIntelligenceView
                onSelectApp={setSelectedApp}
                onExploreCategory={(categorySlug) => {
                  setSelectedCategorySlug(categorySlug);
                  setActiveView('apps');
                }}
              />
            )}

            {activeView === 'pricing' && (
              <PricingIntelligenceView onSelectApp={setSelectedApp} />
            )}

            {activeView === 'reviews' && (
              <ReviewsExplorerView
                onSelectApp={setSelectedApp}
                initialAppSlug={selectedReviewAppSlug || undefined}
                onClearInitialAppSlug={() => setSelectedReviewAppSlug(null)}
              />
            )}
          </ErrorBoundary>
        </main>
      </div>

      {/* App Detail Modal - Shared across all views */}
      <AppDetailModal
        app={selectedApp}
        onClose={() => setSelectedApp(null)}
        onViewAllReviews={(appSlug) => {
          setSelectedReviewAppSlug(appSlug);
          setSelectedApp(null);
          setActiveView('reviews');
        }}
      />
    </div>
  );
}

export default App;
