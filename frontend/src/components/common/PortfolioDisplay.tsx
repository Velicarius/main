import React, { useState } from 'react';
import { CashLedgerMetric, updateBalance } from '../../lib/api';
import { BalanceModal } from '../ui/BalanceModal';

interface PortfolioDisplayProps {
  metrics: CashLedgerMetric;
  onMetricsUpdate: () => void;
}

export const PortfolioDisplay: React.FC<PortfolioDisplayProps> = ({
  metrics,
  onMetricsUpdate,
}) => {
  const [showBalanceModal, setShowBalanceModal] = useState(false);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const handleBalanceUpdate = async (newBalance: number) => {
    await updateBalance(newBalance);
    onMetricsUpdate(); // Обновляем метрики в родительском компоненте
  };

  return (
    <div className="bg-gradient-to-r from-slate-800/50 to-slate-700/50 backdrop-blur-xl rounded-xl p-6 border border-slate-600/50 shadow-lg">
      <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
        <div className="w-8 h-8 bg-blue-500/20 rounded-full flex items-center justify-center mr-3">
          <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        My Portfolio
      </h3>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Free USD - Clickable */}
        <div 
          className="text-center p-4 bg-slate-700/30 rounded-lg border border-slate-600/30 cursor-pointer hover:bg-slate-600/40 hover:border-green-500/50 transition-all duration-200 group"
          onClick={() => setShowBalanceModal(true)}
        >
          <div className="text-2xl font-bold text-green-400 mb-2 group-hover:text-green-300">
            {formatCurrency(metrics.free_usd)}
          </div>
          <div className="text-sm text-slate-400 mb-3">Free USD</div>
          <div className="text-xs text-slate-500 group-hover:text-slate-400">
            Click to manage balance
          </div>
        </div>

        {/* Portfolio Balance */}
        <div className="text-center p-4 bg-slate-700/30 rounded-lg border border-slate-600/30">
          <div className="text-2xl font-bold text-blue-400 mb-2">
            {formatCurrency(metrics.portfolio_balance)}
          </div>
          <div className="text-sm text-slate-400 mb-3">Portfolio Balance</div>
          <div className="text-xs text-slate-500">
            Market value of {metrics.positions_count} position{metrics.positions_count !== 1 ? 's' : ''}
          </div>
        </div>

        {/* Total Equity */}
        <div className="text-center p-4 bg-gradient-to-r from-purple-700/20 to-indigo-700/20 rounded-lg border border-purple-600/30">
          <div className="text-2xl font-bold text-white mb-2">
            {formatCurrency(metrics.total_equity)}
          </div>
          <div className="text-sm text-slate-300 mb-3 font-bold">Total Equity</div>
          <div className="text-xs text-slate-400">
            Total portfolio value
          </div>
        </div>
      </div>

      {/* Additional metrics */}
      <div className="mt-4 pt-4 border-t border-slate-600/30">
        <div className="flex justify-between items-center text-sm text-slate-400">
          <span>Cash allocation: {((metrics.free_usd / metrics.total_equity) * 100).toFixed(1)}%</span>
          <span>Portfolio allocation: {((metrics.portfolio_balance / metrics.total_equity) * 100).toFixed(1)}%</span>
        </div>
      </div>

      {/* Модальное окно через Portal */}
      <BalanceModal
        isOpen={showBalanceModal}
        onClose={() => setShowBalanceModal(false)}
        currentBalance={Number(metrics.free_usd) || 0}
        onBalanceUpdate={handleBalanceUpdate}
      />
    </div>
  );
};