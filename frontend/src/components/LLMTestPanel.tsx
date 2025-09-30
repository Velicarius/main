import { useState, useEffect } from 'react';
import { apiFetch } from '../lib/api';
import { useOllamaModels } from '../hooks/useOllamaModels';
import { createTraceHeaders } from '../utils/traceId';
import { LLMResponse } from '../types/ollama';


export default function LLMTestPanel() {
  const [prompt, setPrompt] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [jsonSchema, setJsonSchema] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<LLMResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [traceId, setTraceId] = useState<string>('');

  // Хук для работы с установленными моделями
  const { models, loading: modelsLoading, error: modelsError, refresh: refreshModels } = useOllamaModels();

  // Восстановление выбранной модели из localStorage при монтировании
  useEffect(() => {
    const savedModel = localStorage.getItem('selected_model');
    if (savedModel) {
      setSelectedModel(savedModel);
    }
  }, []);

  // Сохранение выбранной модели в localStorage
  useEffect(() => {
    if (selectedModel) {
      localStorage.setItem('selected_model', selectedModel);
    }
  }, [selectedModel]);

  // Инициализация Trace ID при монтировании
  useEffect(() => {
    const traceHeaders = createTraceHeaders();
    setTraceId(traceHeaders['X-Trace-Id']);
  }, []);

  // Валидация JSON Schema
  const validateJsonSchema = (schemaText: string) => {
    if (!schemaText.trim()) {
      return { valid: true, schema: null };
    }
    
    try {
      const schema = JSON.parse(schemaText);
      return { valid: true, schema: schema };
    } catch (error: any) {
      return { valid: false, error: error.message };
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Валидация JSON Schema
    const schemaValidation = validateJsonSchema(jsonSchema);
    if (!schemaValidation.valid) {
      setError(`Ошибка в JSON Schema: ${schemaValidation.error}`);
      return;
    }
    
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const traceHeaders = createTraceHeaders();
      setTraceId(traceHeaders['X-Trace-Id']);
      
      const requestData: any = {
        prompt,
        json_schema: schemaValidation.schema,
        temperature: 0.7,
        max_tokens: 1000
      };
      
      // Добавляем модель только если она выбрана
      // Зачем: Если модель не выбрана, используем серверный дефолт
      if (selectedModel) {
        requestData.model = selectedModel;
      }
      
      const response = await apiFetch('/llm/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...traceHeaders
        },
        body: JSON.stringify(requestData)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`HTTP ${response.status}: ${errorData.detail || 'Неизвестная ошибка'}`);
      }
      
      const data = await response.json();
      setResult(data);
      
      // Обновляем Trace ID из заголовков ответа
      const responseTraceId = response.headers.get('X-Trace-Id');
      if (responseTraceId) {
        setTraceId(responseTraceId);
      }
      
    } catch (err: any) {
      setError(err.message || 'Ошибка при отправке запроса');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-600 rounded-lg flex items-center justify-center">
          <span className="text-white text-sm">🔬</span>
        </div>
        <div>
          <h3 className="text-lg font-semibold text-white">LLM Test Panel</h3>
          <p className="text-sm text-slate-400">Тестирование локальных LLM моделей для анализа портфеля</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Промпт */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Промпт для анализа
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Проанализируй мой портфель: 60% акции (AAPL, MSFT, GOOGL), 30% облигации (BND), 10% золото (GLD). Какие риски и возможности?"
            className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 backdrop-blur-sm transition-all duration-200 resize-vertical min-h-[120px]"
            required
          />
        </div>

        {/* Модель */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Модель LLM
          </label>
          <div className="flex gap-2">
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="flex-1 px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 backdrop-blur-sm transition-all duration-200"
              disabled={modelsLoading}
            >
              <option value="">Server default</option>
              {models.map((model) => (
                <option key={model.name} value={model.name}>
                  {model.name}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={refreshModels}
              disabled={modelsLoading}
              className="px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white hover:bg-slate-600/50 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 backdrop-blur-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Refresh models list"
            >
              {modelsLoading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                '↻'
              )}
            </button>
          </div>
          {modelsError && (
            <p className="text-red-400 text-xs mt-1">
              {modelsError}
            </p>
          )}
        </div>

        {/* JSON Schema */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            JSON Schema (опционально, для структурированного ответа)
          </label>
          <textarea
            value={jsonSchema}
            onChange={(e) => setJsonSchema(e.target.value)}
            placeholder='{"type": "object", "properties": {"analysis": {"type": "string"}, "risks": {"type": "array"}, "recommendations": {"type": "array"}}}'
            className={`w-full px-4 py-3 bg-slate-700/50 border rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 backdrop-blur-sm transition-all duration-200 resize-vertical min-h-[100px] font-mono text-sm ${
              jsonSchema && !validateJsonSchema(jsonSchema).valid 
                ? 'border-red-500/50 bg-red-900/20' 
                : 'border-slate-600/50'
            }`}
          />
          {jsonSchema && !validateJsonSchema(jsonSchema).valid && (
            <p className="text-red-400 text-xs mt-1">
              Невалидный JSON: {validateJsonSchema(jsonSchema).error}
            </p>
          )}
        </div>

        {/* Кнопка отправки */}
        <button
          type="submit"
            disabled={loading || (jsonSchema ? !validateJsonSchema(jsonSchema).valid : false)}
          className="w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white rounded-lg transition-all duration-200 shadow-lg shadow-purple-500/25 font-medium disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
        >
          {loading ? (
            <div className="flex items-center justify-center space-x-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              <span>Running…</span>
            </div>
          ) : (
            '🚀 Run'
          )}
        </button>
      </form>

      {/* Результаты */}
      {(result || error) && (
        <div className="mt-6 space-y-4">
          {/* Статус */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-300">Status</span>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${
              error ? 'bg-red-900/50 text-red-300 border border-red-500/30' :
              result?.success ? 'bg-green-900/50 text-green-300 border border-green-500/30' :
              'bg-yellow-900/50 text-yellow-300 border border-yellow-500/30'
            }`}>
              {error ? 'Error' : result?.success ? 'Success' : 'Unknown'}
            </span>
          </div>

          {/* Результат */}
          <div>
            <span className="text-sm font-medium text-slate-300 mb-2 block">Result</span>
            <div className="bg-slate-900/50 border border-slate-600/50 rounded-lg p-4">
              <pre className="text-sm text-slate-300 whitespace-pre-wrap font-mono leading-relaxed max-h-96 overflow-y-auto">
                {error ? error : result ? (
                  result.success ? (
                    `✅ Модель: ${result.model}\n` +
                    `🔢 Токенов использовано: ${result.tokens_used || 'неизвестно'}\n\n` +
                    `📝 Ответ:\n${result.response}\n\n` +
                    (result.raw_response ? `🔧 Сырой ответ от Ollama:\n${result.raw_response}` : '')
                  ) : (
                    `❌ Ошибка: ${result.error}`
                  )
                ) : ''}
              </pre>
            </div>
          </div>

          {/* Trace ID */}
          {traceId && (
            <div>
              <span className="text-sm font-medium text-slate-300 mb-2 block">Trace ID</span>
              <div className="bg-slate-900/50 border border-slate-600/50 rounded-lg p-3">
                <code className="text-xs text-slate-400 font-mono">{traceId}</code>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
