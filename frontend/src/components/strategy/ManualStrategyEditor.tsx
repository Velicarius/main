import { useState, useEffect } from 'react';
import { useStrategyStore } from '../../store/strategy';
import { RiskLevel, RebalancingFrequency, StrategyKey } from '../../types/strategy';
import { AssetAllocationManager } from './AssetAllocationManager';
import { StrategyConstraints } from './StrategyConstraints';
import { calculateStrategyDerivedFields, validateStrategy } from '../../utils/strategy-calculations';
import { fmtCurrency } from '../../lib/format';

interface ManualStrategyEditorProps {
  currentValue?: number;
  onStrategyUpdate?: () => void; // Callback for Sacred Timeline updates
}

const STRATEGY_TEMPLATES = [
  { key: 'conservative' as StrategyKey, label: 'Conservative', riskIcon: '🛡️' },
  { key: 'balanced' as StrategyKey, label: 'Balanced', riskIcon: '⚖️' },
  { key: 'aggressive' as StrategyKey, label: 'Aggressive', riskIcon: '🚀' }
];

const REBALANCING_OPTIONS: { value: RebalancingFrequency; label: string }[] = [
  { value: 'none', label: 'No Rebalancing' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'semiannual', label: 'Semiannual' },
  { value: 'yearly', label: 'Yearly' }
];

