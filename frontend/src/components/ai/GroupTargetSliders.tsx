import { GroupTarget, normalizeTargets } from './types';

// Слайдеры для целевых долей групп с нормализацией к 100%
type GroupTargetSlidersProps = {
  value: GroupTarget;
  onChange: (next: GroupTarget) => void;
};

export function GroupTargetSliders({ value, onChange }: GroupTargetSlidersProps) {
  // Обработка изменения слайдера
  const handleSliderChange = (group: keyof GroupTarget, newValue: number) => {
    const newTargets = { ...value, [group]: newValue };
    const normalized = normalizeTargets(newTargets);
    onChange(normalized);
  };


  // Простой слайдер (заглушка для shadcn/ui Slider)
  const SimpleSlider = ({ 
    value, 
    onChange, 
    min = 0, 
    max = 100, 
    step = 1,
    color = 'blue'
  }: {
    value: number;
    onChange: (value: number) => void;
    min?: number;
    max?: number;
    step?: number;
    color?: string;
  }) => {
    const getColorClass = (color: string) => {
      switch (color) {
        case 'green': return 'bg-green-500';
        case 'yellow': return 'bg-yellow-500';
        case 'red': return 'bg-red-500';
        default: return 'bg-blue-500';
      }
    };

    return (
      <div className="relative">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className={`w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider ${getColorClass(color)}`}
          style={{
            background: `linear-gradient(to right, ${getColorClass(color)} 0%, ${getColorClass(color)} ${value}%, #e5e7eb ${value}%, #e5e7eb 100%)`
          }}
        />
        <style>{`
          .slider::-webkit-slider-thumb {
            appearance: none;
            height: 20px;
            width: 20px;
            border-radius: 50%;
            background: white;
            border: 2px solid #d1d5db;
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
          }
          .slider::-moz-range-thumb {
            height: 20px;
            width: 20px;
            border-radius: 50%;
            background: white;
            border: 2px solid #d1d5db;
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
          }
        `}</style>
      </div>
    );
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Целевые доли групп</h3>
      
      <div className="space-y-6">
        {/* Долгосрочные */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-gray-700">Долгосрочные</label>
            <span className="text-sm font-bold text-green-600">{value.long.toFixed(1)}%</span>
          </div>
          <SimpleSlider
            value={value.long}
            onChange={(val) => handleSliderChange('long', val)}
            color="green"
          />
          <p className="text-xs text-gray-500 mt-1">Стабильные позиции для долгосрочного роста</p>
        </div>

        {/* Спекулятивные */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-gray-700">Спекулятивные</label>
            <span className="text-sm font-bold text-yellow-600">{value.spec.toFixed(1)}%</span>
          </div>
          <SimpleSlider
            value={value.spec}
            onChange={(val) => handleSliderChange('spec', val)}
            color="yellow"
          />
          <p className="text-xs text-gray-500 mt-1">Высокорисковые позиции для краткосрочной прибыли</p>
        </div>

        {/* К продаже */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-gray-700">К продаже</label>
            <span className="text-sm font-bold text-red-600">{value.sell.toFixed(1)}%</span>
          </div>
          <SimpleSlider
            value={value.sell}
            onChange={(val) => handleSliderChange('sell', val)}
            color="red"
          />
          <p className="text-xs text-gray-500 mt-1">Позиции для закрытия или ребалансировки</p>
        </div>
      </div>

      {/* Сводка */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600">Общая сумма:</span>
          <span className={`text-sm font-medium ${
            Math.abs(value.long + value.spec + value.sell - 100) < 0.1 
              ? 'text-green-600' 
              : 'text-red-600'
          }`}>
            {(value.long + value.spec + value.sell).toFixed(1)}%
          </span>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Будет использовано при расчёте allocation_changes
        </p>
      </div>
    </div>
  );
}
