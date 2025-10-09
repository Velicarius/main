"""
Portfolio Analytics Service
Calculates portfolio metrics: returns, allocation, risk metrics
"""
import logging
from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_

from app.models.position import Position, AssetClass
from app.models.price_eod import PriceEOD
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.services.price_eod import PriceEODRepository
from app.pricing.crypto.service import get_crypto_price_service

logger = logging.getLogger(__name__)


class PortfolioAnalytics:
    """
    Service for calculating portfolio analytics

    Features:
    - Calculate total portfolio value
    - Calculate returns (absolute and percentage)
    - Analyze allocation by asset class
    - Identify top holdings
    - Generate portfolio snapshots
    """

    def __init__(self, db: Session):
        self.db = db
        self.price_repo = PriceEODRepository(db)

    async def calculate_portfolio_summary(self, user_id: UUID) -> Dict:
        """
        Calculate comprehensive portfolio summary

        Returns:
            {
                'total_value': Decimal,
                'total_invested': Decimal,
                'total_return_pct': float,
                'positions_count': int,
                'allocation': {'EQUITY': 60.0, 'CRYPTO': 40.0},
                'top_holdings': [...]
            }
        """
        # Get all positions for user
        positions = self.db.execute(
            select(Position).where(Position.user_id == user_id)
        ).scalars().all()

        if not positions:
            return {
                'total_value': Decimal('0'),
                'total_invested': Decimal('0'),
                'total_return_pct': 0.0,
                'positions_count': 0,
                'allocation': {},
                'top_holdings': []
            }

        # Calculate values for each position
        position_values = []
        total_value = Decimal('0')
        total_invested = Decimal('0')
        allocation_by_class = {}

        for pos in positions:
            # Get current price
            current_price = await self._get_current_price(pos)

            if current_price is None:
                logger.warning(f"No price found for {pos.symbol}, skipping from summary")
                continue

            # Calculate position value
            position_value = Decimal(str(pos.quantity)) * current_price
            invested_value = Decimal(str(pos.quantity)) * (Decimal(str(pos.buy_price)) if pos.buy_price else current_price)

            position_values.append({
                'symbol': pos.symbol,
                'quantity': pos.quantity,
                'current_price': current_price,
                'position_value': position_value,
                'invested_value': invested_value,
                'asset_class': pos.asset_class.value
            })

            # Aggregate totals
            total_value += position_value
            total_invested += invested_value

            # Track allocation by asset class
            asset_class = pos.asset_class.value
            allocation_by_class[asset_class] = allocation_by_class.get(asset_class, Decimal('0')) + position_value

        # Calculate return percentage
        total_return_pct = 0.0
        if total_invested > 0:
            total_return_pct = float((total_value - total_invested) / total_invested * 100)

        # Calculate allocation percentages
        allocation = {}
        if total_value > 0:
            for asset_class, value in allocation_by_class.items():
                allocation[asset_class] = round(float(value / total_value * 100), 2)

        # Get top 5 holdings by value
        top_holdings = sorted(position_values, key=lambda x: x['position_value'], reverse=True)[:5]
        top_holdings_formatted = [
            {
                'symbol': h['symbol'],
                'value': float(h['position_value']),
                'pct_of_portfolio': round(float(h['position_value'] / total_value * 100), 2) if total_value > 0 else 0.0
            }
            for h in top_holdings
        ]

        return {
            'total_value': total_value,
            'total_invested': total_invested,
            'total_return_pct': round(total_return_pct, 2),
            'positions_count': len(position_values),
            'allocation': allocation,
            'top_holdings': top_holdings_formatted
        }

    async def create_portfolio_snapshot(self, user_id: UUID, as_of_date: Optional[date] = None) -> PortfolioSnapshot:
        """
        Create a portfolio snapshot for a specific date

        Args:
            user_id: User ID
            as_of_date: Date for snapshot (defaults to today)

        Returns:
            Created PortfolioSnapshot object
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Calculate portfolio summary
        summary = await self.calculate_portfolio_summary(user_id)

        # Check if snapshot already exists for this date
        existing = self.db.execute(
            select(PortfolioSnapshot).where(
                and_(
                    PortfolioSnapshot.user_id == user_id,
                    PortfolioSnapshot.as_of == as_of_date
                )
            )
        ).scalar_one_or_none()

        if existing:
            # Update existing snapshot
            existing.total_value = summary['total_value']
            existing.total_invested = summary['total_invested']
            existing.total_return_pct = Decimal(str(summary['total_return_pct']))
            existing.positions_count = summary['positions_count']
            existing.allocation = summary['allocation']
            existing.top_holdings = summary['top_holdings']
            existing.updated_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(existing)

            logger.info(f"Updated portfolio snapshot for user {user_id} on {as_of_date}")
            return existing
        else:
            # Create new snapshot
            snapshot = PortfolioSnapshot(
                user_id=user_id,
                as_of=as_of_date,
                total_value=summary['total_value'],
                total_invested=summary['total_invested'],
                total_return_pct=Decimal(str(summary['total_return_pct'])),
                positions_count=summary['positions_count'],
                allocation=summary['allocation'],
                top_holdings=summary['top_holdings'],
                risk_metrics={}  # TODO: Calculate risk metrics (volatility, sharpe, etc)
            )

            self.db.add(snapshot)
            self.db.commit()
            self.db.refresh(snapshot)

            logger.info(f"Created portfolio snapshot for user {user_id} on {as_of_date}")
            return snapshot

    async def _get_current_price(self, position: Position) -> Optional[Decimal]:
        """
        Get current price for a position based on asset class

        Args:
            position: Position object

        Returns:
            Current price as Decimal or None if not available
        """
        if position.asset_class == AssetClass.CRYPTO:
            # Get crypto price from service
            try:
                crypto_service = get_crypto_price_service()
                crypto_price = await crypto_service.get_price(position.symbol)

                if crypto_price:
                    return crypto_price.price_usd
            except Exception as e:
                logger.error(f"Error getting crypto price for {position.symbol}: {e}")
                return None
        else:
            # Get stock price from EOD table
            symbols_to_try = [
                position.symbol,
                position.symbol.upper(),
                position.symbol.lower(),
            ]

            for symbol in symbols_to_try:
                latest = self.price_repo.latest_by_symbol(symbol)
                if latest:
                    return latest.close

            logger.warning(f"No EOD price found for {position.symbol}")
            return None
