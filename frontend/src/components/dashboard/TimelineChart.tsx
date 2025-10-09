import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, ReferenceLine, Tooltip } from 'recharts';

export interface TimelineDataPoint {
  date: string;
  actual: number;
  target: number;
  pnl: number;
}

interface TimelineChartProps {
  data: TimelineDataPoint[];
  targetValue?: number;
  className?: string;
}

export const TimelineChart: React.FC<TimelineChartProps> = ({
  data,
  className = ''
}) => {
  const today = new Date();
  
  // Find today's position in the data
  const todayIndex = data.findIndex(point => {
    const pointDate = new Date(point.date);
    return pointDate.toDateString() === today.toDateString();
  });

  // Format currency for Y-axis
  const formatCurrency = (value: number) => {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`;
    } else if (value >= 1000) {
      return `$${(value / 1000).toFixed(0)}K`;
    }
    return `$${value.toFixed(0)}`;
  };

  // Format date for X-axis
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  // Custom tooltip component
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-lg">
          <p className="text-sm text-slate-300 mb-2">{new Date(label).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</p>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
              <span className="text-sm text-slate-200">
                Actual: {formatCurrency(data.actual)}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <span className="text-sm text-slate-200">
                Target: {formatCurrency(data.target)}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
              <span className="text-sm text-slate-200">
                P&L: {data.pnl >= 0 ? '+' : ''}{formatCurrency(data.pnl)}
              </span>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className={`bg-slate-800/50 rounded-lg border border-slate-700/50 p-4 ${className}`} data-testid="sacred-timeline">
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            
            {/* X-axis */}
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              stroke="#9CA3AF"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            
            {/* Y-axis */}
            <YAxis
              tickFormatter={formatCurrency}
              stroke="#9CA3AF"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              domain={['dataMin - 1000', 'dataMax + 1000']}
            />

            {/* Today marker */}
            {todayIndex >= 0 && (
              <ReferenceLine
                x={data[todayIndex]?.date}
                stroke="#F59E0B"
                strokeDasharray="2 2"
                strokeWidth={2}
                data-testid="sacred-today-marker"
              />
            )}

            {/* Target line */}
            <Line
              type="monotone"
              dataKey="target"
              stroke="#00FF99"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              data-testid="sacred-target-line"
            />

            {/* Actual line */}
            <Line
              type="monotone"
              dataKey="actual"
              stroke="#3B82F6"
              strokeWidth={3}
              dot={{ fill: '#3B82F6', strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6, fill: '#3B82F6' }}
            />

            {/* Tooltip */}
            <Tooltip content={<CustomTooltip />} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-end gap-4 mt-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-0.5 bg-blue-500"></div>
          <span className="text-slate-300">Actual</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-0.5 bg-green-500 border-dashed border-t-2 border-green-500"></div>
          <span className="text-slate-300">Target</span>
        </div>
        {todayIndex >= 0 && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 bg-yellow-500 border-dashed border-t-2 border-yellow-500"></div>
            <span className="text-slate-300">Today</span>
          </div>
        )}
      </div>
    </div>
  );
};