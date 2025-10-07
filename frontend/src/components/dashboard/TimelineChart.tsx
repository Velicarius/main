import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TimeRangeGranularity } from './TimeRangeSelector';

export interface ChartDataPoint {
  date: string;
  actual: number | null;
  target?: number | null;
}

export interface TimelineChartProps {
  data: ChartDataPoint[];
  granularity: TimeRangeGranularity;
  formatCurrency: (value: number) => string;
  formatXAxisDate: (dateStr: string) => string;
  tooltipContent: React.ComponentType<any>;
  showTarget?: boolean;
}

export const TimelineChart: React.FC<TimelineChartProps> = ({
  data,
  granularity,
  formatCurrency,
  formatXAxisDate,
  tooltipContent: TooltipContent,
  showTarget = true
}) => {
  // Show dots only for daily view with limited data points
  const showDots = granularity === 'daily' && data.length <= 30;

  return (
    <div className="h-64 transition-all duration-300">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="date"
            tick={{ fill: '#9CA3AF', fontSize: 12 }}
            tickFormatter={formatXAxisDate}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: '#9CA3AF', fontSize: 12 }}
            tickFormatter={(value: number) => formatCurrency(value)}
            domain={['auto', 'auto']}
          />
          <Tooltip content={<TooltipContent />} />
          <Legend
            wrapperStyle={{ paddingTop: '10px' }}
            iconType="line"
          />
          {/* Historical line (blue) with smooth animation */}
          <Line
            type="monotone"
            dataKey="actual"
            stroke="#3B82F6"
            strokeWidth={2}
            dot={showDots ? { fill: '#3B82F6', strokeWidth: 2, r: 3 } : false}
            activeDot={{ r: 6, stroke: '#3B82F6', strokeWidth: 2 }}
            name="Actual"
            connectNulls={false}
            animationDuration={800}
            animationEasing="ease-in-out"
          />
          {/* Target trajectory (green dashed) with smooth animation */}
          {showTarget && (
            <Line
              type="monotone"
              dataKey="target"
              stroke="#10B981"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              name="Target"
              connectNulls={true}
              animationDuration={800}
              animationEasing="ease-in-out"
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
