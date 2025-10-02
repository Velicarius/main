import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine } from 'recharts';
import { fmtCurrency } from '../../lib/format';
import { CurrentValueChip } from '../common/CurrentValueChip';

// Sacred Timeline component showing actual vs strategy forecast
export interface SacredTimelineProps {
  currency: 'USD' | 'EUR' | 'PLN';
  todayISO: string;
  registrationDateISO: string;
  horizonYears: number;
  currentTotalValue: number;                       // same as "Total Value" card
  actualSeries: { t: string; value: number }[];      // EOD history up to today
  strategySeries: { t: string; value: number }[];    // monthly forecast
}

export function SacredTimeline({ 
  currency,
  todayISO,
  registrationDateISO,
  horizonYears,
  currentTotalValue,
  actualSeries,
  strategySeries
}: SacredTimelineProps) {
  // If there is no point in actualSeries for todayISO, append currentTotalValue
  const actualWithToday = [...actualSeries];
  if (!actualWithToday.find(p => p.t === todayISO)) {
    actualWithToday.push({ t: todayISO, value: currentTotalValue });
  }

  // Build window start and end dates
  const today = new Date(todayISO);
  const registrationDate = new Date(registrationDateISO);
  const oneYearAgo = new Date(today.getTime() - 365 * 24 * 60 * 60 * 1000);
  const windowStart = new Date(Math.max(registrationDate.getTime(), oneYearAgo.getTime()));

  const horizonEnd = new Date(registrationDate.getTime() + horizonYears * 365 * 24 * 60 * 60 * 1000);
  const oneYearFromNow = new Date(today.getTime() + 365 * 24 * 60 * 60 * 1000);
  const windowEnd = new Date(Math.min(horizonEnd.getTime(), oneYearFromNow.getTime()));

  // Filter series to window
  const filteredActual = actualWithToday.filter(p => {
    const date = new Date(p.t);
    return date >= windowStart && date <= windowEnd;
  });

  const filteredStrategy = strategySeries.filter(p => {
    const date = new Date(p.t);
    return date >= windowStart && date <= windowEnd;
  });

  // Merge series into one dataset by ISO date
  const allDates = new Set([
    ...filteredActual.map(p => p.t),
    ...filteredStrategy.map(p => p.t)
  ]);

  const mergedData = Array.from(allDates).map(date => ({
    t: date,
    actual: filteredActual.find(p => p.t === date)?.value,
    strategy: filteredStrategy.find(p => p.t === date)?.value
  })).sort((a, b) => new Date(a.t).getTime() - new Date(b.t).getTime());

  // Compute y-domain from all values with 5% padding, clamped to >= 0
  const allValues = mergedData.flatMap(d => [d.actual, d.strategy]).filter(v => v !== undefined) as number[];
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const yDomain = [Math.max(0, min * 0.95), max * 1.05];

  // Interpolate strategy at today (linear between two nearest monthly points)
  const getStrategyValueAtDate = (targetDate: string) => {
    const target = new Date(targetDate);
    const strategyPoints = filteredStrategy.filter(p => new Date(p.t) <= target);
    
    if (strategyPoints.length === 0) return undefined;
    if (strategyPoints.length === 1) return strategyPoints[0].value;
    
    const lastPoint = strategyPoints[strategyPoints.length - 1];
    const prevPoint = strategyPoints[strategyPoints.length - 2];
    
    if (!prevPoint) return lastPoint.value;
    
    // Linear interpolation
    const lastDate = new Date(lastPoint.t);
    const prevDate = new Date(prevPoint.t);
    const timeDiff = target.getTime() - prevDate.getTime();
    const totalDiff = lastDate.getTime() - prevDate.getTime();
    const ratio = timeDiff / totalDiff;
    
    return prevPoint.value + (lastPoint.value - prevPoint.value) * ratio;
  };

  const strategyToday = getStrategyValueAtDate(todayISO);
  const deltaToday = strategyToday ? currentTotalValue - strategyToday : NaN;

  // Format date for display
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('ru-RU', { month: 'short', year: 'numeric' });
  };

  const formatTooltipDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  const windowText = `Окно: ${formatDate(windowStart.toISOString().slice(0, 10))} — ${formatDate(windowEnd.toISOString().slice(0, 10))}`;

  // Empty state
  if (actualSeries.length === 0) {
    return (
      <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white">Священный таймлайн</h3>
            <span className="text-sm text-slate-400">Strategy vs Actual</span>
          </div>
          <CurrentValueChip value={currentTotalValue} currency={currency} />
        </div>
        
        <div className="h-[300px] flex items-center justify-center">
          <div className="text-center">
            <div className="text-slate-400 text-lg mb-2">📊</div>
            <p className="text-slate-400">Добавьте позиции или импортируйте CSV, чтобы увидеть историю.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-white">Священный таймлайн</h3>
          <span className="text-sm text-slate-400">Strategy vs Actual</span>
        </div>
        <div className="flex items-center gap-3">
          <CurrentValueChip value={currentTotalValue} currency={currency} />
          {!isNaN(deltaToday) && (
            <div className={`px-3 py-1 rounded-full text-sm font-medium ${
              deltaToday > 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
            }`}>
              Δ Today: {deltaToday > 0 ? '+' : ''}{fmtCurrency(deltaToday, currency)}
            </div>
          )}
        </div>
      </div>
      
      <div style={{ height: '300px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={mergedData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
            <XAxis 
              dataKey="t" 
              stroke="#94a3b8"
              fontSize={12}
              tick={{ fill: '#94a3b8' }}
              tickFormatter={formatDate}
            />
            <YAxis 
              domain={yDomain}
              stroke="#94a3b8"
              fontSize={12}
              tick={{ fill: '#94a3b8' }}
              tickFormatter={(value) => fmtCurrency(value, currency)}
            />
            <Tooltip
              formatter={(value: number) => [fmtCurrency(Number(value), currency), 'Value']}
              labelFormatter={formatTooltipDate}
              labelStyle={{ color: '#f1f5f9' }}
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #475569',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
                color: '#f1f5f9'
              }}
            />
            <Legend />
            <ReferenceLine x={todayISO} strokeDasharray="3 3" stroke="#94a3b8" />
            <Line 
              name="Actual" 
              dataKey="actual" 
              type="monotone" 
              stroke="#60a5fa" 
              strokeWidth={2} 
              dot={{
                r: 3, 
                strokeWidth: 0,
                className: "fill-blue-400",
              }} 
              activeDot={{ r: 5 }} 
            />
            <Line 
              name="Strategy" 
              dataKey="strategy" 
              type="monotone" 
              stroke="#34d399" 
              strokeWidth={2} 
              strokeDasharray="6 4" 
              dot={false} 
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Window info */}
      <div className="mt-4 text-center text-sm text-slate-400">
        {windowText}
      </div>
    </div>
  );
}
