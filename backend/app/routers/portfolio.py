from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional
import pandas as pd
from app.services.features import basic_portfolio_metrics
from app.services.ai import generate_insights

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

class Position(BaseModel):
    symbol: str
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    sector: Optional[str] = None
    currency: Optional[str] = None

class AnalyzeRequest(BaseModel):
    positions: List[Position]
    cash: float = 0.0
    base_currency: str = "USD"

@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    df = pd.DataFrame([p.model_dump() for p in req.positions])
    metrics = basic_portfolio_metrics(df, cash=req.cash, base_currency=req.base_currency)
    ai = generate_insights(metrics, df)
    return {"metrics": metrics, "ai_insights": ai}
