// График истории стоимости портфеля
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export type ValueHistoryChartProps = {
  data: { t: string; v: number }[];
  period?: string;
};

export function ValueHistoryChart({ data, period = "30 days" }: ValueHistoryChartProps) {
  // Генерация мок-данных если нет реальных
  const generateMockData = () => {
    const mockData = [];
    const baseValue = 10000;
    const now = new Date();
    
    for (let i = 29; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      
      // Синус + шум для реалистичности
      const trend = Math.sin(i * 0.2) * 0.1;
      const noise = (Math.random() - 0.5) * 0.05;
      const value = baseValue * (1 + trend + noise);
      
      mockData.push({
        t: date.toLocaleDateString('ru-RU', { month: 'short', day: 'numeric' }),
        v: Math.round(value)
      });
    }
    
    return mockData;
  };

  const chartData = data.length > 0 ? data : generateMockData();

  // Форматирование значений для tooltip
  const formatValue = (value: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  if (data.length === 0) {
    // Скелетон для отсутствующих данных
    return (
      <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Portfolio Value History</h3>
          <span className="text-sm text-slate-400">Last {period}</span>
        </div>
        
        <div className="h-64 bg-slate-700/30 rounded-lg flex items-center justify-center">
          <div className="text-center">
            <div className="text-slate-400 text-lg mb-2">📊</div>
            <p className="text-slate-400">No data available</p>
            <p className="text-sm text-slate-500">Add positions to see portfolio history</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Portfolio Value History</h3>
        <span className="text-sm text-slate-400">Last {period}</span>
      </div>
      
      <div style={{ height: '260px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
            <XAxis 
              dataKey="t" 
              stroke="#94a3b8"
              fontSize={12}
              tick={{ fill: '#94a3b8' }}
            />
            <YAxis 
              stroke="#94a3b8"
              fontSize={12}
              tick={{ fill: '#94a3b8' }}
              tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
            />
            <Tooltip
              formatter={(value: number) => [formatValue(value), 'Value']}
              labelStyle={{ color: '#f1f5f9' }}
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #475569',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
                color: '#f1f5f9'
              }}
            />
            <Line 
              type="monotone" 
              dataKey="v" 
              stroke="#3b82f6" 
              strokeWidth={2}
              dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6, stroke: '#3b82f6', strokeWidth: 2, fill: '#1e40af' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
