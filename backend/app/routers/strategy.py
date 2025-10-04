"""Strategy management API endpoints"""

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from decimal import Decimal
from typing import Union

from app.database import get_db
from app.models.strategy import Strategy
from app.models.position import Position
from app.crud.strategy import (
    get_by_user_id, 
    upsert_for_user, 
    partial_update_for_user,
    delete_for_user,
    validate_allocation_sum,
    compute_strategy_derived_fields,
    get_all_templates
)
try:
    from app.schemas.strategy import (
        StrategyIn, 
        StrategyOut, 
        StrategyPatch, 
        StrategyEmpty,
        StrategyTemplate
    )
except ImportError:
    # Fallback if schemas not found
    StrategyIn = dict
    StrategyOut = dict  
    StrategyPatch = dict
    StrategyEmpty = dict
    StrategyTemplate = dict

router = APIRouter(prefix="/strategy", tags=["strategy"])


def get_current_user_id(request: Request) -> UUID:
    """
    Extract current user ID from session.
    Returns user ID or raises HTTPException if not authenticated.
    """
    user_id_str = request.session.get("user_id")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        return UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")


async def get_current_portfolio_value(user_id: UUID, db: Session) -> Decimal:
    """
    Calculate current portfolio value for a user.
    Includes positions value + cash balance.
    """
    # Calculate positions value
    positions = db.execute(Position.__table__.select().where(Position.user_id == user_id)).fetchall()
    total_positions_value = Decimal("0")
    
    for position in positions:
        position_value = Decimal(str(position.quantity)) * Decimal(str(position.last if position.last else position.buy_price or 0))
        total_positions_value += position_value
    
    # Get user cash balance  
    from app.models.user import User
    user = db.execute(User.__table__.select().where(User.id == user_id)).first()
    cash_balance = Decimal(str(user.usd_balance)) if user else Decimal("0")
    
    return total_positions_value + cash_balance


