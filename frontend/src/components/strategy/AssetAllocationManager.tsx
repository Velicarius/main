import { useState, useEffect } from 'react';
import { AssetAllocation } from '../../types/strategy';

interface AssetAllocationManagerProps {
  allocation: AssetAllocation | undefined;
  onChange: (allocation: AssetAllocation) => void;
  maxClasses?: number;  // Limit number of asset classes
}

interface AssetClass {
  key: string;
  label: string;
  value: number;
  readonly?: boolean;  // Built-in classes can't be removed
}

const DEFAULT_ASSET_CLASSES: AssetClass[] = [
  { key: 'equities', label: 'Equities', value: 60, readonly: false },
  { key: 'bonds', label: 'Bonds', value: 30, readonly: false },
  { key: 'cash', label: 'Cash & Equivalents', value: 10, readonly: false },
  { key: 'alternatives', label: 'Alternatives', value: 0, readonly: false }
];

const ADDITIONAL_CLASSES: AssetClass[] = [
  { key: 'crypto', label: 'Cryptocurrency', value: 0, readonly: false },
  { key: 'realEstate', label: 'Real Estate', value: 0, readonly: false },
  { key: 'commodities', label: 'Commodities', value: 0, readonly: false },
  { key: 'emerging', label: 'Emerging Markets', value: 0, readonly: false }
];

