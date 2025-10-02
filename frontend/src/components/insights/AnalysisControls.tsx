import React from 'react';
import { InsightsV2Request } from '../../types/insightsV2';

interface AnalysisControlsProps {
  params: InsightsV2Request;
  onChange: (params: InsightsV2Request) => void;
  onAnalyze: () => void;
  isLoading: boolean;
  disabled?: boolean;
}

export const AnalysisControls: React.FC<AnalysisControlsProps> = ({
  params,
  onChange,
  onAnalyze,
  isLoading,
  disabled = false
}) => {
  const handleModelChange = (model: string) => {
    onChange({ ...params, model });
  };

  const handleHorizonChange = (horizon_months: number) => {
    onChange({ ...params, horizon_months });
  };

  const handleRiskProfileChange = (risk_profile: 'Conservative' | 'Balanced' | 'Aggressive') => {
    onChange({ ...params, risk_profile });
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">Параметры анализа</h3>
        <div className="hidden sm:flex items-center space-x-2 text-sm text-slate-400">
          <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse"></div>
          <span>AI Powered</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* Модель */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Модель</label>
          <select
            value={params.model}
            onChange={(e) => handleModelChange(e.target.value)}
            disabled={disabled}
            className="w-full px-3 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <option value="llama3.1:8b">llama3.1:8b (Ollama)</option>
            <option value="gpt-4o-mini">GPT-4o Mini (OpenAI)</option>
            <option value="gpt-4o">GPT-4o (OpenAI)</option>
            <option value="gemma2:9b">gemma2:9b (Ollama)</option>
            <option value="qwen2.5:7b">qwen2.5:7b (Ollama)</option>
          </select>
        </div>

        {/* Горизонт */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Горизонт (мес.)</label>
          <select
            value={params.horizon_months}
            onChange={(e) => handleHorizonChange(Number(e.target.value))}
            disabled={disabled}
            className="w-full px-3 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <option value={3}>3 месяца</option>
            <option value={6}>6 месяцев</option>
            <option value={12}>12 месяцев</option>
            <option value={18}>18 месяцев</option>
            <option value={24}>24 месяца</option>
          </select>
        </div>

        {/* Риск-профиль */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Риск-профиль</label>
          <select
            value={params.risk_profile}
            onChange={(e) => handleRiskProfileChange(e.target.value as 'Conservative' | 'Balanced' | 'Aggressive')}
            disabled={disabled}
            className="w-full px-3 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <option value="Conservative">Консервативный</option>
            <option value="Balanced">Сбалансированный</option>
            <option value="Aggressive">Агрессивный</option>
          </select>
        </div>
      </div>

      {/* Кнопка анализа */}
      <div className="flex justify-end">
        <button 
          onClick={onAnalyze}
          disabled={isLoading || disabled}
          className="px-8 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-lg transition-all duration-200 shadow-lg shadow-purple-500/25 font-medium disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
        >
          {isLoading ? (
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              <span>Анализирую...</span>
            </div>
          ) : (
            'Пересчитать анализ'
          )}
        </button>
      </div>

      {/* Информация о параметрах */}
      <div className="mt-4 p-4 bg-slate-700/30 rounded-lg">
        <div className="text-xs text-slate-400 space-y-1">
          <div className="flex justify-between">
            <span>Модель:</span>
            <span className="font-mono">{params.model}</span>
          </div>
          <div className="flex justify-between">
            <span>Горизонт анализа:</span>
            <span className="font-mono">{params.horizon_months} мес.</span>
          </div>
          <div className="flex justify-between">
            <span>Риск-профиль:</span>
            <span className="font-mono">{params.risk_profile}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
