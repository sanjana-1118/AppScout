import React from 'react';
import { Loader2, AlertTriangle, RefreshCw, HelpCircle } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading data...',
}) => (
  <div className="flex flex-col items-center justify-center py-24 text-center p-8">
    <div className="p-3 bg-blue-50 text-blue-600 rounded-full mb-3 animate-spin">
      <Loader2 className="w-6 h-6" />
    </div>
    <h4 className="text-sm font-bold text-slate-800">Loading Market Data</h4>
    <p className="text-xs text-slate-500 mt-1 max-w-sm">{message}</p>
  </div>
);

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Unable to load data',
  message = 'Please check your connection and try again.',
  onRetry,
}) => (
  <div className="bg-red-50/70 border border-red-200 rounded-xl p-6 text-center my-8 max-w-md mx-auto">
    <div className="w-10 h-10 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-3">
      <AlertTriangle className="w-5 h-5" />
    </div>
    <h4 className="text-sm font-bold text-red-900">{title}</h4>
    <p className="text-xs text-red-700 mt-1.5 leading-relaxed">{message}</p>
    {onRetry && (
      <button
        onClick={onRetry}
        className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors"
      >
        <RefreshCw className="w-3.5 h-3.5" />
        Retry Request
      </button>
    )}
  </div>
);

interface InfoTooltipProps {
  content: string;
}

export const InfoTooltip: React.FC<InfoTooltipProps> = ({ content }) => (
  <span className="group relative inline-flex items-center cursor-help ml-1 align-middle text-slate-400 hover:text-slate-600">
    <HelpCircle className="w-3.5 h-3.5" />
    <span className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 hidden w-56 p-2 bg-slate-900 text-white text-[11px] rounded-lg shadow-lg group-hover:block z-30 font-normal normal-case leading-tight text-center">
      {content}
    </span>
  </span>
);
