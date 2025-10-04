import { StrategyConstraints as ConstraintsType } from '../../types/strategy';

interface StrategyConstraintsProps {
  constraints: ConstraintsType | undefined;
  onChange: (constraints: ConstraintsType) => void;
}

export function StrategyConstraints({ constraints, onChange }: StrategyConstraintsProps) {
  const updateConstraint = (field: keyof ConstraintsType, value: any) => {
    onChange({
      ...constraints,
      [field]: value
    });
  };

  const availableSectors = [
    'Technology',
    'Healthcare', 
    'Financial Services',
    'Energy',
    'Consumer Discretionary',
    'Consumer Staples',
    'Industrials',
    'Materials',
    'Real Estate',
    'Utilities',
    'Communication Services',
    'Cryptocurrency',
    'Biotechnology',
    'Renewable Energy'
  ];

  const toggleSectorExclusion = (sector: string) => {
    const currentExcluded = constraints?.sectorsExcluded || [];
    const newExcluded = currentExcluded.includes(sector)
      ? currentExcluded.filter(s => s !== sector)
      : [...currentExcluded, sector];
    
    updateConstraint('sectorsExcluded', newExcluded);
  };

  return (
    <div className="space-y-4">
      <h4 className="text-sm font-medium text-slate-300 mb-3">Investment Constraints</h4>
      
      {/* Position Limits */}
      <div className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Max % per Single Position
          </label>
          <div className="flex items-center space-x-3">
            <input
              type="range"
              min="1"
              max="50"
              step="1"
              value={constraints?.maxPositionPercent || 15}
              onChange={(e) => updateConstraint('maxPositionPercent', parseInt(e.target.value))}
              className="w-32 h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer"
              style={{
                background: `linear-gradient(to right, #60a5fa 0%, #60a5fa ${constraints?.maxPositionPercent || 15 * 2}%, #4b5563 ${constraints?.maxPositionPercent || 15 * 2}%, #4b5563 100%)`
              }}
            />
            <input
              type="number"
              min="1"
              max="50"
              value={constraints?.maxPositionPercent || 15}
              onChange={(e) => updateConstraint('maxPositionPercent', parseInt(e.target.value) || 15)}
              className="w-16 px-2 py-1 bg-slate-700/50 border border-slate-600/50 rounded text-white text-sm text-right focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            />
            <span className="text-sm text-slate-400">%</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Maximum allocation for any individual security
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            ESG Minimum Allocation
          </label>
          <div className="flex items-center space-x-3">
            <input
              type="range"
              min="0"
              max="50"
              step="1"
              value={constraints?.esgMinPercent || 10}
              onChange={(e) => updateConstraint('esgMinPercent', parseInt(e.target.value))}
              className="w-32 h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer"
              style={{
                background: `linear-gradient(to right, #34d399 0%, #34d399 ${constraints?.esgMinPercent || 10 * 2}%, #4b5563 ${constraints?.esgMinPercent || 10 * 2}%, #4b5563 100%)`
              }}
            />
            <input
              type="number"
              min="0"
              max="50"
              value={constraints?.esgMinPercent || 10}
              onChange={(e) => updateConstraint('esgMinPercent', parseInt(e.target.value) || 0)}
              className="w-16 px-2 py-1 bg-slate-700/50 border border-slate-600/50 rounded text-white text-sm text-right focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            />
            <span className="text-sm text-slate-400">%</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Minimum allocation to ESG-compliant securities
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Max Drawdown Limit
          </label>
          <div className="flex items-center space-x-3">
            <input
              type="range"
              min="5"
              max="80"
              step="1"
              value={constraints?.maxDrawdownLimit || 20}
              onChange={(e) => updateConstraint('maxDrawdownLimit', parseInt(e.target.value))}
              className="w-32 h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer"
              style={{
                background: `linear-gradient(to right, #ef4444 0%, #ef4444 ${constraints?.maxDrawdownLimit || 20 * 100 / 75}%, #4b5563 ${constraints?.maxDrawdownLimit || 20 * 100 / 75}%, #4b5563 100%)`
              }}
            />
            <input
              type="number"
              min="5"
              max="80"
              value={constraints?.maxDrawdownLimit || 20}
              onChange={(e) => updateConstraint('maxDrawdownLimit', parseInt(e.target.value) || 20)}
              className="w-16 px-2 py-1 bg-slate-700/50 border border-slate-600/50 rounded text-white text-sm text-right focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            />
            <span className="text-sm text-slate-400">%</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Maximum acceptable portfolio drawdown
          </p>
        </div>
      </div>

      {/* Sector Exclusions */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Excluded Sectors
        </label>
        <div className="max-h-32 overflow-y-auto bg-slate-700/30 rounded-lg p-3">
          <div className="grid grid-cols-2 gap-2">
            {availableSectors.map(sector => (
              <label key={sector} className="flex items-center space-x-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={constraints?.sectorsExcluded?.includes(sector) || false}
                  onChange={() => toggleSectorExclusion(sector)}
                  className="rounded border-slate-600 text-blue-600 focus:ring-blue-500 focus:ring-2"
                />
                <span className="text-slate-300">{sector}</span>
              </label>
            ))}
          </div>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          Select sectors to exclude from the portfolio
        </p>
      </div>

      {/* Notes */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Investment Notes
        </label>
        <textarea
          value={constraints?.notes || ''}
          onChange={(e) => updateConstraint('notes', e.target.value)}
          placeholder="Additional investment rules, preferences, or constraints..."
          maxLength={300}
          rows={3}
          className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 resize-none"
        />
        <div className="flex justify-between text-xs text-slate-500 mt-1">
          <span>{constraints?.notes?.length || 0}/300 characters</span>
          <span>Optional investment notes and preferences</span>
        </div>
      </div>
    </div>
  );
}
