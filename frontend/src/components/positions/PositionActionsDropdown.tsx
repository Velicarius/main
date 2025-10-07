import React from 'react';
import { Dropdown, DropdownItem } from '../ui';
import { Position } from '../../lib/api';

export interface PositionActionsDropdownProps {
  position: Position;
  onSell: (position: Position) => void;
  onEdit: (position: Position) => void;
  onDelete: (id: string) => void;
}

export const PositionActionsDropdown: React.FC<PositionActionsDropdownProps> = ({
  position,
  onSell,
  onEdit,
  onDelete
}) => {
  const items: DropdownItem[] = [
    {
      key: 'sell',
      label: 'Sell',
      icon: <span>📤</span>,
      onClick: () => onSell(position)
    },
    {
      key: 'edit',
      label: 'Edit',
      icon: <span>✏️</span>,
      onClick: () => onEdit(position)
    },
    {
      key: 'delete',
      label: 'Delete',
      icon: <span>🗑️</span>,
      onClick: () => onDelete(position.id),
      variant: 'danger'
    }
  ];

  return (
    <Dropdown
      trigger={
        <button
          className="p-2 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-lg transition-all duration-200"
          aria-label={`Actions for ${position.symbol}`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"
            />
          </svg>
        </button>
      }
      items={items}
      align="right"
    />
  );
};
