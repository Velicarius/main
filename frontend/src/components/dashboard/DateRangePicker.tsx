import React, { useState, useRef, useEffect } from 'react';

export interface DateRange {
  start: Date;
  end: Date;
  label: string;
}

interface DateRangePickerProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
  className?: string;
}

const PRESETS: Array<{ label: string; getRange: () => DateRange }> = [
  {
    label: 'Last 7 days',
    getRange: () => {
      const end = new Date();
      const start = new Date();
      start.setDate(end.getDate() - 6);
      return {
        start,
        end,
        label: 'Last 7 days'
      };
    }
  },
  {
    label: 'Last 30 days',
    getRange: () => {
      const end = new Date();
      const start = new Date();
      start.setDate(end.getDate() - 29);
      return {
        start,
        end,
        label: 'Last 30 days'
      };
    }
  },
  {
    label: 'Month to Date',
    getRange: () => {
      const end = new Date();
      const start = new Date(end.getFullYear(), end.getMonth(), 1);
      return {
        start,
        end,
        label: 'Month to Date'
      };
    }
  },
  {
    label: 'Year to Date',
    getRange: () => {
      const end = new Date();
      const start = new Date(end.getFullYear(), 0, 1);
      return {
        start,
        end,
        label: 'Year to Date'
      };
    }
  }
];

export const DateRangePicker: React.FC<DateRangePickerProps> = ({
  value,
  onChange,
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [tempStart, setTempStart] = useState<Date | null>(null);
  const [tempEnd, setTempEnd] = useState<Date | null>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Close popover when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setTempStart(null);
        setTempEnd(null);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handlePresetClick = (preset: typeof PRESETS[0]) => {
    const range = preset.getRange();
    onChange(range);
    setIsOpen(false);
  };

  const handleDateClick = (date: Date) => {
    if (!tempStart || (tempStart && tempEnd)) {
      // Start new selection
      setTempStart(date);
      setTempEnd(null);
    } else {
      // Complete selection
      const start = date < tempStart ? date : tempStart;
      const end = date > tempStart ? date : tempStart;
      setTempEnd(end);
      
      // Auto-apply selection after a brief delay
      setTimeout(() => {
        const customRange: DateRange = {
          start,
          end,
          label: `Custom: ${start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} – ${end.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`
        };
        onChange(customRange);
        setIsOpen(false);
        setTempStart(null);
        setTempEnd(null);
      }, 300);
    }
  };

  const isDateSelected = (date: Date) => {
    if (tempStart && tempEnd) {
      return (date.toDateString() === tempStart.toDateString() || date.toDateString() === tempEnd.toDateString()) ||
             (date > tempStart && date < tempEnd);
    }
    if (tempStart) {
      return date.toDateString() === tempStart.toDateString();
    }
    return false;
  };

  const isDateInRange = (date: Date) => {
    if (tempStart && tempEnd) {
      return date > tempStart && date < tempEnd;
    }
    return false;
  };

  const generateCalendarDays = (year: number, month: number) => {
    const firstDay = new Date(year, month, 1);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());
    
    const days = [];
    const current = new Date(startDate);
    
    for (let i = 0; i < 42; i++) {
      days.push(new Date(current));
      current.setDate(current.getDate() + 1);
    }
    
    return days;
  };

  const today = new Date();
  const currentMonth = tempStart ? tempStart.getMonth() : today.getMonth();
  const currentYear = tempStart ? tempStart.getFullYear() : today.getFullYear();
  const calendarDays = generateCalendarDays(currentYear, currentMonth);

  return (
    <div className={`relative ${className}`} ref={popoverRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="px-4 py-2 bg-slate-700/50 border border-slate-600/50 rounded-lg text-slate-200 hover:bg-slate-600/50 transition-colors flex items-center gap-2"
        data-testid="sacred-range-picker"
      >
        <span>📅</span>
        <span className="text-sm">{value.label}</span>
        <span className="text-xs text-slate-400">▼</span>
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 bg-slate-800 border border-slate-600 rounded-lg shadow-xl z-50 p-4 min-w-[600px]">
          <div className="grid grid-cols-2 gap-6">
            {/* Presets */}
            <div>
              <h3 className="text-sm font-medium text-slate-300 mb-3">Quick Presets</h3>
              <div className="space-y-2">
                {PRESETS.map((preset) => (
                  <button
                    key={preset.label}
                    onClick={() => handlePresetClick(preset)}
                    className="w-full text-left px-3 py-2 text-sm text-slate-300 hover:bg-slate-700/50 rounded transition-colors"
                  >
                    {preset.label}
                  </button>
                ))}
                <button
                  onClick={() => {
                    const start = new Date();
                    start.setDate(today.getDate() - 6);
                    const customRange: DateRange = {
                      start,
                      end: today,
                      label: 'Custom: Last 7 days'
                    };
                    onChange(customRange);
                    setIsOpen(false);
                  }}
                  className="w-full text-left px-3 py-2 text-sm text-slate-300 hover:bg-slate-700/50 rounded transition-colors border-t border-slate-600 pt-3 mt-3"
                >
                  Custom range…
                </button>
              </div>
            </div>

            {/* Calendar */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-slate-300">
                  {new Date(currentYear, currentMonth).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                </h3>
                <div className="flex gap-1">
                  <button
                    onClick={() => {
                      const prevMonth = new Date(currentYear, currentMonth - 1);
                      setTempStart(prevMonth);
                    }}
                    className="p-1 text-slate-400 hover:text-slate-200"
                  >
                    ←
                  </button>
                  <button
                    onClick={() => {
                      const nextMonth = new Date(currentYear, currentMonth + 1);
                      setTempStart(nextMonth);
                    }}
                    className="p-1 text-slate-400 hover:text-slate-200"
                  >
                    →
                  </button>
                </div>
              </div>

              {/* Calendar Grid */}
              <div className="grid grid-cols-7 gap-1 text-xs">
                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
                  <div key={day} className="p-2 text-center text-slate-400 font-medium">
                    {day}
                  </div>
                ))}
                {calendarDays.map((date, index) => {
                  const isCurrentMonth = date.getMonth() === currentMonth;
                  const isToday = date.toDateString() === today.toDateString();
                  const isSelected = isDateSelected(date);
                  const isInRange = isDateInRange(date);
                  
                  return (
                    <button
                      key={index}
                      onClick={() => handleDateClick(date)}
                      className={`
                        p-2 text-xs rounded transition-colors
                        ${!isCurrentMonth ? 'text-slate-600' : 'text-slate-200'}
                        ${isToday ? 'bg-blue-600/20 text-blue-300' : ''}
                        ${isSelected ? 'bg-blue-600 text-white' : ''}
                        ${isInRange ? 'bg-blue-600/30' : ''}
                        hover:bg-slate-700/50
                      `}
                    >
                      {date.getDate()}
                    </button>
                  );
                })}
              </div>

              {tempStart && (
                <div className="mt-3 text-xs text-slate-400">
                  {tempEnd ? (
                    <span>
                      Selected: {tempStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} – {tempEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    </span>
                  ) : (
                    <span>
                      Click end date to complete selection
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};