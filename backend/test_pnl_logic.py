#!/usr/bin/env python3
"""
Тест новой логики PnL для пользователя 117.tomcat@gmail.com
"""

import requests
import json

def test_positions_api():
    """Тестирует API позиций для пользователя 117.tomcat@gmail.com"""
    
    # URL API
    base_url = "http://localhost:8001"
    
    # Сначала залогинимся как пользователь 117.tomcat@gmail.com
    login_data = {
        "email": "117.tomcat@gmail.com",
        "password": "test123"  # Предполагаем, что пароль test123
    }
    
    try:
        # Попробуем залогиниться
        login_response = requests.post(f"{base_url}/users/login-json", json=login_data)
        print(f"Login status: {login_response.status_code}")
        
        if login_response.status_code == 200:
            print("Login successful!")
            user_data = login_response.json()
            print(f"User: {user_data}")
            
            # Теперь получим позиции
            session = requests.Session()
            session.cookies.update(login_response.cookies)
            
            positions_response = session.get(f"{base_url}/positions")
            print(f"Positions status: {positions_response.status_code}")
            
            if positions_response.status_code == 200:
                positions = positions_response.json()
                print(f"Found {len(positions)} positions")
                
                # Проверим позиции без buy_price
                for pos in positions:
                    if not pos.get('buy_price'):
                        print(f"\nPosition without buy_price:")
                        print(f"  Symbol: {pos['symbol']}")
                        print(f"  Quantity: {pos['quantity']}")
                        print(f"  Last price: {pos.get('last_price')}")
                        print(f"  Reference price: {pos.get('reference_price')}")
                        print(f"  Reference date: {pos.get('reference_date')}")
                        print(f"  Date added: {pos.get('date_added')}")
                        
                        # Рассчитаем PnL
                        last_price = float(pos.get('last_price', 0))
                        reference_price = float(pos.get('reference_price', 0))
                        quantity = float(pos['quantity'])
                        
                        if last_price > 0 and reference_price > 0:
                            pnl = (last_price - reference_price) * quantity
                            pnl_pct = (pnl / (reference_price * quantity)) * 100
                            print(f"  PnL: ${pnl:.2f} ({pnl_pct:.2f}%)")
                        else:
                            print(f"  PnL: Cannot calculate (missing prices)")
            else:
                print(f"Failed to get positions: {positions_response.text}")
        else:
            print(f"Login failed: {login_response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_positions_api()
