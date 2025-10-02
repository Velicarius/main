import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { StrategyKey, StrategyParams, StrategyState } from '../types/strategy';

// Default strategy parameters
const STRATEGY_DEFAULTS: Record<StrategyKey, Omit<StrategyParams, 'key' | 'monthlyContribution'>> = {
  conservative: {
    expectedReturnAnnual: 0.05,
    volatilityAnnual: 0.08
  },
  balanced: {
    expectedReturnAnnual: 0.075,
    volatilityAnnual: 0.15
  },
  aggressive: {
    expectedReturnAnnual: 0.10,
    volatilityAnnual: 0.25
  }
};

const DEFAULT_STRATEGY: StrategyParams = {
  key: 'balanced',
  expectedReturnAnnual: 0.075,
  volatilityAnnual: 0.15,
  monthlyContribution: 0
};

export const useStrategyStore = create<StrategyState>()(
  persist(
    (set, get) => ({
      current: DEFAULT_STRATEGY,

      setKey: (key: StrategyKey) => {
        const current = get().current;
        const defaults = STRATEGY_DEFAULTS[key];
        
        set({
          current: {
            key,
            expectedReturnAnnual: defaults.expectedReturnAnnual,
            volatilityAnnual: defaults.volatilityAnnual,
            monthlyContribution: current.monthlyContribution // Keep existing contribution
          }
        });
      },

      setMonthlyContribution: (amt: number) => {
        const current = get().current;
        
        set({
          current: {
            ...current,
            monthlyContribution: Math.max(0, amt) // Ensure non-negative
          }
        });
      }
    }),
    {
      name: 'ai-portfolio:strategy',
      partialize: (state) => ({ current: state.current })
    }
  )
);
