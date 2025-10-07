import { Position } from '../lib/api';

export interface PositionWithPrice extends Position {
  last?: number;  // Mapped from last_price for compatibility
}

export interface PnLMetrics {
  totalInvested: number;
  totalMarketValue: number;
  totalPnL: number;
  pnlPercentage: number;
}

/**
 * Calculate P&L metrics for a portfolio of positions
 * Uses consistent logic across Dashboard and Positions pages
 */
export function calculatePortfolioPnL(positions: PositionWithPrice[]): PnLMetrics {
  let totalInvested = 0;
  let totalMarketValue = 0;

  positions.forEach((pos) => {
    const quantity = Number(pos.quantity) || 0;

    // Determine cost basis: buy_price or reference_price
    const buyPrice = Number(pos.buy_price) || 0;
    const referencePrice = Number(pos.reference_price) || 0;
    const effectiveBuyPrice = buyPrice || referencePrice || 0;

    // Determine current price: last_price (or mapped 'last') or fallback to buy_price
    const lastPrice = Number(pos.last_price || pos.last) || 0;
    const currentPrice = lastPrice || effectiveBuyPrice || 0;

    totalInvested += quantity * effectiveBuyPrice;
    totalMarketValue += quantity * currentPrice;
  });

  const totalPnL = totalMarketValue - totalInvested;
  const pnlPercentage = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;

  return {
    totalInvested,
    totalMarketValue,
    totalPnL,
    pnlPercentage
  };
}
