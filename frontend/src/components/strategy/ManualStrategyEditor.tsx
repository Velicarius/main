import { useState, useEffect } from 'react';
import { useStrategyStore } from '../../store/strategy';
import { RiskLevel, StrategyKey } from '../../types/strategy';
import { AssetAllocationManager } from './AssetAllocationManager';
import { StrategyConstraints } from './StrategyConstraints';
import { StrategyHeader } from './StrategyHeader';
import { StrategyTemplateSelector } from './StrategyTemplateSelector';
import { StrategyBasicFields } from './StrategyBasicFields';
import { StrategyRebalancingConfig } from './StrategyRebalancingConfig';
import { StrategySummaryPanel } from './StrategySummaryPanel';
import { useStrategyValidation } from '../../hooks/useStrategyValidation';
import { useStrategyCalculations } from '../../hooks/useStrategyCalculations';
import { Alert, Card } from '../ui';

interface ManualStrategyEditorProps {
  currentValue?: number;
  onStrategyUpdate?: () => void;
}

const TEMPLATE_DEFAULTS: Record<StrategyKey, { riskLevel: RiskLevel; expectedReturn: number; volatility: number; maxDrawdown: number }> = {
  conservative: { riskLevel: 'low' as RiskLevel, expectedReturn: 0.05, volatility: 0.08, maxDrawdown: 12 },
  balanced: { riskLevel: 'medium' as RiskLevel, expectedReturn: 0.075, volatility: 0.15, maxDrawdown: 20 },
  aggressive: { riskLevel: 'high' as RiskLevel, expectedReturn: 0.10, volatility: 0.25, maxDrawdown: 35 }
};

export function ManualStrategyEditor({ currentValue = 0, onStrategyUpdate }: ManualStrategyEditorProps) {
  const { current: strategy, setMode, setTemplate, setField, loadStrategy, saveStrategy } = useStrategyStore();
  const [hasChanges, setHasChanges] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Use custom hooks
  const derivedFields = useStrategyCalculations(strategy, currentValue);
  const { validationErrors } = useStrategyValidation(strategy);

  // Load strategy from API on mount
  useEffect(() => {
    loadStrategy().catch(error => {
      console.error('Failed to load strategy on mount:', error);
    });
  }, []);

  // Notify parent component of changes
  useEffect(() => {
    if (onStrategyUpdate) {
      onStrategyUpdate();
    }
  }, [strategy]);

  const handleFieldChange = <K extends keyof typeof strategy>(field: K, value: any) => {
    setField(field, value);
    setHasChanges(true);
  };

  const handleAssetAllocationChange = (allocation: typeof strategy.assetAllocation) => {
    handleFieldChange('assetAllocation', allocation);
  };

  const handleConstraintsChange = (constraints: typeof strategy.constraints) => {
    handleFieldChange('constraints', constraints);
  };

  const handleTemplateSelection = (templateKey: StrategyKey) => {
    setTemplate(templateKey);
    setHasChanges(true);
  };

  const handleSave = async () => {
    setIsLoading(true);
    setSaveError(null);

    try {
      await saveStrategy();
      setHasChanges(false);
      console.log('Strategy saved successfully');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to save strategy';
      setSaveError(message);
      console.error('Save failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    const defaults = TEMPLATE_DEFAULTS[strategy.key];
    if (defaults) {
      handleFieldChange('riskLevel', defaults.riskLevel);
      handleFieldChange('expectedReturnAnnual', defaults.expectedReturn);
      handleFieldChange('volatilityAnnual', defaults.volatility);
      handleFieldChange('maxDrawdown', defaults.maxDrawdown);
    }
  };

  return (
    <Card>
      <StrategyHeader
        isExpanded={expanded}
        hasChanges={hasChanges}
        isLoading={isLoading}
        onToggleExpand={() => setExpanded(!expanded)}
        onSave={handleSave}
        onReset={handleReset}
      />

      <StrategySummaryPanel
        currentValue={currentValue}
        strategy={strategy}
        isExpanded={expanded}
        progressToGoal={derivedFields.progressToGoal}
      />

      {/* Expanded Editor */}
      {expanded && (
        <div className="space-y-6 mt-6">
          {/* Save Error */}
          {saveError && (
            <Alert type="error" message={saveError} dismissible onDismiss={() => setSaveError(null)} />
          )}

          {/* Validation Errors */}
          {validationErrors.length > 0 && (
            <Alert
              type="warning"
              title="Validation Issues"
              message={validationErrors.join('; ')}
            />
          )}

          {/* Mode & Template Selector */}
          <StrategyTemplateSelector
            mode={strategy.mode || 'manual'}
            selectedKey={strategy.key}
            onModeChange={(mode) => setMode(mode)}
            onTemplateSelect={handleTemplateSelection}
          />

          {/* Basic Fields */}
          <StrategyBasicFields
            targetGoalValue={strategy.targetGoalValue || 0}
            targetDate={strategy.targetDate || ''}
            monthlyContribution={strategy.monthlyContribution || 0}
            currentValue={currentValue}
            onChange={handleFieldChange}
          />

          {/* Asset Allocation */}
          <div>
            <AssetAllocationManager
              allocation={strategy.assetAllocation}
              onChange={handleAssetAllocationChange}
              maxClasses={10}
            />
          </div>

          {/* Rebalancing */}
          <StrategyRebalancingConfig
            frequency={strategy.rebalancingFrequency || 'quarterly'}
            onChange={(freq) => handleFieldChange('rebalancingFrequency', freq)}
          />

          {/* Constraints */}
          <div>
            <StrategyConstraints
              constraints={strategy.constraints}
              onChange={handleConstraintsChange}
            />
          </div>

          {/* Derived Fields Display */}
          {derivedFields.targetCAGR !== undefined && derivedFields.targetCAGR > 0 && (
            <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm text-slate-400">Required CAGR (Calculated)</span>
                <span
                  className={`text-2xl font-bold ${
                    derivedFields.targetCAGR > 0.3
                      ? 'text-red-400'
                      : derivedFields.targetCAGR > 0.15
                      ? 'text-yellow-400'
                      : 'text-green-400'
                  }`}
                >
                  {(derivedFields.targetCAGR * 100).toFixed(1)}%
                </span>
              </div>

              {/* Realism Indicator */}
              {derivedFields.targetCAGR > 0.3 && (
                <div className="text-xs text-red-400 mt-2">
                  ⚠️ This return rate is very ambitious. Consider adjusting your target or timeline.
                </div>
              )}
              {derivedFields.targetCAGR > 0.15 && derivedFields.targetCAGR <= 0.3 && (
                <div className="text-xs text-yellow-400 mt-2">
                  ⚡ This return rate is aggressive. Market average is ~10% annually.
                </div>
              )}
              {derivedFields.targetCAGR <= 0.15 && (
                <div className="text-xs text-green-400 mt-2">
                  ✓ This return rate is achievable with proper diversification.
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
