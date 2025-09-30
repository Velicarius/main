import { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '../lib/api';
import { OllamaModel, InstalledResponse } from '../types/ollama';

// Хук для работы с установленными моделями Ollama
// Зачем: Централизует логику загрузки, кэширования и обновления списка моделей
export function useOllamaModels(cacheTtlMs = 300000) { // 5 минут по умолчанию
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Функция для сортировки моделей
  // Зачем: Показываем модели в удобном порядке: llama*, gemma*, qwen*, остальные
  const sortModels = useCallback((models: OllamaModel[]): OllamaModel[] => {
    return [...models].sort((a, b) => {
      const aName = a.name.toLowerCase();
      const bName = b.name.toLowerCase();
      
      // Сначала llama*
      if (aName.startsWith('llama') && !bName.startsWith('llama')) return -1;
      if (!aName.startsWith('llama') && bName.startsWith('llama')) return 1;
      
      // Затем gemma*
      if (aName.startsWith('gemma') && !bName.startsWith('gemma') && !bName.startsWith('llama')) return -1;
      if (!aName.startsWith('gemma') && bName.startsWith('gemma') && !aName.startsWith('llama')) return 1;
      
      // Затем qwen*
      if (aName.startsWith('qwen') && !bName.startsWith('qwen') && !bName.startsWith('gemma') && !bName.startsWith('llama')) return -1;
      if (!aName.startsWith('qwen') && bName.startsWith('qwen') && !aName.startsWith('gemma') && !aName.startsWith('llama')) return 1;
      
      // Остальные по алфавиту
      return aName.localeCompare(bName);
    });
  }, []);

  // Функция для загрузки моделей с сервера
  const fetchModels = useCallback(async (): Promise<OllamaModel[]> => {
    const response = await apiFetch('/llm/models');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: Failed to fetch models`);
    }
    const data: InstalledResponse = await response.json();
    return data.models || [];
  }, []);

  // Функция для обновления списка моделей
  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Очищаем кэш при принудительном обновлении
      // Зачем: Гарантируем получение актуальных данных
      sessionStorage.removeItem('ollama_models_v1');
      
      const fetchedModels = await fetchModels();
      const sortedModels = sortModels(fetchedModels);
      
      setModels(sortedModels);
      
      // Сохраняем в кэш с таймстампом
      // Зачем: Избегаем повторных запросов в течение TTL
      const cacheData = {
        models: sortedModels,
        timestamp: Date.now()
      };
      sessionStorage.setItem('ollama_models_v1', JSON.stringify(cacheData));
      
    } catch (err: any) {
      setError(err.message || 'Failed to fetch models');
      console.error('Error fetching models:', err);
    } finally {
      setLoading(false);
    }
  }, [fetchModels, sortModels]);

  // Загрузка при монтировании компонента
  useEffect(() => {
    const loadModels = async () => {
      // Проверяем кэш
      // Зачем: Используем кэшированные данные если они свежие
      const cached = sessionStorage.getItem('ollama_models_v1');
      if (cached) {
        try {
          const cacheData = JSON.parse(cached);
          const now = Date.now();
          
          // Проверяем TTL
          if (now - cacheData.timestamp < cacheTtlMs) {
            setModels(sortModels(cacheData.models || []));
            return; // Используем кэш
          }
        } catch (err) {
          console.warn('Invalid cache data, fetching fresh models');
        }
      }
      
      // Загружаем свежие данные
      setLoading(true);
      setError(null);
      
      try {
        const fetchedModels = await fetchModels();
        const sortedModels = sortModels(fetchedModels);
        
        setModels(sortedModels);
        
        // Сохраняем в кэш
        const cacheData = {
          models: sortedModels,
          timestamp: Date.now()
        };
        sessionStorage.setItem('ollama_models_v1', JSON.stringify(cacheData));
        
      } catch (err: any) {
        setError(err.message || 'Failed to fetch models');
        console.error('Error fetching models:', err);
      } finally {
        setLoading(false);
      }
    };

    loadModels();
  }, [fetchModels, sortModels, cacheTtlMs]);

  return {
    models,
    loading,
    error,
    refresh
  };
}
