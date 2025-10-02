// Тизер AI анализа с результатами последнего анализа из localStorage
export type AISnapshotData = {
  score?: number; // 0..100
  risk?: "Conservative" | "Balanced" | "Aggressive";
  baseReturnPct?: number; 
  lowPct?: number; 
  highPct?: number; 
  horizon?: "1m" | "3m" | "6m" | "1y";
  updatedAt?: string; 
  model?: string;
};

export function AISnapshot() {
  // Читаем данные из localStorage
  const getSnapshotData = (): AISnapshotData | null => {
    try {
      const lastResult = localStorage.getItem('insights_last_result');
      const lastMeta = localStorage.getItem('insights_last_meta');
      
      if (!lastResult) return null;
      
      const result = JSON.parse(lastResult);
      const meta = lastMeta ? JSON.parse(lastMeta) : {};
      
      return {
        score: result.overall_score,
        risk: result.risk_level,
        baseReturnPct: result.expected_return?.annualized_pct_range?.base,
        lowPct: result.expected_return?.annualized_pct_range?.low,
        highPct: result.expected_return?.annualized_pct_range?.high,
        horizon: result.expected_return?.horizon,
        updatedAt: meta.updatedAt,
        model: meta.model
      };
    } catch (error) {
      console.warn('Ошибка чтения AI Snapshot:', error);
      return null;
    }
  };

  const data = getSnapshotData();

  // Цвет риска
  const getRiskColor = (risk?: string) => {
    switch (risk) {
      case 'Conservative': return 'bg-green-100 text-green-800';
      case 'Balanced': return 'bg-yellow-100 text-yellow-800';
      case 'Aggressive': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  // Форматирование горизонта
  const getHorizonLabel = (horizon?: string) => {
    switch (horizon) {
      case '1m': return '1 месяц';
      case '3m': return '3 месяца';
      case '6m': return '6 месяцев';
      case '1y': return '1 год';
      default: return horizon || '6 месяцев';
    }
  };

  if (!data || !data.score) {
    return (
      <div className="bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30 rounded-xl p-6 backdrop-blur-xl">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white mb-2">AI Portfolio Analysis</h3>
            <p className="text-slate-300 mb-4">Запустите анализ портфеля для получения AI-инсайтов</p>
            <button
              onClick={() => window.location.href = '/insights'}
              className="px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg font-medium hover:from-purple-700 hover:to-blue-700 transition-all duration-200"
            >
              Open in Insights
            </button>
          </div>
          <div className="text-4xl opacity-20">🤖</div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">AI Portfolio Analysis</h3>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRiskColor(data.risk)}`}>
          {data.risk || 'Unknown'}
        </span>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <div className="text-3xl font-bold text-white mb-1">{data.score}/100</div>
          <div className="text-sm text-slate-300">
            Базовая доходность {data.baseReturnPct?.toFixed(1) || 'N/A'}% годовых · Горизонт {getHorizonLabel(data.horizon)}
          </div>
          {data.updatedAt && (
            <div className="text-xs text-slate-400 mt-1">
              Обновлено: {new Date(data.updatedAt).toLocaleDateString('ru-RU')}
            </div>
          )}
        </div>

        <button
          onClick={() => window.location.href = '/insights'}
          className="px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg font-medium hover:from-purple-700 hover:to-blue-700 transition-all duration-200"
        >
          Open in Insights
        </button>
      </div>
    </div>
  );
}
