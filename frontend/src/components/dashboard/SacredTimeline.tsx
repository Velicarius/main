import { useState, useMemo, useCallback } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { CurrentValueChip } from '../common/CurrentValueChip';
import { StrategyParams } from '../../types/strategy';

// Sacred Timeline component showing portfolio value over time
export interface SacredTimelineProps {
  currency: 'USD' | 'EUR' | 'PLN';
  currentTotalValue: number;                       // current portfolio value
  actualSeries: { date: string; value: number }[];  // EOD history up to today
  strategy?: StrategyParams;                       // strategy data with start_date, target_date, target_value
  loading?: boolean;                               // loading state
}

type TimeRange = '1D' | '1W' | '1M' | 'ALL';

export function SacredTimeline({ 
  currency,
  currentTotalValue,
  actualSeries,
  strategy,
  loading = false
}: SacredTimelineProps) {
  
  const [timeRange, setTimeRange] = useState<TimeRange>('ALL');
  const [zoomState, setZoomState] = useState<{x: number, y: number} | null>(null);

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

  // Format date for X-axis based on time range
  const formatXAxisDate = useCallback((dateStr: string) => {
    const date = new Date(dateStr);
    
    switch (timeRange) {
      case '1D':
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      case '1W':
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      case '1M':
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      case 'ALL':
        return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
      default:
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
  }, [timeRange]);

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

  // Filter data based on time range and add current value
  const filteredData = useMemo(() => {
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

    let startDate: Date;

    switch (timeRange) {
      case '1D':
        startDate = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        break;
      case '1W':
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        break;
      case '1M':
        startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        break;
      case 'ALL':
      default:
        return uniqueSeries.map(point => ({
          date: point.date,
          value: point.value
        }));
    }

    return uniqueSeries
      .filter(point => new Date(point.date) >= startDate)
      .map(point => ({
        date: point.date,
        value: point.value
      }));
  }, [actualSeries, timeRange, currentTotalValue]);

  // Calculate target series for strategy goal
  const targetSeries = useMemo(() => {
    if (!strategy?.targetGoalValue || !strategy?.targetDate) {
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
    
    // Linear projection (can be improved later with compound interest)
    const monthsToTarget = Math.ceil((endDate.getTime() - today.getTime()) / (30 * 24 * 60 * 60 * 1000));
    const monthlyGrowth = (endValue - startValue) / monthsToTarget;
    
    return Array.from({ length: monthsToTarget + 1 }, (_, i) => {
      const date = new Date(today.getTime() + i * 30 * 24 * 60 * 60 * 1000);
      return {
        date: date.toISOString().split('T')[0],
        value: startValue + (monthlyGrowth * i)
      };
    });
  }, [strategy?.targetGoalValue, strategy?.targetDate, currentTotalValue]);

  // Combine actual and target data for chart
  const chartData = useMemo(() => {
    const dataMap = new Map();
    
    // Add historical data
    filteredData.forEach(point => {
      dataMap.set(point.date, { date: point.date, actual: point.value });
    });
    
    // Add target trajectory
    targetSeries.forEach(point => {
      const existing = dataMap.get(point.date);
      if (existing) {
        existing.target = point.value;
      } else {
        dataMap.set(point.date, { date: point.date, actual: null, target: point.value });
      }
    });
    
    // Convert Map to array and sort by date
    return Array.from(dataMap.values()).sort((a, b) => 
      new Date(a.date).getTime() - new Date(b.date).getTime()
    );
  }, [filteredData, targetSeries]);

  // Custom tooltip component
  const CustomTooltip = ({ active, payload, label }: {
    active?: boolean;
    payload?: any[];
    label?: string;
  }) => {
    if (active && payload && payload.length > 0) {
      return (
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-lg">
          <p className="text-white font-medium mb-1">
            {label ? formatTooltipDate(label) : ''}
          </p>
          {payload.map((entry: any) => {
            if (entry.value === null) return null;
            return (
              <p key={entry.dataKey} style={{ color: entry.stroke }}>
                {entry.name}: {formatCurrency(entry.value)}
              </p>
            );
          })}
        </div>
      );
    }
    return null;
  };

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
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white">Sacred Timeline</h3>
            <span className="text-sm text-slate-400">Portfolio Value Over Time</span>
          </div>
          <div className="flex items-center gap-3">
            <CurrentValueChip value={currentTotalValue} currency={currency} />
          </div>
        </div>

        {/* Time range controls */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex gap-2">
            {(['1D', '1W', '1M', 'ALL'] as TimeRange[]).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                  timeRange === range
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {range}
              </button>
            ))}
          </div>
          {zoomState && (
            <button
              onClick={() => setZoomState(null)}
              className="px-3 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded text-sm transition-colors"
            >
              Reset Zoom
            </button>
          )}
        </div>

        {/* Chart */}
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={noHistoryData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis 
                dataKey="date" 
                tick={{ fill: '#9CA3AF', fontSize: 12 }}
                tickFormatter={formatXAxisDate}
              />
              <YAxis 
                tick={{ fill: '#9CA3AF', fontSize: 12 }}
                tickFormatter={(value: number) => formatCurrency(value)}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend 
                wrapperStyle={{ paddingTop: '10px' }}
                iconType="line"
              />
              <Line 
                type="monotone" 
                dataKey="value" 
                stroke="#3B82F6" 
                strokeWidth={2}
                dot={{ fill: '#3B82F6', strokeWidth: 2, r: 4 }}
                activeDot={{ r: 6, stroke: '#3B82F6', strokeWidth: 2 }}
                name="Actual"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

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
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-white">Sacred Timeline</h3>
          <span className="text-sm text-slate-400">Portfolio Value Over Time</span>
        </div>
        <div className="flex items-center gap-3">
          <CurrentValueChip value={currentTotalValue} currency={currency} />
        </div>
      </div>

      {/* Time range controls */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-2">
          {(['1D', '1W', '1M', 'ALL'] as TimeRange[]).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                timeRange === range
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {range}
            </button>
          ))}
        </div>
        {zoomState && (
          <button
            onClick={() => setZoomState(null)}
            className="px-3 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded text-sm transition-colors"
          >
            Reset Zoom
          </button>
        )}
      </div>

      {/* Chart */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart 
            data={chartData}
            onMouseDown={(e: any) => {
              if (e && e.activeLabel) {
                setZoomState({ x: e.activeLabel, y: 0 });
              }
            }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis 
              dataKey="date" 
              tick={{ fill: '#9CA3AF', fontSize: 12 }}
              tickFormatter={formatXAxisDate}
            />
            <YAxis 
              tick={{ fill: '#9CA3AF', fontSize: 12 }}
              tickFormatter={(value: number) => formatCurrency(value)}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend 
              wrapperStyle={{ paddingTop: '10px' }}
              iconType="line"
            />
            {/* Historical line (blue) */}
            <Line
              type="monotone"
              dataKey="actual"
              stroke="#3B82F6"
              strokeWidth={2}
              dot={chartData.length <= 30 ? { fill: '#3B82F6', strokeWidth: 2, r: 3 } : false}
              activeDot={{ r: 6, stroke: '#3B82F6', strokeWidth: 2 }}
              name="Actual"
              connectNulls={false}
            />
            {/* Target trajectory (green dashed) */}
            <Line
              type="monotone"
              dataKey="target"
              stroke="#10B981"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              name="Target"
              connectNulls={true}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}