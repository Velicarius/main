"""Types for crypto pricing"""

from typing import Optional
from decimal import Decimal
from datetime import datetime
from dataclasses import dataclass


@dataclass
class CryptoPrice:
    """Crypto price data"""
    symbol: str
    price_usd: Decimal
    timestamp: datetime
    source: str  # 'binance', 'coingecko', 'cache'
    
    def __post_init__(self):
        if isinstance(self.price_usd, (int, float)):
            self.price_usd = Decimal(str(self.price_usd))


# Mapping of crypto symbols to Binance trading pairs
BINANCE_SYMBOL_MAP = {
    'BTC': 'BTCUSDT',
    'ETH': 'ETHUSDT', 
    'SOL': 'SOLUSDT',
    'BNB': 'BNBUSDT',
    'ADA': 'ADAUSDT',
    'XRP': 'XRPUSDT',
    'DOGE': 'DOGEUSDT',
    'AVAX': 'AVAXUSDT',
    'MATIC': 'MATICUSDT',
}

# Mapping of crypto symbols to CoinGecko IDs
COINGECKO_SYMBOL_MAP = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'SOL': 'solana',
    'BNB': 'binancecoin',
    'ADA': 'cardano',
    'XRP': 'ripple',
    'DOGE': 'dogecoin',
    'AVAX': 'avalanche-2',
    'MATIC': 'matic-network',
}

# Allowed crypto symbols (whitelist)
ALLOWED_CRYPTO_SYMBOLS = set(BINANCE_SYMBOL_MAP.keys())
