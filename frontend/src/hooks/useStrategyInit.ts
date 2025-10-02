import { useEffect } from 'react';
import { useStrategyStore } from '../store/strategy';

// Hook to initialize strategy from onboarding data
export function useStrategyInit() {
  const { current, setMonthlyContribution } = useStrategyStore();

  useEffect(() => {
    // Only initialize if current monthly contribution is zero
    if (current.monthlyContribution === 0) {
      // Check for onboarding data in localStorage
      try {
        const onboardingData = localStorage.getItem('ai-portfolio:onboarding');
        if (onboardingData) {
          const parsed = JSON.parse(onboardingData);
          const monthlyContribution = parsed.monthlyContribution;
          
          if (monthlyContribution && monthlyContribution > 0) {
            setMonthlyContribution(monthlyContribution);
          }
        }
      } catch (error) {
        console.warn('Failed to parse onboarding data:', error);
      }
    }
  }, [current.monthlyContribution, setMonthlyContribution]);
}
