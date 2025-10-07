"""CoinGecko price provider for crypto assets"""

import asyncio
import aiohttp
import logging
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, List

from .types import CryptoPrice, COINGECKO_SYMBOL_MAP, ALLOWED_CRYPTO_SYMBOLS

logger = logging.getLogger(__name__)


class CoinGeckoPriceProvider:
    """CoinGecko API price provider for crypto assets"""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    TIMEOUT = 10  # seconds (CoinGecko is slower)
    MAX_RETRIES = 2
    
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
    
    def _get_coingecko_id(self, crypto_symbol: str) -> Optional[str]:
        """Convert crypto symbol to CoinGecko ID"""
        if crypto_symbol.upper() not in ALLOWED_CRYPTO_SYMBOLS:
            return None
        return COINGECKO_SYMBOL_MAP.get(crypto_symbol.upper())
    
    async def get_last_price(self, symbol: str) -> Optional[CryptoPrice]:
        """
        Get last price for crypto symbol from CoinGecko
        
        Args:
            symbol: Crypto symbol (e.g., 'BTC', 'ETH')
            
        Returns:
            CryptoPrice object or None if failed
        """
        if not self.session:
            raise RuntimeError("Provider not initialized. Use async context manager.")
        
        coingecko_id = self._get_coingecko_id(symbol)
        if not coingecko_id:
            logger.warning(f"Symbol {symbol} not supported by CoinGecko")
            return None
        
        url = f"{self.BASE_URL}/simple/price"
        params = {
            "ids": coingecko_id,
            "vs_currencies": "usd"
        }
        
        for attempt in range(self.MAX_RETRIES):
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if coingecko_id in data and "usd" in data[coingecko_id]:
                            price = Decimal(str(data[coingecko_id]["usd"]))
                            
                            return CryptoPrice(
                                symbol=symbol.upper(),
                                price_usd=price,
                                timestamp=datetime.utcnow(),
                                source="coingecko"
                            )
                        else:
                            logger.warning(f"CoinGecko response missing price for {symbol}")
                            
                    elif response.status == 429:
                        # Rate limit - wait longer
                        logger.warning(f"CoinGecko rate limit for {symbol}")
                        if attempt < self.MAX_RETRIES - 1:
                            await asyncio.sleep(2)
                            continue
                    else:
                        logger.warning(f"CoinGecko API returned {response.status} for {symbol}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"CoinGecko API timeout for {symbol} (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"CoinGecko API error for {symbol}: {e}")
            
            if attempt < self.MAX_RETRIES - 1:
                # Linear backoff: 1s, 2s
                await asyncio.sleep(1 + attempt)
        
        logger.error(f"Failed to get price for {symbol} from CoinGecko after {self.MAX_RETRIES} attempts")
        return None
    
    async def get_batch_prices(self, symbols: List[str]) -> Dict[str, Optional[CryptoPrice]]:
        """
        Get prices for multiple symbols in one request (more efficient)
        
        Args:
            symbols: List of crypto symbols
            
        Returns:
            Dict mapping symbol to CryptoPrice or None
        """
        if not self.session:
            raise RuntimeError("Provider not initialized. Use async context manager.")
        
        # Filter valid symbols and get their CoinGecko IDs
        valid_symbols = []
        symbol_to_id = {}
        
        for symbol in symbols:
            coingecko_id = self._get_coingecko_id(symbol)
            if coingecko_id:
                valid_symbols.append(symbol)
                symbol_to_id[symbol] = coingecko_id
        
        if not valid_symbols:
            return {symbol: None for symbol in symbols}
        
        # Get all IDs for batch request
        coingecko_ids = list(symbol_to_id.values())
        url = f"{self.BASE_URL}/simple/price"
        params = {
            "ids": ",".join(coingecko_ids),
            "vs_currencies": "usd"
        }
        
        result = {symbol: None for symbol in symbols}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for symbol in valid_symbols:
                        coingecko_id = symbol_to_id[symbol]
                        if coingecko_id in data and "usd" in data[coingecko_id]:
                            price = Decimal(str(data[coingecko_id]["usd"]))
                            
                            result[symbol] = CryptoPrice(
                                symbol=symbol.upper(),
                                price_usd=price,
                                timestamp=datetime.utcnow(),
                                source="coingecko"
                            )
                else:
                    logger.warning(f"CoinGecko batch API returned {response.status}")
                    
        except Exception as e:
            logger.error(f"CoinGecko batch API error: {e}")
        
        return result
