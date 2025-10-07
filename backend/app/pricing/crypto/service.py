"""Crypto price service with caching and fallback providers"""

import asyncio
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.config import settings
from .types import CryptoPrice, ALLOWED_CRYPTO_SYMBOLS
from .binance_provider import BinancePriceProvider
from .coingecko_provider import CoinGeckoPriceProvider

logger = logging.getLogger(__name__)


class CryptoPriceService:
    """Service for getting crypto prices with caching and fallback providers"""
    
    def __init__(self):
        self._cache: Dict[str, CryptoPrice] = {}
        self._cache_ttl = timedelta(seconds=settings.crypto_price_ttl_seconds)
        self._primary_provider = settings.crypto_price_primary.lower()
        
        # Parse allowed symbols from config
        self._allowed_symbols = set(
            symbol.strip().upper() 
            for symbol in settings.crypto_allowed_symbols.split(",")
        )
        
        logger.info(f"CryptoPriceService initialized with primary={self._primary_provider}, "
                   f"ttl={self._cache_ttl.total_seconds()}s, "
                   f"allowed_symbols={len(self._allowed_symbols)}")
    
    def _is_symbol_allowed(self, symbol: str) -> bool:
        """Check if symbol is in whitelist"""
        return symbol.upper() in self._allowed_symbols
    
    def _is_cache_valid(self, price: CryptoPrice) -> bool:
        """Check if cached price is still valid"""
        if not price:
            return False
        age = datetime.utcnow() - price.timestamp
        return age < self._cache_ttl
    
    def _get_from_cache(self, symbol: str) -> Optional[CryptoPrice]:
        """Get price from cache if valid"""
        symbol = symbol.upper()
        if symbol in self._cache:
            cached_price = self._cache[symbol]
            if self._is_cache_valid(cached_price):
                logger.debug(f"Cache hit for {symbol}: {cached_price.price_usd} USD")
                return cached_price
            else:
                # Remove expired cache entry
                del self._cache[symbol]
                logger.debug(f"Cache expired for {symbol}")
        return None
    
    def _set_cache(self, price: CryptoPrice):
        """Store price in cache"""
        if price:
            self._cache[price.symbol] = price
            logger.debug(f"Cached price for {price.symbol}: {price.price_usd} USD from {price.source}")
    
    async def get_price(self, symbol: str) -> Optional[CryptoPrice]:
        """
        Get crypto price with caching and fallback providers
        
        Args:
            symbol: Crypto symbol (e.g., 'BTC', 'ETH')
            
        Returns:
            CryptoPrice object or None if failed
        """
        symbol = symbol.upper()
        
        # Check if symbol is allowed
        if not self._is_symbol_allowed(symbol):
            logger.warning(f"Symbol {symbol} not in allowed list")
            return None
        
        # Try cache first
        cached_price = self._get_from_cache(symbol)
        if cached_price:
            return cached_price
        
        # Try primary provider
        primary_price = await self._try_primary_provider(symbol)
        if primary_price:
            self._set_cache(primary_price)
            return primary_price
        
        # Try fallback provider
        fallback_price = await self._try_fallback_provider(symbol)
        if fallback_price:
            self._set_cache(fallback_price)
            return fallback_price
        
        # Return stale cache if available (better than nothing)
        if symbol in self._cache:
            stale_price = self._cache[symbol]
            logger.warning(f"Using stale cache for {symbol} (age: {datetime.utcnow() - stale_price.timestamp})")
            return stale_price
        
        logger.error(f"Failed to get price for {symbol} from all providers")
        return None
    
    async def get_batch_prices(self, symbols: List[str]) -> Dict[str, Optional[CryptoPrice]]:
        """
        Get prices for multiple symbols efficiently
        
        Args:
            symbols: List of crypto symbols
            
        Returns:
            Dict mapping symbol to CryptoPrice or None
        """
        # Filter allowed symbols
        valid_symbols = [s.upper() for s in symbols if self._is_symbol_allowed(s.upper())]
        result = {symbol: None for symbol in symbols}
        
        # Check cache for all symbols
        cache_misses = []
        for symbol in valid_symbols:
            cached_price = self._get_from_cache(symbol)
            if cached_price:
                result[symbol] = cached_price
            else:
                cache_misses.append(symbol)
        
        if not cache_misses:
            return result
        
        # Try to get missing prices from providers
        logger.debug(f"Cache misses for {len(cache_misses)} symbols: {cache_misses}")
        
        # Try primary provider for batch
        if self._primary_provider == "coingecko":
            primary_prices = await self._try_coingecko_batch(cache_misses)
        else:
            # Binance doesn't support batch, so try individual requests
            primary_prices = await self._try_binance_batch(cache_misses)
        
        # Update results and cache
        for symbol, price in primary_prices.items():
            if price:
                result[symbol] = price
                self._set_cache(price)
        
        # Try fallback for remaining misses
        remaining_misses = [s for s in cache_misses if result[s] is None]
        if remaining_misses:
            if self._primary_provider == "coingecko":
                fallback_prices = await self._try_binance_batch(remaining_misses)
            else:
                fallback_prices = await self._try_coingecko_batch(remaining_misses)
            
            for symbol, price in fallback_prices.items():
                if price:
                    result[symbol] = price
                    self._set_cache(price)
        
        return result
    
    async def _try_primary_provider(self, symbol: str) -> Optional[CryptoPrice]:
        """Try to get price from primary provider"""
        if self._primary_provider == "binance":
            return await self._try_binance(symbol)
        elif self._primary_provider == "coingecko":
            return await self._try_coingecko(symbol)
        else:
            logger.error(f"Unknown primary provider: {self._primary_provider}")
            return None
    
    async def _try_fallback_provider(self, symbol: str) -> Optional[CryptoPrice]:
        """Try to get price from fallback provider"""
        if self._primary_provider == "binance":
            return await self._try_coingecko(symbol)
        elif self._primary_provider == "coingecko":
            return await self._try_binance(symbol)
        else:
            return None
    
    async def _try_binance(self, symbol: str) -> Optional[CryptoPrice]:
        """Try to get price from Binance"""
        try:
            async with BinancePriceProvider() as provider:
                return await provider.get_last_price(symbol)
        except Exception as e:
            logger.error(f"Binance provider error for {symbol}: {e}")
            return None
    
    async def _try_coingecko(self, symbol: str) -> Optional[CryptoPrice]:
        """Try to get price from CoinGecko"""
        try:
            async with CoinGeckoPriceProvider() as provider:
                return await provider.get_last_price(symbol)
        except Exception as e:
            logger.error(f"CoinGecko provider error for {symbol}: {e}")
            return None
    
    async def _try_binance_batch(self, symbols: List[str]) -> Dict[str, Optional[CryptoPrice]]:
        """Try to get prices from Binance (individual requests)"""
        result = {}
        tasks = []
        
        async with BinancePriceProvider() as provider:
            for symbol in symbols:
                task = asyncio.create_task(provider.get_last_price(symbol))
                tasks.append((symbol, task))
            
            for symbol, task in tasks:
                try:
                    result[symbol] = await task
                except Exception as e:
                    logger.error(f"Binance batch error for {symbol}: {e}")
                    result[symbol] = None
        
        return result
    
    async def _try_coingecko_batch(self, symbols: List[str]) -> Dict[str, Optional[CryptoPrice]]:
        """Try to get prices from CoinGecko (batch request)"""
        try:
            async with CoinGeckoPriceProvider() as provider:
                return await provider.get_batch_prices(symbols)
        except Exception as e:
            logger.error(f"CoinGecko batch error: {e}")
            return {symbol: None for symbol in symbols}
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics for monitoring"""
        now = datetime.utcnow()
        valid_entries = 0
        expired_entries = 0
        
        for price in self._cache.values():
            if self._is_cache_valid(price):
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_ttl_seconds": self._cache_ttl.total_seconds(),
            "primary_provider": self._primary_provider,
            "allowed_symbols_count": len(self._allowed_symbols)
        }


# Global service instance
_crypto_price_service: Optional[CryptoPriceService] = None


def get_crypto_price_service() -> CryptoPriceService:
    """Get global crypto price service instance"""
    global _crypto_price_service
    if _crypto_price_service is None:
        _crypto_price_service = CryptoPriceService()
    return _crypto_price_service
