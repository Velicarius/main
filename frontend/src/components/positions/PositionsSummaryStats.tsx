import React from 'react';
import { Position } from '../../lib/api';
import { calculatePortfolioPnL } from '../../utils/pnl';

export interface PositionsSummaryStatsProps {
  positions: Position[];
}

export const PositionsSummaryStats: React.FC<PositionsSummaryStatsProps> = ({ positions }) => {
  // Use shared P&L calculation logic
  const { totalMarketValue, totalPnL, pnlPercentage } = calculatePortfolioPnL(positions as any);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-slate-700/30 rounded-lg border border-slate-600/30">
      <div className="text-center">
        <div className="text-2xl font-bold text-white">${totalMarketValue.toFixed(2)}</div>
        <div className="text-sm text-slate-400">Total Value</div>
      </div>
      <div className="text-center">
        <div className={`text-2xl font-bold ${totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          ${totalPnL.toFixed(2)}
        </div>
        <div className="text-sm text-slate-400">Total P&L</div>
      </div>
      <div className="text-center">
        <div className={`text-2xl font-bold ${pnlPercentage >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          {pnlPercentage.toFixed(2)}%
        </div>
        <div className="text-sm text-slate-400">Return %</div>
      </div>
    </div>
  );
};
