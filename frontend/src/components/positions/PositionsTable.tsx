import React from 'react';
import { Position } from '../../lib/api';
import { PositionRow } from './PositionRow';
import { Card } from '../ui';

export type SortField = 'symbol' | 'currentPrice' | 'value' | 'pnl';
export type SortDirection = 'asc' | 'desc';

export interface PositionsTableProps {
  positions: Position[];
  sortField: SortField;
  sortDirection: SortDirection;
  expandedPositionId: string | null;
  onSort: (field: SortField) => void;
  onToggleExpand: (id: string) => void;
  onSell: (position: Position) => void;
  onEdit: (position: Position) => void;
  onDelete: (id: string) => void;
}

interface SortableHeaderProps {
  field: SortField;
  label: string;
  currentSortField: SortField;
  sortDirection: SortDirection;
  align?: 'left' | 'right';
  onSort: (field: SortField) => void;
}

const SortableHeader: React.FC<SortableHeaderProps> = ({
  field,
  label,
  currentSortField,
  sortDirection,
  align = 'left',
  onSort
}) => {
  const isActive = currentSortField === field;
  const justifyClass = align === 'right' ? 'justify-end ml-auto' : '';

  return (
    <th className={`py-4 px-6 ${align === 'right' ? 'text-right' : 'text-left'}`}>
      <button
        onClick={() => onSort(field)}
        className={`flex items-center space-x-2 text-slate-400 font-medium hover:text-slate-300 transition-colors duration-200 ${justifyClass}`}
        aria-label={`Sort by ${label}`}
      >
        <span>{label}</span>
        {isActive && (
          <div
            className={`transition-transform duration-200 ${
              sortDirection === 'desc' ? 'rotate-180' : ''
            }`}
            aria-hidden="true"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </div>
        )}
      </button>
    </th>
  );
};

export const PositionsTable: React.FC<PositionsTableProps> = ({
  positions,
  sortField,
  sortDirection,
  expandedPositionId,
  onSort,
  onToggleExpand,
  onSell,
  onEdit,
  onDelete
}) => {
  if (positions.length === 0) {
    return (
      <Card>
        <div className="p-12 text-center">
          <div className="w-16 h-16 bg-slate-700/50 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl text-slate-400">📊</span>
          </div>
          <p className="text-slate-400 text-lg">No positions yet</p>
          <p className="text-slate-500 text-sm mt-2">
            Add your first position above to get started
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card noPadding>
      <div className="overflow-x-auto relative">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-700/50">
              <SortableHeader
                field="symbol"
                label="Position"
                currentSortField={sortField}
                sortDirection={sortDirection}
                onSort={onSort}
              />
              <SortableHeader
                field="currentPrice"
                label="Current Price"
                currentSortField={sortField}
                sortDirection={sortDirection}
                align="right"
                onSort={onSort}
              />
              <SortableHeader
                field="value"
                label="Value"
                currentSortField={sortField}
                sortDirection={sortDirection}
                align="right"
                onSort={onSort}
              />
              <SortableHeader
                field="pnl"
                label="PnL"
                currentSortField={sortField}
                sortDirection={sortDirection}
                align="right"
                onSort={onSort}
              />
              <th className="text-center py-4 px-6 w-16">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {positions.map((position) => (
              <PositionRow
                key={position.id}
                position={position}
                isExpanded={expandedPositionId === position.id}
                onToggleExpand={() => onToggleExpand(position.id)}
                onSell={onSell}
                onEdit={onEdit}
                onDelete={onDelete}
              />
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
};
