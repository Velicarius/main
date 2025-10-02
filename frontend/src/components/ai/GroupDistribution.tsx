import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

// Вертикальный бар-чарт распределения позиций по группам
type GroupDistributionProps = {
  data: {
    group: "Long-term" | "Speculative" | "To-Sell";
    pct: number;
    tickers?: string[]; // для tooltip
  }[];
};

export function GroupDistribution({ data }: GroupDistributionProps) {
  // Цвета для групп
  const getGroupColor = (group: string) => {
    switch (group) {
      case 'Long-term': return '#10b981'; // green
      case 'Speculative': return '#f59e0b'; // yellow
      case 'To-Sell': return '#ef4444'; // red
      default: return '#6b7280'; // gray
    }
  };

  // Локализация названий групп
  const getGroupLabel = (group: string) => {
    switch (group) {
      case 'Long-term': return 'Долгосрочные';
      case 'Speculative': return 'Спекулятивные';
      case 'To-Sell': return 'К продаже';
      default: return group;
    }
  };

  // Подготовка данных для чарта
  const chartData = data.map(item => ({
    ...item,
    groupLabel: getGroupLabel(item.group),
    fill: getGroupColor(item.group)
  }));

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <h3 className="text-lg font-semibold text-white mb-4">Распределение по группам</h3>
      
      <div style={{ height: '220px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            layout="horizontal"
            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
            <XAxis 
              type="number" 
              domain={[0, 100]}
              tickFormatter={(value) => `${value}%`}
              stroke="#94a3b8"
              tick={{ fill: '#94a3b8' }}
            />
            <YAxis 
              type="category" 
              dataKey="groupLabel"
              width={80}
              stroke="#94a3b8"
              tick={{ fill: '#94a3b8' }}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload[0]) {
                  const data = payload[0].payload;
                  return (
                    <div className="bg-slate-700 p-3 border border-slate-600 rounded-lg shadow-lg">
                      <p className="font-medium text-white">{data.groupLabel}</p>
                      <p className="text-sm text-slate-300">{data.pct.toFixed(1)}% от портфеля</p>
                      {data.tickers && data.tickers.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs text-slate-400">Позиции:</p>
                          <p className="text-xs text-slate-300">{data.tickers.join(', ')}</p>
                        </div>
                      )}
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar dataKey="pct" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Легенда */}
      <div className="flex items-center justify-center space-x-6 mt-4 text-sm">
        {chartData.map(item => (
          <div key={item.group} className="flex items-center space-x-2">
            <div 
              className="w-3 h-3 rounded"
              style={{ backgroundColor: item.fill }}
            ></div>
            <span className="text-slate-300">{item.groupLabel}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
