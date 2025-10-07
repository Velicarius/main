import { useState, useMemo, useCallback } from 'react';
import { StrategyParams } from '../../types/strategy';
import { TimeRangeSelector, TimeRangeGranularity, TimeRangePeriod } from './TimeRangeSelector';
import { TimelineChart, ChartDataPoint } from './TimelineChart';
import { TimelineTooltip } from './TimelineTooltip';
import { DateRangePicker } from './DateRangePicker';

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

  const [granularity, setGranularity] = useState<TimeRangeGranularity>('daily');
  const [period, setPeriod] = useState<TimeRangePeriod>('1D');
  const [customStartDate, setCustomStartDate] = useState<string | null>(null);
  const [customEndDate, setCustomEndDate] = useState<string | null>(null);

  // Auto-switch granularity based on period for optimal viewing
  const handlePeriodChange = useCallback((newPeriod: TimeRangePeriod) => {
    setPeriod(newPeriod);

    // Reset custom dates when switching away from CUSTOM
    if (newPeriod !== 'CUSTOM') {
      setCustomStartDate(null);
      setCustomEndDate(null);
    }

    // Auto-select granularity based on zoom level
    // 1D, 1W → Daily view (show individual days/weeks)
    // 1M, 3M → Daily view (still detailed enough)
    // 6M, 1Y, ALL → Monthly view for better overview
    if (['1D', '1W', '1M', '3M'].includes(newPeriod)) {
      setGranularity('daily');
    } else if (newPeriod === 'CUSTOM') {
      // For custom range, default to daily
      setGranularity('daily');
    } else {
      setGranularity('monthly');
    }
  }, []);

  // Handle custom date range application
  const handleApplyCustomRange = useCallback((startDate: string, endDate: string) => {
    setCustomStartDate(startDate);
    setCustomEndDate(endDate);
    setPeriod('CUSTOM');
    setGranularity('daily');
  }, []);

  // Handle custom date range reset
  const handleResetCustomRange = useCallback(() => {
    setCustomStartDate(null);
    setCustomEndDate(null);
    setPeriod('ALL');
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

  // Format date for X-axis based on granularity and period
  const formatXAxisDate = useCallback((dateStr: string) => {
    const date = new Date(dateStr);

    if (period === '1W') {
      // For weekly view, show week range
      const monday = new Date(date);
      const dayOfWeek = date.getDay();
      const diff = date.getDate() - dayOfWeek + (dayOfWeek === 0 ? -6 : 1);
      monday.setDate(diff);
      
      const sunday = new Date(monday);
      sunday.setDate(monday.getDate() + 6);
      
      return `${monday.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${sunday.toLocaleDateString('en-US', { day: 'numeric' })}`;
    } else if (granularity === 'daily') {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    }
  }, [granularity, period]);

  // Format tooltip date
  const formatTooltipDate = useCallback((dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      weekday: 'short'
    });
  }, []);

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

    // Apply granularity aggregation
    let processedData = uniqueSeries;

    if (granularity === 'monthly') {
      // Group by month and take last value of each month
      const monthlyMap = new Map<string, { date: string; value: number }>();

      uniqueSeries.forEach(point => {
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
    } else if (period === '1W') {
      // For weekly view, group by week (Monday to Sunday)
      const weeklyMap = new Map<string, { date: string; value: number }>();

      uniqueSeries.forEach(point => {
        const date = new Date(point.date);
        // Get Monday of the week
        const monday = new Date(date);
        const dayOfWeek = date.getDay();
        const diff = date.getDate() - dayOfWeek + (dayOfWeek === 0 ? -6 : 1); // Adjust when day is Sunday
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

    // Apply period filter - SYMMETRIC (past + future from today)
    if (period === 'ALL') {
      return processedData.map(point => ({
        date: point.date,
        value: point.value
      }));
    }

    if (period === 'CUSTOM' && customStartDate && customEndDate) {
      const start = new Date(customStartDate);
      const end = new Date(customEndDate);
      return processedData
        .filter(point => {
          const pointDate = new Date(point.date);
          return pointDate >= start && pointDate <= end;
        })
        .map(point => ({
          date: point.date,
          value: point.value
        }));
    }

    // Symmetric zoom: show X units in past AND X units in future
    let unitsInPastAndFuture: number;
    let unitInDays: number;

    switch (period) {
      case '1D':
        unitsInPastAndFuture = 10; // 10 days past, 10 days future
        unitInDays = 1;
        break;
      case '1W':
        unitsInPastAndFuture = 10; // 10 weeks past, 10 weeks future
        unitInDays = 7;
        break;
      case '1M':
        unitsInPastAndFuture = 10; // 10 months past, 10 months future
        unitInDays = 30;
        break;
      case '3M':
        unitsInPastAndFuture = 6; // 6 quarters past, 6 quarters future
        unitInDays = 90;
        break;
      case '6M':
        unitsInPastAndFuture = 4; // 4 half-years past, 4 half-years future
        unitInDays = 180;
        break;
      case '1Y':
        unitsInPastAndFuture = 3; // 3 years past, 3 years future
        unitInDays = 365;
        break;
      default:
        return processedData.map(point => ({
          date: point.date,
          value: point.value
        }));
    }

    const rangeInMs = unitsInPastAndFuture * unitInDays * 24 * 60 * 60 * 1000;
    const startDate = new Date(now.getTime() - rangeInMs);
    const endDate = new Date(now.getTime() + rangeInMs);

    return processedData
      .filter(point => {
        const pointDate = new Date(point.date);
        return pointDate >= startDate && pointDate <= endDate;
      })
      .map(point => ({
        date: point.date,
        value: point.value
      }));
  }, [actualSeries, granularity, period, currentTotalValue, customStartDate, customEndDate]);

  // Calculate target series for strategy goal
  const targetSeries = useMemo(() => {
    console.log('SacredTimeline strategy:', strategy);
    console.log('targetGoalValue:', strategy?.targetGoalValue);
    console.log('targetDate:', strategy?.targetDate);
    
    if (!strategy?.targetGoalValue || !strategy?.targetDate) {
      console.log('No target data, returning empty series');
      return [];
    }
    
    // Target line starts TODAY with current value
    const today = new Date();
    today.setHours(0, 0, 0, 0); // Reset time to start of day
    
    const endDate = new Date(strategy.targetDate);
    const startValue = currentTotalValue;
    const endValue = strategy.targetGoalValue;
    
    // Check that target_date is in the future
    if (endDate <= today) {
      return [];
    }
    
    // Adjust granularity based on period for target series
    let intervalDays: number;
    if (period === '1W') {
      intervalDays = 7; // Weekly intervals
    } else if (period === '1D') {
      intervalDays = 1; // Daily intervals
    } else {
      intervalDays = 30; // Monthly intervals for longer periods
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
  }, [strategy?.targetGoalValue, strategy?.targetDate, currentTotalValue, period]);

  // Combine actual and target data for chart
  const chartData: ChartDataPoint[] = useMemo(() => {
    const dataMap = new Map<string, ChartDataPoint>();

    // Add historical data
    aggregatedData.forEach(point => {
      dataMap.set(point.date, { date: point.date, actual: point.value });
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
            dataMap.set(point.date, { date: point.date, actual: null, target: point.value });
          }
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

  // Create tooltip component wrapper with bound formatting functions
  const TooltipComponent = useCallback((props: any) => {
    const firstPoint = aggregatedData.length > 0 ? aggregatedData[0] : null;
    return (
      <TimelineTooltip
        {...props}
        formatCurrency={formatCurrency}
        formatDate={formatTooltipDate}
        firstPointValue={firstPoint?.value}
        targetValue={strategy?.targetGoalValue}
        currentTotalValue={currentTotalValue}
      />
    );
  }, [formatCurrency, formatTooltipDate, aggregatedData, strategy?.targetGoalValue, currentTotalValue]);

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
          granularity={granularity}
          period={period}
          onGranularityChange={setGranularity}
          onPeriodChange={handlePeriodChange}
        />

        {/* Chart */}
        <TimelineChart
          data={noHistoryData.map(p => ({ date: p.date, actual: p.value }))}
          granularity={granularity}
          formatCurrency={formatCurrency}
          formatXAxisDate={formatXAxisDate}
          tooltipContent={TooltipComponent}
          showTarget={false}
        />

        <div className="mt-4 text-center text-slate-400 text-sm">
          No portfolio history available. Showing current value only.
        </div>
      </div>
    );
  }

  // Main render with history
  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-white">Sacred Timeline</h3>
        <span className="text-sm text-slate-400">Portfolio Value Over Time</span>
      </div>

      {/* Time range controls */}
      <TimeRangeSelector
        granularity={granularity}
        period={period}
        onGranularityChange={setGranularity}
        onPeriodChange={handlePeriodChange}
      />

      {/* Custom Date Range Picker */}
      <DateRangePicker
        isActive={period === 'CUSTOM'}
        onApply={handleApplyCustomRange}
        onReset={handleResetCustomRange}
      />

      {/* Period Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {/* Portfolio Size */}
        <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600/30">
          <div className="text-xs text-slate-400 mb-1">Portfolio Size</div>
          <div className="text-xl font-bold text-white">
            {formatCurrency(periodMetrics.portfolioSize)}
          </div>
        </div>

        {/* Period P&L */}
        <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600/30">
          <div className="text-xs text-slate-400 mb-1">Period P&L</div>
          <div className={`text-xl font-bold ${periodMetrics.periodPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {periodMetrics.periodPnL >= 0 ? '+' : ''}{formatCurrency(periodMetrics.periodPnL)}
          </div>
          <div className={`text-xs ${periodMetrics.periodPnLPercent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {periodMetrics.periodPnLPercent >= 0 ? '+' : ''}{periodMetrics.periodPnLPercent.toFixed(2)}%
          </div>
        </div>

        {/* Target Value */}
        <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600/30">
          <div className="text-xs text-slate-400 mb-1">Target Value</div>
          <div className="text-xl font-bold text-blue-400">
            {periodMetrics.targetValue > 0 ? formatCurrency(periodMetrics.targetValue) : '—'}
          </div>
        </div>

        {/* Delta to Target */}
        <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600/30">
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
        key={`${period}-${granularity}`}
        data={chartData}
        granularity={granularity}
        formatCurrency={formatCurrency}
        formatXAxisDate={formatXAxisDate}
        tooltipContent={TooltipComponent}
        showTarget={true}
      />
    </div>
  );
}