import React from 'react';

interface AppScoutLogoProps {
  size?: number;
  className?: string;
  showWordmark?: boolean;
}

/**
 * AppScout Logo — Modern SaaS Brand Mark
 * Represents app discovery, market scouting, and connected ecosystem data.
 * Features a high-contrast scout lens aperture focusing on connected app nodes.
 */
export const AppScoutLogo: React.FC<AppScoutLogoProps> = ({
  size = 32,
  className = '',
  showWordmark = false,
}) => {
  return (
    <div className={`inline-flex items-center gap-2.5 ${className}`}>
      {/* SVG Icon Mark */}
      <svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0 transition-transform duration-200 group-hover:scale-105"
      >
        <defs>
          <linearGradient id="as_bg_grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#2563EB" />
            <stop offset="100%" stopColor="#4F46E5" />
          </linearGradient>
          <linearGradient id="as_lens_grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#67E8F9" />
            <stop offset="100%" stopColor="#FFFFFF" />
          </linearGradient>
          <filter id="as_shadow" x="-10%" y="-10%" width="120%" height="120%">
            <feDropShadow dx="0" dy="1" stdDeviation="1" floodOpacity="0.15" />
          </filter>
        </defs>

        {/* Squircle Container */}
        <rect
          width="40"
          height="40"
          rx="10"
          fill="url(#as_bg_grad)"
          filter="url(#as_shadow)"
        />

        {/* Subtle Inner Border */}
        <rect
          x="0.5"
          y="0.5"
          width="39"
          height="39"
          rx="9.5"
          stroke="rgba(255, 255, 255, 0.2)"
          fill="none"
        />

        {/* Connected Ecosystem Node Lines */}
        <path
          d="M13 25 L21 27 L27 15"
          stroke="rgba(255, 255, 255, 0.35)"
          strokeWidth="1.75"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M13 16 L27 15"
          stroke="rgba(255, 255, 255, 0.25)"
          strokeWidth="1.5"
          strokeDasharray="2 2"
          strokeLinecap="round"
        />

        {/* Node 1 (Bottom-Left App Node) */}
        <rect
          x="10.5"
          y="22.5"
          width="5.5"
          height="5.5"
          rx="1.5"
          fill="#FFFFFF"
          fillOpacity="0.85"
        />

        {/* Node 2 (Top-Left App Node) */}
        <rect
          x="10.5"
          y="13"
          width="5"
          height="5"
          rx="1.5"
          fill="#FFFFFF"
          fillOpacity="0.6"
        />

        {/* Node 3 (Bottom-Center App Node) */}
        <rect
          x="19"
          y="24.5"
          width="5"
          height="5"
          rx="1.5"
          fill="#FFFFFF"
          fillOpacity="0.75"
        />

        {/* Scout Lens / Exploration Focal Ring (Top-Right) */}
        <circle
          cx="26.5"
          cy="14.5"
          r="6"
          stroke="url(#as_lens_grad)"
          strokeWidth="2"
          fill="none"
        />

        {/* Scout Directional Beam Point / Central Star */}
        <path
          d="M26.5 11.5 L27.5 14 L30 14.5 L27.5 15 L26.5 17.5 L25.5 15 L23 14.5 L25.5 14 Z"
          fill="#FFFFFF"
        />

        {/* Scout Center Spark */}
        <circle cx="26.5" cy="14.5" r="1" fill="#06B6D4" />
      </svg>

      {/* Optional Typography Wordmark */}
      {showWordmark && (
        <div className="flex flex-col">
          <span className="text-base font-bold text-slate-900 tracking-tight leading-tight">
            AppScout
          </span>
          <span className="text-[11px] font-medium text-slate-400 leading-none mt-0.5">
            App Directory & Insights
          </span>
        </div>
      )}
    </div>
  );
};
export default AppScoutLogo;
