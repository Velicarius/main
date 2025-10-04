import React from 'react';

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  badge?: {
    text: string;
    variant: 'success' | 'warning' | 'danger' | 'neutral';
  };
  icon?: React.ReactNode;
  asOf?: string;
  isLoading?: boolean;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  subtitle,
  badge,
  icon,
  asOf,
  isLoading = false
}) => {
  const getBadgeClasses = (variant: string) => {
    switch (variant) {
      case 'success': return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'warning': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'danger': return 'bg-red-500/20 text-red-400 border-red-500/30';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  if (isLoading) {
    return (
      <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
        <div className="animate-pulse">
          <div className="h-4 bg-slate-700 rounded w-2/3 mb-4"></div>
          <div className="h-8 bg-slate-700 rounded w-1/2 mb-2"></div>
          <div className="h-3 bg-slate-700 rounded w-full"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg hover:shadow-xl transition-all duration-300">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">{title}</h3>
        {icon && (
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            {icon}
          </div>
        )}
      </div>
      
      <div className="text-center">
        <div className="text-3xl font-bold text-white mb-2">
          {typeof value === 'string' && value === '—' ? '—' : value}
        </div>
        
        {subtitle && (
          <div className="text-sm text-slate-400 mb-3">{subtitle}</div>
        )}
        
        {badge && (
          <div className="mb-3">
            <span className={`inline-flex px-3 py-1 rounded-full text-xs font-medium border ${getBadgeClasses(badge.variant)}`}>
              {badge.text}
            </span>
          </div>
        )}

        {asOf && (
          <div className="text-xs text-slate-500">
            as of {asOf}
          </div>
        )}
      </div>
    </div>
  );
};







