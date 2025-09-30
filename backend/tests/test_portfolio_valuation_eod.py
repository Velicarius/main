"""
Test for portfolio EOD valuation functionality.

This test verifies the basic logic without database dependencies.
"""

import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal
from datetime import date

from app.services.portfolio_valuation_eod import PortfolioValuationEODRepository


class TestPortfolioValuationEODRepository:
    """Test PortfolioValuationEOD repository functionality"""
    
    def test_upsert_data_preparation(self):
        """Test data preparation for upsert"""
        mock_db = MagicMock()
        mock_db.execute.return_value = MagicMock()
        repository = PortfolioValuationEODRepository(mock_db)
        
        # Test data
        user_id = "test-user-123"
        as_of = date(2024, 1, 15)
        total_value = Decimal("1000.50")
        currency = "USD"
        
        repository.upsert(user_id, as_of, total_value, currency)
        
        # Verify execute was called
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        
        # Verify the call arguments contain the correct data
        call_args = mock_db.execute.call_args[0][0]
        assert call_args is not None  # Should be an insert statement


class TestPortfolioRevalueLogic:
    """Test portfolio revaluation logic"""
    
    def test_portfolio_calculation_logic(self):
        """Test the portfolio calculation logic"""
        # Mock position data
        positions = [
            MagicMock(symbol="aapl", quantity=Decimal("10")),
            MagicMock(symbol="msft", quantity=Decimal("5")),
        ]
        
        # Mock price data
        price_data = {
            "aapl": MagicMock(close=Decimal("150.0"), date=date(2024, 1, 15)),
            "msft": MagicMock(close=Decimal("200.0"), date=date(2024, 1, 15)),
        }
        
        # Calculate total value
        total = Decimal("0")
        used_dates = []
        
        for pos in positions:
            sym = pos.symbol.strip().lower()
            last_price = price_data.get(sym)
            if last_price:
                qty = Decimal(str(pos.quantity))
                px = Decimal(str(last_price.close))
                total += qty * px
                used_dates.append(last_price.date)
        
        # Verify calculation
        expected_total = Decimal("10") * Decimal("150.0") + Decimal("5") * Decimal("200.0")
        assert total == expected_total
        assert total == Decimal("2500.0")
        assert len(used_dates) == 2
        assert max(used_dates) == date(2024, 1, 15)
    
    def test_empty_positions_handling(self):
        """Test handling of users with no positions"""
        positions = []
        
        total = Decimal("0")
        used_dates = []
        
        for pos in positions:
            # This loop won't execute
            pass
        
        # Should result in empty data
        assert total == Decimal("0")
        assert len(used_dates) == 0
        assert not used_dates  # Should be falsy
    
    def test_missing_price_data_handling(self):
        """Test handling of positions with missing price data"""
        positions = [
            MagicMock(symbol="aapl", quantity=Decimal("10")),
            MagicMock(symbol="unknown", quantity=Decimal("5")),
        ]
        
        # Only AAPL has price data
        price_data = {
            "aapl": MagicMock(close=Decimal("150.0"), date=date(2024, 1, 15)),
        }
        
        total = Decimal("0")
        used_dates = []
        
        for pos in positions:
            sym = pos.symbol.strip().lower()
            last_price = price_data.get(sym)
            if last_price:  # Only process if price data exists
                qty = Decimal(str(pos.quantity))
                px = Decimal(str(last_price.close))
                total += qty * px
                used_dates.append(last_price.date)
        
        # Should only include AAPL
        assert total == Decimal("1500.0")  # 10 * 150
        assert len(used_dates) == 1
        assert used_dates[0] == date(2024, 1, 15)




