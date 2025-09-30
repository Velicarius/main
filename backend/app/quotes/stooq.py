"""
Stooq client for fetching EOD (End of Day) price data.

This module provides functionality to fetch daily price data from Stooq.com
in CSV format and normalize it for our database schema.
"""

import logging
import pandas as pd
import requests
from datetime import date, datetime
from typing import List, Dict, Optional
from urllib.parse import urlencode

from app.core.config import settings

logger = logging.getLogger(__name__)


class StooqFetchError(Exception):
    """Custom exception for Stooq API errors"""
    pass


def fetch_daily_csv(symbol: str) -> pd.DataFrame:
    """
    Fetch daily CSV data from Stooq for a given symbol.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL.US', 'MSFT.US')
        
    Returns:
        pandas.DataFrame with normalized columns: ['as_of', 'open', 'high', 'low', 'close', 'volume']
        
    Raises:
        StooqFetchError: If data cannot be fetched or is invalid
    """
    logger.info(f"Fetching EOD data for symbol: {symbol}")
    
    # Construct Stooq URL
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    
    try:
        # Fetch data with timeout
        response = requests.get(url, timeout=settings.stq_timeout)
        response.raise_for_status()
        
        # Check if response is empty or contains error message
        if not response.text.strip():
            raise StooqFetchError(f"Empty response from Stooq for symbol {symbol}")
        
        # Check for common error patterns in Stooq responses
        if "error" in response.text.lower() or "not found" in response.text.lower():
            raise StooqFetchError(f"Stooq returned error for symbol {symbol}: {response.text[:200]}")
        
        # Parse CSV data
        try:
            df = pd.read_csv(
                url, 
                parse_dates=['Date'],
                date_format='%Y-%m-%d'
            )
        except Exception as e:
            # If URL parsing fails, try with response text
            from io import StringIO
            df = pd.read_csv(
                StringIO(response.text),
                parse_dates=['Date'],
                date_format='%Y-%m-%d'
            )
        
        # Validate that we have data
        if df.empty:
            raise StooqFetchError(f"No data returned for symbol {symbol}")
        
        # Check required columns
        required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise StooqFetchError(f"Missing required columns for {symbol}: {missing_columns}")
        
        # Normalize column names and data
        df = df.rename(columns={
            'Date': 'as_of',
            'Open': 'open',
            'High': 'high', 
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
        
        # Select only the columns we need
        df = df[['as_of', 'open', 'high', 'low', 'close', 'volume']].copy()
        
        # Fill NaN values and ensure proper data types
        df['open'] = pd.to_numeric(df['open'], errors='coerce')
        df['high'] = pd.to_numeric(df['high'], errors='coerce')
        df['low'] = pd.to_numeric(df['low'], errors='coerce')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        
        # Fill NaN values with 0 for volume, forward fill for prices
        df['volume'] = df['volume'].fillna(0)
        df['open'] = df['open'].fillna(method='ffill')
        df['high'] = df['high'].fillna(method='ffill')
        df['low'] = df['low'].fillna(method='ffill')
        df['close'] = df['close'].fillna(method='ffill')
        
        # Remove rows where all price data is NaN
        df = df.dropna(subset=['open', 'high', 'low', 'close'], how='all')
        
        # Validate data quality
        if df.empty:
            raise StooqFetchError(f"No valid price data for symbol {symbol}")
        
        # Check for reasonable price ranges (basic validation)
        if df['close'].min() <= 0:
            logger.warning(f"Symbol {symbol} has non-positive close prices")
        
        logger.info(f"Successfully fetched {len(df)} rows for {symbol}, date range: {df['as_of'].min()} to {df['as_of'].max()}")
        
        return df
        
    except requests.exceptions.Timeout:
        raise StooqFetchError(f"Timeout ({settings.stq_timeout}s) fetching data for {symbol}")
    except requests.exceptions.RequestException as e:
        raise StooqFetchError(f"Network error fetching data for {symbol}: {str(e)}")
    except pd.errors.EmptyDataError:
        raise StooqFetchError(f"No data available for symbol {symbol}")
    except Exception as e:
        raise StooqFetchError(f"Unexpected error fetching data for {symbol}: {str(e)}")


def fetch_eod(symbol: str) -> List[Dict]:
    """
    Fetch EOD data and convert to list of dictionaries for database insertion.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL.US', 'MSFT.US')
        
    Returns:
        List of dictionaries with keys: date, open, high, low, close, volume, source
        
    Raises:
        StooqFetchError: If data cannot be fetched or is invalid
    """
    df = fetch_daily_csv(symbol)
    
    # Convert DataFrame to list of dictionaries
    result = []
    for _, row in df.iterrows():
        result.append({
            'date': row['as_of'].date() if isinstance(row['as_of'], datetime) else row['as_of'],
            'open': float(row['open']) if pd.notna(row['open']) else None,
            'high': float(row['high']) if pd.notna(row['high']) else None,
            'low': float(row['low']) if pd.notna(row['low']) else None,
            'close': float(row['close']) if pd.notna(row['close']) else None,
            'volume': int(row['volume']) if pd.notna(row['volume']) else 0,
            'source': 'stooq'
        })
    
    logger.info(f"Converted {len(result)} rows to dict format for {symbol}")
    return result




