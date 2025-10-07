import React from 'react';

export type TimeRangeGranularity = 'daily' | 'monthly';
export type TimeRangePeriod = '1D' | '1W' | '1M' | '3M' | '6M' | '1Y' | 'ALL' | 'CUSTOM';

export interface TimeRangeSelectorProps {
  granularity: TimeRangeGranularity;
  period: TimeRangePeriod;
  onGranularityChange: (granularity: TimeRangeGranularity) => void;
  onPeriodChange: (period: TimeRangePeriod) => void;
}

const ZOOM_OPTIONS: { value: TimeRangePeriod; label: string; description: string }[] = [
  { value: '1D', label: '1D', description: '±10 days from today' },
  { value: '1W', label: '1W', description: '±10 weeks from today' },
  { value: '1M', label: '1M', description: '±10 months from today' },
  { value: '3M', label: '3M', description: '±6 quarters from today' },
  { value: '6M', label: '6M', description: '±2 years from today' },
  { value: '1Y', label: '1Y', description: '±3 years from today' },
  { value: 'ALL', label: 'ALL', description: 'All history' },
  { value: 'CUSTOM', label: 'Custom', description: 'Custom date range' }
];

export const TimeRangeSelector: React.FC<TimeRangeSelectorProps> = ({
  granularity,
  period,
  onPeriodChange
}) => {
  return (
    <div className="mb-4">
      {/* Simplified zoom selector */}
      <div className="flex flex-wrap gap-2">
        {ZOOM_OPTIONS.map((option) => (
          <button
            key={option.value}
            onClick={() => onPeriodChange(option.value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              period === option.value
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30 scale-105'
                : 'bg-slate-700/50 text-slate-300 hover:bg-slate-600/70 hover:scale-102'
            }`}
            title={option.description}
          >
            {option.label}
          </button>
        ))}
      </div>
      <div className="mt-2 text-xs text-slate-400 flex items-center gap-2">
        <span className="inline-block w-2 h-2 rounded-full bg-blue-500"></span>
        <span>
          Showing: {granularity === 'daily' ? 'Daily view' : 'Monthly view'}
          {period !== 'ALL' && ` • ${ZOOM_OPTIONS.find(o => o.value === period)?.description}`}
        </span>
      </div>
    </div>
  );
};
