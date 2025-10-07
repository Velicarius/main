import React from 'react';
import { StrategyKey } from '../../types/strategy';
import { Button } from '../ui';

const STRATEGY_TEMPLATES = [
  { key: 'conservative' as StrategyKey, label: 'Conservative', riskIcon: '🛡️' },
  { key: 'balanced' as StrategyKey, label: 'Balanced', riskIcon: '⚖️' },
  { key: 'aggressive' as StrategyKey, label: 'Aggressive', riskIcon: '🚀' }
];

export interface StrategyTemplateSelectorProps {
  mode: 'manual' | 'template';
  selectedKey: StrategyKey;
  onModeChange: (mode: 'manual' | 'template') => void;
  onTemplateSelect: (key: StrategyKey) => void;
}

export const StrategyTemplateSelector: React.FC<StrategyTemplateSelectorProps> = ({
  mode,
  selectedKey,
  onModeChange,
  onTemplateSelect
}) => {
  return (
    <div className="bg-slate-700/30 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-medium text-slate-300">Strategy Mode</h4>
        <div className="flex space-x-2">
          <Button
            size="sm"
            variant={mode === 'manual' ? 'primary' : 'secondary'}
            onClick={() => onModeChange('manual')}
          >
            Manual
          </Button>
          <Button
            size="sm"
            variant={mode === 'template' ? 'primary' : 'secondary'}
            onClick={() => onModeChange('template')}
          >
            Template
          </Button>
        </div>
      </div>

      {mode === 'template' && (
        <div className="space-y-2">
          <div className="grid grid-cols-3 gap-2">
            {STRATEGY_TEMPLATES.map(template => (
              <button
                key={template.key}
                onClick={() => onTemplateSelect(template.key)}
                className={`flex items-center justify-center space-x-2 p-2 rounded text-sm font-medium transition-colors ${
                  selectedKey === template.key
                    ? 'bg-green-500/20 text-green-400 border border-green-500/50'
                    : 'bg-slate-600/50 text-slate-300 hover:bg-slate-500/50'
                }`}
                aria-label={`Select ${template.label} strategy`}
              >
                <span>{template.riskIcon}</span>
                <span>{template.label}</span>
              </button>
            ))}
          </div>
          <p className="text-xs text-slate-500">
            Select a template to auto-fill parameters. You can still edit individual fields afterward.
          </p>
        </div>
      )}
    </div>
  );
};
