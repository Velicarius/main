import { Position, Tag } from './types';

// Теггер позиций с segmented control для группировки
type PositionsTaggerProps = {
  positions: Position[];
  value: Record<string, Tag>;           // текущее присвоение
  onChange: (next: Record<string, Tag>) => void;
};

export function PositionsTagger({ positions, value, onChange }: PositionsTaggerProps) {
  // Автоматическая разметка (эвристики)
  const handleAutoTag = () => {
    const megaCaps = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA'];
    const newValue: Record<string, Tag> = {};

    positions.forEach(pos => {
      if (megaCaps.includes(pos.ticker)) {
        newValue[pos.ticker] = 'Long-term';
      } else if (pos.ticker.includes('.U') || pos.ticker.length > 4) {
        // Волатильные тикеры (заглушка)
        newValue[pos.ticker] = 'Speculative';
      } else {
        newValue[pos.ticker] = 'Long-term'; // default
      }
    });

    onChange(newValue);
  };

  // Изменение тега для позиции
  const handleTagChange = (ticker: string, tag: Tag) => {
    onChange({
      ...value,
      [ticker]: tag
    });
  };

  // Подсчет процентов по группам
  const getGroupPercentages = () => {
    const groups = { 'Long-term': 0, 'Speculative': 0, 'To-Sell': 0 };
    
    positions.forEach(pos => {
      const tag = value[pos.ticker] || 'Long-term';
      groups[tag] += pos.pct;
    });

    return groups;
  };

  const groupPercentages = getGroupPercentages();
  const totalPercentage = Object.values(groupPercentages).reduce((sum, pct) => sum + pct, 0);

  // Цвет прогресс-бара в зависимости от суммы
  const getProgressColor = () => {
    if (totalPercentage >= 98 && totalPercentage <= 102) return 'bg-green-500';
    if (totalPercentage >= 95 && totalPercentage <= 105) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  // Цвет предупреждения
  const getWarningColor = () => {
    if (totalPercentage >= 98 && totalPercentage <= 102) return 'text-green-600';
    if (totalPercentage >= 95 && totalPercentage <= 105) return 'text-yellow-600';
    return 'text-red-600';
  };

  if (positions.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Группировка позиций</h3>
        <p className="text-gray-500 text-center py-8">Нет позиций для группировки</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Группировка позиций</h3>
        <button
          onClick={handleAutoTag}
          className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors"
        >
          Авто-разметка (beta)
        </button>
      </div>

      {/* Прогресс-бар суммы */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-600">Сумма долей</span>
          <span className={`text-sm font-medium ${getWarningColor()}`}>
            {totalPercentage.toFixed(1)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className={`h-2 rounded-full transition-colors ${getProgressColor()}`}
            style={{ width: `${Math.min(totalPercentage, 100)}%` }}
          ></div>
        </div>
        {totalPercentage < 98 && (
          <p className="text-xs text-red-600 mt-1">Сумма долей меньше 100%</p>
        )}
        {totalPercentage > 102 && (
          <p className="text-xs text-red-600 mt-1">Сумма долей больше 100%</p>
        )}
      </div>

      {/* Список позиций с segmented control */}
      <div className="space-y-3">
        {positions.map(pos => (
          <div key={pos.ticker} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-3">
              <span className="font-medium text-gray-900">{pos.ticker}</span>
              <span className="text-sm text-gray-500">{pos.pct.toFixed(1)}%</span>
            </div>

            {/* Segmented control */}
            <div className="flex bg-white rounded-lg p-1 border border-gray-200">
              {(['Long-term', 'Speculative', 'To-Sell'] as Tag[]).map(tag => {
                const isActive = (value[pos.ticker] || 'Long-term') === tag;
                const label = tag === 'Long-term' ? 'Долгосрочные' : 
                             tag === 'Speculative' ? 'Спекулятивные' : 'К продаже';
                
                return (
                  <button
                    key={tag}
                    onClick={() => handleTagChange(pos.ticker, tag)}
                    className={`px-3 py-1 text-xs rounded-md transition-colors ${
                      isActive 
                        ? 'bg-blue-500 text-white' 
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Сводка по группам */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-green-600">{groupPercentages['Long-term'].toFixed(1)}%</div>
            <div className="text-sm text-gray-500">Долгосрочные</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-yellow-600">{groupPercentages['Speculative'].toFixed(1)}%</div>
            <div className="text-sm text-gray-500">Спекулятивные</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-red-600">{groupPercentages['To-Sell'].toFixed(1)}%</div>
            <div className="text-sm text-gray-500">К продаже</div>
          </div>
        </div>
      </div>
    </div>
  );
}
