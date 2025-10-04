// @ts-nocheck
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { StrategyKey, StrategyParams, StrategyState, StrategyMode } from '../types/strategy';
import { StrategyAPI, apiResponseToStrategyParams, strategyParamsToApiRequest } from '../lib/api-strategy';

// Default strategy templates
const STRATEGY_DEFAULTS: Record<StrategyKey, Omit<StrategyParams, 'key' | 'monthlyContribution' | 'mode' | 'progressToGoal' | 'targetCAGR' | 'actualVsTarget'>> = {
  conservative: {
    expectedReturnAnnual: 0.05,
    volatilityAnnual: 0.08,
    targetGoalValue: 100000,
    targetDate: '2027-12-31',
    assetAllocation: { equities: 40, bonds: 50, cash: 10 },
    maxDrawdown: 12,
    riskLevel: 'low',
    rebalancingFrequency: 'quarterly',
    constraints: {
      maxPositionPercent: 10,
      esgMinPercent: 15,
      notes: 'Conservative approach: focus on capital preservation'
    }
  },
  balanced: {
    expectedReturnAnnual: 0.075,
    volatilityAnnual: 0.15,
    targetGoalValue: 150000,
    targetDate: '2027-12-31',
    assetAllocation: { equities: 60, bonds: 30, cash: 10 },
    maxDrawdown: 20,
    riskLevel: 'medium',
    rebalancingFrequency: 'quarterly',
    constraints: {
      maxPositionPercent: 15,
      esgMinPercent: 10,
      notes: 'Balanced approach: growth with moderate risk'
    }
  },
  aggressive: {
    expectedReturnAnnual: 0.10,
    volatilityAnnual: 0.25,
    targetGoalValue: 200000,
    targetDate: '2027-12-31',
    assetAllocation: { equities: 80, bonds: 15, cash: 5 },
    maxDrawdown: 35,
    riskLevel: 'high',
    rebalancingFrequency: 'quarterly',
    constraints: {
      maxPositionPercent: 20,
      esgMinPercent: 5,
      notes: 'Aggressive approach: maximum growth potential'
    }
  }
};

const DEFAULT_STRATEGY: StrategyParams = {
  key: 'balanced',
  mode: 'manual',
  expectedReturnAnnual: 0.075,
  volatilityAnnual: 0.15,
  monthlyContribution: 0,
  targetGoalValue: 150000,
  targetDate: '2027-12-31',
  assetAllocation: { equities: 60, bonds: 30, cash: 10 },
  maxDrawdown: 20,
  riskLevel: 'medium',
  rebalancingFrequency: 'quarterly',
  constraints: {
    maxPositionPercent: 15,
    esgMinPercent: 10,
    notes: 'Balanced approach: growth with moderate risk'
  }
};

