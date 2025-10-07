import React from 'react';
import { Position } from '../../lib/api';
import { PositionActionsDropdown } from './PositionActionsDropdown';
import { PositionRowExpanded } from './PositionRowExpanded';

export interface PositionRowProps {
  position: Position;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onSell: (position: Position) => void;
  onEdit: (position: Position) => void;
  onDelete: (id: string) => void;
}

export const PositionRow: React.FC<PositionRowProps> = ({
  position,
  isExpanded,
  onToggleExpand,
  onSell,
  onEdit,
  onDelete
}) => {
  // Calculate prices and PnL
  const lastPrice = Number((position as any).last_price) || 0;
  const buyPrice = Number(position.buy_price) || 0;
  const quantity = Number(position.quantity) || 0;
  const currentPrice = lastPrice || buyPrice || 0;
  const value = currentPrice ? quantity * currentPrice : 0;

  // PnL logic:
  // 1. If buy_price exists - use it as baseline
  // 2. If not - use reference_price (price at date_added)
  const hasEodPrice = lastPrice > 0;
  const referencePrice = Number((position as any).reference_price) || 0;
  const effectiveBuyPrice = buyPrice > 0 ? buyPrice : referencePrice;

  const pnl =
    hasEodPrice && effectiveBuyPrice > 0
      ? lastPrice * quantity - effectiveBuyPrice * quantity
      : 0;

  const pnlPercentage =
    hasEodPrice && effectiveBuyPrice > 0 && quantity * effectiveBuyPrice > 0
      ? (pnl / (quantity * effectiveBuyPrice)) * 100
      : 0;

  return (
    <>
      <tr
        className="border-b border-slate-700/30 hover:bg-slate-700/20 transition-colors duration-200 cursor-pointer"
        onClick={onToggleExpand}
      >
        {/* Symbol & Quantity */}
        <td className="py-4 px-6">
          <div className="flex items-center space-x-3">
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-white font-medium text-lg">{position.symbol}</span>
                {position.asset_class === 'CRYPTO' && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300">
                    CRYPTO
                  </span>
                )}
              </div>
              <div className="text-slate-400 text-sm mt-1">
                {quantity.toLocaleString()} {position.asset_class === 'CRYPTO' ? 'coins' : 'shares'}
              </div>
            </div>
            <div
              className={`transition-transform duration-200 ${
                isExpanded ? 'rotate-180' : ''
              }`}
              aria-hidden="true"
            >
              <svg
                className="w-5 h-5 text-slate-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </div>
          </div>
        </td>

        {/* Current Price */}
        <td className="py-4 px-6 text-right text-slate-300">
          {currentPrice > 0 ? `$${currentPrice.toFixed(2)}` : '—'}
        </td>

        {/* Value */}
        <td className="py-4 px-6 text-right text-slate-300 font-medium">
          {value > 0 ? `$${value.toFixed(2)}` : '—'}
        </td>

        {/* P&L */}
        <td
          className={`py-4 px-6 text-right font-medium ${
            hasEodPrice ? (pnl >= 0 ? 'text-green-400' : 'text-red-400') : 'text-slate-400'
          }`}
        >
          {hasEodPrice ? (
            <div>
              <div className="text-lg flex items-center justify-end">
                {pnl >= 0 ? (
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                  </svg>
                )}
                ${pnl.toFixed(2)}
              </div>
              <div className="text-xs opacity-75">({pnlPercentage.toFixed(2)}%)</div>
              {(position as any).last_date && (
                <div className="text-xs text-slate-500">{(position as any).last_date}</div>
              )}
            </div>
          ) : (
            <div>
              <div className="text-lg text-slate-400">$0.00</div>
              <div className="text-xs text-slate-500">No EOD data</div>
            </div>
          )}
        </td>

        {/* Actions */}
        <td className="py-4 px-6 text-center" onClick={(e) => e.stopPropagation()}>
          <PositionActionsDropdown
            position={position}
            onSell={onSell}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        </td>
      </tr>

      {/* Expanded Details */}
      {isExpanded && <PositionRowExpanded position={position} />}
    </>
  );
};
