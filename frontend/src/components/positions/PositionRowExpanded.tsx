import React from 'react';
import { Position } from '../../lib/api';
import { Button } from '../ui';

export interface PositionRowExpandedProps {
  position: Position;
}

export const PositionRowExpanded: React.FC<PositionRowExpandedProps> = ({ position }) => {
  const quantity = Number(position.quantity) || 0;
  const buyPrice = Number(position.buy_price) || 0;

  return (
    <tr className="bg-slate-700/20">
      <td colSpan={5} className="py-6 px-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-lg font-semibold text-white">Transaction History</h4>
            <Button size="sm" variant="success">
              Add Transaction
            </Button>
          </div>

          {/* Mock transaction data - replace with real API call */}
          <div className="space-y-3">
            <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-600/30">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-white font-medium">
                    Buy {quantity.toLocaleString()} shares
                  </div>
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
              <p className="text-sm mt-1">
                Add more purchases or sales to see detailed history
              </p>
            </div>
          </div>
        </div>
      </td>
    </tr>
  );
};
