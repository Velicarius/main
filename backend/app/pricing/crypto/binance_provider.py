"""Binance price provider for crypto assets"""

import asyncio
import aiohttp
import logging
from decimal import Decimal
from datetime import datetime
from typing import Optional

from .types import CryptoPrice, BINANCE_SYMBOL_MAP, ALLOWED_CRYPTO_SYMBOLS

logger = logging.getLogger(__name__)


class BinancePriceProvider:
    """Binance API price provider for crypto assets"""
    
    BASE_URL = "https://api.binance.com/api/v3"
    TIMEOUT = 5  # seconds
    MAX_RETRIES = 3
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.TIMEOUT)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _get_binance_symbol(self, crypto_symbol: str) -> Optional[str]:
        """Convert crypto symbol to Binance trading pair"""
        if crypto_symbol.upper() not in ALLOWED_CRYPTO_SYMBOLS:
            return None
        return BINANCE_SYMBOL_MAP.get(crypto_symbol.upper())
    
    async def get_last_price(self, symbol: str) -> Optional[CryptoPrice]:
        """
        Get last price for crypto symbol from Binance
        
        Args:
            symbol: Crypto symbol (e.g., 'BTC', 'ETH')
            
        Returns:
            CryptoPrice object or None if failed
        """
        if not self.session:
            raise RuntimeError("Provider not initialized. Use async context manager.")
        
        binance_symbol = self._get_binance_symbol(symbol)
        if not binance_symbol:
            logger.warning(f"Symbol {symbol} not supported by Binance")
            return None
        
        url = f"{self.BASE_URL}/ticker/price"
        params = {"symbol": binance_symbol}
        
        for attempt in range(self.MAX_RETRIES):
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = Decimal(data["price"])
                        
                        return CryptoPrice(
                            symbol=symbol.upper(),
                            price_usd=price,
                            timestamp=datetime.utcnow(),
                            source="binance"
                        )
                    else:
                        logger.warning(f"Binance API returned {response.status} for {symbol}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"Binance API timeout for {symbol} (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"Binance API error for {symbol}: {e}")
            
            if attempt < self.MAX_RETRIES - 1:
                # Exponential backoff: 0.5s, 1s, 2s
                await asyncio.sleep(0.5 * (2 ** attempt))
        
        logger.error(f"Failed to get price for {symbol} from Binance after {self.MAX_RETRIES} attempts")
        return None
