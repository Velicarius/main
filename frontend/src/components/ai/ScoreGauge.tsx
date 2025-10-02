import { RadialBarChart, RadialBar, ResponsiveContainer, Tooltip } from 'recharts';

// Гейдж общего балла портфеля (0-100) с индикатором риска
type ScoreGaugeProps = {
  score: number;
  risk: "Conservative" | "Balanced" | "Aggressive";
  why?: string; // объяснение балла для tooltip
};

export function ScoreGauge({ score, risk, why }: ScoreGaugeProps) {
  // Цвет в зависимости от балла
  const getColor = (score: number) => {
    if (score >= 80) return '#10b981'; // green
    if (score >= 60) return '#f59e0b'; // yellow
    return '#ef4444'; // red
  };

  // Цвет риска
  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'Conservative': return 'bg-green-100 text-green-800';
      case 'Balanced': return 'bg-yellow-100 text-yellow-800';
      case 'Aggressive': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const data = [
    {
      name: 'score',
      value: score,
      fill: getColor(score)
    }
  ];

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Общая оценка</h3>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRiskColor(risk)}`}>
          {risk}
        </span>
      </div>

      <div className="relative" style={{ height: '180px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            cx="50%"
            cy="50%"
            innerRadius="60%"
            outerRadius="90%"
            startAngle={180}
            endAngle={0}
            data={data}
          >
            <RadialBar
              dataKey="value"
              cornerRadius={10}
              fill={getColor(score)}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload[0] && why) {
                  return (
                    <div className="bg-slate-700 p-3 border border-slate-600 rounded-lg shadow-lg">
                      <p className="text-sm text-slate-300">{why}</p>
                    </div>
                  );
                }
                return null;
              }}
            />
          </RadialBarChart>
        </ResponsiveContainer>

        {/* Центральная цифра */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <div className="text-3xl font-bold text-white">{score}</div>
            <div className="text-sm text-slate-400">из 100</div>
          </div>
        </div>
      </div>
    </div>
  );
}
