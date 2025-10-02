"""
Единый сервис для загрузки цен с рынка.
"""

import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from app.marketdata.stooq_client import fetch_latest_from_stooq
from app.services.price_eod import PriceEODRepository

logger = logging.getLogger(__name__)


class PriceService:
    """Сервис для загрузки и управления ценами"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = PriceEODRepository(db)
    
    def load_price_for_symbol(self, symbol: str) -> bool:
        """
        Загружает цену для символа, если её нет в базе данных.
        
        Args:
            symbol: Символ акции (например, 'AAPL', 'MSFT')
            
        Returns:
            True если цена была загружена, False если уже существует или ошибка
        """
        try:
            # Проверяем, есть ли уже данные для этого символа
            existing_prices = self.repository.get_latest_price(symbol)
            
            if existing_prices:
                logger.debug(f"Price data already exists for {symbol}, skipping auto-load")
                return False
            
            # Загружаем данные из Stooq
            logger.info("price_service_start", extra={"symbol": symbol})
            latest_price = fetch_latest_from_stooq(symbol)
            
            if not latest_price:
                logger.warning(f"No price data available for {symbol}")
                return False
            
            # Сохраняем в базу данных
            price_data = [latest_price]
            inserted_count = self.repository.upsert_prices(symbol, price_data)
            logger.info("price_service_success", extra={
                "symbol": symbol, 
                "rows": inserted_count, 
                "last_date": latest_price['date']
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Unexpected error loading price for {symbol}: {e}")
            return False
    
    def load_prices_for_symbols(self, symbols: List[str]) -> Dict[str, bool]:
        """
        Загружает цены для списка символов.
        
        Args:
            symbols: Список символов акций
            
        Returns:
            Словарь с результатами: {symbol: success}
        """
        results = {}
        for symbol in symbols:
            results[symbol] = self.load_price_for_symbol(symbol)
        return results
    
    def check_stooq_availability(self) -> bool:
        """
        Проверяет доступность Stooq API.
        
        Returns:
            True если API доступен, False иначе
        """
        try:
            # Пытаемся загрузить цену для AAPL как тест
            test_price = fetch_latest_from_stooq("AAPL")
            return test_price is not None
        except Exception as e:
            logger.error(f"Stooq API check failed: {e}")
            return False


def load_price_for_symbol(symbol: str, db: Session) -> bool:
    """
    Удобная функция для загрузки цены одного символа.
    
    Args:
        symbol: Символ акции
        db: Сессия базы данных
        
    Returns:
        True если цена была загружена, False иначе
    """
    service = PriceService(db)
    return service.load_price_for_symbol(symbol)


def load_prices_for_symbols(symbols: List[str], db: Session) -> Dict[str, bool]:
    """
    Удобная функция для загрузки цен нескольких символов.
    
    Args:
        symbols: Список символов акций
        db: Сессия базы данных
        
    Returns:
        Словарь с результатами: {symbol: success}
    """
    service = PriceService(db)
    return service.load_prices_for_symbols(symbols)
