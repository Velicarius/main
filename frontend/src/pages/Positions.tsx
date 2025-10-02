import { useState, useEffect } from 'react';
import { getPositions, addPosition, deletePosition, updatePosition, sellPosition, Position, AddPositionRequest, SellPositionRequest, getBaseUrl, getBalance, getCashLedger, CashLedgerMetric } from '../lib/api';
import { useAuthStore } from '../store/auth';
import { AddPositionForm } from '../components/common/AddPositionForm';
import { PortfolioDisplay } from '../components/common/PortfolioDisplay';

export default function Positions() {
  const { loggedIn } = useAuthStore();
  const [positions, setPositions] = useState<Position[]>([]);
  const [cashLedgerMetrics, setCashLedgerMetrics] = useState<CashLedgerMetric | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedPosition, setExpandedPosition] = useState<string | null>(null);
  const [sellingPosition, setSellingPosition] = useState<Position | null>(null);
  const [sellFormData, setSellFormData] = useState({
    quantity: '',
    sell_price: '',
  });
  

  // Edit state
  const [editingPosition, setEditingPosition] = useState<Position | null>(null);
  const [editFormData, setEditFormData] = useState({
    symbol: '',
    quantity: '',
    buy_price: '',
  });

  // Add position state
  const [isAddingPosition, setIsAddingPosition] = useState(false);
  
  // Edit/Sell form states
  const [isProcessingEdit, setIsProcessingEdit] = useState(false);
  const [isProcessingSell, setIsProcessingSell] = useState(false);
  const [operationError, setOperationError] = useState<string | null>(null);
  
  // Sorting state
  type SortField = 'symbol' | 'currentPrice' | 'value' | 'pnl';
  type SortDirection = 'asc' | 'desc';
  const [sortField, setSortField] = useState<SortField>('value');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  
  // Actions dropdown state
  const [actionsDropdown, setActionsDropdown] = useState<string | null>(null);

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
      
      setPositions(nonUsdPositions);
      
      // Загружаем метрики кассы
      try {
        const cashLedger = await getCashLedger();
        setCashLedgerMetrics(cashLedger);
        console.log('Cash Ledger:', cashLedger);
      } catch (cashLedgerError) {
        console.warn('Failed to fetch cash ledger:', cashLedgerError);
        // Fallback к старой логике если новый API не работает
        try {
          const balanceResponse = await getBalance();
          // Создаем минимальные метрики кассы для fallback
          setCashLedgerMetrics({
            free_usd: balanceResponse.usd_balance,
            portfolio_balance: 0,
            total_equity: balanceResponse.usd_balance,
            positions_count: 0
          });
        } catch (balanceError) {
          const usdPosition = enrichedPositions.find(p => p.symbol === 'USD');
          const fallbackBalance = usdPosition ? Number(usdPosition.quantity) : 0;
          setCashLedgerMetrics({
            free_usd: fallbackBalance,
            portfolio_balance: 0,
            total_equity: fallbackBalance,
            positions_count: 0
          });
        }
      }
      
      console.log('Set positions:', nonUsdPositions);
    } catch (err) {
      console.error('Error fetching positions:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch positions');
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    fetchPositions();
  }, []);

  // Refresh positions when auth state changes
  useEffect(() => {
    fetchPositions();
  }, [loggedIn]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element;
      if (actionsDropdown && !target.closest('.actions-dropdown')) {
        setActionsDropdown(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [actionsDropdown]);

  // Sorting functions
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc'); // Default to desc for value, asc for others
    }
  };

  const sortedPositions = [...positions].sort((a, b) => {
    let aValue: number | string;
    let bValue: number | string;

    // Объявляем переменные один раз для всех случаев
    const aLastPrice = Number((a as any).last_price) || 0;
    const bLastPrice = Number((b as any).last_price) || 0;
    const aBuyPrice = Number(a.buy_price) || 0;
    const bBuyPrice = Number(b.buy_price) || 0;

    switch (sortField) {
      case 'symbol':
        aValue = a.symbol;
        bValue = b.symbol;
        return sortDirection === 'asc' 
          ? (aValue as string).localeCompare(bValue as string)
          : (bValue as string).localeCompare(aValue as string);

      case 'currentPrice':
        aValue = aLastPrice || aBuyPrice || 0;
        bValue = bLastPrice || bBuyPrice || 0;
        break;

      case 'value':
        aValue = (aLastPrice || aBuyPrice || 0) * Number(a.quantity);
        bValue = (bLastPrice || bBuyPrice || 0) * Number(b.quantity);
        break;

      case 'pnl':
        // PnL только если есть EOD данные
        aValue = (aLastPrice > 0 && aBuyPrice > 0) 
          ? (aLastPrice * Number(a.quantity)) - (aBuyPrice * Number(a.quantity))
          : 0;
        bValue = (bLastPrice > 0 && bBuyPrice > 0)
          ? (bLastPrice * Number(b.quantity)) - (bBuyPrice * Number(b.quantity))
          : 0;
        break;

      default:
        return 0;
    }

    return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
  });


  const handleAddPosition = async (data: { symbol: string; quantity: number }) => {
    try {
      setIsAddingPosition(true);
      
      const newPosition: AddPositionRequest = {
        symbol: data.symbol.toUpperCase(),
        quantity: data.quantity,
      };

      await addPosition(newPosition);
      
      // Refresh positions list
      await fetchPositions();
    } catch (err) {
      console.error('Failed to add position:', err);
      throw err; // Перебрасываем ошибку для обработки в компоненте
    } finally {
      setIsAddingPosition(false);
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
    const buy_price = editFormData.buy_price ? parseFloat(editFormData.buy_price) : null;

    if (!symbol) {
      setOperationError('Symbol is required');
      return;
    }
    if (!quantity || quantity <= 0) {
      setOperationError('Quantity must be greater than 0');
      return;
    }
    if (buy_price !== null && buy_price < 0) {
      setOperationError('Buy price must be 0 or greater');
      return;
    }

    try {
      setIsProcessingEdit(true);
      setOperationError(null);

      const updateData: Partial<AddPositionRequest> = {
        symbol,
        quantity,
        ...(buy_price !== null && { buy_price }),
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
      setOperationError(err instanceof Error ? err.message : 'Failed to update position');
    } finally {
      setIsProcessingEdit(false);
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

    setIsProcessingSell(true);
    setOperationError(null);

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
      setOperationError(err instanceof Error ? err.message : 'Failed to sell position');
    } finally {
      setIsProcessingSell(false);
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

           {/* Cash Ledger Display */}
           {cashLedgerMetrics && (
             <PortfolioDisplay
               metrics={cashLedgerMetrics}
               onMetricsUpdate={() => fetchPositions()}
             />
           )}

      {/* Add Position Form */}
      <AddPositionForm onSubmit={handleAddPosition} isLoading={isAddingPosition} />

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
                const totalValue = sortedPositions.reduce((sum, pos) => {
                  const lastPrice = Number((pos as any).last_price) || 0;
                  const buyPrice = Number(pos.buy_price) || 0;
                  const currentPrice = lastPrice || buyPrice || 0;
                  const quantity = Number(pos.quantity) || 0;
                  return sum + (currentPrice * quantity);
                }, 0);
                
                const totalPnL = sortedPositions.reduce((sum, pos) => {
                  const lastPrice = Number((pos as any).last_price) || 0;
                  const buyPrice = Number(pos.buy_price) || 0;
                  const quantity = Number(pos.quantity) || 0;
                  
                  // PnL только если есть EOD данные
                  if (lastPrice > 0 && buyPrice > 0) {
                    const pnl = (lastPrice * quantity) - (buyPrice * quantity);
                    return sum + pnl;
                  }
                  return sum; // 0 если нет EOD данных
                }, 0);
                
                const totalPnLPercentage = (() => {
                  let totalWeightedReturn = 0;
                  let validPositionsCount = 0;
                  
                  sortedPositions.forEach(pos => {
                    const lastPrice = Number((pos as any).last_price) || 0;
                    const buyPrice = Number(pos.buy_price) || 0;
                    const quantity = Number(pos.quantity) || 0;
                    const invested = quantity * buyPrice;
                    
                    // Только позиции с EOD данными
                    if (lastPrice > 0 && invested > 0) {
                      const pnl = (lastPrice * quantity) - invested;
                      const returnPercentage = (pnl / invested) * 100;
                      totalWeightedReturn += returnPercentage;
                      validPositionsCount++;
                    }
                  });
                  
                  return validPositionsCount > 0 ? totalWeightedReturn / validPositionsCount : 0;
                })();
                
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
            <div className="overflow-x-auto relative">
              <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700/50">
                  <th className="text-left py-4 px-6">
                    <button
                      onClick={() => handleSort('symbol')}
                      className="flex items-center space-x-2 text-slate-400 font-medium hover:text-slate-300 transition-colors duration-200"
                    >
                      <span>Position</span>
                      {sortField === 'symbol' && (
                        <div className={`transition-transform duration-200 ${sortDirection === 'desc' ? 'rotate-180' : ''}`}>
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </div>
                      )}
                    </button>
                  </th>
                  <th className="text-right py-4 px-6">
                    <button
                      onClick={() => handleSort('currentPrice')}
                      className="flex items-center justify-end space-x-2 text-slate-400 font-medium hover:text-slate-300 transition-colors duration-200 ml-auto"
                    >
                      <span>Current Price</span>
                      {sortField === 'currentPrice' && (
                        <div className={`transition-transform duration-200 ${sortDirection === 'desc' ? 'rotate-180' : ''}`}>
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </div>
                      )}
                    </button>
                  </th>
                  <th className="text-right py-4 px-6">
                    <button
                      onClick={() => handleSort('value')}
                      className="flex items-center justify-end space-x-2 text-slate-400 font-medium hover:text-slate-300 transition-colors duration-200 ml-auto"
                    >
                      <span>Value</span>
                      {sortField === 'value' && (
                        <div className={`transition-transform duration-200 ${sortDirection === 'desc' ? 'rotate-180' : ''}`}>
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </div>
                      )}
                    </button>
                  </th>
                  <th className="text-right py-4 px-6">
                    <button
                      onClick={() => handleSort('pnl')}
                      className="flex items-center justify-end space-x-2 text-slate-400 font-medium hover:text-slate-300 transition-colors duration-200 ml-auto"
                    >
                      <span>PnL</span>
                      {sortField === 'pnl' && (
                        <div className={`transition-transform duration-200 ${sortDirection === 'desc' ? 'rotate-180' : ''}`}>
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </div>
                      )}
                    </button>
                  </th>
                  <th className="text-center py-4 px-6 w-16">
                    {/* Колонка действий без названия */}
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedPositions.map((position) => {
                  const lastPrice = Number((position as any).last_price) || 0;
                  const buyPrice = Number(position.buy_price) || 0;
                  const quantity = Number(position.quantity) || 0;
                  const currentPrice = lastPrice || buyPrice || 0; // Для отображения используем EOD цену или buy_price
                  const value = currentPrice ? quantity * currentPrice : 0;
                  
                  // PnL должен быть 0 если нет EOD цены (нет сохраненных цен за день)
                  // Если есть EOD цена и buy_price - рассчитываем PnL от buy_price  
                  const hasEodPrice = lastPrice > 0;
                  const pnl = hasEodPrice && buyPrice > 0 
                    ? (lastPrice * quantity) - (buyPrice * quantity)
                    : 0;
                  const pnlPercentage = hasEodPrice && buyPrice > 0 && (quantity * buyPrice) > 0
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
                          hasEodPrice ? (pnl >= 0 ? 'text-green-400' : 'text-red-400') : 'text-slate-400'
                        }`}>
                          {hasEodPrice ? (
                            <div>
                              <div className="text-lg">${pnl.toFixed(2)}</div>
                              <div className="text-xs opacity-75">({pnlPercentage.toFixed(2)}%)</div>
                              {(position as any).last_date && (
                                <div className="text-xs text-slate-500">
                                  {(position as any).last_date}
                                </div>
                              )}
                            </div>
                          ) : (
                            <div>
                              <div className="text-lg text-slate-400">$0.00</div>
                              <div className="text-xs text-slate-500">No EOD data</div>
                            </div>
                          )}
                        </td>
                        <td className="py-4 px-6 text-center">
                          <div className="relative flex justify-center actions-dropdown">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setActionsDropdown(actionsDropdown === position.id ? null : position.id);
                              }}
                              className="p-2 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-lg transition-all duration-200"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                              </svg>
                            </button>
                            
                            {/* Actions Dropdown */}
                            {actionsDropdown === position.id && (
                              <div className="absolute top-0 right-0 z-50 mt-8 w-32 bg-slate-700/90 backdrop-blur-xl border border-slate-600/50 rounded-lg shadow-xl overflow-hidden">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleSell(position);
                                    setActionsDropdown(null);
                                  }}
                                  className="w-full text-left px-3 py-2 text-sm text-white hover:bg-slate-600/50 transition-colors duration-200"
                                >
                                  📤 Sell
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleEdit(position);
                                    setActionsDropdown(null);
                                  }}
                                  className="w-full text-left px-3 py-2 text-sm text-white hover:bg-slate-600/50 transition-colors duration-200"
                                >
                                  ✏️ Edit
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDelete(position.id);
                                    setActionsDropdown(null);
                                  }}
                                  className="w-full text-left px-3 py-2 text-sm text-red-400 hover:bg-red-500/20 transition-colors duration-200"
                                >
                                  🗑️ Delete
                                </button>
                              </div>
                            )}
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

                  {operationError && (
                    <div className="p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
                      <p className="text-red-400 text-sm">{operationError}</p>
                    </div>
                  )}

                   <div className="flex gap-3 pt-4">
                     <button
                       type="submit"
                       disabled={isProcessingEdit}
                       className="flex-1 px-4 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 disabled:from-slate-600 disabled:to-slate-700 text-white rounded-lg transition-all duration-200 shadow-lg shadow-green-500/25 font-medium"
                     >
                       {isProcessingEdit ? (
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
                  Buy Price <span className="text-slate-500">(optional)</span>
                </label>
                <input
                  type="number"
                  id="edit_buy_price"
                  value={editFormData.buy_price}
                  onChange={(e) => setEditFormData({...editFormData, buy_price: e.target.value})}
                  placeholder="150.00 (leave empty to use current market price)"
                  min="0"
                  step="0.01"
                  className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200"
                />
                <div className="text-xs text-slate-500 mt-1">
                  If empty, will use current market price for P&L calculations
                </div>
              </div>

                  {operationError && (
                    <div className="p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
                      <p className="text-red-400 text-sm">{operationError}</p>
                    </div>
                  )}

              <div className="flex gap-3 pt-4">
                <button
                  type="submit"
                  disabled={isProcessingSell}
                  className="flex-1 px-4 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:from-slate-600 disabled:to-slate-700 text-white rounded-lg transition-all duration-200 shadow-lg shadow-blue-500/25 font-medium"
                >
                  {isProcessingSell ? (
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
