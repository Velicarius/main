import React, { useState, useEffect } from 'react';
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
  const symbolValue = watch('symbol');

  // Функция поиска символов
  const searchSymbols = async (query: string) => {
    if (query.length < 2) {
      setSuggestions([]);
      return;
    }

    try {
      setSearchLoading(true);
      const response = await fetch(`http://localhost:8001/symbols/external/search?q=${encodeURIComponent(query.toUpperCase())}`);
      
      if (response.ok) {
        const symbols: string[] = await response.json();
        const formattedSuggestions = symbols.slice(0, 10).map(symbol => ({
          symbol,
          name: ''
        }));
        setSuggestions(formattedSuggestions);
      } else {
        setSuggestions([]);
      }
    } catch (error) {
      console.error('Error searching symbols:', error);
      setSuggestions([]);
    } finally {
      setSearchLoading(false);
    }
  };

  // Debounced search
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      searchSymbols(symbolValue);
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [symbolValue]);

  // Автоматически показывать dropdown когда suggestions загружены
  useEffect(() => {
    if (suggestions.length > 0 && symbolValue.length >= 2) {
      setShowSuggestions(true);
    } else if (symbolValue.length < 2) {
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
    setValue('symbol', suggestion.symbol);
    setShowSuggestions(false);
  };

  // Обработка фокуса на поле symbol
  const handleSymbolFocus = () => {
    // Показывать dropdown если есть символы в поле и suggestions уже загружены
    if (symbolValue.length >= 2 && suggestions.length > 0) {
      setShowSuggestions(true);
    }
  };


  // Обработка клика вне области
  useEffect(() => {
    const handleClickOutside = () => {
      setShowSuggestions(false);
    };

    if (showSuggestions) {
      document.addEventListener('click', handleClickOutside);
    }

    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  }, [showSuggestions]);

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <h3 className="text-lg font-semibold text-white mb-6">Add New Position</h3>
      
      <form onSubmit={handleSubmit(onFormSubmit)} className="flex flex-wrap gap-6 items-end">
        {/* Symbol Input with Autocomplete */}
        <div className="flex-1 min-w-[150px] relative">
          <label htmlFor="symbol" className="block text-sm text-slate-400 mb-1">
            Symbol *
          </label>
          <div className="relative">
            <input
              {...register('symbol')}
              type="text"
              id="symbol"
              placeholder="AAPL"
              className={`w-full px-4 py-3 bg-slate-700/50 border rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 backdrop-blur-sm transition-all duration-200 ${
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
          
          {/* Error message */}
          {errors.symbol && (
            <p className="mt-1 text-sm text-red-400">{errors.symbol.message}</p>
          )}

          {/* Suggestions dropdown */}
          {showSuggestions && suggestions.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 max-h-60 overflow-auto bg-slate-700/95 backdrop-blur-xl border border-slate-600/50 rounded-lg shadow-xl">
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
            placeholder="100"
            className={`w-full px-4 py-3 bg-slate-700/50 border rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 backdrop-blur-sm transition-all duration-200 ${
              errors.quantity ? 'border-red-500' : 'border-slate-600/50'
            }`}
          />
          {errors.quantity && (
            <p className="mt-1 text-sm text-red-400">{errors.quantity.message}</p>
          )}
        </div>

        {/* Submit Button */}
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
      </form>
    </div>
  );
};
