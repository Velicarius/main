import { useMemo } from 'react';
import { StrategyParams } from '../types/strategy';
import { calculateStrategyDerivedFields } from '../utils/strategy-calculations';

export const useStrategyCalculations = (strategy: StrategyParams, currentValue: number) => {
  const derivedFields = useMemo(() => {
    return calculateStrategyDerivedFields(strategy, currentValue);
  }, [strategy, currentValue]);

  return derivedFields;
};
