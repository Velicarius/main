"""
Test for portfolio valuations EOD read API functionality.

This test verifies the basic logic without database dependencies.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from app.services.portfolio_valuation_eod import PortfolioValuationEODRepository


class TestPortfolioValuationEODRepositoryRead:
    """Test PortfolioValuationEOD repository read functionality"""
    
    def test_list_by_user_no_filters(self):
        """Test listing valuations for a user without date filters"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        
        repository = PortfolioValuationEODRepository(mock_db)
        user_id = uuid4()
        
        result = repository.list_by_user(user_id)
        
        # Verify query chain
        mock_db.query.assert_called_once()
        mock_query.filter.assert_called_once()
        mock_query.order_by.assert_called_once()
        mock_query.all.assert_called_once()
        
        assert result == []
    
    def test_list_by_user_with_date_filters(self):
        """Test listing valuations with date filters"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        
        repository = PortfolioValuationEODRepository(mock_db)
        user_id = uuid4()
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        result = repository.list_by_user(user_id, start_date, end_date)
        
        # Verify multiple filter calls (user_id, start_date, end_date)
        assert mock_query.filter.call_count == 3
        mock_query.order_by.assert_called_once()
        mock_query.all.assert_called_once()
        
        assert result == []
    
    def test_latest_by_user_found(self):
        """Test getting latest valuation for a user"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        
        # Mock the latest valuation
        mock_valuation = MagicMock()
        mock_valuation.id = uuid4()
        mock_valuation.user_id = uuid4()
        mock_valuation.as_of = date(2024, 1, 15)
        mock_valuation.total_value = Decimal("2500.50")
        mock_valuation.currency = "USD"
        mock_valuation.created_at = datetime.now()
        
        mock_query.first.return_value = mock_valuation
        
        repository = PortfolioValuationEODRepository(mock_db)
        user_id = uuid4()
        
        result = repository.latest_by_user(user_id)
        
        # Verify query chain
        mock_db.query.assert_called_once()
        mock_query.filter.assert_called_once()
        mock_query.order_by.assert_called_once()
        mock_query.first.assert_called_once()
        
        assert result == mock_valuation
    
    def test_latest_by_user_not_found(self):
        """Test getting latest valuation when none exists"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None
        
        repository = PortfolioValuationEODRepository(mock_db)
        user_id = uuid4()
        
        result = repository.latest_by_user(user_id)
        
        # Verify query chain
        mock_db.query.assert_called_once()
        mock_query.filter.assert_called_once()
        mock_query.order_by.assert_called_once()
        mock_query.first.assert_called_once()
        
        assert result is None


class TestPortfolioValuationsAPI:
    """Test portfolio valuations API endpoints"""
    
    def test_list_valuations_endpoint_params(self):
        """Test that list_valuations endpoint accepts correct parameters"""
        # This test verifies the endpoint signature matches expectations
        from app.routers.portfolio_valuations import list_valuations
        
        # Check that the function exists and has the right signature
        import inspect
        sig = inspect.signature(list_valuations)
        params = list(sig.parameters.keys())
        
        expected_params = ['user_id', 'start_date', 'end_date', 'db']
        assert all(param in params for param in expected_params)
    
    def test_latest_valuation_endpoint_params(self):
        """Test that latest_valuation endpoint accepts correct parameters"""
        from app.routers.portfolio_valuations import latest_valuation
        
        # Check that the function exists and has the right signature
        import inspect
        sig = inspect.signature(latest_valuation)
        params = list(sig.parameters.keys())
        
        expected_params = ['user_id', 'db']
        assert all(param in params for param in expected_params)
    
    def test_portfolio_valuation_schema_structure(self):
        """Test that PortfolioValuationEODOut schema has correct fields"""
        from app.schemas import PortfolioValuationEODOut
        
        # Check that the schema exists and has the right fields
        fields = PortfolioValuationEODOut.__fields__
        expected_fields = ['id', 'user_id', 'as_of', 'total_value', 'currency', 'created_at']
        
        assert all(field in fields for field in expected_fields)
        
        # Check field types
        assert fields['id'].type_ == uuid4().__class__  # UUID type
        assert fields['as_of'].type_ == date  # date type
        assert fields['total_value'].type_ == Decimal  # Decimal type
        assert fields['currency'].type_ == str  # str type
        assert fields['created_at'].type_ == datetime  # datetime type


class TestPortfolioValuationsIntegration:
    """Test portfolio valuations integration scenarios"""
    
    def test_empty_user_portfolio(self):
        """Test handling of user with no portfolio valuations"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []  # Empty result
        
        repository = PortfolioValuationEODRepository(mock_db)
        user_id = uuid4()
        
        # Test list
        valuations = repository.list_by_user(user_id)
        assert valuations == []
        
        # Test latest
        latest = repository.latest_by_user(user_id)
        assert latest is None
    
    def test_user_with_multiple_valuations(self):
        """Test handling of user with multiple portfolio valuations"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        
        # Mock multiple valuations
        mock_valuations = [
            MagicMock(as_of=date(2024, 1, 10)),
            MagicMock(as_of=date(2024, 1, 15)),
            MagicMock(as_of=date(2024, 1, 20)),
        ]
        mock_query.all.return_value = mock_valuations
        mock_query.first.return_value = mock_valuations[-1]  # Latest
        
        repository = PortfolioValuationEODRepository(mock_db)
        user_id = uuid4()
        
        # Test list
        valuations = repository.list_by_user(user_id)
        assert len(valuations) == 3
        
        # Test latest
        latest = repository.latest_by_user(user_id)
        assert latest == mock_valuations[-1]
        assert latest.as_of == date(2024, 1, 20)