export function ManualStrategyEditor({ currentValue = 0, onStrategyUpdate }: ManualStrategyEditorProps) {
  const { current: strategy, setMode, setTemplate, setField, loadStrategy, saveStrategy } = useStrategyStore();
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [hasChanges, setHasChanges] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Helper function to format numbers with commas
  const formatNumber = (num: number) => {
    if (!num) return '';
    return num.toLocaleString('en-US');
  };

  // Calculate derived fields whenever strategy or current value changes
  const derivedFields = calculateStrategyDerivedFields(strategy, currentValue);

  // Validate strategy whenever it changes
  useEffect(() => {
    const errors = validateStrategy(strategy);
    setValidationErrors(errors);
  }, [strategy]);

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
  }, [strategy]); // Убираем onStrategyUpdate из зависимостей чтобы избежать бесконечного цикла

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
    // Reset to template values
    const templateDefaults: Record<string, { riskLevel: RiskLevel; expectedReturn: number; volatility: number; maxDrawdown: number }> = {
      conservative: { riskLevel: 'low' as RiskLevel, expectedReturn: 0.05, volatility: 0.08, maxDrawdown: 12 },
      balanced: { riskLevel: 'medium' as RiskLevel, expectedReturn: 0.075, volatility: 0.15, maxDrawdown: 20 },
      aggressive: { riskLevel: 'high' as RiskLevel, expectedReturn: 0.10, volatility: 0.25, maxDrawdown: 35 }
    };
    
    const defaults = templateDefaults[strategy.key];
    if (defaults) {
      handleFieldChange('riskLevel', defaults.riskLevel);
      handleFieldChange('expectedReturnAnnual', defaults.expectedReturn);
      handleFieldChange('volatilityAnnual', defaults.volatility);
      handleFieldChange('maxDrawdown', defaults.maxDrawdown);
    }
  };

  // Calculate time to goal
  const timeToGoal = strategy.targetDate ? 
    Math.ceil((new Date(strategy.targetDate).getTime() - new Date().getTime()) / (30 * 24 * 60 * 60 * 1000)) : 0;
  
  // Calculate amount needed to grow
  const amountToGrow = strategy.targetGoalValue ? strategy.targetGoalValue - currentValue : 0;
  const growthPercentage = currentValue > 0 ? (amountToGrow / currentValue) * 100 : 0;

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">Investment Strategy</h3>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-slate-400 hover:text-white transition-colors"
        >
          {expanded ? '−' : '+'}
        </button>
      </div>

      {/* Summary Card */}
      <div className="bg-gradient-to-br from-blue-600/20 to-purple-600/20 border border-blue-500/30 rounded-xl p-6 mb-6">
        <div className="grid grid-cols-3 gap-6 text-center">
          <div>
            <div className="text-sm text-slate-400 mb-1">Current Value</div>
            <div className="text-2xl font-bold text-white">{fmtCurrency(currentValue, 'USD')}</div>
          </div>
          <div>
            <div className="text-sm text-slate-400 mb-1">Target Value</div>
            <div className="text-2xl font-bold text-blue-400">
              {strategy.targetGoalValue ? fmtCurrency(strategy.targetGoalValue, 'USD') : 'Not Set'}
            </div>
          </div>
          <div>
            <div className="text-sm text-slate-400 mb-1">Time to Goal</div>
            <div className="text-2xl font-bold text-purple-400">
              {timeToGoal > 0 ? `${timeToGoal} months` : 'Not Set'}
            </div>
          </div>
        </div>
        
        {/* Growth Summary */}
        {strategy.targetGoalValue && amountToGrow > 0 && (
          <div className="mt-4 text-center">
            <div className="text-sm text-slate-400">
              Need to grow: <span className="text-green-400 font-semibold">{fmtCurrency(amountToGrow, 'USD')}</span> 
              <span className="text-yellow-400"> ({growthPercentage.toFixed(1)}%)</span>
              {strategy.targetDate && (
                <span> by {new Date(strategy.targetDate).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}</span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Compact Summary */}
      {!expanded && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center p-3 bg-slate-700/30 rounded-lg">
              <div className="text-lg font-bold text-blue-400">
                {strategy.targetGoalValue ? fmtCurrency(strategy.targetGoalValue, 'USD') : 'N/A'}
              </div>
              <div className="text-xs text-slate-400">Target Goal</div>
            </div>
            <div className="text-center p-3 bg-slate-700/30 rounded-lg">
              <div className="text-lg font-bold text-green-400 capitalize">
                {strategy.riskLevel || 'Manual'}
              </div>
              <div className="text-xs text-slate-400">Risk Level</div>
            </div>
          </div>
          
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Expected Return:</span>
            <span className="text-green-400">
              {(strategy.expectedReturnAnnual * 100).toFixed(1)}% annually
            </span>
          </div>
          
          {strategy.monthlyContribution > 0 && (
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Monthly Contribution:</span>
              <span className="text-blue-400">{fmtCurrency(strategy.monthlyContribution, 'USD')}</span>
            </div>
          )}

          {/* Progress Indicator */}
          {derivedFields.progressToGoal !== undefined && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Goal Progress</span>
                <span className="text-blue-400">{derivedFields.progressToGoal.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-slate-600/50 rounded-full h-1">
                <div 
                  className="h-1 rounded-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-500"
                  style={{ width: `${Math.min(derivedFields.progressToGoal, 100)}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Expanded Editor */}
      {expanded && (
        <div className="space-y-6">
          {/* Mode Selector */}
          <div className="bg-slate-700/30 rounded-lg p-4">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-sm font-medium text-slate-300">Strategy Mode</h4>
              <div className="flex space-x-2">
                <button
                  onClick={() => setMode('manual')}
                  className={`px-3 py-1 text-sm font-medium rounded ${
                    strategy.mode === 'manual' 
                      ? 'bg-blue-500 text-white' 
                      : 'bg-slate-600 text-slate-300 hover:bg-slate-500'
                  }`}
                >
                  Manual
                </button>
                <button
                  onClick={() => setMode('template')}
                  className={`px-3 py-1 text-sm font-medium rounded ${
                    strategy.mode === 'template' 
                      ? 'bg-blue-500 text-white' 
                      : 'bg-slate-600 text-slate-300 hover:bg-slate-500'
                  }`}
                >
                  Template
                </button>
              </div>
            </div>
            
            {strategy.mode === 'template' && (
              <div className="space-y-2">
                <div className="grid grid-cols-3 gap-2">
                  {STRATEGY_TEMPLATES.map(template => (
                    <button
                      key={template.key}
                      onClick={() => handleTemplateSelection(template.key)}
                      className={`flex items-center justify-center space-x-2 p-2 rounded text-sm font-medium transition-colors ${
                        strategy.key === template.key
                          ? 'bg-green-500/20 text-green-400 border border-green-500/50'
                          : 'bg-slate-600/50 text-slate-300 hover:bg-slate-500/50'
                      }`}
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

          {/* Target Goal Section - Priority 1 */}
          <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-lg p-6 mb-6">
            <h3 className="text-lg font-semibold mb-4 text-white">🎯 Target Goal</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Target Value
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">$</span>
                  <input
                    type="text"
                    inputMode="numeric"
                    value={strategy.targetGoalValue ? formatNumber(strategy.targetGoalValue) : ''}
                    onChange={(e) => {
                      const value = e.target.value.replace(/[^0-9]/g, '');
                      handleFieldChange('targetGoalValue', Number(value));
                    }}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 pl-8 py-2.5 text-white focus:border-blue-500 focus:outline-none text-right"
                    placeholder="80,000"
                  />
                </div>
                {strategy.targetGoalValue && strategy.targetGoalValue < currentValue && (
                  <p className="text-xs text-yellow-400 mt-1">
                    Target is less than current value
                  </p>
                )}
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Target Date
                </label>
                <input
                  type="text"
                  value={strategy.targetDate || ''}
                  onChange={(e) => handleFieldChange('targetDate', e.target.value)}
                  placeholder="YYYY-MM-DD"
                  pattern="\d{4}-\d{2}-\d{2}"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-white focus:border-blue-500 focus:outline-none"
                />
                {strategy.targetDate && new Date(strategy.targetDate) < new Date() && (
                  <p className="text-xs text-red-400 mt-1">
                    Target date must be in the future
                  </p>
                )}
              </div>
            </div>
            
            {/* Progress indicator */}
            {strategy.targetGoalValue && amountToGrow > 0 && (
              <div className="mt-4 text-sm text-slate-400">
                Need to grow: <span className="text-green-400 font-semibold">{fmtCurrency(amountToGrow, 'USD')}</span> 
                <span className="text-yellow-400"> ({growthPercentage.toFixed(1)}%)</span>
                {strategy.targetDate && (
                  <span> by {new Date(strategy.targetDate).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}</span>
                )}
              </div>
            )}
          </div>

          {/* Monthly Contribution Section - Priority 2 */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 mb-6">
            <h3 className="text-base font-semibold mb-3 text-white">💰 Contributions</h3>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Monthly Contribution
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">$</span>
                <input
                  type="text"
                  inputMode="numeric"
                  value={strategy.monthlyContribution ? formatNumber(strategy.monthlyContribution) : ''}
                  onChange={(e) => {
                    const value = e.target.value.replace(/[^0-9]/g, '');
                    handleFieldChange('monthlyContribution', Number(value));
                  }}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 pl-8 py-2.5 text-white focus:border-blue-500 focus:outline-none text-right"
                  placeholder="1,000"
                />
              </div>
              {strategy.monthlyContribution > 0 && timeToGoal > 0 && (
                <div className="text-sm text-slate-400 mt-2">
                  ${strategy.monthlyContribution}/month × {timeToGoal} months = ${fmtCurrency(strategy.monthlyContribution * timeToGoal, 'USD')} total contribution
                </div>
              )}
            </div>
          </div>

          {/* Risk & Return Section - Advanced Parameters */}
          <details className="bg-slate-800/30 border border-slate-700 rounded-lg mb-4">
            <summary className="cursor-pointer p-4 font-semibold text-white hover:bg-slate-700/30 transition-colors">
              📊 Risk & Return Parameters (Advanced)
            </summary>
            <div className="p-4 pt-0">
              <div className="space-y-4">
              {/* Risk Level */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Risk Level
                </label>
                <select
                  value={strategy.riskLevel || 'medium'}
                  onChange={(e) => handleFieldChange('riskLevel', e.target.value as RiskLevel)}
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
                >
                  <option value="low">Low Risk</option>
                  <option value="medium">Medium Risk</option>
                  <option value="high">High Risk</option>
                </select>
                <p className="text-xs text-slate-500 mt-1">
                  Risk level selection doesn't automatically update other parameters
                </p>
              </div>

              {/* Expected Return */}
              <div className="mb-6">
                <label className="text-sm font-medium mb-2 flex justify-between">
                  <span>Expected Return (Annual)</span>
                  <span className="text-blue-400">{(strategy.expectedReturnAnnual * 100).toFixed(1)}%</span>
                </label>
                <div className="flex items-center space-x-3">
                  <input
                    type="range"
                    min="0"
                    max="30"
                    step="0.1"
                    value={strategy.expectedReturnAnnual * 100}
                    onChange={(e) => handleFieldChange('expectedReturnAnnual', parseFloat(e.target.value) / 100)}
                    className="flex-1 h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer"
                    style={{
                      background: `linear-gradient(to right, #60a5fa 0%, #60a5fa ${strategy.expectedReturnAnnual * 100 * 100 / 30}%, #4b5563 ${strategy.expectedReturnAnnual * 100 * 100 / 30}%, #4b5563 100%)`
                    }}
                  />
                  <input
                    type="text"
                    inputMode="numeric"
                    value={(strategy.expectedReturnAnnual * 100).toFixed(1)}
                    onChange={(e) => {
                      const value = e.target.value.replace(/[^0-9.]/g, '');
                      handleFieldChange('expectedReturnAnnual', parseFloat(value) / 100);
                    }}
                    className="w-20 px-2 py-1 bg-slate-800 border border-slate-700 rounded text-white text-sm text-center focus:border-blue-500 focus:outline-none"
                  />
                  <span className="text-sm text-slate-400">%</span>
                </div>
                <div className="flex justify-between text-xs text-slate-500 mt-1">
                  <span>Conservative (5%)</span>
                  <span>Moderate (10%)</span>
                  <span>Aggressive (20%)</span>
                </div>
              </div>

              {/* Volatility */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Volatility (Annual)
                </label>
                <div className="flex items-center space-x-3">
                  <input
                    type="range"
                    min="0"
                    max="60"
                    step="0.1"
                    value={strategy.volatilityAnnual * 100}
                    onChange={(e) => handleFieldChange('volatilityAnnual', parseFloat(e.target.value) / 100)}
                    className="flex-1 h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer"
                    style={{
                      background: `linear-gradient(to right, #fbbf24 0%, #fbbf24 ${strategy.volatilityAnnual * 100 * 100 / 60}%, #4b5563 ${strategy.volatilityAnnual * 100 * 100 / 60}%, #4b5563 100%)`
                    }}
                  />
                  <input
                    type="text"
                    inputMode="numeric"
                    value={(strategy.volatilityAnnual * 100).toFixed(1)}
                    onChange={(e) => {
                      const value = e.target.value.replace(/[^0-9.]/g, '');
                      handleFieldChange('volatilityAnnual', parseFloat(value) / 100);
                    }}
                    className="w-20 px-2 py-1 bg-slate-800 border border-slate-700 rounded text-white text-sm text-right focus:border-blue-500 focus:outline-none"
                  />
                  <span className="text-sm text-slate-400">%</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Annual standard deviation of portfolio returns
                </p>
              </div>

              {/* Max Drawdown */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Max Drawdown
                </label>
                <div className="flex items-center space-x-3">
                  <input
                    type="range"
                    min="0"
                    max="80"
                    step="1"
                    value={strategy.maxDrawdown || 20}
                    onChange={(e) => handleFieldChange('maxDrawdown', parseInt(e.target.value))}
                    className="flex-1 h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer"
                    style={{
                      background: `linear-gradient(to right, #ef4444 0%, #ef4444 ${(strategy.maxDrawdown || 20) * 100 / 80}%, #4b5563 ${(strategy.maxDrawdown || 20) * 100 / 80}%, #4b5563 100%)`
                    }}
                  />
                  <input
                    type="text"
                    inputMode="numeric"
                    value={strategy.maxDrawdown || 20}
                    onChange={(e) => {
                      const value = e.target.value.replace(/[^0-9]/g, '');
                      handleFieldChange('maxDrawdown', parseInt(value));
                    }}
                    className="w-20 px-2 py-1 bg-slate-800 border border-slate-700 rounded text-white text-sm text-right focus:border-blue-500 focus:outline-none"
                  />
                  <span className="text-sm text-slate-400">%</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Expected maximum decline from peak to trough
                </p>
              </div>

              {/* Target CAGR (Read-only) with Realism Indicator */}
              {derivedFields.targetCAGR !== undefined && (
                <div className="bg-slate-800/50 rounded-lg p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm text-slate-400">Required CAGR (Calculated)</span>
                    <span className={`text-2xl font-bold ${
                      derivedFields.targetCAGR > 0.30 ? 'text-red-400' : 
                      derivedFields.targetCAGR > 0.15 ? 'text-yellow-400' : 'text-green-400'
                    }`}>
                      {(derivedFields.targetCAGR * 100).toFixed(1)}%
                    </span>
                  </div>
                  
                  {/* Realism Indicator */}
                  {derivedFields.targetCAGR > 0.30 && (
                    <div className="text-xs text-red-400 mt-2">
                      ⚠️ This return rate is very ambitious. Consider adjusting your target or timeline.
                    </div>
                  )}
                  {derivedFields.targetCAGR > 0.15 && derivedFields.targetCAGR <= 0.30 && (
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
            </div>
          </details>

          {/* Asset Allocation */}
          <div>
            <AssetAllocationManager
              allocation={strategy.assetAllocation}
              onChange={handleAssetAllocationChange}
              maxClasses={10}
            />
          </div>

          {/* Rebalancing */}
          <div>
            <h4 className="text-sm font-medium text-slate-300 mb-3">🔄 Rebalancing</h4>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Frequency
                </label>
                <select
                  value={strategy.rebalancingFrequency || 'quarterly'}
                  onChange={(e) => handleFieldChange('rebalancingFrequency', e.target.value as RebalancingFrequency)}
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
                >
                  {REBALANCING_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-slate-500 mt-1">
                  Portfolio rebalancing frequency to maintain target allocation
                </p>
              </div>
            </div>
          </div>

          {/* Constraints */}
          <div>
            <StrategyConstraints
              constraints={strategy.constraints}
              onChange={handleConstraintsChange}
            />
          </div>

          {/* Performance Indicators */}
          <div>
            <h4 className="text-sm font-medium text-slate-300 mb-3">📊 Performance Indicators</h4>
            <div className="bg-slate-700/30 rounded-lg p-4 space-y-3">
              {/* Progress to Goal */}
              {derivedFields.progressToGoal !== undefined && (
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-400">Goal Progress</span>
                  <div className="text-white font-medium">
                    {derivedFields.progressToGoal.toFixed(1)}%
                    <span className="text-xs text-slate-500 ml-2">
                      ({fmtCurrency(currentValue, 'USD')}/{fmtCurrency(strategy.targetGoalValue || 0, 'USD')})
                    </span>
                  </div>
                </div>
              )}

              {/* Actual vs Target */}
              {derivedFields.actualVsTarget && (
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-400">Actual vs Target</span>
                  <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                    derivedFields.actualVsTarget === 'ahead' ? 'bg-green-500/20 text-green-400' :
                    derivedFields.actualVsTarget === 'on_track' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-red-500/20 text-red-400'
                  }`}>
                    {derivedFields.actualVsTarget === 'ahead' ? '📈 Ahead' :
                     derivedFields.actualVsTarget === 'on_track' ? '🎯 On Track' : '📉 Behind'}
                  </div>
                </div>
              )}

              {/* Target CAGR */}
              {derivedFields.targetCAGR !== undefined && (
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-400">Target CAGR</span>
                  <div className="text-white font-medium">
                    {(derivedFields.targetCAGR * 100).toFixed(1)}%
                    <span className="text-xs text-slate-500 ml-2">required</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* API Save Error */}
          {saveError && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
              <h5 className="text-sm font-medium text-red-400 mb-2">Save Failed</h5>
              <p className="text-xs text-red-300">{saveError}</p>
            </div>
          )}

          {/* Validation Errors */}
          {validationErrors.length > 0 && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
              <h5 className="text-sm font-medium text-red-400 mb-2">Validation Issues</h5>
              <ul className="space-y-1">
                {validationErrors.map((error, index) => (
                  <li key={index} className="text-xs text-red-300">• {error}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-between pt-4 border-t border-slate-600/50">
            <div className="flex space-x-3">
              <button
                onClick={handleReset}
                className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
              >
                Reset to Template
              </button>
              <button
                onClick={() => setHasChanges(false)}
                className="text-sm text-slate-400 hover:text-slate-300 transition-colors"
              >
                Revert Changes
              </button>
            </div>
            
            <div className="flex space-x-3">
              {hasChanges && (
                <span className="text-xs text-slate-500 flex items-center">
                  ● Unsaved changes
                </span>
              )}
              <button
                onClick={handleSave}
                disabled={validationErrors.length > 0 || isLoading}
                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-slate-600 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
              >
                {isLoading ? 'Saving...' : 'Save Strategy'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