export const useStrategyStore = create<StrategyState>()(
  persist(
    (set: any, get: any) => ({
      current: DEFAULT_STRATEGY,

      // New: Set strategy mode (manual/template)
      setMode: (mode: StrategyMode) => {
        set({
          current: {
            ...get().current,
            mode
          }
        });
      },

      // New: Apply template values (one-time fill)
      setTemplate: (key: StrategyKey) => {
        const current = get().current;
        const defaults = STRATEGY_DEFAULTS[key];
        
        set({
          current: {
            ...current,
            expectedReturnAnnual: defaults.expectedReturnAnnual,
            volatilityAnnual: defaults.volatilityAnnual,
            targetGoalValue: defaults.targetGoalValue,
            targetDate: defaults.targetDate,
            assetAllocation: defaults.assetAllocation,
            maxDrawdown: defaults.maxDrawdown,
            riskLevel: defaults.riskLevel,
            rebalancingFrequency: defaults.rebalancingFrequency,
            constraints: defaults.constraints,
            // Keep existing contributions and mode
            monthlyContribution: current.monthlyContribution,
            mode: current.mode
          }
        });
      },

      // New: Generic field setter
      setField: <K extends keyof StrategyParams>(field: K, value: StrategyParams[K]) => {
        set({
          current: {
            ...get().current,
            [field]: value
          }
        });
      },

      // New: Load strategy from API
      loadStrategy: async () => {
        try {
          const response = await StrategyAPI.getStrategy();
          
          // Check if response is empty
          if ('message' in response) {
            // No strategy found - keep current defaults
            return;
          }
          
          // Convert API response to frontend format
          const strategyParams = apiResponseToStrategyParams(response);
          
          set({
            current: {
              ...strategyParams,
              mode: strategyParams.mode || 'manual'
            }
          });
        } catch (error) {
          console.error('Failed to load strategy from API:', error);
          // Keep current state on error
        }
      },

      // New: Save strategy to API
      saveStrategy: async () => {
        try {
          const current = get().current;
          const apiRequest = strategyParamsToApiRequest(current);
          
          const response = await StrategyAPI.upsertStrategy(apiRequest);
          
          // Update with computed fields from API response
          const updatedParams = apiResponseToStrategyParams(response);
          
          set({
            current: {
              ...current,
              progressToGoal: updatedParams.progressToGoal,
              targetCAGR: updatedParams.targetCAGR,
              actualVsTarget: updatedParams.actualVsTarget
            }
          });
          
          return true; // Success
        } catch (error) {
          console.error('Failed to save strategy:', error);
          throw error; // Re-throw for component handling
        }
      },

      // New: Patch strategy fields to API
      patchStrategy: async (fields: Partial<StrategyParams>) => {
        try {
          const apiRequest: any = {};
          
          // Convert frontend fields to API format
          if ('targetGoalValue' in fields) apiRequest.target_value = fields.targetGoalValue;
          if ('targetDate' in fields) apiRequest.target_date = fields.targetDate;
          if ('riskLevel' in fields) apiRequest.risk_level = fields.riskLevel;
          if ('expectedReturnAnnual' in fields) apiRequest.expected_return = fields.expectedReturnAnnual;
          if ('volatilityAnnual' in fields) apiRequest.volatility = fields.volatilityAnnual;
          if ('maxDrawdown' in fields) apiRequest.max_drawdown = fields.maxDrawdown ? fields.maxDrawdown / 100 : undefined;
          if ('monthlyContribution' in fields) apiRequest.monthly_contribution = fields.monthlyContribution;
          if ('rebalancingFrequency' in fields) apiRequest.rebalancing_frequency = fields.rebalancingFrequency;
          if ('assetAllocation' in fields) apiRequest.allocation = fields.assetAllocation;
          if ('constraints' in fields) apiRequest.constraints = fields.constraints;
          
          const response = await StrategyAPI.patchStrategy(apiRequest);
          
          if ('message' in response) {
            // No strategy found to update
            return false;
          }
          
          // Update current state with response
          const updatedParams = apiResponseToStrategyParams(response);
          
          set({
            current: {
              ...get().current,
              ...fields, // Apply the changes first
              ...updatedParams // Then overlay computed fields
            }
          });
          
          return true; // Success
        } catch (error) {
          console.error('Failed to patch strategy:', error);
          throw error;
        }
      },

      // Legacy: Set strategy key (updates all fields)
      setKey: (key: StrategyKey) => {
        const current = get().current;
        const defaults = STRATEGY_DEFAULTS[key];
        
        set({
          current: {
            ...current,
            expectedReturnAnnual: defaults.expectedReturnAnnual,
            volatilityAnnual: defaults.volatilityAnnual,
            targetGoalValue: defaults.targetGoalValue,
            targetDate: defaults.targetDate,
            assetAllocation: defaults.assetAllocation,
            maxDrawdown: defaults.maxDrawdown,
            riskLevel: defaults.riskLevel,
            rebalancingFrequency: defaults.rebalancingFrequency,
            constraints: defaults.constraints,
            // Keep existing contribution and mode  
            monthlyContribution: current.monthlyContribution,
            mode: current.mode || 'manual'
          }
        });
      },

      // Legacy: Set monthly contribution
      setMonthlyContribution: (amt: number) => {
        set({
          current: {
            ...get().current,
            monthlyContribution: Math.max(0, amt) // Ensure non-negative
          }
        });
      }
    }),
    {
      name: 'ai-portfolio:strategy',
      partialize: (state: any) => ({ current: state.current })
    }
  )
);