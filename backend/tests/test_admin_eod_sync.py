"""
Test for the synchronous EOD refresh endpoint.

This test verifies the basic functionality without making actual network calls.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import date

from app.marketdata.stooq_client import fetch_latest_from_stooq, StooqFetchError


class TestStooqClientSync:
    """Test synchronous Stooq client functionality"""
    
    def test_fetch_latest_from_stooq_success(self):
        """Test successful data fetching and parsing"""
        # Mock CSV data
        csv_content = """Date,Open,High,Low,Close,Volume
2024-01-01,100.0,105.0,95.0,102.0,1000000
2024-01-02,102.0,108.0,98.0,106.0,1200000"""
        
        with patch('urllib.request.urlopen') as mock_urlopen:
            # Mock response
            mock_response = MagicMock()
            mock_response.read.return_value = csv_content.encode('utf-8')
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            result = fetch_latest_from_stooq("aapl")
            
            # Verify result structure
            assert result is not None
            assert result['date'] == date(2024, 1, 2)  # Last row
            assert result['open'] == 102.0
            assert result['high'] == 108.0
            assert result['low'] == 98.0
            assert result['close'] == 106.0
            assert result['volume'] == 1200000
            assert result['source'] == 'stooq'
    
    def test_fetch_latest_from_stooq_empty_data(self):
        """Test handling of empty CSV data"""
        csv_content = """Date,Open,High,Low,Close,Volume"""
        
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = csv_content.encode('utf-8')
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            result = fetch_latest_from_stooq("invalid")
            
            assert result is None
    
    def test_fetch_latest_from_stooq_network_error(self):
        """Test handling of network errors"""
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = Exception("Network error")
            
            with pytest.raises(StooqFetchError, match="Failed to fetch"):
                fetch_latest_from_stooq("aapl")
    
    def test_fetch_latest_from_stooq_malformed_csv(self):
        """Test handling of malformed CSV data"""
        csv_content = """Date,Open,High,Low,Close,Volume
invalid-date,invalid,invalid,invalid,invalid,invalid"""
        
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = csv_content.encode('utf-8')
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            with pytest.raises(StooqFetchError, match="Malformed CSV"):
                fetch_latest_from_stooq("aapl")
    
    def test_fetch_latest_from_stooq_null_values(self):
        """Test handling of null/empty values in CSV"""
        csv_content = """Date,Open,High,Low,Close,Volume
2024-01-01,100.0,105.0,95.0,102.0,1000000
2024-01-02,,108.0,,106.0,"""
        
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = csv_content.encode('utf-8')
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            result = fetch_latest_from_stooq("aapl")
            
            assert result is not None
            assert result['open'] is None
            assert result['high'] == 108.0
            assert result['low'] is None
            assert result['close'] == 106.0
            assert result['volume'] is None





