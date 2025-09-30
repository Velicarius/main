"""
Smoke tests for Stooq client functionality.

These tests verify basic functionality without making actual network calls.
"""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import date, datetime
from io import StringIO

from app.quotes.stooq import fetch_daily_csv, fetch_eod, StooqFetchError
from app.services.price_eod import PriceEODRepository
from app.tasks.fetch_eod import run_eod_refresh


class TestStooqClient:
    """Test Stooq client functionality"""
    
    def test_fetch_daily_csv_success(self):
        """Test successful CSV parsing and normalization"""
        # Mock CSV data
        csv_data = """Date,Open,High,Low,Close,Volume
2024-01-01,100.0,105.0,95.0,102.0,1000000
2024-01-02,102.0,108.0,98.0,106.0,1200000
2024-01-03,106.0,110.0,104.0,108.0,900000"""
        
        with patch('requests.get') as mock_get:
            # Mock successful response
            mock_response = MagicMock()
            mock_response.text = csv_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Mock pandas.read_csv to use our test data
            with patch('pandas.read_csv') as mock_read_csv:
                mock_read_csv.return_value = pd.read_csv(StringIO(csv_data), parse_dates=['Date'])
                
                result = fetch_daily_csv("AAPL.US")
                
                # Verify result structure
                assert isinstance(result, pd.DataFrame)
                assert len(result) == 3
                assert list(result.columns) == ['as_of', 'open', 'high', 'low', 'close', 'volume']
                
                # Verify data types
                assert result['open'].dtype == 'float64'
                assert result['volume'].dtype == 'float64'
                
                # Verify date parsing
                assert isinstance(result['as_of'].iloc[0], datetime)
    
    def test_fetch_daily_csv_empty_response(self):
        """Test handling of empty response"""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = ""
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            with pytest.raises(StooqFetchError, match="Empty response"):
                fetch_daily_csv("INVALID.US")
    
    def test_fetch_daily_csv_error_response(self):
        """Test handling of error response"""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = "error: symbol not found"
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            with pytest.raises(StooqFetchError, match="Stooq returned error"):
                fetch_daily_csv("INVALID.US")
    
    def test_fetch_daily_csv_timeout(self):
        """Test handling of timeout"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Timeout")
            
            with pytest.raises(StooqFetchError, match="Network error"):
                fetch_daily_csv("AAPL.US")
    
    def test_fetch_eod_conversion(self):
        """Test conversion from DataFrame to list of dicts"""
        # Create test DataFrame
        test_data = {
            'as_of': [date(2024, 1, 1), date(2024, 1, 2)],
            'open': [100.0, 102.0],
            'high': [105.0, 108.0],
            'low': [95.0, 98.0],
            'close': [102.0, 106.0],
            'volume': [1000000, 1200000]
        }
        df = pd.DataFrame(test_data)
        
        with patch('app.quotes.stooq.fetch_daily_csv', return_value=df):
            result = fetch_eod("AAPL.US")
            
            assert isinstance(result, list)
            assert len(result) == 2
            
            # Check first record
            first_record = result[0]
            assert first_record['date'] == date(2024, 1, 1)
            assert first_record['open'] == 100.0
            assert first_record['close'] == 102.0
            assert first_record['volume'] == 1000000
            assert first_record['source'] == 'stooq'


class TestPriceEODRepository:
    """Test PriceEOD repository functionality"""
    
    def test_upsert_prices_empty_list(self):
        """Test upsert with empty price list"""
        mock_db = MagicMock()
        repository = PriceEODRepository(mock_db)
        
        result = repository.upsert_prices("AAPL.US", [])
        
        assert result == 0
        mock_db.execute.assert_not_called()
    
    def test_upsert_prices_data_preparation(self):
        """Test data preparation for upsert"""
        mock_db = MagicMock()
        mock_db.execute.return_value = MagicMock()
        repository = PriceEODRepository(mock_db)
        
        prices = [
            {
                'date': date(2024, 1, 1),
                'open': 100.0,
                'high': 105.0,
                'low': 95.0,
                'close': 102.0,
                'volume': 1000000,
                'source': 'stooq'
            }
        ]
        
        result = repository.upsert_prices("AAPL.US", prices)
        
        assert result == 1
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()


class TestEODTask:
    """Test EOD task functionality"""
    
    @patch('app.tasks.fetch_eod.settings')
    def test_run_eod_refresh_disabled(self, mock_settings):
        """Test EOD refresh when feature is disabled"""
        mock_settings.eod_enable = False
        
        result = run_eod_refresh()
        
        assert result['status'] == 'disabled'
        assert result['message'] == 'EOD feature is disabled'
        assert result['total_symbols'] == 0
    
    @patch('app.tasks.fetch_eod.settings')
    def test_run_eod_refresh_unsupported_source(self, mock_settings):
        """Test EOD refresh with unsupported source"""
        mock_settings.eod_enable = True
        mock_settings.eod_source = 'yahoo'  # Unsupported source
        
        result = run_eod_refresh()
        
        assert result['status'] == 'unsupported_source'
        assert 'yahoo' in result['message']
        assert result['total_symbols'] == 0





