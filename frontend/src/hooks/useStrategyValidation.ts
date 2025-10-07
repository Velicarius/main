import { useMemo } from 'react';
import { StrategyParams } from '../types/strategy';
import { validateStrategy } from '../utils/strategy-calculations';

export const useStrategyValidation = (strategy: StrategyParams) => {
  const validationErrors = useMemo(() => {
    return validateStrategy(strategy);
  }, [strategy]);

  const isValid = validationErrors.length === 0;

  return {
    validationErrors,
    isValid
  };
};
