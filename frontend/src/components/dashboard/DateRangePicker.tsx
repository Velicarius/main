import React, { useState } from 'react';

export interface DateRangePickerProps {
  onApply: (startDate: string, endDate: string) => void;
  onReset: () => void;
  isActive: boolean;
}

export const DateRangePicker: React.FC<DateRangePickerProps> = ({
  onApply,
  onReset,
  isActive
}) => {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const handleApply = () => {
    if (startDate && endDate) {
      onApply(startDate, endDate);
    }
  };

  const handleReset = () => {
    setStartDate('');
    setEndDate('');
    onReset();
  };

  return (
    <div className={`transition-all duration-300 overflow-hidden ${isActive ? 'max-h-32 opacity-100 mb-4' : 'max-h-0 opacity-0'}`}>
      <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600/30">
        <div className="flex flex-wrap items-end gap-3">
          {/* From Date */}
          <div className="flex-1 min-w-[140px]">
            <label className="block text-xs text-slate-400 mb-1">From</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* To Date */}
          <div className="flex-1 min-w-[140px]">
            <label className="block text-xs text-slate-400 mb-1">To</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <button
              onClick={handleApply}
              disabled={!startDate || !endDate}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Apply
            </button>
            <button
              onClick={handleReset}
              className="px-4 py-2 bg-slate-600 text-white rounded-lg text-sm font-medium hover:bg-slate-500 transition-colors"
            >
              Reset
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
