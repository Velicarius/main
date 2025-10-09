// Тестовая стратегия для пользователя 117.tomcat@gmail.com
// Выполнить в консоли браузера на http://localhost:8080

const testStrategy = {
  current: {
    key: 'balanced',
    mode: 'manual',
    expectedReturnAnnual: 0.075,
    volatilityAnnual: 0.15,
    monthlyContribution: 2000,
    targetGoalValue: 100000,
    targetDate: '2026-12-31',
    assetAllocation: { equities: 60, bonds: 30, cash: 10 },
    maxDrawdown: 20,
    riskLevel: 'medium',
    rebalancingFrequency: 'quarterly',
    constraints: {
      maxPositionPercent: 15,
      esgMinPercent: 10,
      notes: 'Test strategy for debugging target line'
    }
  }
};

// Сохраняем в localStorage
localStorage.setItem('ai-portfolio:strategy', JSON.stringify(testStrategy));

console.log('Test strategy saved to localStorage');
console.log('Strategy:', testStrategy);

// Перезагружаем страницу для применения изменений
window.location.reload();

