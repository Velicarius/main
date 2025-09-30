import { useState, useEffect } from 'react';
import { apiFetch, getPositions, Position } from '../../lib/api';
import { useAuthStore } from '../../store/auth';

// TypeScript типы, соответствующие JSON Schema
type PortfolioAnalysis = {
  overall_score: number;
  risk_level: "Conservative" | "Balanced" | "Aggressive";
  summary: string;
  expected_return: {
    horizon: "1m" | "3m" | "6m" | "1y";
    annualized_pct_range: { low?: number; base: number; high?: number };
    rationale?: string;
  };
  key_risks: { name: string; severity: number; why: string; hedge?: string | null }[];
  suggestions: { action: string; reason: string; priority?: number }[];
  allocation_changes?: { ticker: string; current_pct?: number | null; target_pct: number; note?: string | null }[];
  diversification?: { herfindahl?: number | null; sector_gaps?: string[] };
  warnings?: string[];
  assumptions?: string[];
};

// Тип для ошибок
type ErrorInfo = {
  status: number;
  code: string;
  message: string;
  raw?: string | null;
};

// Типы анализа
const ANALYSIS_TYPES = {
  'income': {
    title: 'Доходность',
    description: 'Анализ потенциальной доходности и дивидендных выплат',
    focus: 'доходность, дивиденды, купоны, yield'
  },
  'structure': {
    title: 'Структура',
    description: 'Анализ структуры портфеля и распределения активов',
    focus: 'структура, распределение, сектора, география'
  },
  'risks': {
    title: 'Риски',
    description: 'Выявление и оценка рисков портфеля',
    focus: 'риски, волатильность, корреляции, концентрация'
  },
  'strategy': {
    title: 'Стратегия',
    description: 'Стратегические рекомендации и оптимизация',
    focus: 'стратегия, оптимизация, ребалансировка, тактика'
  },
  'diversification': {
    title: 'Диверсификация',
    description: 'Анализ диверсификации и корреляций',
    focus: 'диверсификация, корреляции, концентрация, распределение'
  }
};

