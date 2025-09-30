import { useState } from 'react';
import { apiFetch } from '../lib/api';
import { useOllamaModels } from '../hooks/useOllamaModels';
import { useAllowedModels } from '../hooks/useAllowedModels';
import { createTraceHeaders } from '../utils/traceId';
import { PullModelRequest, PullModelResponse } from '../types/ollama';

// Компонент для управления моделями Ollama
// Зачем: Позволяет скачивать новые модели и просматривать установленные
export default function ModelsSection() {
  const [selectedTag, setSelectedTag] = useState('');
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);

  // Хуки для работы с моделями
  const { models, refresh: refreshModels } = useOllamaModels();
  const { allowedModels, loading: allowedLoading, error: allowedError } = useAllowedModels();

  // Функция для форматирования размера модели
  // Зачем: Показываем размер в удобочитаемом формате
  const formatModelSize = (size?: number): string => {
    if (!size) return 'Unknown';
    const gb = size / (1024 * 1024 * 1024);
    return `${gb.toFixed(1)} ГБ`;
  };

  // Функция для скачивания модели
  const downloadModel = async () => {
    if (!selectedTag) return;

    setDownloading(true);
    setDownloadError(null);
    setDownloadSuccess(null);

    try {
      const traceHeaders = createTraceHeaders();
      
      const requestData: PullModelRequest = {
        tag: selectedTag
      };

      const response = await apiFetch('/llm/pull', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...traceHeaders
        },
        body: JSON.stringify(requestData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`HTTP ${response.status}: ${errorData.detail || 'Failed to download model'}`);
      }

      const data: PullModelResponse = await response.json();
      
      if (data.success) {
        setDownloadSuccess(`Model ${selectedTag} installed successfully`);
        // Очищаем кэш и обновляем список моделей
        // Зачем: Показываем новую модель в списке установленных
        await refreshModels();
        setSelectedTag(''); // Сбрасываем выбор
      } else {
        throw new Error(data.error || 'Download failed');
      }

    } catch (err: any) {
      setDownloadError(err.message || 'Failed to download model');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-600 rounded-lg flex items-center justify-center">
          <span className="text-white text-sm">📦</span>
        </div>
        <div>
          <h3 className="text-lg font-semibold text-white">Models</h3>
          <p className="text-sm text-slate-400">Download and manage Ollama models</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Скачивание моделей */}
        <div className="space-y-4">
          <h4 className="text-md font-medium text-white">Download Models</h4>
          
          {/* Выбор модели для скачивания */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Available Models
            </label>
            <select
              value={selectedTag}
              onChange={(e) => setSelectedTag(e.target.value)}
              className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200"
              disabled={allowedLoading || downloading}
            >
              <option value="">Select a model to download</option>
              {allowedModels.map((model) => (
                <option key={model.tag} value={model.tag}>
                  {model.label}
                </option>
              ))}
            </select>
            {allowedError && (
              <p className="text-red-400 text-xs mt-1">
                {allowedError}
              </p>
            )}
          </div>

          {/* Кнопка скачивания */}
          <button
            onClick={downloadModel}
            disabled={!selectedTag || downloading || allowedLoading}
            className="w-full px-6 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white rounded-lg transition-all duration-200 shadow-lg shadow-blue-500/25 font-medium disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
          >
            {downloading ? (
              <div className="flex items-center justify-center space-x-2">
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                <span>Downloading…</span>
              </div>
            ) : (
              'Download'
            )}
          </button>

          {/* Подсказка */}
          <p className="text-xs text-slate-500">
            Модели скачиваются локально через Ollama; это может занять время.
          </p>

          {/* Сообщения об ошибках и успехе */}
          {downloadError && (
            <div className="p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
              <p className="text-red-400 text-sm">{downloadError}</p>
            </div>
          )}

          {downloadSuccess && (
            <div className="p-3 bg-green-900/20 border border-green-500/30 rounded-lg">
              <p className="text-green-400 text-sm">{downloadSuccess}</p>
            </div>
          )}
        </div>

        {/* Установленные модели */}
        <div className="space-y-4">
          <h4 className="text-md font-medium text-white">Installed Models</h4>
          
          <div className="bg-slate-900/50 border border-slate-600/50 rounded-lg p-4 max-h-64 overflow-y-auto">
            {models.length === 0 ? (
              <p className="text-slate-400 text-sm">No models installed</p>
            ) : (
              <div className="space-y-3">
                {models.map((model) => (
                  <div key={model.name} className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h5 className="text-white font-medium text-sm">{model.name}</h5>
                        {model.family && (
                          <p className="text-slate-400 text-xs mt-1">Family: {model.family}</p>
                        )}
                        {model.modified && (
                          <p className="text-slate-500 text-xs mt-1">
                            Modified: {new Date(model.modified).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                      <div className="text-right">
                        <p className="text-slate-300 text-xs font-mono">
                          {formatModelSize(model.size)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
