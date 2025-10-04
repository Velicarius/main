import { StrategyParams } from '../types/strategy';

/**
 * Calculate derived strategy fields
 */
export function calculateStrategyDerivedFields(
  strategy: StrategyParams,
  currentPortfolioValue?: number
): Pick<StrategyParams, 'progressToGoal' | 'targetCAGR' | 'actualVsTarget'> {
  const currentValue = currentPortfolioValue || 0;
  const targetValue = strategy.targetGoalValue || 0;
  const targetDate = strategy.targetDate;
  const monthlyContribution = strategy.monthlyContribution || 0;
  const expectedReturn = strategy.expectedReturnAnnual || 0;

  // Progress to Goal (%)
  const progressToGoal = targetValue > 0 ? (currentValue / targetValue) * 100 : 0;

  // Target CAGR calculation
  let targetCAGR = 0;
  if (targetDate && targetValue > 0 && currentValue > 0) {
    const now = new Date();
    const target = new Date(targetDate);
    const yearsRemaining = Math.max((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24 * 365), 0.01); // Avoid division by zero
    
    // Future value with contributions
    const contributionGrowth = monthlyContribution * 12 * yearsRemaining;
    const targetWithoutContribution = targetValue - contributionGrowth;
    
    // CAGR formula: FV = PV * (1 + CAGR)^t
    if (targetWithoutContribution > 0) {
      targetCAGR = Math.pow(targetWithoutContribution / currentValue, 1 / yearsRemaining) - 1;
    }
  }

  // Actual vs Target performance indicator
  let actualVsTarget: 'ahead' | 'on_track' | 'behind' = 'on_track';
  
  if (expectedReturn > 0 && targetDate && currentValue > 0) {
    const now = new Date();
    const monthsElapsed = Math.max((now.getTime() - new Date('2024-01-01').getTime()) / (1000 * 60 * 60 * 24 * 30), 1); // Base from registration
    
    // Expected portfolio value at current date (simplified)
    const monthlyReturn = Math.pow(1 + expectedReturn, 1/12) - 1;
    const compoundGrowth = Math.pow(1 + monthlyReturn, monthsElapsed);
    const contributionGrowth = monthlyContribution * ((Math.pow(1 + monthlyReturn, monthsElapsed) - 1) / monthlyReturn);
    const expectedValue = (currentValue || 10000) * compoundGrowth + contributionGrowth;
    
    // Compare actual vs expected
    const performanceRatio = currentValue / expectedValue;
    
    if (performanceRatio >= 1.05) {
      actualVsTarget = 'ahead';
    } else if (performanceRatio >= 0.95) {
      actualVsTarget = 'on_track';
    } else {
      actualVsTarget = 'behind';
    }
  }

  return {
    progressToGoal,
    targetCAGR,
    actualVsTarget
  };
}

/**
 * Validate strategy parameters
 */
export function validateStrategy(strategy: StrategyParams): string[] {
  const errors: string[] = [];

  // Basic validations
  if (strategy.targetGoalValue !== undefined && strategy.targetGoalValue <= 0) {
    errors.push('Target goal value must be positive');
  }

  if (strategy.expectedReturnAnnual < 0 || strategy.expectedReturnAnnual > 1) {
    errors.push('Expected return must be between 0% and 100%');
  }

  if (strategy.volatilityAnnual < 0 || strategy.volatilityAnnual > 1) {
    errors.push('Volatility must be between 0% and 100%');
  }

  if (strategy.maxDrawdown !== undefined && (strategy.maxDrawdown < 0 || strategy.maxDrawdown > 100)) {
    errors.push('Max drawdown must be between 0% and 100%');
  }

  if (strategy.monthlyContribution < 0) {
    errors.push('Monthly contribution cannot be negative');
  }

  // Date validations
  if (strategy.targetDate !== undefined) {
    const targetDate = new Date(strategy.targetDate);
    const today = new Date();
    
    if (targetDate <= today) {
      errors.push('Target date must be in the future');
    }
  }

  // Asset allocation validation
  if (strategy.assetAllocation) {
    const total = Object.values(strategy.assetAllocation)
      .reduce((sum: number, value) => sum + (value || 0), 0);
    
    if (Math.abs(total - 100) > 0.1) { // Allow small rounding errors
      errors.push(`Asset allocation total is ${total.toFixed(1)}%. Must equal 100%`);
    }

    // Check that all allocations are positive
    const negativeAllocations = Object.entries(strategy.assetAllocation)
      .filter(([_, value]) => (value || 0) < 0);

    if (negativeAllocations.length > 0) {
      errors.push('Asset allocations cannot be negative');
    }
  }

  // Constraints validation
  if (strategy.constraints) {
    const { maxPositionPercent, esgMinPercent, maxDrawdownLimit } = strategy.constraints;
    
    if (maxPositionPercent !== undefined && (maxPositionPercent < 1 || maxPositionPercent > 50)) {
      errors.push('Max position percentage must be between 1% and 50%');
    }

    if (esgMinPercent !== undefined && (esgMinPercent < 0 || esgMinPercent > 50)) {
      errors.push('ESG minimum percentage must be between 0% and 50%');
    }

    if (maxDrawdownLimit !== undefined && (maxDrawdownLimit < 5 || maxDrawdownLimit > 80)) {
      errors.push('Max drawdown limit must be between 5% and 80%');
    }

    if (strategy.constraints.notes && strategy.constraints.notes.length > 300) {
      errors.push('Investment notes cannot exceed 300 characters');
    }
  }

  return errors;
}
