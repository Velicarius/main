import { useState, useMemo, useCallback, useEffect } from 'react';
import { StrategyParams } from '../../types/strategy';
import { TimeRangeSelector, TimeRange } from './TimeRangeSelector';
import { TimelineChart, TimelineDataPoint } from './TimelineChart';
import { DateRangePicker, DateRange } from './DateRangePicker';
// Using native Date methods instead of date-fns

// Sacred Timeline component showing portfolio value over time
export interface SacredTimelineProps {
  currency: 'USD' | 'EUR' | 'PLN';
  currentTotalValue: number;                       // current portfolio value
  actualSeries: { date: string; value: number }[];  // EOD history up to today
  strategy?: StrategyParams;                       // strategy data with start_date, target_date, target_value
  loading?: boolean;                               // loading state
}

export function SacredTimeline({
  currency,
  currentTotalValue,
  actualSeries,
  strategy,
  loading = false
}: SacredTimelineProps) {

  // State management with localStorage persistence
  const [selectedTimeRange, setSelectedTimeRange] = useState<TimeRange>(() => {
    const saved = localStorage.getItem('sacred-timeline-time-range');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        // Fallback to default
      }
    }
    return { label: '1M', days: 30, aggregation: 'weekly' };
  });

  const [selectedDateRange, setSelectedDateRange] = useState<DateRange>(() => {
    const saved = localStorage.getItem('sacred-timeline-date-range');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return {
          start: new Date(parsed.start),
          end: new Date(parsed.end),
          label: parsed.label
        };
      } catch {
        // Fallback to default
      }
    }
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - 29);
    return {
      start,
      end,
      label: 'Last 30 days'
    };
  });

  const [useCustomRange, setUseCustomRange] = useState(false);

  // Persist state to localStorage
  useEffect(() => {
    localStorage.setItem('sacred-timeline-time-range', JSON.stringify(selectedTimeRange));
  }, [selectedTimeRange]);

  useEffect(() => {
    localStorage.setItem('sacred-timeline-date-range', JSON.stringify({
      start: selectedDateRange.start.toISOString(),
      end: selectedDateRange.end.toISOString(),
      label: selectedDateRange.label
    }));
  }, [selectedDateRange]);

  // Handle time range change (preset buttons)
  const handleTimeRangeChange = useCallback((newRange: TimeRange) => {
    setSelectedTimeRange(newRange);
    setUseCustomRange(false);
  }, []);

  // Handle date range change (custom picker)
  const handleDateRangeChange = useCallback((newRange: DateRange) => {
    setSelectedDateRange(newRange);
    setUseCustomRange(true);
  }, []);

  // Format currency based on currency type
  const formatCurrency = useCallback((value: number) => {
    const locale = currency === 'EUR' ? 'de-DE' : currency === 'PLN' ? 'pl-PL' : 'en-US';
    const currencyCode = currency === 'USD' ? 'USD' : currency === 'EUR' ? 'EUR' : 'PLN';

    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currencyCode,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  }, [currency]);


  // Aggregate data by granularity and filter by period
  const aggregatedData = useMemo(() => {
    const now = new Date();
    const today = now.toISOString().split('T')[0];

    // Add current value as today's point
    const seriesWithCurrent = [
      ...actualSeries,
      {
        date: today,
        value: currentTotalValue
      }
    ];

    // Remove duplicates and sort by date
    const uniqueSeries = seriesWithCurrent.reduce((acc: any[], point: any) => {
      const existing = acc.find(p => p.date === point.date);
      if (!existing) {
        acc.push(point);
      } else {
        // Keep the current value if there's a duplicate for today
        if (point.date === today) {
          existing.value = point.value;
        }
      }
      return acc;
    }, []).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

    if (uniqueSeries.length === 0) return [];

    // Determine date range to filter
    let startDate: Date;
    let endDate: Date;

    if (useCustomRange) {
      startDate = selectedDateRange.start;
      endDate = selectedDateRange.end;
    } else {
      // Use time range presets
      const daysBack = selectedTimeRange.days;
      startDate = new Date();
      startDate.setDate(now.getDate() - daysBack);
      endDate = now;
    }

    // Filter data by date range
    const filteredData = uniqueSeries.filter(point => {
      const pointDate = new Date(point.date);
      return pointDate >= startDate && pointDate <= endDate;
    });

    // Apply aggregation based on time range
    let processedData = filteredData;

    if (selectedTimeRange.aggregation === 'monthly') {
      // Group by month and take last value of each month
      const monthlyMap = new Map<string, { date: string; value: number }>();

      filteredData.forEach(point => {
        const date = new Date(point.date);
        const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;

        // Always update with the latest value for the month
        if (!monthlyMap.has(monthKey) || new Date(point.date) > new Date(monthlyMap.get(monthKey)!.date)) {
          monthlyMap.set(monthKey, point);
        }
      });

      processedData = Array.from(monthlyMap.values()).sort(
        (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
      );
    } else if (selectedTimeRange.aggregation === 'weekly') {
      // Group by week (Monday to Sunday)
      const weeklyMap = new Map<string, { date: string; value: number }>();

      filteredData.forEach(point => {
        const date = new Date(point.date);
        // Get Monday of the week
        const monday = new Date(date);
        const dayOfWeek = date.getDay();
        const diff = date.getDate() - dayOfWeek + (dayOfWeek === 0 ? -6 : 1);
        monday.setDate(diff);
        
        const weekKey = `${monday.getFullYear()}-W${String(Math.ceil((monday.getDate() + 6) / 7)).padStart(2, '0')}`;

        // Always update with the latest value for the week
        if (!weeklyMap.has(weekKey) || new Date(point.date) > new Date(weeklyMap.get(weekKey)!.date)) {
          weeklyMap.set(weekKey, point);
        }
      });

      processedData = Array.from(weeklyMap.values()).sort(
        (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
      );
    }

    return processedData.map(point => ({
      date: point.date,
      value: point.value
    }));
  }, [actualSeries, selectedTimeRange, selectedDateRange, useCustomRange, currentTotalValue]);

  // Calculate target series for strategy goal
  const targetSeries = useMemo(() => {
    if (!strategy?.targetGoalValue || !strategy?.targetDate) {
      return [];
    }
    
    // Target line starts TODAY with current value
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const endDate = new Date(strategy.targetDate);
    const startValue = currentTotalValue;
    const endValue = strategy.targetGoalValue;
    
    // Check that target_date is in the future
    if (endDate <= today) {
      return [];
    }
    
    // Adjust granularity based on aggregation for target series
    let intervalDays: number;
    if (selectedTimeRange.aggregation === 'weekly') {
      intervalDays = 7;
    } else if (selectedTimeRange.aggregation === 'daily') {
      intervalDays = 1;
    } else {
      intervalDays = 30; // Monthly intervals
    }
    
    const totalDays = Math.ceil((endDate.getTime() - today.getTime()) / (24 * 60 * 60 * 1000));
    const intervals = Math.ceil(totalDays / intervalDays);
    const growthPerInterval = (endValue - startValue) / intervals;
    
    return Array.from({ length: intervals + 1 }, (_, i) => {
      const date = new Date(today.getTime() + i * intervalDays * 24 * 60 * 60 * 1000);
      return {
        date: date.toISOString().split('T')[0],
        value: startValue + (growthPerInterval * i)
      };
    });
  }, [strategy?.targetGoalValue, strategy?.targetDate, currentTotalValue, selectedTimeRange.aggregation]);

  // Combine actual and target data for chart
  const chartData: TimelineDataPoint[] = useMemo(() => {
    const dataMap = new Map<string, TimelineDataPoint>();

    // Add historical data
    aggregatedData.forEach(point => {
      dataMap.set(point.date, { 
        date: point.date, 
        actual: point.value,
        target: 0,
        pnl: 0
      });
    });

    // Filter target series to match the visible date range from aggregatedData
    if (aggregatedData.length > 0) {
      const firstDate = new Date(aggregatedData[0].date);
      const lastDate = new Date(aggregatedData[aggregatedData.length - 1].date);

      // Add target trajectory only within visible range
      targetSeries
        .filter((point: { date: string; value: number }) => {
          const pointDate = new Date(point.date);
          return pointDate >= firstDate && pointDate <= lastDate;
        })
        .forEach((point: { date: string; value: number }) => {
          const existing = dataMap.get(point.date);
          if (existing) {
            existing.target = point.value;
          } else {
            dataMap.set(point.date, { 
              date: point.date, 
              actual: 0, 
              target: point.value,
              pnl: 0
            });
          }
        });
    }

    // Calculate P&L for each point
    const firstPoint = aggregatedData[0];
    if (firstPoint) {
      dataMap.forEach((point) => {
        point.pnl = point.actual - firstPoint.value;
      });
    }

    // Convert Map to array and sort by date
    return Array.from(dataMap.values()).sort((a, b) =>
      new Date(a.date).getTime() - new Date(b.date).getTime()
    );
  }, [aggregatedData, targetSeries]);

  // Calculate metrics for the selected period
  const periodMetrics = useMemo(() => {
    if (aggregatedData.length === 0) {
      return {
        portfolioSize: currentTotalValue,
        periodPnL: 0,
        periodPnLPercent: 0,
        targetValue: strategy?.targetGoalValue || 0,
        deltaToTarget: strategy?.targetGoalValue ? strategy.targetGoalValue - currentTotalValue : 0
      };
    }

    // Get first value in the displayed period
    const firstPoint = aggregatedData[0];

    const periodPnL = currentTotalValue - firstPoint.value;
    const periodPnLPercent = firstPoint.value > 0 ? (periodPnL / firstPoint.value) * 100 : 0;

    return {
      portfolioSize: currentTotalValue,
      periodPnL,
      periodPnLPercent,
      targetValue: strategy?.targetGoalValue || 0,
      deltaToTarget: strategy?.targetGoalValue ? strategy.targetGoalValue - currentTotalValue : 0
    };
  }, [aggregatedData, currentTotalValue, strategy?.targetGoalValue]);

  // Tooltip component is now handled by TimelineChart

  // Loading state
  if (loading) {
    return (
      <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
        <div className="animate-pulse">
          <div className="h-6 bg-slate-700 rounded mb-4 w-1/3"></div>
          <div className="h-64 bg-slate-700 rounded"></div>
        </div>
      </div>
    );
  }

  // No strategy state
  if (!strategy) {
    return (
      <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
        <div className="text-center py-8">
          <div className="text-slate-400 mb-4">
            <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">Strategy Not Configured</h3>
          <p className="text-slate-400 mb-4">
            Set up your investment strategy to view the timeline
          </p>
          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
            Configure Strategy
          </button>
        </div>
      </div>
    );
  }

  // No history state - show only current value point
  if (actualSeries.length === 0) {
    const today = new Date().toISOString().split('T')[0];
    const noHistoryData = [{
      date: today,
      value: currentTotalValue
    }];

    return (
      <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
        {/* Header */}
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-white">Sacred Timeline</h3>
          <span className="text-sm text-slate-400">Portfolio Value Over Time</span>
        </div>

        {/* Time range controls */}
        <TimeRangeSelector
          value={selectedTimeRange}
          onChange={handleTimeRangeChange}
        />

        {/* Chart */}
        <TimelineChart
          data={noHistoryData.map(p => ({ 
            date: p.date, 
            actual: p.value,
            target: 0,
            pnl: 0
          }))}
        />

        <div className="mt-4 text-center text-slate-400 text-sm">
          No portfolio history available. Showing current value only.
        </div>
      </div>
    );
  }

  // Main render with history
  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg" data-testid="sacred-timeline">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-white">Sacred Timeline</h3>
        <span className="text-sm text-slate-400">Portfolio Value Over Time</span>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between mb-6">
        <TimeRangeSelector
          value={selectedTimeRange}
          onChange={handleTimeRangeChange}
        />
        <DateRangePicker
          value={selectedDateRange}
          onChange={handleDateRangeChange}
        />
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {/* Portfolio Size */}
        <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600/30" data-testid="sacred-summary-size">
          <div className="text-xs text-slate-400 mb-1">Portfolio Size</div>
          <div className="text-xl font-bold text-white">
            {formatCurrency(periodMetrics.portfolioSize)}
          </div>
        </div>

        {/* Period P&L */}
        <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600/30" data-testid="sacred-summary-pnl">
          <div className="text-xs text-slate-400 mb-1">Period P&L</div>
          <div className={`text-xl font-bold ${periodMetrics.periodPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {periodMetrics.periodPnL >= 0 ? '+' : ''}{formatCurrency(periodMetrics.periodPnL)}
          </div>
          <div className={`text-xs ${periodMetrics.periodPnLPercent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {periodMetrics.periodPnLPercent >= 0 ? '+' : ''}{periodMetrics.periodPnLPercent.toFixed(2)}%
          </div>
          <div className="text-xs text-slate-500 mt-1">for selected window</div>
        </div>

        {/* Target Value */}
        <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600/30" data-testid="sacred-summary-target">
          <div className="text-xs text-slate-400 mb-1">Target Value</div>
          <div className="text-xl font-bold text-blue-400">
            {periodMetrics.targetValue > 0 ? formatCurrency(periodMetrics.targetValue) : '—'}
          </div>
        </div>

        {/* Delta to Target */}
        <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600/30" data-testid="sacred-summary-delta">
          <div className="text-xs text-slate-400 mb-1">Delta to Target</div>
          <div className={`text-xl font-bold ${periodMetrics.deltaToTarget <= 0 ? 'text-green-400' : 'text-amber-400'}`}>
            {periodMetrics.targetValue > 0 ? (
              <>
                {periodMetrics.deltaToTarget >= 0 ? '+' : ''}{formatCurrency(periodMetrics.deltaToTarget)}
              </>
            ) : '—'}
          </div>
        </div>
      </div>

      {/* Chart */}
      <TimelineChart
        data={chartData}
        targetValue={strategy?.targetGoalValue}
      />
    </div>
  );
}