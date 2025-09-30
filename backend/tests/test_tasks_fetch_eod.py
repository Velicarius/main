import pytest
import asyncio
from datetime import date, datetime
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict

import httpx
from sqlalchemy.orm import Session

from app.quotes.stooq import fetch_eod_csv, parse_eod_csv, fetch_eod, normalize_symbol_for_url
from app.tasks.fetch_eod import fetch_eod_for_symbols, _get_distinct_symbols_from_positions
from app.services.price_eod import PriceEODRepository


class TestStooqAdapter:
    """Test Stooq EOD adapter functions"""
    
    def test_normalize_symbol_for_url(self):
        """Test symbol normalization for URL"""
        assert normalize_symbol_for_url("AAPL.US") == "aapl.us"
        assert normalize_symbol_for_url("MSFT.US") == "msft.us"
        assert normalize_symbol_for_url("PKN.PL") == "pkn.pl"
    
    def test_parse_eod_csv_valid_data(self):
        """Test parsing valid CSV data"""
        csv_data = """Date,Open,High,Low,Close,Volume
2025-09-12,100.0,110.0,99.0,105.0,1000
2025-09-15,106.0,111.0,101.0,109.0,1200"""
        
        result = parse_eod_csv(csv_data)
        
        assert len(result) == 2
        assert result[0]["date"] == date(2025, 9, 12)
        assert result[0]["open"] == 100.0
        assert result[0]["high"] == 110.0
        assert result[0]["low"] == 99.0
        assert result[0]["close"] == 105.0
        assert result[0]["volume"] == 1000
        assert result[0]["source"] == "stooq"
        
        assert result[1]["date"] == date(2025, 9, 15)
        assert result[1]["close"] == 109.0
        assert result[1]["volume"] == 1200
    
    def test_parse_eod_csv_empty_volume(self):
        """Test parsing CSV with empty volume"""
        csv_data = """Date,Open,High,Low,Close,Volume
2025-09-12,100.0,110.0,99.0,105.0,"""
        
        result = parse_eod_csv(csv_data)
        
        assert len(result) == 1
        assert result[0]["volume"] is None
    
    def test_parse_eod_csv_empty_data(self):
        """Test parsing empty CSV"""
        result = parse_eod_csv("")
        assert result == []
        
        result = parse_eod_csv("   ")
        assert result == []
    
    def test_parse_eod_csv_invalid_rows(self):
        """Test parsing CSV with invalid rows"""
        csv_data = """Date,Open,High,Low,Close,Volume
2025-09-12,100.0,110.0,99.0,105.0,1000
invalid,row,data
2025-09-15,106.0,111.0,101.0,109.0,1200"""
        
        result = parse_eod_csv(csv_data)
        
        # Should skip invalid row and return valid ones
        assert len(result) == 2
        assert result[0]["date"] == date(2025, 9, 12)
        assert result[1]["date"] == date(2025, 9, 15)
    
    @pytest.mark.asyncio
    async def test_fetch_eod_csv_success(self):
        """Test successful CSV fetching"""
        mock_response = Mock()
        mock_response.text = "Date,Open,High,Low,Close,Volume\n2025-09-12,100,110,99,105,1000"
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await fetch_eod_csv("AAPL.US")
            
            assert result == "Date,Open,High,Low,Close,Volume\n2025-09-12,100,110,99,105,1000"
            mock_response.raise_for_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_eod_csv_http_error(self):
        """Test CSV fetching with HTTP error"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404 Not Found", request=Mock(), response=Mock()
            )
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            with pytest.raises(httpx.HTTPStatusError):
                await fetch_eod_csv("INVALID.SYMBOL")
    
    @pytest.mark.asyncio
    async def test_fetch_eod_success(self):
        """Test complete EOD fetching"""
        mock_csv = "Date,Open,High,Low,Close,Volume\n2025-09-12,100,110,99,105,1000"
        
        with patch('app.quotes.stooq.fetch_eod_csv', return_value=mock_csv):
            result = await fetch_eod("AAPL.US")
            
            assert len(result) == 1
            assert result[0]["date"] == date(2025, 9, 12)
            assert result[0]["close"] == 105.0
            assert result[0]["source"] == "stooq"


class TestFetchEODTask:
    """Test EOD fetching Celery task"""
    
    def test_get_distinct_symbols_from_positions(self):
        """Test getting distinct symbols from positions"""
        mock_db = Mock(spec=Session)
        mock_result = Mock()
        mock_result.fetchall.return_value = [("AAPL.US",), ("MSFT.US",), ("PKN.PL",)]
        mock_db.execute.return_value = mock_result
        
        result = _get_distinct_symbols_from_positions(mock_db)
        
        assert result == ["AAPL.US", "MSFT.US", "PKN.PL"]
    
    @patch('app.tasks.fetch_eod.asyncio.run')
    @patch('app.tasks.fetch_eod.PriceEODRepository')
    @patch('app.tasks.fetch_eod.SessionLocal')
    def test_fetch_eod_for_symbols_with_symbols(self, mock_session_local, mock_repo_class, mock_asyncio_run):
        """Test task execution with provided symbols"""
        # Setup mocks
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.upsert_prices.return_value = 2
        
        # Mock fetch_eod to return test data
        test_data = [
            {"date": date(2025, 9, 12), "open": 100.0, "high": 110.0, "low": 99.0, "close": 105.0, "volume": 1000, "source": "stooq"},
            {"date": date(2025, 9, 15), "open": 106.0, "high": 111.0, "low": 101.0, "close": 109.0, "volume": 1200, "source": "stooq"}
        ]
        mock_asyncio_run.return_value = test_data
        
        # Execute task
        result = fetch_eod_for_symbols(["AAPL.US"], "2025-09-13")
        
        # Verify results
        assert result["total_symbols"] == 1
        assert result["inserted_rows"] == 2  # Only 2025-09-15 row should be inserted (after since date)
        assert result["since"] == "2025-09-13"
        assert len(result["errors"]) == 0
        
        # Verify repository was called correctly
        mock_repo.upsert_prices.assert_called_once()
        call_args = mock_repo.upsert_prices.call_args
        assert call_args[0][0] == "AAPL.US"  # symbol
        # Check that only filtered data was passed
        filtered_data = call_args[0][1]
        assert len(filtered_data) == 1
        assert filtered_data[0]["date"] == date(2025, 9, 15)
    
    @patch('app.tasks.fetch_eod._get_distinct_symbols_from_positions')
    @patch('app.tasks.fetch_eod.asyncio.run')
    @patch('app.tasks.fetch_eod.PriceEODRepository')
    @patch('app.tasks.fetch_eod.SessionLocal')
    def test_fetch_eod_for_symbols_auto_discover(self, mock_session_local, mock_repo_class, mock_asyncio_run, mock_get_symbols):
        """Test task execution with auto-discovered symbols"""
        # Setup mocks
        mock_get_symbols.return_value = ["AAPL.US", "MSFT.US"]
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.upsert_prices.return_value = 1
        
        # Mock fetch_eod to return test data
        test_data = [
            {"date": date(2025, 9, 12), "open": 100.0, "high": 110.0, "low": 99.0, "close": 105.0, "volume": 1000, "source": "stooq"}
        ]
        mock_asyncio_run.return_value = test_data
        
        # Execute task without symbols (auto-discover)
        result = fetch_eod_for_symbols(None, None)
        
        # Verify results
        assert result["total_symbols"] == 2
        assert result["inserted_rows"] == 2  # 1 per symbol
        assert result["since"] is None
        assert len(result["errors"]) == 0
        
        # Verify symbols were auto-discovered
        mock_get_symbols.assert_called_once_with(mock_db)
    
    @patch('app.tasks.fetch_eod.asyncio.run')
    @patch('app.tasks.fetch_eod.PriceEODRepository')
    @patch('app.tasks.fetch_eod.SessionLocal')
    def test_fetch_eod_for_symbols_with_retries(self, mock_session_local, mock_repo_class, mock_asyncio_run):
        """Test task execution with retry logic"""
        # Setup mocks
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.upsert_prices.return_value = 1
        
        # Mock asyncio.run to fail first, then succeed
        mock_asyncio_run.side_effect = [
            httpx.HTTPStatusError("500 Server Error", request=Mock(), response=Mock()),
            httpx.HTTPStatusError("500 Server Error", request=Mock(), response=Mock()),
            [{"date": date(2025, 9, 12), "open": 100.0, "high": 110.0, "low": 99.0, "close": 105.0, "volume": 1000, "source": "stooq"}]
        ]
        
        # Execute task
        result = fetch_eod_for_symbols(["AAPL.US"], None)
        
        # Verify results - the task should succeed after retries
        assert result["total_symbols"] == 1
        assert result["inserted_rows"] == 1
        assert len(result["errors"]) == 0
        
        # Verify retries were attempted (at least 3 calls)
        assert mock_asyncio_run.call_count >= 3
    
    @patch('app.tasks.fetch_eod.asyncio.run')
    @patch('app.tasks.fetch_eod.PriceEODRepository')
    @patch('app.tasks.fetch_eod.SessionLocal')
    def test_fetch_eod_for_symbols_all_retries_fail(self, mock_session_local, mock_repo_class, mock_asyncio_run):
        """Test task execution when all retries fail"""
        # Setup mocks
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        # Mock asyncio.run to always fail
        mock_asyncio_run.side_effect = httpx.HTTPStatusError("500 Server Error", request=Mock(), response=Mock())
        
        # Execute task
        result = fetch_eod_for_symbols(["AAPL.US"], None)
        
        # Verify results
        assert result["total_symbols"] == 1
        assert result["inserted_rows"] == 0
        assert len(result["errors"]) == 1
        assert "Failed to process AAPL.US" in result["errors"][0]
    
    def test_fetch_eod_for_symbols_invalid_since_date(self):
        """Test task execution with invalid since date"""
        with pytest.raises(ValueError, match="Invalid since date format"):
            fetch_eod_for_symbols(["AAPL.US"], "invalid-date")


class TestAdminTasksRouter:
    """Test admin tasks router endpoints"""
    
    @pytest.mark.asyncio
    async def test_trigger_fetch_eod_success(self):
        """Test successful task triggering"""
        from app.routers.admin_tasks import trigger_fetch_eod, FetchEODRequest
        
        mock_task = Mock()
        mock_task.id = "test-task-id"
        
        with patch('app.routers.admin_tasks.fetch_eod_for_symbols.delay', return_value=mock_task):
            request = FetchEODRequest(symbols=["AAPL.US"], since="2025-01-01")
            result = await trigger_fetch_eod(request)
            
            assert result.status == "queued"
            assert result.task_id == "test-task-id"
            assert "queued successfully" in result.message
    
    @pytest.mark.asyncio
    async def test_trigger_fetch_eod_invalid_date(self):
        """Test task triggering with invalid date"""
        from app.routers.admin_tasks import trigger_fetch_eod, FetchEODRequest
        
        request = FetchEODRequest(symbols=["AAPL.US"], since="invalid-date")
        
        with pytest.raises(Exception):  # Should raise HTTPException
            await trigger_fetch_eod(request)
    
    @pytest.mark.asyncio
    async def test_get_task_status(self):
        """Test getting task status"""
        from app.routers.admin_tasks import get_task_status
        
        mock_task = Mock()
        mock_task.status = "SUCCESS"
        mock_task.ready.return_value = True
        mock_task.result = {"total_symbols": 1, "inserted_rows": 2}
        mock_task.failed.return_value = False
        
        with patch('app.routers.admin_tasks.celery_app.AsyncResult', return_value=mock_task):
            result = await get_task_status("test-task-id")
            
            assert result["task_id"] == "test-task-id"
            assert result["status"] == "SUCCESS"
            assert result["result"]["total_symbols"] == 1