export default function AIInsightsPortfolioAnalyzer() {
  const { user_id } = useAuthStore();
  
  // Состояние формы
  const [horizon, setHorizon] = useState<'1m' | '3m' | '6m' | '1y'>('6m');
  const [riskProfile, setRiskProfile] = useState<'Conservative' | 'Balanced' | 'Aggressive'>('Balanced');
  const [ignoreCrypto, setIgnoreCrypto] = useState(false);
  const [preferLowFees, setPreferLowFees] = useState(false);
  const [esgTilt, setEsgTilt] = useState(false);
  
  // Состояние позиций
  const [userPositions, setUserPositions] = useState<Position[]>([]);
  const [showPortfolioDetails, setShowPortfolioDetails] = useState(false);
  const [selectedAnalysisType, setSelectedAnalysisType] = useState<keyof typeof ANALYSIS_TYPES>('income');
  
  // Состояние анализа
  const [analysis, setAnalysis] = useState<PortfolioAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ErrorInfo | string | null>(null);
  const [rawResponse, setRawResponse] = useState<string | null>(null);
  const [showRawJson, setShowRawJson] = useState(false);
  
  // Состояние модели
  const [selectedModel, setSelectedModel] = useState('');
  const [availableModels, setAvailableModels] = useState<any[]>([]);

  // Загрузка доступных моделей и позиций при монтировании
  useEffect(() => {
    loadAvailableModels();
    loadFormState();
    if (user_id) {
      loadUserPositions();
    }
  }, [user_id]);

  // Загрузка доступных моделей Ollama
  const loadAvailableModels = async () => {
    try {
      const response = await apiFetch('/llm/models');
      const data = await response.json();
      if (data.success && data.models.length > 0) {
        setAvailableModels(data.models);
        // Выбираем первую доступную модель по умолчанию
        if (data.models[0]?.name) {
          setSelectedModel(data.models[0].name);
        }
      }
    } catch (err) {
      console.warn('Не удалось загрузить модели:', err);
    }
  };

  // Загрузка позиций пользователя
  const loadUserPositions = async () => {
    if (!user_id) return;
    
    try {
      const positions = await getPositions();
      setUserPositions(positions);
    } catch (err) {
      console.warn('Не удалось загрузить позиции:', err);
    }
  };

  // Загрузка состояния формы из localStorage
  const loadFormState = () => {
    try {
      const saved = localStorage.getItem('portfolio_form_v1');
      if (saved) {
        const formState = JSON.parse(saved);
        setHorizon(formState.horizon || '6m');
        setRiskProfile(formState.riskProfile || 'Balanced');
        setIgnoreCrypto(formState.ignoreCrypto || false);
        setPreferLowFees(formState.preferLowFees || false);
        setEsgTilt(formState.esgTilt || false);
      }
    } catch (err) {
      console.warn('Ошибка загрузки состояния формы:', err);
    }
  };

  // Сохранение состояния формы в localStorage
  const saveFormState = () => {
    try {
      const formState = {
        horizon,
        riskProfile,
        ignoreCrypto,
        preferLowFees,
        esgTilt
      };
      localStorage.setItem('portfolio_form_v1', JSON.stringify(formState));
    } catch (err) {
      console.warn('Ошибка сохранения состояния формы:', err);
    }
  };

  // Выбор типа анализа
  const selectAnalysisType = (type: keyof typeof ANALYSIS_TYPES) => {
    setSelectedAnalysisType(type);
  };

  // Построение промпта для LLM
  const buildPrompt = (): string => {
    const constraints = [];
    if (ignoreCrypto) constraints.push('Игнорировать криптовалюты');
    if (preferLowFees) constraints.push('Предпочитать низкие комиссии');
    if (esgTilt) constraints.push('ESG-ориентированный подход');

    // Форматируем позиции из портфеля пользователя
    const formattedPositions = userPositions.length > 0 
      ? userPositions.map(pos => {
          const value = pos.quantity * (pos.buy_price || 0);
          return `${pos.symbol} ${pos.quantity} шт. (${value.toFixed(2)} ${pos.currency})`;
        }).join('\n')
      : 'Нет позиций в портфеле';

    const analysisType = ANALYSIS_TYPES[selectedAnalysisType];
    
    return `Ты — финансовый аналитик. Верни строго JSON по схеме. Не давай советов, несовместимых с входными ограничениями. Краткость важнее воды. Не используй язык, который звучит как финансовая рекомендация; это аналитическая сводка.

Тип анализа: ${analysisType.title} - ${analysisType.description}
Фокус анализа: ${analysisType.focus}

Данные портфеля (строка на позицию):
${formattedPositions.slice(0, 5000)}

Горизонт: ${horizon}
Риск-профиль: ${riskProfile}
Ограничения: ${constraints.length > 0 ? constraints.join(', ') : 'Нет'}

Если данных не хватает — ставь null/[] и перечисли в assumptions.`;
  };

  // Выполнение анализа
  const runAnalysis = async () => {
    if (userPositions.length === 0) {
      setError('Нет позиций в портфеле. Добавьте позиции на странице "Позиции"');
      return;
    }

    if (!selectedModel) {
      setError('Выберите модель для анализа');
      return;
    }

    setLoading(true);
    setError(null);
    setAnalysis(null);
    setRawResponse(null);

    try {
      // Получаем схему
      const schemaResponse = await apiFetch('/llm/schemas/portfolio_v1');
      const schema = await schemaResponse.json();

      // Генерируем trace ID
      let traceId = localStorage.getItem('trace_id');
      if (!traceId) {
        traceId = `trace_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        localStorage.setItem('trace_id', traceId);
      }

      // Отправляем запрос к LLM
      const requestBody = {
        model: selectedModel,
        system: "You are a strict JSON generator. Output JSON only.",
        prompt: buildPrompt(),
        json_schema: schema
      };
      
      console.log('Отправляем запрос:', requestBody);
      
      let chatResponse: Response;
      try {
        chatResponse = await apiFetch('/llm/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Trace-Id': traceId
          },
          body: JSON.stringify(requestBody)
        });
      } catch (apiError: any) {
        console.log('Ошибка apiFetch:', apiError);
        console.log('Сообщение ошибки:', apiError.message);
        console.log('Статус ошибки:', apiError.status);
        console.log('Данные ошибки:', apiError.data);
        
        // Извлекаем детали из объекта ошибки
        let errorDetails: any = { message: apiError.message };
        
        // Если есть данные ошибки, используем их
        if (apiError.data) {
          if (apiError.data.detail && typeof apiError.data.detail === 'object') {
            errorDetails = apiError.data.detail;
          } else {
            errorDetails = apiError.data;
          }
        } else {
          // Пытаемся распарсить JSON из сообщения
          try {
            if (apiError.message.includes('{')) {
              const jsonMatch = apiError.message.match(/\{.*\}/);
              if (jsonMatch) {
                errorDetails = JSON.parse(jsonMatch[0]);
              }
            }
          } catch {
            // Игнорируем ошибки парсинга
          }
        }
        
        setError({
          status: apiError.status || 422,
          code: errorDetails?.code ?? "http_error",
          message: errorDetails?.message ?? apiError.message ?? "Request failed",
          raw: errorDetails?.raw_text ?? null,
        });
        return;
      }

      // Обрабатываем успешный ответ
      console.log('Статус ответа:', chatResponse.status);

      const chatData = await chatResponse.json();
      
      if (!chatData.success) {
        const errorMsg = typeof chatData.error === 'string' ? chatData.error : 'Ошибка анализа';
        throw new Error(errorMsg);
      }

      setRawResponse(chatData.response);

      // Пытаемся распарсить JSON
      try {
        const parsed = JSON.parse(chatData.response);
        setAnalysis(parsed);
      } catch (parseError) {
        // Если не удалось распарсить, показываем сырой ответ
        console.warn('Не удалось распарсить JSON ответ:', parseError);
        setError('Модель вернула невалидный JSON. Показан сырой ответ.');
      }

    } catch (err: any) {
      console.error('Ошибка анализа:', err);
      let errorMessage = 'Ошибка при анализе портфеля';
      
      if (err && typeof err === 'object') {
        if (err.message && typeof err.message === 'string') {
          if (err.message.includes('422')) {
            errorMessage = 'Ошибка валидации запроса. Проверьте данные портфеля.';
          } else {
            errorMessage = err.message;
          }
        } else if (err.status || err.code || err.raw) {
          // Это уже структурированная ошибка
          setError(err);
          return;
        }
      } else if (typeof err === 'string') {
        errorMessage = err;
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
      saveFormState();
    }
  };

  // Форматирование чисел
  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 1 }).format(num);
  };

  // Подсчет общей стоимости портфеля
  const calculatePortfolioValue = () => {
    return userPositions.reduce((total, pos) => {
      return total + (pos.quantity * (pos.buy_price || 0));
    }, 0);
  };

  // Получение цвета для уровня риска
  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'Conservative': return 'bg-green-100 text-green-800';
      case 'Balanced': return 'bg-yellow-100 text-yellow-800';
      case 'Aggressive': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  // Получение цвета для приоритета
  const getPriorityColor = (priority?: number) => {
    if (!priority) return 'bg-gray-100 text-gray-800';
    if (priority >= 3) return 'bg-red-100 text-red-800';
    if (priority >= 2) return 'bg-yellow-100 text-yellow-800';
    return 'bg-green-100 text-green-800';
  };

  return (
    <div className="space-y-6">
      {/* Заголовок */}
      <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
        <h2 className="text-2xl font-bold text-white mb-2">📊 Portfolio Analyzer v1</h2>
        <p className="text-slate-400">Анализ портфеля с использованием локальных LLM моделей</p>
      </div>

      {/* Типы анализа */}
      <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
        <h3 className="text-lg font-semibold text-white mb-4">Тип анализа</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.entries(ANALYSIS_TYPES).map(([key, type]) => (
            <button
              key={key}
              onClick={() => selectAnalysisType(key as keyof typeof ANALYSIS_TYPES)}
              className={`p-4 rounded-lg border-2 transition-all duration-200 text-left ${
                selectedAnalysisType === key
                  ? 'border-blue-500 bg-blue-500/10 text-blue-300'
                  : 'border-slate-600 bg-slate-700/30 text-slate-300 hover:border-slate-500 hover:bg-slate-700/50'
              }`}
            >
              <div className="font-medium text-sm mb-1">{type.title}</div>
              <div className="text-xs text-slate-400">{type.description}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Портфель пользователя */}
      {user_id && (
        <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl border border-slate-700/50 shadow-lg">
          <div 
            className="p-6 cursor-pointer"
            onClick={() => setShowPortfolioDetails(!showPortfolioDetails)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-emerald-600 rounded-lg flex items-center justify-center">
                  <span className="text-white text-sm">📊</span>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">Мой портфель</h3>
                  <p className="text-sm text-slate-400">
                    {userPositions.length} позиций • {formatNumber(calculatePortfolioValue())} USD
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-slate-400 text-sm">
                  {showPortfolioDetails ? '▼' : '▶'}
                </span>
              </div>
            </div>
          </div>
          
          {showPortfolioDetails && (
            <div className="px-6 pb-6 border-t border-slate-700/50">
              <div className="mt-4 space-y-2 max-h-64 overflow-y-auto">
                {userPositions.map((pos, index) => {
                  const value = pos.quantity * (pos.buy_price || 0);
                  return (
                    <div key={index} className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
                      <div>
                        <div className="font-medium text-white">{pos.symbol}</div>
                        <div className="text-sm text-slate-400">
                          {pos.quantity} шт. × {pos.buy_price?.toFixed(2) || '0.00'} {pos.currency}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-medium text-white">{formatNumber(value)} {pos.currency}</div>
                        <div className="text-sm text-slate-400">
                          {pos.account || 'Основной счет'}
                        </div>
                      </div>
                    </div>
                  );
                })}
                {userPositions.length === 0 && (
                  <div className="text-center py-8 text-slate-400">
                    <p>Нет позиций в портфеле</p>
                    <p className="text-sm mt-1">Добавьте позиции на странице "Позиции"</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Настройки анализа */}
      <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Левая колонка - основные поля */}
          <div className="space-y-4">

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Горизонт
                </label>
                <select
                  id="horizon"
                  value={horizon}
                  onChange={(e) => setHorizon(e.target.value as any)}
                  className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200"
                >
                  <option value="1m">1 месяц</option>
                  <option value="3m">3 месяца</option>
                  <option value="6m">6 месяцев</option>
                  <option value="1y">1 год</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Риск-профиль
                </label>
                <select
                  id="riskProfile"
                  value={riskProfile}
                  onChange={(e) => setRiskProfile(e.target.value as any)}
                  className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200"
                >
                  <option value="Conservative">Консервативный</option>
                  <option value="Balanced">Сбалансированный</option>
                  <option value="Aggressive">Агрессивный</option>
                </select>
              </div>
            </div>
          </div>

          {/* Правая колонка - дополнительные опции */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Модель LLM
              </label>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200"
              >
                <option value="">Выберите модель</option>
                {availableModels.map((model) => (
                  <option key={model.name} value={model.name}>
                    {model.name} ({model.size ? `${(model.size / 1024 / 1024 / 1024).toFixed(1)}GB` : 'N/A'})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-3">
                Дополнительные ограничения
              </label>
              <div className="space-y-3">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={ignoreCrypto}
                    onChange={(e) => setIgnoreCrypto(e.target.checked)}
                    className="w-4 h-4 text-blue-600 bg-slate-700 border-slate-600 rounded focus:ring-blue-500 focus:ring-2"
                  />
                  <span className="ml-2 text-sm text-slate-300">Игнорировать криптовалюты</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={preferLowFees}
                    onChange={(e) => setPreferLowFees(e.target.checked)}
                    className="w-4 h-4 text-blue-600 bg-slate-700 border-slate-600 rounded focus:ring-blue-500 focus:ring-2"
                  />
                  <span className="ml-2 text-sm text-slate-300">Предпочитать низкие комиссии</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={esgTilt}
                    onChange={(e) => setEsgTilt(e.target.checked)}
                    className="w-4 h-4 text-blue-600 bg-slate-700 border-slate-600 rounded focus:ring-blue-500 focus:ring-2"
                  />
                  <span className="ml-2 text-sm text-slate-300">ESG-ориентированный подход</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        {/* Кнопки действий */}
        <div className="flex flex-wrap gap-3 mt-6">
          <button
            onClick={runAnalysis}
            disabled={loading || userPositions.length === 0 || !selectedModel}
            className="px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-lg transition-all duration-200 shadow-lg shadow-purple-500/25 font-medium disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
          >
            {loading ? (
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                <span>Running…</span>
              </div>
            ) : (
              `Анализировать ${ANALYSIS_TYPES[selectedAnalysisType].title}`
            )}
          </button>
        </div>

        {/* Ошибки */}
        {error && (
          <div className="mt-4 p-4 bg-gradient-to-r from-red-900/20 to-red-800/20 border border-red-500/30 rounded-lg backdrop-blur-sm">
            <div className="flex items-center space-x-3">
              <div className="w-6 h-6 bg-red-500/20 rounded-full flex items-center justify-center">
                <span className="text-red-400 text-sm">!</span>
              </div>
              <div className="flex-1">
                {typeof error === 'string' ? (
                  <p className="text-red-400 font-medium">{error}</p>
                ) : (
                  <div>
                    <p className="text-red-400 font-bold">
                      {error.status} / {error.code}
                    </p>
                    <p className="text-red-300 text-sm mt-1">{error.message}</p>
                    {error.raw && (
                      <details className="mt-3">
                        <summary className="text-red-300 text-sm cursor-pointer hover:text-red-200">
                          Raw model output
                        </summary>
                        <pre className="mt-2 p-3 bg-slate-900/50 rounded text-xs text-slate-300 overflow-auto max-h-40">
                          {error.raw}
                        </pre>
                      </details>
                    )}
                  </div>
                )}
              </div>
            </div>
            {(typeof error === 'string' && error.includes('невалидный JSON')) || 
             (typeof error === 'object' && error.code === 'invalid_json') ? (
              <button
                onClick={runAnalysis}
                className="mt-3 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Повторить
              </button>
            ) : null}
          </div>
        )}
      </div>

      {/* Результаты анализа */}
      {analysis && (
        <div className="space-y-6">
          {/* Общая оценка */}
          <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
            <h3 className="text-xl font-semibold text-white mb-4">Общая оценка</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="text-4xl font-bold text-blue-400 mb-2">
                  {formatNumber(analysis.overall_score)}/100
                </div>
                <div className="w-full bg-slate-700 rounded-full h-3 mb-2">
                  <div 
                    className="bg-gradient-to-r from-blue-500 to-purple-600 h-3 rounded-full transition-all duration-500"
                    style={{ width: `${analysis.overall_score}%` }}
                  ></div>
                </div>
                <p className="text-sm text-slate-400">Общий балл</p>
              </div>
              <div className="text-center">
                <span className={`inline-flex px-4 py-2 rounded-full text-sm font-medium ${getRiskLevelColor(analysis.risk_level)}`}>
                  {analysis.risk_level}
                </span>
                <p className="text-sm text-slate-400 mt-2">Уровень риска</p>
              </div>
              <div className="text-center">
                <p className="text-slate-300 text-sm leading-relaxed">{analysis.summary}</p>
              </div>
            </div>
          </div>

          {/* Прогноз доходности */}
          <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
            <h3 className="text-xl font-semibold text-white mb-4">Прогноз доходности</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <div className="text-2xl font-bold text-green-400 mb-2">
                  {formatNumber(analysis.expected_return.annualized_pct_range.base)}% годовых
                </div>
                <div className="text-sm text-slate-400 mb-4">
                  Горизонт: {analysis.expected_return.horizon}
                </div>
                {analysis.expected_return.annualized_pct_range.low && analysis.expected_return.annualized_pct_range.high && (
                  <div className="text-sm text-slate-300">
                    Диапазон: {formatNumber(analysis.expected_return.annualized_pct_range.low)}% - {formatNumber(analysis.expected_return.annualized_pct_range.high)}%
                  </div>
                )}
              </div>
              {analysis.expected_return.rationale && (
                <div>
                  <p className="text-slate-300 text-sm leading-relaxed">{analysis.expected_return.rationale}</p>
                </div>
              )}
            </div>
          </div>

          {/* Ключевые риски */}
          <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
            <h3 className="text-xl font-semibold text-white mb-4">Ключевые риски</h3>
            <div className="space-y-4">
              {analysis.key_risks.map((risk, index) => (
                <div key={index} className="bg-slate-700/30 rounded-lg p-4 border border-slate-600/30">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium text-white">{risk.name}</h4>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-slate-400">Серьезность:</span>
                      <div className="flex space-x-1">
                        {[1, 2, 3, 4, 5].map((level) => (
                          <div
                            key={level}
                            className={`w-3 h-3 rounded-full ${
                              level <= risk.severity ? 'bg-red-500' : 'bg-slate-600'
                            }`}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                  <p className="text-sm text-slate-300 mb-2">{risk.why}</p>
                  {risk.hedge && (
                    <p className="text-xs text-slate-400 bg-slate-600/30 p-2 rounded">
                      💡 Хеджирование: {risk.hedge}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Рекомендации */}
          <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
            <h3 className="text-xl font-semibold text-white mb-4">Рекомендации</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-700/50">
                <thead className="bg-slate-700/50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Действие</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Обоснование</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Приоритет</th>
                  </tr>
                </thead>
                <tbody className="bg-slate-800/30 divide-y divide-slate-700/30">
                  {analysis.suggestions.map((suggestion, index) => (
                    <tr key={index} className="hover:bg-slate-700/20 transition-colors">
                      <td className="px-6 py-4 text-sm text-white font-medium">{suggestion.action}</td>
                      <td className="px-6 py-4 text-sm text-slate-400">{suggestion.reason}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {suggestion.priority && (
                          <span className={`px-3 py-1 text-xs font-medium rounded-full ${getPriorityColor(suggestion.priority)}`}>
                            {suggestion.priority}/3
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Целевые доли */}
          {analysis.allocation_changes && analysis.allocation_changes.length > 0 && (
            <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
              <h3 className="text-xl font-semibold text-white mb-4">Целевые доли</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-700/50">
                  <thead className="bg-slate-700/50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Тикер</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Текущая доля</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Целевая доля</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Примечание</th>
                    </tr>
                  </thead>
                  <tbody className="bg-slate-800/30 divide-y divide-slate-700/30">
                    {analysis.allocation_changes.map((change, index) => (
                      <tr key={index} className="hover:bg-slate-700/20 transition-colors">
                        <td className="px-6 py-4 text-sm text-white font-medium">{change.ticker}</td>
                        <td className="px-6 py-4 text-sm text-slate-400">
                          {change.current_pct ? `${formatNumber(change.current_pct)}%` : '—'}
                        </td>
                        <td className="px-6 py-4 text-sm text-green-400 font-medium">{formatNumber(change.target_pct)}%</td>
                        <td className="px-6 py-4 text-sm text-slate-400">{change.note || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Диверсификация */}
          {analysis.diversification && (
            <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
              <h3 className="text-xl font-semibold text-white mb-4">Диверсификация</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {analysis.diversification.herfindahl && (
                  <div>
                    <div className="text-2xl font-bold text-blue-400 mb-2">
                      {formatNumber(analysis.diversification.herfindahl)}
                    </div>
                    <p className="text-sm text-slate-400">Индекс Херфиндаля</p>
                  </div>
                )}
                {analysis.diversification.sector_gaps && analysis.diversification.sector_gaps.length > 0 && (
                  <div>
                    <h4 className="font-medium text-white mb-2">Пробелы в секторах:</h4>
                    <ul className="space-y-1">
                      {analysis.diversification.sector_gaps.map((gap, index) => (
                        <li key={index} className="text-sm text-slate-300">• {gap}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Примечания */}
          {(analysis.warnings && analysis.warnings.length > 0) || (analysis.assumptions && analysis.assumptions.length > 0) ? (
            <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
              <h3 className="text-xl font-semibold text-white mb-4">Примечания</h3>
              <div className="space-y-4">
                {analysis.warnings && analysis.warnings.length > 0 && (
                  <div>
                    <h4 className="font-medium text-red-400 mb-2">Предупреждения:</h4>
                    <ul className="space-y-1">
                      {analysis.warnings.map((warning, index) => (
                        <li key={index} className="text-sm text-slate-300">⚠️ {warning}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {analysis.assumptions && analysis.assumptions.length > 0 && (
                  <div>
                    <h4 className="font-medium text-yellow-400 mb-2">Предположения:</h4>
                    <ul className="space-y-1">
                      {analysis.assumptions.map((assumption, index) => (
                        <li key={index} className="text-sm text-slate-300">💭 {assumption}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ) : null}

          {/* Raw JSON (collapsible) */}
          {rawResponse && (
            <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
              <button
                onClick={() => setShowRawJson(!showRawJson)}
                className="flex items-center space-x-2 text-slate-400 hover:text-white transition-colors"
              >
                <span className="text-sm font-medium">
                  {showRawJson ? 'Скрыть' : 'Показать'} Raw JSON
                </span>
                <span className="text-xs">({showRawJson ? '▼' : '▶'})</span>
              </button>
              {showRawJson && (
                <pre className="mt-4 p-4 bg-slate-900/50 rounded-lg text-xs text-slate-300 overflow-x-auto">
                  {rawResponse}
                </pre>
              )}
            </div>
          )}

          {/* Дисклеймер */}
          <div className="bg-slate-700/50 backdrop-blur-xl rounded-xl p-4 border border-slate-600/50 shadow-lg">
            <p className="text-xs text-slate-400 text-center">
              Материал носит информационный характер и не является инвестиционной рекомендацией
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
