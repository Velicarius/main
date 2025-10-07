"""
News summary schemas for LLM-generated ticker briefs
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Scenario(BaseModel):
    """Investment scenario model"""
    name: str = Field(..., description="Scenario name (Base/Bull/Bear)")
    horizon: str = Field(..., description="Time horizon (e.g., '3-6m')")
    narrative: str = Field(..., description="Scenario narrative/description")
    watch_items: List[str] = Field(default_factory=list, description="Key items to watch")
    confidence: int = Field(..., ge=0, le=100, description="Confidence level 0-100")


class Posture(BaseModel):
    """Non-advisory investment posture"""
    label: str = Field(..., description="Posture label (Accumulate/Hold/Avoid)")
    rationale: str = Field(..., description="Reasoning behind posture")
    risk_level: str = Field(..., description="Risk level (Low/Medium/High)")
    time_horizon: str = Field(..., description="Time horizon (e.g., '1-3m')")


class Fact(BaseModel):
    """Extracted fact with source attribution"""
    text: str = Field(..., description="Fact text (number/date/event)")
    source_id: str = Field(..., description="Reference to source article ID")


class Source(BaseModel):
    """News source reference"""
    id: str = Field(..., description="Source article ID")
    domain: str = Field(..., description="Source domain/publisher")
    published_at: str = Field(..., description="Publication timestamp (ISO format)")


class NewsSummary(BaseModel):
    """LLM-generated structured brief for a ticker"""
    ticker: str = Field(..., description="Stock ticker symbol")
    window: str = Field(..., description="Time window (e.g., '24h', '72h')")
    prospects: List[str] = Field(
        default_factory=list,
        description="Positive prospects identified"
    )
    opportunities: List[str] = Field(
        default_factory=list,
        description="Growth opportunities identified"
    )
    risks: List[str] = Field(
        default_factory=list,
        description="Risks and challenges identified"
    )
    scenarios: List[Scenario] = Field(
        default_factory=list,
        description="Base/Bull/Bear scenarios"
    )
    posture: Posture = Field(..., description="Non-advisory posture assessment")
    confidence: int = Field(
        ...,
        ge=0,
        le=100,
        description="Overall confidence in analysis (0-100)"
    )
    facts: List[Fact] = Field(
        default_factory=list,
        description="Extracted verifiable facts"
    )
    sources: List[Source] = Field(
        default_factory=list,
        description="Source articles used"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "TSLA",
                "window": "24h",
                "prospects": [
                    "Cheaper Model Y Standard can expand addressable demand",
                    "Higher mix of entry trims may support volume stabilization"
                ],
                "opportunities": [
                    "Cross-selling FSD to larger installed base",
                    "Energy/storage segment growth"
                ],
                "risks": [
                    "Price cuts compress automotive gross margin",
                    "Competitive response from legacy and Chinese OEMs"
                ],
                "scenarios": [
                    {
                        "name": "Base",
                        "horizon": "3-6m",
                        "narrative": "Volume improves on entry models, but margin pressure persists",
                        "watch_items": ["unit deliveries", "gross margin ex-credits"],
                        "confidence": 68
                    }
                ],
                "posture": {
                    "label": "Hold/Neutral",
                    "rationale": "Near-term demand boost vs. margin pressure",
                    "risk_level": "Medium",
                    "time_horizon": "1-3m"
                },
                "confidence": 64,
                "facts": [
                    {
                        "text": "New cheaper trims for Model Y and Model 3 announced",
                        "source_id": "s1"
                    }
                ],
                "sources": [
                    {
                        "id": "s1",
                        "domain": "finnhub.io",
                        "published_at": "2025-10-07T20:02:00Z"
                    }
                ]
            }
        }


class NewsSummaryRequest(BaseModel):
    """Request for news summary generation"""
    ticker: str = Field(..., description="Stock ticker symbol")
    window_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Time window in hours (1-168)"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Max articles to analyze (1-50)"
    )
    portfolio_hint: Optional[str] = Field(
        None,
        description="Optional portfolio context for analysis"
    )
    model: Optional[str] = Field(
        default=None,
        description="AI model to use (e.g., 'llama3.1:8b', 'gpt-4o-mini')"
    )
    provider: Optional[str] = Field(
        default=None,
        description="AI provider ('ollama' or 'openai')"
    )


class NewsSummaryResponse(BaseModel):
    """Response from news summary endpoint"""
    summary: NewsSummary
    cached: bool = Field(False, description="Whether result was cached")
    latency_ms: int = Field(..., description="Generation latency in milliseconds")
