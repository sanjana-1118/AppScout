import React from 'react';
import { Star } from 'lucide-react';
import { formatPricingType } from '../utils/formatters';

interface PricingBadgeProps {
  type: string;
}

export const PricingBadge: React.FC<PricingBadgeProps> = ({ type }) => {
  const { label, badgeClass } = formatPricingType(type);
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${badgeClass}`}
    >
      {label}
    </span>
  );
};

export const RatingBadge: React.FC<{
  rating: number | null;
  reviewCount?: number | null;
  showReviewLabel?: boolean;
}> = ({ rating, reviewCount, showReviewLabel = false }) => {
  // If an app has zero or NULL public reviews, display "No public reviews"
  if (
    reviewCount === 0 ||
    reviewCount === null ||
    reviewCount === undefined ||
    rating === null ||
    rating === undefined ||
    rating === 0
  ) {
    return (
      <span className="inline-flex items-center text-xs text-slate-400 font-medium">
        No public reviews
      </span>
    );
  }

  return (
    <div className="inline-flex items-center gap-1.5">
      <div className="inline-flex items-center gap-1 font-bold text-xs text-amber-800 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
        <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
        <span>{rating.toFixed(1)}</span>
      </div>
      <span className="text-xs text-slate-500 font-medium">
        ({reviewCount.toLocaleString()} {showReviewLabel ? 'public reviews' : 'reviews'})
      </span>
    </div>
  );
};
