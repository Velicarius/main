import React from 'react';

export interface TimeRange {
  label: string;
  days: number;
  aggregation: 'daily' | 'weekly' | 'monthly';
}

interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
  className?: string;
}

const TIME_RANGES: TimeRange[] = [
  { label: '1D', days: 1, aggregation: 'daily' },
  { label: '1W', days: 7, aggregation: 'daily' },
  { label: '1M', days: 30, aggregation: 'weekly' },
  { label: '3M', days: 90, aggregation: 'weekly' },
  { label: '6M', days: 180, aggregation: 'monthly' },
  { label: '1Y', days: 365, aggregation: 'monthly' }
];

export const TimeRangeSelector: React.FC<TimeRangeSelectorProps> = ({
  value,
  onChange,
  className = ''
}) => {
  return (
    <div className={`inline-flex bg-slate-700/50 rounded-lg p-1 border border-slate-600/50 ${className}`} data-testid="sacred-range-buttons">
      {TIME_RANGES.map((range) => (
        <button
          key={range.label}
          onClick={() => onChange(range)}
          className={`
            relative px-3 py-2 text-sm font-medium rounded-md transition-all duration-200
            ${
              value.label === range.label
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-300 hover:text-white hover:bg-slate-600/50'
            }
          `}
        >
          {range.label}
        </button>
      ))}
    </div>
  );
};