export function AssetAllocationManager({ allocation, onChange, maxClasses = 10 }: AssetAllocationManagerProps) {
  const [assetClasses, setAssetClasses] = useState<AssetClass[]>([]);
  const [customClasses, setCustomClasses] = useState<AssetClass[]>([]);

  // Initialize from allocation prop
  useEffect(() => {
    const initialClasses: AssetClass[] = [];
    const initCustom: AssetClass[] = [];

    // Initialize default classes
    DEFAULT_ASSET_CLASSES.forEach(cls => {
      const value = allocation?.[cls.key as keyof AssetAllocation] || cls.value;
      initialClasses.push({ ...cls, value });
    });

    // Initialize additional classes if they have values or are explicitly set
    ADDITIONAL_CLASSES.forEach(cls => {
      const value = allocation?.[cls.key as keyof AssetAllocation];
      if (value !== undefined && value > 0) {
        initialClasses.push({ ...cls, value });
      }
    });

    // Initialize custom classes (any key not in default/additional)
    if (allocation) {
      Object.keys(allocation).forEach(key => {
        const defaultExists = DEFAULT_ASSET_CLASSES.some(c => c.key === key);
        const additionalExists = ADDITIONAL_CLASSES.some(c => c.key === key);
        
        if (!defaultExists && !additionalExists) {
          const value = allocation[key as keyof AssetAllocation] as number || 0;
          initCustom.push({ key, label: key.charAt(0).toUpperCase() + key.slice(1), value });
        }
      });
    }

    setAssetClasses([...initialClasses]);
    setCustomClasses(initCustom);
  }, [allocation]);

  // Calculate total allocation
  const currentTotal = [...assetClasses, ...customClasses].reduce((sum, cls) => sum + cls.value, 0);
  const isTotalValid = currentTotal <= 105; // Allow slight over-allocation (adjustment needed)
  const remainingAllocation = Math.max(0, 100 - currentTotal);

  // Update allocation when classes change
  useEffect(() => {
    const newAllocation: AssetAllocation = {};
    [...assetClasses, ...customClasses].forEach(cls => {
      if (cls.value > 0) {
        newAllocation[cls.key as keyof AssetAllocation] = cls.value;
      }
    });
    onChange(newAllocation);
  }, [assetClasses, customClasses]); // Убираем onChange из зависимостей чтобы избежать бесконечного цикла

  const updateValue = (index: number, value: number) => {
    const newClasses = [...assetClasses];
    newClasses[index] = { ...newClasses[index], value: Math.max(0, Math.min(100, value)) };
    setAssetClasses(newClasses);
  };

  const updateCustomValue = (index: number, value: number) => {
    const newCustom = [...customClasses];
    newCustom[index] = { ...newCustom[index], value: Math.max(0, Math.min(100, value)) };
    setCustomClasses(newCustom);
  };

  const removeCustomClass = (index: number) => {
    setCustomClasses(customClasses.filter((_, i) => i !== index));
  };

  const addCustomClass = () => {
    if (customClasses.length + assetClasses.length >= maxClasses) return;
    
    const customLabel = prompt('Enter custom asset class name:');
    if (customLabel && customLabel.trim()) {
      const key = customLabel.toLowerCase().replace(/[^a-z0-9]/g, '');
      const newClass: AssetClass = {
        key,
        label: customLabel.trim(),
        value: 0,
        readonly: false
      };
      setCustomClasses([...customClasses, newClass]);
    }
  };

  const allClasses = [...assetClasses, ...customClasses];

  return (
    <div className="space-y-4">
      {/* Header with progress */}
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <h4 className="text-sm font-medium text-slate-300">Asset Allocation</h4>
          <div className={`text-sm font-medium px-2 py-1 rounded ${
            isTotalValid ? 'text-green-400 bg-green-500/20' : 'text-red-400 bg-red-500/20'
          }`}>
            Total: {currentTotal.toFixed(1)}%
          </div>
        </div>
        
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="w-full bg-slate-600/50 rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all duration-300 ${
                isTotalValid ? 'bg-gradient-to-r from-green-500 to-green-400' : 'bg-gradient-to-r from-red-500 to-red-400'
              }`}
              style={{ width: `${Math.min(currentTotal, 100)}%` }}
            />
          </div>
          
          {remainingAllocation > 0 && (
            <div className="text-xs text-slate-400">
              {remainingAllocation.toFixed(1)}% remaining to allocate
            </div>
          )}
        </div>
      </div>

      {/* Asset Classes List */}
      <div className="space-y-3">
        {/* Default/Additional Classes */}
        {assetClasses.map((cls, index) => (
          <div key={cls.key} className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 flex-1">
              <div 
                className="w-3 h-3 rounded-full bg-gradient-to-r from-blue-500 to-purple-400"
              />
              <span className="text-sm text-slate-300 flex-1">{cls.label}</span>
            </div>
            
            <div className="flex items-center space-x-2">
              <input
                type="range"
                min="0"
                max="100"
                step="0.1"
                value={cls.value}
                onChange={(e) => updateValue(index, parseFloat(e.target.value))}
                className="w-20 h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer"
                style={{
                  background: `linear-gradient(to right, #60a5fa 0%, #60a5fa ${cls.value}%, #4b5563 ${cls.value}%, #4b5563 100%)`
                }}
              />
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={cls.value}
                onChange={(e) => updateValue(index, parseFloat(e.target.value) || 0)}
                className="w-16 px-2 py-1 bg-slate-700/50 border border-slate-600/50 rounded text-white text-sm text-right focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              />
              <span className="text-sm text-slate-400 w-8">%</span>
            </div>
          </div>
        ))}

        {/* Custom Classes */}
        {customClasses.map((cls, index) => (
          <div key={cls.key} className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 flex-1">
              <div 
                className="w-3 h-3 rounded-full bg-gradient-to-r from-purple-500 to-pink-400"
              />
              <span className="text-sm text-slate-300 flex-1">{cls.label}</span>
            </div>
            
            <div className="flex items-center space-x-2">
              <input
                type="range"
                min="0"
                max="100"
                step="0.1"
                value={cls.value}
                onChange={(e) => updateCustomValue(index, parseFloat(e.target.value))}
                className="w-20 h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer"
                style={{
                  background: `linear-gradient(to right, #a78bfa 0%, #a78bfa ${cls.value}%, #4b5563 ${cls.value}%, #4b5563 100%)`
                }}
              />
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={cls.value}
                onChange={(e) => updateCustomValue(index, parseFloat(e.target.value) || 0)}
                className="w-16 px-2 py-1 bg-slate-700/50 border border-slate-600/50 rounded text-white text-sm text-right focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              />
              <span className="text-sm text-slate-400 w-8">%</span>
              <button
                onClick={() => removeCustomClass(index)}
                className="text-red-400 hover:text-red-300 text-sm"
                title="Remove asset class"
              >
                ✕
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Add Custom Class Button */}
      {allClasses.length < maxClasses && (
        <div className="pt-2">
          <button
            onClick={addCustomClass}
            className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
          >
            + Add custom asset class
          </button>
        </div>
      )}

      {/* Validation Messages */}
      {currentTotal !== 100 && (
        <div className="text-xs text-center p-2 bg-slate-700/30 rounded">
          {currentTotal < 100 ? (
            <span className="text-yellow-400">
              ⚠️ Total allocation: {currentTotal.toFixed(1)}%. Complete allocation for accurate projections.
            </span>
          ) : (
            <span className="text-red-400">
              ❌ Total allocation exceeds 100%. Please reduce allocations.
            </span>
          )}
        </div>
      )}
    </div>
  );
}
