import { useState, useMemo } from 'react';
import { Position } from '../lib/api';
import { SortField, SortDirection } from '../components/positions';

export interface UsePositionsTableReturn {
  sortField: SortField;
  sortDirection: SortDirection;
  sortedPositions: Position[];
  handleSort: (field: SortField) => void;
}

export const usePositionsTable = (positions: Position[]): UsePositionsTableReturn => {
  const [sortField, setSortField] = useState<SortField>('value');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc'); // Default to desc for numeric fields
    }
  };

  const sortedPositions = useMemo(() => {
    return [...positions].sort((a, b) => {
      let aValue: number | string;
      let bValue: number | string;

      // Get prices once for reuse
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
          // PnL only if we have EOD data
          aValue =
            aLastPrice > 0 && aBuyPrice > 0
              ? aLastPrice * Number(a.quantity) - aBuyPrice * Number(a.quantity)
              : 0;
          bValue =
            bLastPrice > 0 && bBuyPrice > 0
              ? bLastPrice * Number(b.quantity) - bBuyPrice * Number(b.quantity)
              : 0;
          break;

        default:
          return 0;
      }

      return sortDirection === 'asc'
        ? (aValue as number) - (bValue as number)
        : (bValue as number) - (aValue as number);
    });
  }, [positions, sortField, sortDirection]);

  return {
    sortField,
    sortDirection,
    sortedPositions,
    handleSort
  };
};
