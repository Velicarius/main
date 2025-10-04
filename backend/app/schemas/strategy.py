from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, Literal
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID

# Reusable types for enums
RiskLevel = Literal["low", "medium", "high"]
RebalancingFrequency = Literal["none", "quarterly", "semiannual", "yearly"]

class StrategyBase(BaseModel):
    """Base strategy schema with all optional fields"""
    base_currency: Optional[str] = Field(default="USD", max_length=3)
    target_value: Optional[Decimal] = Field(None, gt=0, description="Target portfolio value")
    target_date: Optional[date] = Field(None, description="Target date for goal")
    
    # Risk and return parameters
    risk_level: Optional[RiskLevel] = Field(None, description="Risk level independent of other parameters")
    expected_return: Optional[Decimal] = Field(None, ge=0, le=1, description="Expected annual return (0.075 = 7.5%)")
    volatility: Optional[Decimal] = Field(None, ge=0, le=1, description="Annual volatility (0.15 = 15%)")
    max_drawdown: Optional[Decimal] = Field(None, ge=0, le=1, description="Maximum expected drawdown (0.20 = 20%)")
    
    # Contribution and rebalancing
    monthly_contribution: Optional[Decimal] = Field(None, ge=0, description="Monthly contribution amount")
    rebalancing_frequency: RebalancingFrequency = Field(default="none", description="Rebalancing frequency")
    
    # Complex fields
    allocation: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Asset allocation as percentage values")
    constraints: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Investment constraints and rules")

    @validator('allocation')
    def validate_allocation_sum(cls, v):
        """Validate that allocation percentages sum to approximately 100%"""
        if not v:
            return v
        
        # Convert all values to numbers and sum them
        total = sum(float(val) for val in v.values() if isinstance(val, (int, float, str)))
        
        # Allow 5% tolerance for rounding errors
        if not (95.0 <= total <= 105.0):
            raise ValueError(f"Asset allocation must sum to ~100%, got {total}%")
        
        return v

    @validator('target_date')
    def validate_target_date(cls, v):
        """Validate that target date is in the future"""
        if v and v <= date.today():
            raise ValueError("Target date must be in the future")
        return v

    class Config:
        json_encoders = {
            Decimal: str,  # Convert Decimal to string for JSON serialization
            datetime: lambda v: v.isoformat(),
        }

class StrategyIn(StrategyBase):
    """Schema for strategy input (PUT/PATCH requests)"""
    pass

class StrategyOut(StrategyBase):
    """Schema for strategy output with computed fields"""
    id: UUID
    user_id: UUID
    created_at: int  # Unix timestamp
    updated_at: int  # Unix timestamp
    
    # Computed fields (added by API layer)
    progress_to_goal: Optional[float] = Field(None, description="Progress towards goal as percentage")
    target_cagr: Optional[float] = Field(None, description="Required CAGR to reach target")
    actual_vs_target: Optional[Literal["ahead", "on_track", "behind"]] = Field(
        None, description="Performance indicator compared to target"
    )

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
        }

class StrategyPatch(BaseModel):
    """Schema for partial updates (PATCH requests)"""
    base_currency: Optional[str] = None
    target_value: Optional[Decimal] = None
    target_date: Optional[date] = None
    risk_level: Optional[RiskLevel] = None
    expected_return: Optional[Decimal] = None
    volatility: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    monthly_contribution: Optional[Decimal] = None
    rebalancing_frequency: Optional[RebalancingFrequency] = None
    allocation: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, Any]] = None

    @validator('allocation')
    def validate_allocation_sum(cls, v):
        """Validate allocation sum if provided"""
        if v is not None:
            # Validate only if allocation is completely replaced
            total = sum(float(val) for val in v.values() if isinstance(val, (int, float, str)))
            if not (95.0 <= total <= 105.0):
                raise ValueError(f"Asset allocation must sum to ~100%, got {total}%")
        return v

    @validator('target_date')
    def validate_target_date(cls, v):
        """Validate target date if provided"""
        if v and v <= date.today():
            raise ValueError("Target date must be in the future")
        return v

    class Config:
        json_encoders = {
            Decimal: str,
        }

# Utility schemas for frontend compatibility
class StrategyTemplate(BaseModel):
    """Template schema for quick setup"""
    key: Literal["conservative", "balanced", "aggressive"] = Field(description="Template identifier")
    name: str = Field(description="Human-readable name")
    risk_level: RiskLevel = Field(description="Default risk level")
    expected_return: Decimal = Field(description="Default expected return")
    volatility: Decimal = Field(description="Default volatility")
    max_drawdown: Decimal = Field(description="Default max drawdown")
    allocation: Dict[str, Any] = Field(description="Default allocation")

# Response schemas
class StrategyEmpty(BaseModel):
    """Empty strategy response when user has no strategy"""
    message: str = Field(default="No strategy found for user")

class StrategyValidationError(BaseModel):
    """Validation error details"""
    field: str = Field(description="Field that failed validation")
    message: str = Field(description="Validation error message")
    value: Any = Field(description="Invalid value that was provided")


