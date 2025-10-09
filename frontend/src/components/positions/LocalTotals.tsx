import React from 'react';
import { Position } from '../../lib/api';

interface LocalTotalsProps {
  positions: Position[];
  assetClass: 'EQUITY' | 'CRYPTO';
}

export const LocalTotals: React.FC<LocalTotalsProps> = ({ positions, assetClass }) => {
  // Calculate totals for current asset class
  const totals = React.useMemo(() => {
    const filteredPositions = positions.filter(pos => pos.asset_class === assetClass);
    
    if (filteredPositions.length === 0) {
      return {
        totalValue: 0,
        totalPnL: 0,
        totalReturn: 0,
        count: 0
      };
    }

    const totalValue = filteredPositions.reduce((sum, pos) => {
      const lastPrice = parseFloat(pos.last_price?.toString() || '0');
      const quantity = parseFloat(pos.quantity?.toString() || '0');
      const currentValue = lastPrice * quantity;
      return sum + currentValue;
    }, 0);

    const totalPnL = filteredPositions.reduce((sum, pos) => {
      const lastPrice = parseFloat(pos.last_price?.toString() || '0');
      const buyPrice = parseFloat(pos.buy_price?.toString() || '0');
      const quantity = parseFloat(pos.quantity?.toString() || '0');
      const currentValue = lastPrice * quantity;
      const costBasis = buyPrice * quantity;
      return sum + (currentValue - costBasis);
    }, 0);

    // Calculate total cost basis for return calculation
    const totalCostBasis = filteredPositions.reduce((sum, pos) => {
      const buyPrice = parseFloat(pos.buy_price?.toString() || '0');
      const quantity = parseFloat(pos.quantity?.toString() || '0');
      const costBasis = buyPrice * quantity;
      return sum + costBasis;
    }, 0);

    // Calculate return percentage: (PnL / Cost Basis) * 100
    // Handle edge cases: no cost basis, zero or negative values
    let totalReturn = 0;
    if (totalCostBasis > 0) {
      totalReturn = (totalPnL / totalCostBasis) * 100;
    } else if (totalValue > 0 && totalCostBasis === 0) {
      // If we have value but no cost basis, it's likely a data issue
      // Show 0% return instead of infinity
      totalReturn = 0;
    }

    // Debug logging for development (commented out for production)
    // console.log(`LocalTotals Debug (${assetClass}):`, {
    //   totalValue,
    //   totalPnL,
    //   totalCostBasis,
    //   totalReturn,
    //   positionsCount: filteredPositions.length
    // });

    return {
      totalValue,
      totalPnL,
      totalReturn,
      count: filteredPositions.length
    };
  }, [positions, assetClass]);

  const assetClassLabel = assetClass === 'EQUITY' ? 'Stocks' : 'Crypto';
  const assetClassIcon = assetClass === 'EQUITY' ? '📈' : '₿';

  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700/50 p-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">{assetClassIcon}</span>
        <h3 className="text-sm font-medium text-slate-300">
          Totals — {assetClassLabel}
        </h3>
        <span className="text-xs text-slate-500">
          ({totals.count} {totals.count === 1 ? 'position' : 'positions'})
        </span>
      </div>
      
      <div className="grid grid-cols-3 gap-4">
        <div>
          <div className="text-xs text-slate-400 mb-1">Total Value</div>
          <div className="text-lg font-semibold text-white">
            ${totals.totalValue.toLocaleString('en-US', { 
              minimumFractionDigits: 2, 
              maximumFractionDigits: 2 
            })}
          </div>
        </div>
        
        <div>
          <div className="text-xs text-slate-400 mb-1">Total P&L</div>
          <div className={`text-lg font-semibold ${
            totals.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'
          }`}>
            {totals.totalPnL >= 0 ? '+' : ''}
            ${totals.totalPnL.toLocaleString('en-US', { 
              minimumFractionDigits: 2, 
              maximumFractionDigits: 2 
            })}
          </div>
        </div>
        
        <div>
          <div className="text-xs text-slate-400 mb-1">Return %</div>
          <div className={`text-lg font-semibold ${
            totals.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'
          }`}>
            {totals.totalReturn >= 0 ? '+' : ''}
            {totals.totalReturn.toFixed(2)}%
          </div>
        </div>
      </div>
    </div>
  );
};
