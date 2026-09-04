import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface KPICardProps {
  label: string;
  value: string | number;
  description?: string;
  icon?: LucideIcon;
  trend?: string;
  variant?: 'default' | 'accent' | 'emerald' | 'indigo' | 'amber';
}

export const KPICard: React.FC<KPICardProps> = ({
  label,
  value,
  description,
  icon: Icon,
  trend,
  variant = 'default',
}) => {
  const variantStyles = {
    default: 'bg-white border-slate-200 text-slate-900',
    accent: 'bg-blue-50/50 border-blue-100 text-blue-950',
    emerald: 'bg-emerald-50/50 border-emerald-100 text-emerald-950',
    indigo: 'bg-indigo-50/50 border-indigo-100 text-indigo-950',
    amber: 'bg-amber-50/50 border-amber-100 text-amber-950',
  };

  const iconBgStyles = {
    default: 'bg-slate-100 text-slate-700',
    accent: 'bg-blue-100 text-blue-600',
    emerald: 'bg-emerald-100 text-emerald-600',
    indigo: 'bg-indigo-100 text-indigo-600',
    amber: 'bg-amber-100 text-amber-600',
  };

  return (
    <div className={`p-5 rounded-xl border shadow-sm transition-all hover:shadow-md ${variantStyles[variant]}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{label}</p>
          <p className="text-2xl font-bold mt-1 text-slate-900 tracking-tight">{value}</p>
        </div>
        {Icon && (
          <div className={`p-2.5 rounded-lg ${iconBgStyles[variant]}`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>
      {(description || trend) && (
        <div className="mt-3 flex items-center text-xs text-slate-500 gap-1.5">
          {trend && <span className="font-semibold text-emerald-600">{trend}</span>}
          {description && <span>{description}</span>}
        </div>
      )}
    </div>
  );
};
