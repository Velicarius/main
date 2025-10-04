import { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '../lib/api';
import { AllowedModel, AllowedResponse } from '../types/ollama';

// Хук для работы с whitelist разрешенных моделей
// Зачем: Загружает список моделей, которые можно скачать через Ollama
export function useAllowedModels() {
  const [allowedModels, setAllowedModels] = useState<AllowedModel[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Функция для загрузки whitelist с сервера
  const fetchAllowedModels = useCallback(async (): Promise<AllowedModel[]> => {
    const response = await apiFetch('/llm/allowed_models');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: Failed to fetch allowed models`);
    }
    const data: AllowedResponse = await response.json();
    return data.allowed || [];
  }, []);

  // Функция для обновления списка разрешенных моделей
  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Очищаем кэш при принудительном обновлении
      sessionStorage.removeItem('allowed_models_v1');
      
      const fetchedModels = await fetchAllowedModels();
      setAllowedModels(fetchedModels);
      
      // Сохраняем в кэш с коротким TTL (60 секунд)
      // Зачем: Whitelist меняется редко, но кэшируем на короткое время
      const cacheData = {
        models: fetchedModels,
        timestamp: Date.now()
      };
      sessionStorage.setItem('allowed_models_v1', JSON.stringify(cacheData));
      
    } catch (err: any) {
      setError(err.message || 'Failed to fetch allowed models');
      console.error('Error fetching allowed models:', err);
    } finally {
      setLoading(false);
    }
  }, [fetchAllowedModels]);

  // Загрузка при монтировании компонента
  useEffect(() => {
    const loadAllowedModels = async () => {
      // Проверяем кэш (короткий TTL - 60 секунд)
      const cached = sessionStorage.getItem('allowed_models_v1');
      if (cached) {
        try {
          const cacheData = JSON.parse(cached);
          const now = Date.now();
          
          // Проверяем TTL (60 секунд)
          if (now - cacheData.timestamp < 60000) {
            setAllowedModels(cacheData.models || []);
            return; // Используем кэш
          }
        } catch (err) {
          console.warn('Invalid cache data, fetching fresh allowed models');
        }
      }
      
      // Загружаем свежие данные
      setLoading(true);
      setError(null);
      
      try {
        const fetchedModels = await fetchAllowedModels();
        setAllowedModels(fetchedModels);
        
        // Сохраняем в кэш
        const cacheData = {
          models: fetchedModels,
          timestamp: Date.now()
        };
        sessionStorage.setItem('allowed_models_v1', JSON.stringify(cacheData));
        
      } catch (err: any) {
        setError(err.message || 'Failed to fetch allowed models');
        console.error('Error fetching allowed models:', err);
      } finally {
        setLoading(false);
      }
    };

    loadAllowedModels();
  }, []); // Убираем fetchAllowedModels из зависимостей чтобы избежать бесконечного цикла

  return {
    allowedModels,
    loading,
    error,
    refresh
  };
}
