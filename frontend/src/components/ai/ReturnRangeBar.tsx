
// Горизонтальная шкала доходности с диапазоном low-base-high
type ReturnRangeProps = {
  horizon: "1m" | "3m" | "6m" | "1y";
  base: number;
  low?: number;
  high?: number;
  note?: string;
};

export function ReturnRangeBar({ horizon, base, low, high, note }: ReturnRangeProps) {
  // Форматирование горизонта
  const getHorizonLabel = (h: string) => {
    switch (h) {
      case '1m': return '1 месяц';
      case '3m': return '3 месяца';
      case '6m': return '6 месяцев';
      case '1y': return '1 год';
      default: return h;
    }
  };

  // Определяем диапазон для отображения
  const minValue = low || base * 0.8; // fallback если нет low
  const maxValue = high || base * 1.2; // fallback если нет high
  const range = maxValue - minValue;

  // Позиция base на шкале (0-100%)
  const basePosition = range > 0 ? ((base - minValue) / range) * 100 : 50;

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Прогноз доходности</h3>
        <span className="text-sm text-slate-400">{getHorizonLabel(horizon)}</span>
      </div>

      <div className="space-y-4">
        {/* Шкала */}
        <div className="relative" style={{ height: '80px' }}>
          {/* Фон шкалы */}
          <div className="absolute inset-0 bg-slate-700 rounded-full"></div>
          
          {/* Диапазон low-high */}
          <div 
            className="absolute top-1/2 transform -translate-y-1/2 bg-blue-500/30 rounded-full"
            style={{
              left: '10%',
              right: '10%',
              height: '8px'
            }}
          ></div>

          {/* Маркер base */}
          <div 
            className="absolute top-1/2 transform -translate-y-1/2 w-4 h-4 bg-blue-500 rounded-full border-2 border-slate-800 shadow-md"
            style={{
              left: `calc(10% + ${basePosition * 0.8}%)`,
              marginLeft: '-8px'
            }}
          ></div>

          {/* Подписи значений */}
          <div className="absolute bottom-0 left-0 right-0 flex justify-between text-xs text-slate-400">
            <span>{minValue.toFixed(1)}%</span>
            <span className="font-medium text-blue-400">{base.toFixed(1)}%</span>
            <span>{maxValue.toFixed(1)}%</span>
          </div>
        </div>

        {/* Легенда */}
        <div className="flex items-center justify-center space-x-6 text-sm">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-blue-500/30 rounded"></div>
            <span className="text-slate-300">Диапазон</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-blue-500 rounded"></div>
            <span className="text-slate-300">Базовая оценка</span>
          </div>
        </div>

        {/* Примечание */}
        {note && (
          <div className="text-sm text-slate-300 bg-slate-700/50 p-3 rounded-lg">
            {note}
          </div>
        )}
      </div>
    </div>
  );
}
