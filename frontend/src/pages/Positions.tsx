import { useState, useEffect, useRef, useCallback } from 'react';
import { getPositions, addPosition, deletePosition, updatePosition, sellPosition, Position, AddPositionRequest, SellPositionRequest, searchSymbols, getPopularSymbols, SymbolSuggestion, getBaseUrl } from '../lib/api';
import { useAuthStore } from '../store/auth';

export default function Positions() {
  const { loggedIn } = useAuthStore();
  const [positions, setPositions] = useState<Position[]>([]);
  const [usdBalance, setUsdBalance] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [expandedPosition, setExpandedPosition] = useState<string | null>(null);
  const [sellingPosition, setSellingPosition] = useState<Position | null>(null);
  const [sellFormData, setSellFormData] = useState({
    quantity: '',
    sell_price: '',
  });
  
  // Form state
  const [formData, setFormData] = useState({
    symbol: '',
    quantity: '',
    buy_price: '',
  });

  // Edit state
  const [editingPosition, setEditingPosition] = useState<Position | null>(null);
  const [editFormData, setEditFormData] = useState({
    symbol: '',
    quantity: '',
    buy_price: '',
  });

  // Symbol autocomplete state
  const [symbolInput, setSymbolInput] = useState('');
  const [suggestions, setSuggestions] = useState<SymbolSuggestion[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  
  // Refs for dropdown management
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceTimeoutRef = useRef<number | null>(null);

  const fetchPositions = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('Fetching positions...');
      const pos = await getPositions();
      console.log('Got positions:', pos);
      
        // Fetch current prices for each position (skip USD)
        const enrichedPositions = await Promise.all(
          pos.map(async (position) => {
            // Skip price fetching for USD
            if (position.symbol === 'USD') {
              return {
                ...position,
                last: 1.0  // USD always has price of 1.0
              };
            }
            
            try {
              const response = await fetch(`${getBaseUrl()}/prices-eod/${encodeURIComponent(position.symbol)}/latest`);
              let currentPrice = null;
              
              if (response.ok) {
                const priceData = await response.json();
                currentPrice = priceData.close;
              }
              
              return {
                ...position,
                last: currentPrice
              };
            } catch (error) {
              console.warn(`Failed to fetch price for ${position.symbol}:`, error);
              return {
                ...position,
                last: null
              };
            }
          })
        );
      
      // Разделяем позиции и USD баланс
      const nonUsdPositions = enrichedPositions.filter(p => p.symbol !== 'USD');
      const usdPosition = enrichedPositions.find(p => p.symbol === 'USD');
      
      setPositions(nonUsdPositions);
      setUsdBalance(usdPosition ? Number(usdPosition.quantity) : 0);
      console.log('Set positions:', nonUsdPositions);
      console.log('USD Balance:', usdPosition ? Number(usdPosition.quantity) : 0);
    } catch (err) {
      console.error('Error fetching positions:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch positions');
    } finally {
      setLoading(false);
    }
  };

  // Normalize search results to consistent format
  const normalizeSearchResults = (rawResults: any[]): SymbolSuggestion[] => {
    return rawResults.map(item => ({
      symbol: item.symbol ?? item.ticker ?? item.code ?? item.Symbol ?? String(item),
      name: item.name ?? item.companyName ?? item.displayName ?? item.Name ?? ""
    }));
  };

  // Debounced symbol search function
  const searchSymbolSuggestions = useCallback(async (query: string) => {
    console.log(`[SYMBOLS] query=${query}`);
    
    try {
      setLoadingSuggestions(true);
      let rawResults: any[];
      
      if (query.trim().length >= 2) {
        // Normalize query: uppercase and ASCII only
        const normalizedQuery = query.trim().toUpperCase().replace(/[^\x00-\x7F]/g, '');
        rawResults = await searchSymbols(normalizedQuery);
        
        // Log first item to verify data shape
        if (rawResults.length > 0) {
          console.log("[SYMBOLS] first item", rawResults[0]);
        }
        
        // If search returns empty (422 handled in API), fallback to popular symbols
        if (rawResults.length === 0) {
          rawResults = await getPopularSymbols();
          if (rawResults.length > 0) {
            console.log("[SYMBOLS] popular first item", rawResults[0]);
          }
        }
      } else {
        rawResults = await getPopularSymbols();
        if (rawResults.length > 0) {
          console.log("[SYMBOLS] popular first item", rawResults[0]);
        }
      }
      
      // Normalize results to consistent format
      const normalizedResults = normalizeSearchResults(rawResults);
      console.log(`[SYMBOLS] results=`, normalizedResults.length);
      setSuggestions(normalizedResults);
    } catch (err) {
      console.error('Failed to fetch symbol suggestions:', err);
      setSuggestions([]);
    } finally {
      setLoadingSuggestions(false);
    }
  }, []);

  // Debounced search effect
  useEffect(() => {
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }

    debounceTimeoutRef.current = setTimeout(() => {
      searchSymbolSuggestions(symbolInput);
    }, 300);

    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, [symbolInput, searchSymbolSuggestions]);

  // Load popular symbols on mount
  useEffect(() => {
    searchSymbolSuggestions('');
  }, [searchSymbolSuggestions]);

  useEffect(() => {
    fetchPositions();
  }, []);

  // Refresh positions when auth state changes
  useEffect(() => {
    fetchPositions();
  }, [loggedIn]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSymbolChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.toUpperCase().trim();
    setSymbolInput(value);
    setFormData(prev => ({
      ...prev,
      symbol: value
    }));
    setShowSuggestions(true);
  };

  const handleSymbolSelect = (suggestion: SymbolSuggestion) => {
    setSymbolInput(suggestion.symbol);
    setFormData(prev => ({
      ...prev,
      symbol: suggestion.symbol
    }));
    setShowSuggestions(false);
  };

  const handleSymbolBlur = () => {
    // Delay hiding suggestions to allow for click events
    setTimeout(() => {
      setShowSuggestions(false);
    }, 150);
  };

  const handleSymbolFocus = () => {
    setShowSuggestions(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validation
    const symbol = formData.symbol.trim();
    const quantity = parseFloat(formData.quantity);
    const buy_price = parseFloat(formData.buy_price);

    if (!symbol) {
      setSubmitError('Symbol is required');
      return;
    }
    if (!quantity || quantity <= 0) {
      setSubmitError('Quantity must be greater than 0');
      return;
    }
    if (buy_price < 0) {
      setSubmitError('Buy price must be 0 or greater');
      return;
    }

    try {
      setSubmitting(true);
      setSubmitError(null);

      const newPosition: AddPositionRequest = {
        symbol,
        quantity,
        buy_price,
      };

      await addPosition(newPosition);
      
      // Reset form
      setFormData({
        symbol: '',
        quantity: '',
        buy_price: '',
      });
      setSymbolInput('');
      setShowSuggestions(false);

      // Refresh positions list
      await fetchPositions();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to add position');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (position: Position) => {
    setEditingPosition(position);
    setEditFormData({
      symbol: position.symbol,
      quantity: position.quantity.toString(),
      buy_price: position.buy_price?.toString() || '',
    });
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!editingPosition) return;
    
    // Validation
    const symbol = editFormData.symbol.trim();
    const quantity = parseFloat(editFormData.quantity);
    const buy_price = parseFloat(editFormData.buy_price);

    if (!symbol) {
      setSubmitError('Symbol is required');
      return;
    }
    if (!quantity || quantity <= 0) {
      setSubmitError('Quantity must be greater than 0');
      return;
    }
    if (buy_price < 0) {
      setSubmitError('Buy price must be 0 or greater');
      return;
    }

    try {
      setSubmitting(true);
      setSubmitError(null);

      const updateData: Partial<AddPositionRequest> = {
        symbol,
        quantity,
        buy_price,
      };

      console.log('Updating position:', editingPosition.id, updateData);
      await updatePosition(editingPosition.id, updateData);
      console.log('Position updated successfully');
      
      // Reset edit form
      setEditingPosition(null);
      setEditFormData({
        symbol: '',
        quantity: '',
        buy_price: '',
      });

      // Refresh positions list
      console.log('Refreshing positions...');
      await fetchPositions();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to update position');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancelEdit = () => {
    setEditingPosition(null);
    setEditFormData({
      symbol: '',
      quantity: '',
      buy_price: '',
    });
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this position?')) {
      return;
    }

    try {
      await deletePosition(id);
      await fetchPositions();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete position');
    }
  };

  const handlePositionClick = (positionId: string) => {
    setExpandedPosition(expandedPosition === positionId ? null : positionId);
  };

  const handleSell = (position: Position) => {
    setSellingPosition(position);
    setSellFormData({
      quantity: '',
      sell_price: position.buy_price?.toString() || '',
    });
  };

  const handleSellSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sellingPosition) return;

    setSubmitting(true);
    setSubmitError(null);

    try {
      const sellData: SellPositionRequest = {
        position_id: sellingPosition.id,
        quantity: parseFloat(sellFormData.quantity),
        sell_price: sellFormData.sell_price ? parseFloat(sellFormData.sell_price) : undefined,
      };

      await sellPosition(sellData);
      await fetchPositions();
      setSellingPosition(null);
      setSellFormData({ quantity: '', sell_price: '' });
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to sell position');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancelSell = () => {
    setSellingPosition(null);
    setSellFormData({ quantity: '', sell_price: '' });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
          <div className="text-slate-400">Loading positions...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
           <div className="flex items-center justify-between">
             <div>
               <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
                 📊 Positions
               </h1>
               <p className="text-slate-400 mt-2">Manage your investment positions</p>
             </div>
             <div className="hidden sm:flex items-center space-x-2 text-sm text-slate-400">
               <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
               <span>Live prices</span>
             </div>
           </div>

           {/* USD Balance Card */}
           <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
             <div className="flex items-center justify-between">
               <div>
                 <h3 className="text-lg font-semibold text-white">💰 Free Cash</h3>
                 <p className="text-slate-400 text-sm">Available for investment</p>
               </div>
               <div className="text-right">
                 <div className="text-3xl font-bold text-green-400">
                   ${usdBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                 </div>
                 <div className="text-sm text-slate-400">USD</div>
               </div>
             </div>
           </div>

      {/* Add Position Form */}
      <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
        <h3 className="text-lg font-semibold text-white mb-6">Add New Position</h3>
        
        <form onSubmit={handleSubmit} className="flex flex-wrap gap-6 items-end">
          <div className="flex-1 min-w-[120px] relative">
            <label htmlFor="symbol" className="block text-sm text-slate-400 mb-1">
              Symbol
            </label>
            <input
              ref={inputRef}
              type="text"
              id="symbol"
              name="symbol"
              value={symbolInput}
              onChange={handleSymbolChange}
              onBlur={handleSymbolBlur}
              onFocus={handleSymbolFocus}
              placeholder="AAPL"
              className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200"
              required
            />
            
            {/* Suggestions Dropdown */}
            {showSuggestions && (
              <div
                ref={dropdownRef}
                className="absolute z-10 w-full mt-2 bg-slate-700/90 backdrop-blur-xl border border-slate-600/50 rounded-lg shadow-xl max-h-60 overflow-y-auto"
              >
                {loadingSuggestions ? (
                  <div className="px-4 py-3 text-slate-400 text-sm flex items-center space-x-2">
                    <div className="w-4 h-4 border-2 border-slate-400/30 border-t-slate-400 rounded-full animate-spin"></div>
                    <span>Loading...</span>
                  </div>
                ) : suggestions.length === 0 ? (
                  <div className="px-4 py-3 text-slate-400 text-sm">No matches found</div>
                ) : (
                  suggestions.map((suggestion, index) => (
                    <button
                      key={`${suggestion.symbol}-${index}`}
                      type="button"
                      onClick={() => handleSymbolSelect(suggestion)}
                      className="w-full text-left px-4 py-3 hover:bg-slate-600/50 text-slate-200 text-sm border-b border-slate-600/30 last:border-b-0 transition-colors duration-200"
                    >
                      <div className="flex items-center">
                        <strong className="text-blue-400">{suggestion.symbol}</strong>
                        {suggestion.name && (
                          <span className="opacity-70 ml-2 text-slate-400">{suggestion.name}</span>
                        )}
                      </div>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>

          <div className="flex-1 min-w-[120px]">
            <label htmlFor="quantity" className="block text-sm text-slate-400 mb-1">
              Quantity
            </label>
            <input
              type="number"
              id="quantity"
              name="quantity"
              value={formData.quantity}
              onChange={handleInputChange}
              placeholder="100"
              min="0.00000001"
              step="0.00000001"
              className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200"
              required
            />
          </div>

          <div className="flex-1 min-w-[120px]">
            <label htmlFor="buy_price" className="block text-sm text-slate-400 mb-1">
              Buy Price
            </label>
            <input
              type="number"
              id="buy_price"
              name="buy_price"
              value={formData.buy_price}
              onChange={handleInputChange}
              placeholder="150.00"
              min="0"
              step="0.01"
              className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200"
              required
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="px-6 py-3 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 disabled:from-slate-600 disabled:to-slate-700 disabled:cursor-not-allowed text-white rounded-lg transition-all duration-200 shadow-lg shadow-emerald-500/25 font-medium"
          >
            {submitting ? (
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                <span>Adding...</span>
              </div>
            ) : (
              'Add Position'
            )}
          </button>
        </form>

        {submitError && (
          <div className="mt-6 p-4 bg-gradient-to-r from-red-900/20 to-red-800/20 border border-red-500/30 rounded-lg backdrop-blur-sm">
            <div className="flex items-center space-x-3">
              <div className="w-6 h-6 bg-red-500/20 rounded-full flex items-center justify-center">
                <span className="text-red-400 text-sm">!</span>
              </div>
              <p className="text-red-400 font-medium">{submitError}</p>
            </div>
          </div>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-gradient-to-r from-red-900/20 to-red-800/20 border border-red-500/30 rounded-xl p-6 backdrop-blur-sm">
          <div className="flex items-center space-x-3">
            <div className="w-6 h-6 bg-red-500/20 rounded-full flex items-center justify-center">
              <span className="text-red-400 text-sm">!</span>
            </div>
            <div className="text-red-400 font-medium">Error: {error}</div>
          </div>
        </div>
      )}

      {/* Positions Table */}
      <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl border border-slate-700/50 shadow-lg">
        <div className="p-6 border-b border-slate-700/50">
          <h3 className="text-lg font-semibold text-white">Your Positions</h3>
        </div>
        
        {positions.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-16 h-16 bg-slate-700/50 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl text-slate-400">📊</span>
            </div>
            <p className="text-slate-400 text-lg">No positions yet</p>
            <p className="text-slate-500 text-sm mt-2">Add your first position above to get started</p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Summary Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-slate-700/30 rounded-lg border border-slate-600/30">
              {(() => {
                const totalValue = positions.reduce((sum, pos) => {
                  const currentPrice = Number((pos as any).last) || Number(pos.buy_price) || 0;
                  const quantity = Number(pos.quantity) || 0;
                  return sum + (currentPrice * quantity);
                }, 0);
                
                const totalPnL = positions.reduce((sum, pos) => {
                  const currentPrice = Number((pos as any).last) || Number(pos.buy_price) || 0;
                  const buyPrice = Number(pos.buy_price) || 0;
                  const quantity = Number(pos.quantity) || 0;
                  const value = currentPrice * quantity;
                  const pnl = value - (quantity * buyPrice);
                  return sum + pnl;
                }, 0);
                
                const totalPnLPercentage = positions.reduce((sum, pos) => {
                  const currentPrice = Number((pos as any).last) || Number(pos.buy_price) || 0;
                  const buyPrice = Number(pos.buy_price) || 0;
                  const quantity = Number(pos.quantity) || 0;
                  const invested = quantity * buyPrice;
                  if (invested > 0) {
                    const pnl = (currentPrice * quantity) - invested;
                    return sum + (pnl / invested) * 100;
                  }
                  return sum;
                }, 0) / positions.length;
                
                return (
                  <>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-white">${totalValue.toFixed(2)}</div>
                      <div className="text-sm text-slate-400">Total Value</div>
                    </div>
                    <div className="text-center">
                      <div className={`text-2xl font-bold ${totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        ${totalPnL.toFixed(2)}
                      </div>
                      <div className="text-sm text-slate-400">Total P&L</div>
                    </div>
                    <div className="text-center">
                      <div className={`text-2xl font-bold ${totalPnLPercentage >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {totalPnLPercentage.toFixed(2)}%
                      </div>
                      <div className="text-sm text-slate-400">Avg Return</div>
                    </div>
                  </>
                );
              })()}
            </div>
            
            {/* Positions Table */}
            <div className="overflow-x-auto">
              <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700/50">
                  <th className="text-left py-4 px-6 text-slate-400 font-medium">Position</th>
                  <th className="text-right py-4 px-6 text-slate-400 font-medium">Current Price</th>
                  <th className="text-right py-4 px-6 text-slate-400 font-medium">Value</th>
                  <th className="text-right py-4 px-6 text-slate-400 font-medium">PnL</th>
                  <th className="text-center py-4 px-6 text-slate-400 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((position) => {
                  const currentPrice = Number((position as any).last) || Number(position.buy_price) || 0;
                  const buyPrice = Number(position.buy_price) || 0;
                  const quantity = Number(position.quantity) || 0;
                  const value = currentPrice ? quantity * currentPrice : 0;
                  const pnl = value - (quantity * buyPrice);
                  const pnlPercentage = (quantity * buyPrice) > 0 
                    ? (pnl / (quantity * buyPrice)) * 100 
                    : 0;

                  return (
                    <>
                      <tr 
                        key={position.id} 
                        className="border-b border-slate-700/30 hover:bg-slate-700/20 transition-colors duration-200 cursor-pointer"
                        onClick={() => handlePositionClick(position.id)}
                      >
                        <td className="py-4 px-6">
                          <div className="flex items-center space-x-3">
                            <div>
                              <div className="text-white font-medium text-lg">{position.symbol}</div>
                              <div className="text-slate-400 text-sm mt-1">
                                {quantity.toLocaleString()} shares
                              </div>
                            </div>
                            <div className={`transition-transform duration-200 ${
                              expandedPosition === position.id ? 'rotate-180' : ''
                            }`}>
                              <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                              </svg>
                            </div>
                          </div>
                        </td>
                        <td className="py-4 px-6 text-right text-slate-300">
                          ${currentPrice > 0 ? currentPrice.toFixed(2) : '—'}
                        </td>
                        <td className="py-4 px-6 text-right text-slate-300 font-medium">
                          ${value > 0 ? value.toFixed(2) : '—'}
                        </td>
                        <td className={`py-4 px-6 text-right font-medium ${
                          pnl >= 0 ? 'text-green-400' : 'text-red-400'
                        }`}>
                          {currentPrice > 0 ? (
                            <div>
                              <div className="text-lg">${pnl.toFixed(2)}</div>
                              <div className="text-xs opacity-75">({pnlPercentage.toFixed(2)}%)</div>
                            </div>
                          ) : '—'}
                        </td>
                        <td className="py-4 px-6 text-center">
                          <div className="flex gap-2 justify-center">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSell(position);
                              }}
                              className="px-3 py-1.5 text-xs bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white rounded-lg transition-all duration-200 shadow-lg shadow-green-500/25"
                            >
                              Sell
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleEdit(position);
                              }}
                              className="px-3 py-1.5 text-xs bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-lg transition-all duration-200 shadow-lg shadow-blue-500/25"
                            >
                              Edit
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDelete(position.id);
                              }}
                              className="px-3 py-1.5 text-xs bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white rounded-lg transition-all duration-200 shadow-lg shadow-red-500/25"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                      
                      {/* Expanded Details */}
                      {expandedPosition === position.id && (
                        <tr className="bg-slate-700/20">
                          <td colSpan={5} className="py-6 px-6">
                            <div className="space-y-4">
                              <div className="flex items-center justify-between">
                                <h4 className="text-lg font-semibold text-white">Transaction History</h4>
                                <button className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 text-white rounded-lg transition-all duration-200 shadow-lg shadow-emerald-500/25 text-sm">
                                  Add Transaction
                                </button>
                              </div>
                              
                              {/* Mock transaction data - replace with real API call */}
                              <div className="space-y-3">
                                <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-600/30">
                                  <div className="flex items-center justify-between">
                                    <div>
                                      <div className="text-white font-medium">Buy {quantity.toLocaleString()} shares</div>
                                      <div className="text-slate-400 text-sm">${buyPrice.toFixed(2)} per share</div>
                                    </div>
                                    <div className="text-right">
                                      <div className="text-slate-300">${(quantity * buyPrice).toFixed(2)}</div>
                                      <div className="text-slate-400 text-sm">Total cost</div>
                                    </div>
                                  </div>
                                </div>
                                
                                {/* Placeholder for additional transactions */}
                                <div className="text-center py-8 text-slate-400">
                                  <div className="w-12 h-12 bg-slate-700/50 rounded-full flex items-center justify-center mx-auto mb-3">
                                    <span className="text-xl">📈</span>
                                  </div>
                                  <p>No additional transactions</p>
                                  <p className="text-sm mt-1">Add more purchases or sales to see detailed history</p>
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })}
              </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

           {/* Sell Position Modal */}
           {sellingPosition && (
             <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
               <div className="bg-slate-800/90 backdrop-blur-xl rounded-xl p-6 w-full max-w-md border border-slate-700/50 shadow-2xl">
                 <h3 className="text-lg font-semibold text-white mb-6">Sell Position</h3>
                 
                 <div className="mb-4 p-3 bg-slate-700/30 rounded-lg">
                   <div className="text-sm text-slate-400">Selling</div>
                   <div className="text-white font-medium">{sellingPosition.symbol}</div>
                   <div className="text-sm text-slate-400">
                     Available: {sellingPosition.quantity.toLocaleString()} shares
                   </div>
                 </div>
                 
                 <form onSubmit={handleSellSubmit} className="space-y-6">
                   <div>
                     <label htmlFor="sell_quantity" className="block text-sm text-slate-400 mb-2">
                       Quantity to Sell
                     </label>
                     <input
                       type="number"
                       id="sell_quantity"
                       value={sellFormData.quantity}
                       onChange={(e) => setSellFormData({...sellFormData, quantity: e.target.value})}
                       placeholder="0"
                       min="0"
                       max={sellingPosition.quantity}
                       step="0.01"
                       className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200"
                       required
                     />
                   </div>

                   <div>
                     <label htmlFor="sell_price" className="block text-sm text-slate-400 mb-2">
                       Sell Price (optional)
                     </label>
                     <input
                       type="number"
                       id="sell_price"
                       value={sellFormData.sell_price}
                       onChange={(e) => setSellFormData({...sellFormData, sell_price: e.target.value})}
                       placeholder="0.00"
                       min="0"
                       step="0.01"
                       className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200"
                     />
                     <div className="text-xs text-slate-500 mt-1">
                       If empty, will use buy price: ${sellingPosition.buy_price?.toFixed(2) || '0.00'}
                     </div>
                   </div>

                   {submitError && (
                     <div className="p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
                       <p className="text-red-400 text-sm">{submitError}</p>
                     </div>
                   )}

                   <div className="flex gap-3 pt-4">
                     <button
                       type="submit"
                       disabled={submitting}
                       className="flex-1 px-4 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 disabled:from-slate-600 disabled:to-slate-700 text-white rounded-lg transition-all duration-200 shadow-lg shadow-green-500/25 font-medium"
                     >
                       {submitting ? (
                         <div className="flex items-center justify-center space-x-2">
                           <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                           <span>Selling...</span>
                         </div>
                       ) : (
                         'Sell Position'
                       )}
                     </button>
                     <button
                       type="button"
                       onClick={handleCancelSell}
                       className="flex-1 px-4 py-3 bg-slate-600/50 hover:bg-slate-600 text-white rounded-lg transition-all duration-200 backdrop-blur-sm"
                     >
                       Cancel
                     </button>
                   </div>
                 </form>
               </div>
             </div>
           )}

           {/* Edit Position Modal */}
           {editingPosition && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800/90 backdrop-blur-xl rounded-xl p-6 w-full max-w-md border border-slate-700/50 shadow-2xl">
            <h3 className="text-lg font-semibold text-white mb-6">Edit Position</h3>
            
            <form onSubmit={handleEditSubmit} className="space-y-6">
              <div>
                <label htmlFor="edit_symbol" className="block text-sm text-slate-400 mb-2">
                  Symbol
                </label>
                <input
                  type="text"
                  id="edit_symbol"
                  value={editFormData.symbol}
                  onChange={(e) => setEditFormData({...editFormData, symbol: e.target.value})}
                  placeholder="AAPL"
                  className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200"
                  required
                />
              </div>

              <div>
                <label htmlFor="edit_quantity" className="block text-sm text-slate-400 mb-2">
                  Quantity
                </label>
                <input
                  type="number"
                  id="edit_quantity"
                  value={editFormData.quantity}
                  onChange={(e) => setEditFormData({...editFormData, quantity: e.target.value})}
                  placeholder="10"
                  min="0"
                  step="0.01"
                  className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200"
                  required
                />
              </div>

              <div>
                <label htmlFor="edit_buy_price" className="block text-sm text-slate-400 mb-2">
                  Buy Price
                </label>
                <input
                  type="number"
                  id="edit_buy_price"
                  value={editFormData.buy_price}
                  onChange={(e) => setEditFormData({...editFormData, buy_price: e.target.value})}
                  placeholder="150.00"
                  min="0"
                  step="0.01"
                  className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200"
                  required
                />
              </div>

              {submitError && (
                <div className="p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
                  <p className="text-red-400 text-sm">{submitError}</p>
                </div>
              )}

              <div className="flex gap-3 pt-4">
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 px-4 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:from-slate-600 disabled:to-slate-700 text-white rounded-lg transition-all duration-200 shadow-lg shadow-blue-500/25 font-medium"
                >
                  {submitting ? (
                    <div className="flex items-center justify-center space-x-2">
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                      <span>Updating...</span>
                    </div>
                  ) : (
                    'Update Position'
                  )}
                </button>
                <button
                  type="button"
                  onClick={handleCancelEdit}
                  className="flex-1 px-4 py-3 bg-slate-600/50 hover:bg-slate-600 text-white rounded-lg transition-all duration-200 backdrop-blur-sm"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
