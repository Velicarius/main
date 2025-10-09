"""
Pydantic schemas for news admin endpoints.
"""

from pydantic import BaseModel
from typing import Dict, Any, List


class ToggleShadowRequest(BaseModel):
    """Request to toggle provider shadow mode."""
    provider: str
    live: bool


class NewsStatusResponse(BaseModel):
    """Response for news system status."""
    planner: Dict[str, Any]
    fetch: Dict[str, Any]
    cache: Dict[str, Any]
    flags: Dict[str, Any]

