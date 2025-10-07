import React from 'react';
import { Button } from '../ui';

export interface StrategyHeaderProps {
  isExpanded: boolean;
  hasChanges: boolean;
  isLoading: boolean;
  onToggleExpand: () => void;
  onSave: () => void;
  onReset: () => void;
}

export const StrategyHeader: React.FC<StrategyHeaderProps> = ({
  isExpanded,
  hasChanges,
  isLoading,
  onToggleExpand,
  onSave,
  onReset
}) => {
  return (
    <div className="flex items-center justify-between mb-6">
      <h3 className="text-lg font-semibold text-white">Investment Strategy</h3>

      <div className="flex items-center space-x-3">
        {isExpanded && hasChanges && (
          <>
            <Button
              size="sm"
              variant="secondary"
              onClick={onReset}
              disabled={isLoading}
            >
              Reset
            </Button>
            <Button
              size="sm"
              variant="primary"
              onClick={onSave}
              loading={isLoading}
            >
              Save Changes
            </Button>
          </>
        )}

        <button
          onClick={onToggleExpand}
          className="text-slate-400 hover:text-white transition-colors p-2"
          aria-label={isExpanded ? 'Collapse strategy editor' : 'Expand strategy editor'}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {isExpanded ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            )}
          </svg>
        </button>
      </div>
    </div>
  );
};