@router.get("", response_model=Union[StrategyOut, StrategyEmpty])
def get_strategy(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get current user's strategy or empty response if none exists.
    
    Returns:
    - StrategyOut: If strategy exists with computed derived fields
    - StrategyEmpty: If no strategy found
    """
    try:
        user_id = get_current_user_id(request)
        strategy = get_by_user_id(db, user_id)
        
        if not strategy:
            return StrategyEmpty(message="No strategy found for user")
        
        # Get current portfolio value for derived calculations
        portfolio_value = 0  # Simplified for now - disable threading issue
        
        # Compute derived fields
        derived_fields = compute_strategy_derived_fields(strategy, Decimal(str(portfolio_value)))
        
        # Create response with derived fields
        strategy_dict = {
            "id": strategy.id,
            "user_id": strategy.user_id,
            "base_currency": strategy.base_currency,
            "target_value": strategy.target_value,
            "target_date": strategy.target_date,
            "risk_level": strategy.risk_level,
            "expected_return": strategy.expected_return,
            "volatility": strategy.volatility,
            "max_drawdown": strategy.max_drawdown,
            "monthly_contribution": strategy.monthly_contribution,
            "rebalancing_frequency": strategy.rebalancing_frequency,
            "allocation": strategy.allocation or {},
            "constraints": strategy.constraints or {},
            "created_at": int(strategy.created_at),
            "updated_at": int(strategy.updated_at),
            **derived_fields
        }
        
        return StrategyOut(**strategy_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("", response_model=StrategyOut)
def upsert_strategy(
    strategy_data: StrategyIn,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Create or update strategy for current user.
    Validates allocation sum and stores as complete strategy.
    
    Returns StrategyOut with computed derived fields.
    """
    try:
        user_id = get_current_user_id(request)
        
        # Validate allocation if provided
        if strategy_data.allocation:
            if not validate_allocation_sum(strategy_data.allocation):
                raise HTTPException(
                    status_code=400, 
                    detail="Asset allocation must sum to approximately 100%"
                )
        
        # Upsert strategy
        strategy = upsert_for_user(db, user_id, strategy_data)
        
        # Calculate derived fields and return
        portfolio_value = 0  # Simplified for now
        derived_fields = compute_strategy_derived_fields(strategy, Decimal(str(portfolio_value)))
        
        strategy_dict = {
            "id": strategy.id,
            "user_id": strategy.user_id,
            "base_currency": strategy.base_currency,
            "target_value": strategy.target_value,
            "target_date": strategy.target_date,
            "risk_level": strategy.risk_level,
            "expected_return": strategy.expected_return,
            "volatility": strategy.volatility,
            "max_drawdown": strategy.max_drawdown,
            "monthly_contribution": strategy.monthly_contribution,
            "rebalancing_frequency": strategy.rebalancing_frequency,
            "allocation": strategy.allocation or {},
            "constraints": strategy.constraints or {},
            "created_at": int(strategy.created_at),
            "updated_at": int(strategy.updated_at),
            **derived_fields
        }
        
        return StrategyOut(**strategy_dict)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.patch("", response_model=Union[StrategyOut, StrategyEmpty])
def partial_update_strategy(
    patch_data: StrategyPatch,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Partially update strategy for current user.
    Updates only provided fields, validates allocation if provided.
    
    Returns:
    - StrategyOut: If strategy existed and was updated
    - StrategyEmpty: If no strategy found to update
    """
    try:
        user_id = get_current_user_id(request)
        
        # Validate allocation if being updated
        if patch_data.allocation:
            if not validate_allocation_sum(patch_data.allocation):
                raise HTTPException(
                    status_code=400,
                    detail="Asset allocation must sum to approximately 100%"
                )
        
        # Partial update
        strategy = partial_update_for_user(db, user_id, patch_data)
        
        if not strategy:
            return StrategyEmpty(message="No strategy found to update")
        
        # Calculate derived fields and return
        portfolio_value = 0  # Simplified for now
        derived_fields = compute_strategy_derived_fields(strategy, Decimal(str(portfolio_value)))
        
        strategy_dict = {
            "id": strategy.id,
            "user_id": strategy.user_id,
            "base_currency": strategy.base_currency,
            "target_value": strategy.target_value,
            "target_date": strategy.target_date,
            "risk_level": strategy.risk_level,
            "expected_return": strategy.expected_return,
            "volatility": strategy.volatility,
            "max_drawdown": strategy.max_drawdown,
            "monthly_contribution": strategy.monthly_contribution,
            "rebalancing_frequency": strategy.rebalancing_frequency,
            "allocation": strategy.allocation or {},
            "constraints": strategy.constraints or {},
            "created_at": int(strategy.created_at),
            "updated_at": int(strategy.updated_at),
            **derived_fields
        }
        
        return StrategyOut(**strategy_dict)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("")
def delete_strategy(request: Request, db: Session = Depends(get_db)):
    """
    Delete strategy for current user.
    
    Returns success message or 404 if no strategy found.
    """
    try:
        user_id = get_current_user_id(request)
        
        deleted = delete_for_user(db, user_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="No strategy found to delete")
        
        return {"message": "Strategy deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/templates", response_model=list[StrategyTemplate])
def get_strategy_templates():
    """
    Get predefined strategy templates for auto-filling.
    These are static templates used by the frontend.
    """
    return get_all_templates()


@router.get("/validate-allocation")
def validate_allocation_only(
    request: Request,
    allocation: dict = None
):
    """
    Validate asset allocation percentages without storing.
    Useful for client-side validation.
    """
    
    if not allocation:
        raise HTTPException(status_code=400, detail="Allocation data required")
    
    try:
        is_valid = validate_allocation_sum(allocation)
        
        if is_valid:
            total = sum(float(val) for val in allocation.values() if isinstance(val, (int, float, str)))
            return {
                "valid": True,
                "total_percentage": round(total, 2),
                "message": f"Valid allocation totaling {total:.1f}%"
            }
        else:
            total = sum(float(val) for val in allocation.values() if isinstance(val, (int, float, str)))
            return {
                "valid": False,
                "total_percentage": round(total, 2),
                "message": f"Invalid allocation totaling {total:.1f}%. Must sum to ~100%"
            }
            
    except (ValueError, TypeError):
        return {
            "valid": False,
            "total_percentage": None,
            "message": "Invalid allocation data format"
        }
