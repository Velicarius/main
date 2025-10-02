# DEPRECATED: use app.marketdata.stooq_client instead.
# This shim re-exports the new client to avoid legacy code paths breaking.
import logging, inspect
from app.marketdata.stooq_client import (
    fetch_latest_from_stooq,
    fetch_eod_dataframe_from_stooq,
    symbol_to_stooq,
)

_logger = logging.getLogger(__name__)
_logger.warning(
    "DEPRECATED import: app.quotes.stooq -> app.marketdata.stooq_client (%s)",
    inspect.getfile(fetch_latest_from_stooq),
)

# Legacy compatibility functions
def fetch_eod(symbol: str):
    """Legacy function - returns list of dicts for compatibility"""
    latest = fetch_latest_from_stooq(symbol)
    if latest:
        return [latest]
    return []

def fetch_daily_csv(symbol: str):
    """Legacy function - returns DataFrame for compatibility"""
    return fetch_eod_dataframe_from_stooq(symbol)

# Legacy exception for compatibility
class StooqFetchError(Exception):
    """Legacy exception - kept for compatibility"""
    pass

__all__ = [
    "fetch_latest_from_stooq",
    "fetch_eod_dataframe_from_stooq", 
    "symbol_to_stooq",
    "fetch_eod",
    "fetch_daily_csv",
    "StooqFetchError",
]