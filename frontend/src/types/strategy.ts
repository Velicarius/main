export type StrategyKey = 'conservative' | 'balanced' | 'aggressive';

export interface StrategyParams {
  key: StrategyKey;
  expectedReturnAnnual: number;   // e.g. 0.075
  volatilityAnnual: number;       // e.g. 0.15
  monthlyContribution: number;    // e.g. 200 (from onboarding; default 0)
}

export interface StrategyState {
  current: StrategyParams;
  setKey: (key: StrategyKey) => void;
  setMonthlyContribution: (amt: number) => void;
}
