import React, { useState, useEffect } from 'react';
import { getBaseUrl } from '../../lib/api';

interface AIProviderStatusProps {
  provider: 'ollama' | 'openai';
  model: string;
}

interface ProviderStatus {
  available: boolean;
  error?: string;
  models?: string[];
}

export const AIProviderStatus: React.FC<AIProviderStatusProps> = ({ provider, model }) => {
  const [status, setStatus] = useState<ProviderStatus>({ available: false });
  const [loading, setLoading] = useState(false);

  const checkProviderStatus = async () => {
    setLoading(true);
    try {
      if (provider === 'ollama') {
        // Check Ollama directly
        const response = await fetch('http://localhost:11434/api/tags');
        if (response.ok) {
          const data = await response.json();
          const availableModels = data.models?.map((m: any) => m.name) || [];
          const modelAvailable = availableModels.includes(model);
          
          setStatus({
            available: modelAvailable,
            models: availableModels,
            error: modelAvailable ? undefined : `Model ${model} not found. Available: ${availableModels.join(', ')}`
          });
        } else {
          setStatus({
            available: false,
            error: 'Ollama not running. Please start Ollama on localhost:11434'
          });
        }
      } else {
        // Check OpenAI via our API
        const response = await fetch(`${getBaseUrl()}/llm/models`);
        if (response.ok) {
          const data = await response.json();
          setStatus({
            available: true,
            models: data.models || []
          });
        } else {
          setStatus({
            available: false,
            error: 'OpenAI API key not configured'
          });
        }
      }
    } catch (error) {
      setStatus({
        available: false,
        error: provider === 'ollama' 
          ? 'Ollama not available. Please ensure Ollama is running.'
          : 'OpenAI service unavailable'
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkProviderStatus();
  }, [provider, model]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm">
        <div className="w-3 h-3 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin"></div>
        <span className="text-slate-400">Checking {provider}...</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-sm">
      <div className={`w-2 h-2 rounded-full ${status.available ? 'bg-green-500' : 'bg-red-500'}`}></div>
      <span className={status.available ? 'text-green-400' : 'text-red-400'}>
        {status.available ? `${provider} available` : status.error}
      </span>
      {status.available && status.models && (
        <span className="text-slate-500 text-xs">
          ({status.models.length} models)
        </span>
      )}
    </div>
  );
};
