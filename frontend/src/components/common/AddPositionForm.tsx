import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { PlusIcon } from '@heroicons/react/20/solid';

// Схема валидации с помощью Zod
const addPositionSchema = z.object({
  symbol: z.string()
    .min(1, 'Symbol is required')
    .max(10, 'Symbol must be 10 characters or less'),
  quantity: z.string()
    .min(1, 'Quantity is required')
    .refine((val) => {
      const num = parseFloat(val);
      return !isNaN(num) && num > 0;
    }, 'Quantity must be a positive number')
});

type AddPositionFormData = z.infer<typeof addPositionSchema>;

interface SymbolSuggestion {
  symbol: string;
  name?: string;
}

interface AddPositionFormProps {
  onSubmit: (data: { symbol: string; quantity: number }) => Promise<void>;
  isLoading?: boolean;
}

export const AddPositionForm: React.FC<AddPositionFormProps> = ({ 
  onSubmit, 
  isLoading = false 
}) => {
  // React Hook Form
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
    reset
  } = useForm<AddPositionFormData>({
    resolver: zodResolver(addPositionSchema),
    defaultValues: {
      symbol: '',
      quantity: ''
    }
  });

  // Состояние для autocomplete
  const [suggestions, setSuggestions] = useState<SymbolSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchCache, setSearchCache] = useState<Map<string, SymbolSuggestion[]>>(new Map());
  const isSelectingRef = useRef(false); // Флаг для предотвращения поиска после выбора
  const symbolValue = watch('symbol');

  // Функция умной сортировки по релевантности
  const sortByRelevance = (results: SymbolSuggestion[], query: string): SymbolSuggestion[] => {
    const queryUpper = query.toUpperCase();
    
    // Популярные символы для приоритизации
    const popularSymbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'AMD', 'INTC', 'SPY', 'QQQ'];
    
    return results.sort((a, b) => {
      const aSymbol = a.symbol.toUpperCase();
      const bSymbol = b.symbol.toUpperCase();
      
      // 1. Точное совпадение
      if (aSymbol === queryUpper && bSymbol !== queryUpper) return -1;
      if (bSymbol === queryUpper && aSymbol !== queryUpper) return 1;
      
      // 2. Начинается с query
      const aStarts = aSymbol.startsWith(queryUpper);
      const bStarts = bSymbol.startsWith(queryUpper);
      if (aStarts && !bStarts) return -1;
      if (bStarts && !aStarts) return 1;
      
      // 3. Содержит query в названии (если есть name)
      const aContainsName = a.name?.toUpperCase().includes(queryUpper) || false;
      const bContainsName = b.name?.toUpperCase().includes(queryUpper) || false;
      if (aContainsName && !bContainsName) return -1;
      if (bContainsName && !aContainsName) return 1;
      
      // 4. Популярность (если оба начинаются с query или оба содержат)
      const aPopular = popularSymbols.includes(aSymbol);
      const bPopular = popularSymbols.includes(bSymbol);
      if (aPopular && !bPopular) return -1;
      if (bPopular && !aPopular) return 1;
      
      // 5. Алфавитный порядок
      return aSymbol.localeCompare(bSymbol);
    });
  };

  // Загружаем популярные символы при инициализации
  useEffect(() => {
    const loadPopularSymbols = async () => {
      try {
        const response = await fetch('http://localhost:8001/symbols/external/popular?limit=20');
        if (response.ok) {
          const symbols: string[] = await response.json();
          const popularSuggestions = symbols.map(symbol => ({
            symbol,
            name: ''
          }));
          setSearchCache(prev => new Map(prev).set('', popularSuggestions));
        }
      } catch (error) {
        console.error('Error loading popular symbols:', error);
      }
    };
    
    loadPopularSymbols();
  }, []);

  // Функция поиска символов с кэшированием и умной сортировкой
  const searchSymbols = useCallback(async (query: string) => {
    console.log('🔍 searchSymbols called with:', query);
    
    if (query.length < 2) {
      console.log('❌ Query too short, clearing suggestions');
      setSuggestions([]);
      return;
    }

    const queryUpper = query.toUpperCase();
    
    // Проверяем кэш
    if (searchCache.has(queryUpper)) {
      console.log('💾 Using cached results for:', queryUpper);
      const cachedResults = searchCache.get(queryUpper)!;
      const sortedResults = sortByRelevance(cachedResults, queryUpper);
      setSuggestions(sortedResults);
      return;
    }

    try {
      console.log('🌐 Fetching from API for:', queryUpper);
      setSearchLoading(true);
      const response = await fetch(`http://localhost:8001/symbols/external/search?q=${encodeURIComponent(queryUpper)}&limit=50`);
      
      if (response.ok) {
        const symbols: string[] = await response.json();
        console.log('📥 API response:', symbols.length, 'symbols');
        
        const formattedSuggestions = symbols.map(symbol => ({
          symbol,
          name: ''
        }));
        
        // Применяем умную сортировку
        const sortedSuggestions = sortByRelevance(formattedSuggestions, queryUpper).slice(0, 10);
        console.log('📊 Sorted suggestions:', sortedSuggestions.map(s => s.symbol));
        
        // Сохраняем в кэш
        setSearchCache(prev => new Map(prev).set(queryUpper, sortedSuggestions));
        setSuggestions(sortedSuggestions);
      } else {
        console.log('❌ API error:', response.status);
        setSuggestions([]);
      }
    } catch (error) {
      console.error('💥 Error searching symbols:', error);
      setSuggestions([]);
    } finally {
      setSearchLoading(false);
    }
  }, [searchCache, sortByRelevance]);

  // Debounced search с использованием ref для флага блокировки
  useEffect(() => {
    console.log('🔍 Debounced search triggered:', { symbolValue, isSelecting: isSelectingRef.current, suggestionsLength: suggestions.length, showSuggestions });
    
    // Проверяем ref синхронно - блокируем поиск если пользователь только что выбрал символ
    if (isSelectingRef.current) {
      console.log('⏭️ Skipping search - user is selecting');
      isSelectingRef.current = false; // Сбрасываем флаг
      return;
    }

    const timeoutId = setTimeout(() => {
      console.log('⏰ Timeout executed:', { symbolValue, length: symbolValue.length });
      
      // Если поле не пустое, ищем символы
      if (symbolValue.length >= 2) {
        console.log('🔎 Starting search for:', symbolValue);
        searchSymbols(symbolValue);
      } else if (symbolValue.length === 0) {
        // Если поле очищено, скрываем dropdown
        console.log('🧹 Clearing suggestions - empty field');
        setShowSuggestions(false);
        setSuggestions([]);
      }
    }, 500);

    return () => clearTimeout(timeoutId);
  }, [symbolValue, searchSymbols]);

  // Автоматически показывать dropdown когда suggestions загружены
  useEffect(() => {
    console.log('👁️ Auto-show dropdown check:', { suggestionsLength: suggestions.length, symbolLength: symbolValue.length, showSuggestions });
    
    if (suggestions.length > 0 && symbolValue.length >= 2) {
      console.log('👁️ Showing dropdown - suggestions available');
      setShowSuggestions(true);
    } else if (symbolValue.length < 2) {
      console.log('👁️ Hiding dropdown - symbol too short');
      setShowSuggestions(false);
    }
  }, [suggestions, symbolValue]);

  // Обработка отправки формы
  const onFormSubmit = async (data: AddPositionFormData) => {
    try {
      await onSubmit({
        symbol: data.symbol.toUpperCase().trim(),
        quantity: parseFloat(data.quantity)
      });
      reset();
      setShowSuggestions(false);
    } catch (error) {
      console.error('Failed to add position:', error);
    }
  };

  // Обработка выбора символа из suggestions
  const handleSymbolSelect = (suggestion: SymbolSuggestion) => {
    console.log('🎯 Symbol selected:', suggestion.symbol);
    
    // Синхронно устанавливаем флаг блокировки
    isSelectingRef.current = true;
    
    // Скрываем dropdown и очищаем suggestions
    setShowSuggestions(false);
    setSuggestions([]);
    
    // Устанавливаем значение поля
    setValue('symbol', suggestion.symbol);
    
    console.log('✅ Selection completed, isSelectingRef set to true');
  };

  // Обработка фокуса на поле symbol
  const handleSymbolFocus = () => {
    // Если поле пустое, показываем популярные символы
    if (symbolValue.length === 0 && searchCache.has('')) {
      setSuggestions(searchCache.get('')!);
      setShowSuggestions(true);
    }
    // НЕ показываем dropdown если поле уже заполнено
    // Пользователь может кликнуть для редактирования, но не для автокомплита
  };


  // Обработка клика вне области
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      // Проверяем, что клик не по dropdown и не по input
      if (!target.closest('.suggestions-dropdown') && !target.closest('#symbol')) {
        setShowSuggestions(false);
      }
    };

    if (showSuggestions) {
      // Добавляем небольшую задержку, чтобы не мешать выбору
      const timeoutId = setTimeout(() => {
        document.addEventListener('click', handleClickOutside);
      }, 100);
      
      return () => {
        clearTimeout(timeoutId);
        document.removeEventListener('click', handleClickOutside);
      };
    }
  }, [showSuggestions]);

  return (
    <div className="relative z-50 bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <h3 className="text-lg font-semibold text-white mb-6">Add New Position</h3>
      
      <form onSubmit={handleSubmit(onFormSubmit)} className="flex flex-wrap gap-6">
        {/* Symbol Input with Autocomplete */}
        <div className="flex-1 min-w-[150px]">
          <label htmlFor="symbol" className="block text-sm text-slate-400 mb-1">
            Symbol *
          </label>
          <div className="relative">
            <input
              {...register('symbol')}
              type="text"
              id="symbol"
              placeholder="e.g. AAPL, MSFT"
              className={`w-full px-4 py-3 bg-slate-700/50 border rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 backdrop-blur-sm transition-all duration-200 ${
                errors.symbol ? 'border-red-500' : 'border-slate-600/50'
              }`}
              onFocus={handleSymbolFocus}
            />
            {searchLoading && (
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                <div className="w-4 h-4 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin"></div>
              </div>
            )}
          </div>
          
          {/* Helper text */}
          <p className="mt-1 text-xs text-slate-500/70">
            Enter stock ticker (e.g. AAPL, MSFT, TSLA)
          </p>
          
          {/* Error message */}
          {errors.symbol && (
            <p className="mt-1 text-sm text-red-400">{errors.symbol.message}</p>
          )}

          {/* Suggestions dropdown */}
          {showSuggestions && suggestions.length > 0 && (
            <div className="suggestions-dropdown absolute top-full left-0 right-0 mt-1 max-h-60 overflow-auto bg-slate-700/95 backdrop-blur-xl border border-slate-600/50 rounded-lg shadow-xl z-[200]">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion.symbol}
                  type="button"
                  className="w-full text-left px-4 py-3 hover:bg-slate-600/50 text-slate-200 text-sm transition-colors duration-200"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSymbolSelect(suggestion);
                  }}
                >
                  <span className="font-medium text-blue-300">{suggestion.symbol}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Quantity Input */}
        <div className="flex-1 min-w-[120px]">
          <label htmlFor="quantity" className="block text-sm text-slate-400 mb-1">
            Quantity *
          </label>
          <input
            {...register('quantity')}
            type="number"
            id="quantity"
            step="0.01"
            min="0"
            placeholder="e.g. 100"
            className={`w-full px-4 py-3 bg-slate-700/50 border rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 backdrop-blur-sm transition-all duration-200 ${
              errors.quantity ? 'border-red-500' : 'border-slate-600/50'
            }`}
          />
          
          {/* Helper text */}
          <p className="mt-1 text-xs text-slate-500/70">
            Enter number of shares
          </p>
          
          {errors.quantity && (
            <p className="mt-1 text-sm text-red-400">{errors.quantity.message}</p>
          )}
        </div>

        {/* Submit Button */}
        <div className="self-end">
          <button
            type="submit"
            disabled={isLoading}
            className="flex items-center space-x-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white rounded-lg transition-all duration-200 backdrop-blur-sm disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                <span>Adding...</span>
              </>
            ) : (
              <>
                <PlusIcon className="w-4 h-4" />
                <span>Add Position</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
