"""
Автоматическая загрузка цен для новых позиций.
DEPRECATED: Use app.services.price_service instead.
"""

import logging
from typing import List, Dict
from sqlalchemy.orm import Session

from app.services.price_service import load_price_for_symbol as _load_price_for_symbol, load_prices_for_symbols as _load_prices_for_symbols

logger = logging.getLogger(__name__)


def load_price_for_symbol(symbol: str, db: Session) -> bool:
    """
    Загружает цену для символа, если её нет в базе данных.
    
    DEPRECATED: Use app.services.price_service.load_price_for_symbol instead.
    
    Args:
        symbol: Символ акции (например, 'AAPL', 'MSFT')
        
    Returns:
        True если цена была загружена, False если уже существует или ошибка
    """
    logger.warning("DEPRECATED: auto_price_loader.load_price_for_symbol -> price_service.load_price_for_symbol")
    return _load_price_for_symbol(symbol, db)


def load_prices_for_symbols(symbols: List[str], db: Session) -> Dict[str, bool]:
    """
    Загружает цены для списка символов.
    
    DEPRECATED: Use app.services.price_service.load_prices_for_symbols instead.
    
    Args:
        symbols: Список символов акций
        
    Returns:
        Словарь с результатами: {symbol: success}
    """
    logger.warning("DEPRECATED: auto_price_loader.load_prices_for_symbols -> price_service.load_prices_for_symbols")
    return _load_prices_for_symbols(symbols, db)