from __future__ import annotations
import json
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.ai.openai_client import get_client, default_model
from app.ai.portfolio_assessor import build_snapshot, make_ai_inputs, result_json_schema

router = APIRouter(prefix="/ai/portfolio", tags=["ai-portfolio"])

@router.post("/assess")
def assess_portfolio(
    user_id: UUID,
    model: Optional[str] = Query(default=None, description="OpenAI model, e.g. gpt-4o-mini"),
    language: str = Query(default="ru"),
    db: Session = Depends(get_db),
):
    # 1) снимок портфеля
    snapshot = build_snapshot(db, user_id)

    # Если нет ключа — сделаем мягкий отказ с подсказкой
    try:
        client = get_client()
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="AI disabled: set OPENAI_API_KEY in environment to enable."
        )

    # 2) промпт и JSON-схема
    inputs = make_ai_inputs(snapshot, language)
    schema = result_json_schema()
    mdl = model or default_model()

    # 3) Вызов Responses API со структурированным выводом
    try:
        resp = client.responses.create(
            model=mdl,
            input=[
                {"role":"system","content": inputs["system"]},
                {"role":"user","content": inputs["user"]},
                {"role":"developer","content": json.dumps(inputs["context"])},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema["name"],
                    "schema": schema["schema"],
                    "strict": schema["strict"],
                }
            }
        )
        payload = resp.output_text  # JSON-строка согласно schema
        data = json.loads(payload)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI call failed: {e}")

    return {
        "status": "ok",
        "model": mdl,
        "snapshot": {
            "total_value": snapshot.total_value,
            "hhi": snapshot.hhi,
            "top_concentration_pct": snapshot.top_concentration_pct,
            "missing_prices": snapshot.missing_prices,
        },
        "ai": data,
    }




