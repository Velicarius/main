"""CRUD operations for Strategy model"""

from sqlalchemy.orm import Session
from sqlalchemy import select, update
from uuid import UUID
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import date

from app.models.strategy import Strategy
from app.schemas.strategy import StrategyBase, StrategyIn, StrategyPatch


def get_by_user_id(db: Session, user_id: UUID) -> Optional[Strategy]:
    """Get strategy for a specific user or None if not found"""
    result = db.execute(select(Strategy).where(Strategy.user_id == user_id))
    return result.scalar_one_or_none()


def upsert_for_user(db: Session, user_id: UUID, strategy_data: StrategyBase) -> Strategy:
    """
    Upsert (insert or update) strategy for a user.
    Each user can have at most one strategy.
    """
    # First try to get existing strategy
    existing_strategy = get_by_user_id(db, user_id)
    
    # Prepare data for insertion/update
    strategy_dict = strategy_data.dict(exclude_unset=True)
    strategy_dict["user_id"] = user_id
    
    if existing_strategy:
        # Update existing strategy
        for key, value in strategy_dict.items():
            setattr(existing_strategy, key, value)
        db.commit()
        db.refresh(existing_strategy)
        return existing_strategy
    else:
        # Create new strategy
        new_strategy = Strategy(**strategy_dict)
        db.add(new_strategy)
        db.commit()
        db.refresh(new_strategy)
        return new_strategy


def partial_update_for_user(db: Session, user_id: UUID, patch_data: StrategyPatch) -> Optional[Strategy]:
    """
    Partially update strategy for a user.
    Returns None if no strategy exists for the user.
    """
    existing_strategy = get_by_user_id(db, user_id)
    if not existing_strategy:
        return None
    
    # Update only provided fields
    update_dict = patch_data.dict(exclude_unset=True, exclude_none=True)
    
    for key, value in update_dict.items():
        setattr(existing_strategy, key, value)
    
    db.commit()
    db.refresh(existing_strategy)
    return existing_strategy


def delete_for_user(db: Session, user_id: UUID) -> bool:
    """
    Delete strategy for a user.
    Returns True if deleted, False if not found.
    """
    existing_strategy = get_by_user_id(db, user_id)
    if not existing_strategy:
        return False
    
    db.delete(existing_strategy)
    db.commit()
    return True


def validate_allocation_sum(allocation: Optional[Dict[str, Any]]) -> bool:
    """
    Validate that asset allocation percentages sum to approximately 100%.
    Returns True if valid, False otherwise.
    """
    if not allocation:
        return True
    
    try:
        total = sum(float(val) for val in allocation.values() if isinstance(val, (int, float, str)))
        return 95.0 <= total <= 105.0  # Allow 5% tolerance
    except (ValueError, TypeError):
        return False


def get_all_templates() -> list:
    """
    Get predefined strategy templates for frontend use.
    These are static templates used for auto-filling.
    """
    return [
        {
            "key": "conservative",
            "name": "Conservative",
            "risk_level": "low",
            "expected_return": Decimal("0.05"),  # 5%
            "volatility": Decimal("0.08"),       # 8%
            "max_drawdown": Decimal("0.12"),     # 12%
            "allocation": {
                "equities": 40.0,
                "bonds": 50.0,
                "cash": 10.0
            }
        },
        {
            "key": "balanced", 
            "name": "Balanced",
            "risk_level": "medium",
            "expected_return": Decimal("0.075"), # 7.5%
            "volatility": Decimal("0.15"),       # 15%
            "max_drawdown": Decimal("0.20"),    # 20%
            "allocation": {
                "equities": 60.0,
                "bonds": 30.0,
                "cash": 10.0
            }
        },
        {
            "key": "aggressive",
            "name": "Aggressive", 
            "risk_level": "high",
            "expected_return": Decimal("0.10"),  # 10%
            "volatility": Decimal("0.25"),      # 25%
            "max_drawdown": Decimal("0.35"),    # 35%
            "allocation": {
                "equities": 80.0,
                "bonds": 15.0,
                "cash": 5.0
            }
        }
    ]


def compute_strategy_derived_fields(strategy: Strategy, current_portfolio_value: Optional[Decimal] = None) -> Dict[str, Any]:
    """
    Compute derived fields for strategy output.
    This mimics the frontend calculation logic.
    """
    result = {}
    
    if current_portfolio_value is None:
        current_portfolio_value = Decimal("0")
    
    # Progress to Goal
    if strategy.target_value and strategy.target_value > 0:
        result["progress_to_goal"] = float((current_portfolio_value / strategy.target_value) * 100)
    else:
        result["progress_to_goal"] = None
    
    # Target CAGR calculation
    if strategy.target_date and strategy.target_value and strategy.target_value > 0 and current_portfolio_value > 0:
        from datetime import datetime
        
        today = datetime.now().date()
        years_remaining = max((strategy.target_date - today).days / 365.25, 0.01)
        
        # Account for monthly contributions
        if strategy.monthly_contribution:
            contribution_growth = strategy.monthly_contribution * Decimal(str(12 * years_remaining))
            target_without_contribution = strategy.target_value - contribution_growth
        else:
            target_without_contribution = strategy.target_value
            
        if target_without_contribution > 0:
            result["target_cagr"] = float((target_without_contribution / current_portfolio_value) ** (1 / years_remaining) - 1)
        else:
            result["target_cagr"] = None
    else:
        result["target_cagr"] = None
    
    # Actual vs Target (simplified calculation)
    # In a real implementation, this would compare against historical performance
    if strategy.expected_return and current_portfolio_value > 0:
        # Simplified: assume user is meeting expectations for now
        result["actual_vs_target"] = "on_track"
    else:
        result["actual_vs_target"] = None
    
    return result


