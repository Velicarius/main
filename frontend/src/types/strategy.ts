export type StrategyKey = 'conservative' | 'balanced' | 'aggressive';

export type StrategyMode = 'manual' | 'template';
export type RiskLevel = 'low' | 'medium' | 'high';
export type RebalancingFrequency = 'none' | 'quarterly' | 'semiannual' | 'yearly';

export interface StrategyParams {
  key: StrategyKey;
  mode: StrategyMode;                    // New: manual/template mode
  expectedReturnAnnual: number;           // e.g. 0.075 (7.5%)
  volatilityAnnual: number;              // e.g. 0.15 (15%)
  monthlyContribution: number;           // e.g. 200 (USD, default 0)
  targetGoalValue?: number;              // Target portfolio value (USD)
  targetDate?: string;                    // Target date in YYYY-MM-DD format
  assetAllocation?: AssetAllocation;     // Rebalance allocation
  maxDrawdown?: number;                  // Expected maximum drawdown (positive value, e.g. 20)
  riskLevel?: RiskLevel;                 // New: independent risk level selection
  rebalancingFrequency?: RebalancingFrequency;  // Updated frequency options
  constraints?: StrategyConstraints;     // New: structured constraints
  
  // Derived fields (read-only, computed on frontend)
  progressToGoal?: number;              // Current progress percentage
  targetCAGR?: number;                   // Calculated CAGR needed to reach goal
  actualVsTarget?: 'ahead' | 'on_track' | 'behind';  // Performance indicator
}

export interface AssetAllocation {
  equities?: number;     // Percentage allocation to equities
  bonds?: number;        // Percentage allocation to bonds
  cash?: number;         // Percentage allocation to cash/equivalents
  alternatives?: number; // Optional alternatives allocation
  crypto?: number;       // New: crypto allocation
  realEstate?: number;   // New: real estate allocation
  
  // Custom asset classes (dynamic)
  [key: string]: number | undefined;     // Allow custom asset classes
}

export interface StrategyConstraints {
  maxPositionPercent?: number;   // Max % per single position (e.g., 10)
  esgMinPercent?: number;        // ESG minimum % (e.g., 15)
  maxDrawdownLimit?: number;     // Maximum acceptable drawdown %
  sectorsExcluded?: string[];    // Excluded sectors
  notes?: string;                // Free-form notes (200-300 chars)
}

export interface StrategyState {
  current: StrategyParams;
  
  // Actions
  setMode: (mode: StrategyMode) => void;
  setTemplate: (key: StrategyKey) => void;     // Apply template values (one-time)
  setField: <K extends keyof StrategyParams>(field: K, value: StrategyParams[K]) => void;
  
  // API integration
  loadStrategy: () => Promise<void>;           // Load from server
  saveStrategy: () => Promise<boolean>;        // Save to server
  patchStrategy: (fields: Partial<StrategyParams>) => Promise<boolean>; // Partial update
  
  // Legacy actions (kept for compatibility)
  setKey: (key: StrategyKey) => void;
  setMonthlyContribution: (amt: number) => void;
}