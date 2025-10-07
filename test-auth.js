// Тестовая аутентификация для пользователя 117.tomcat@gmail.com
// Выполнить в консоли браузера на http://localhost:8080

const testAuth = {
  email: '117.tomcat@gmail.com',
  name: 'Test User',
  user_id: '41e10fbf-bad3-4227-9a34-dfc15ba6d6e8',
  loggedIn: true
};

// Сохраняем в localStorage
localStorage.setItem('auth-storage', JSON.stringify(testAuth));

console.log('Test auth saved to localStorage');
console.log('Auth:', testAuth);

// Перезагружаем страницу для применения изменений
window.location.reload();
