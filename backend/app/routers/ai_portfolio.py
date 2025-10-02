from __future__ import annotations
import json
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.ai.openai_client import get_client, default_model
from app.ai.portfolio_assessor import build_snapshot, make_ai_inputs, result_json_schema
from app.routers.llm_proxy import LLMChatRequest, generate_with_ollama

router = APIRouter(prefix="/ai/portfolio", tags=["ai-portfolio"])

@router.post("/assess")
async def assess_portfolio(
    user_id: UUID,
    model: Optional[str] = Query(default=None, description="Model name, e.g. gpt-4o-mini or llama3.1:8b"),
    language: str = Query(default="ru"),
    db: Session = Depends(get_db),
):
    # 1) снимок портфеля
    snapshot = build_snapshot(db, user_id)

    # 2) промпт и JSON-схема
    inputs = make_ai_inputs(snapshot, language)
    schema = result_json_schema()
    
    # Определяем модель и провайдера
    if model and model.startswith(('llama', 'gemma', 'qwen', 'mistral', 'codellama')):
        # Используем Ollama для локальных моделей
        mdl = model
        provider = "ollama"
    else:
        # Используем OpenAI для облачных моделей
        mdl = model or default_model()
        provider = "openai"

    # 3) Вызов AI в зависимости от провайдера
    try:
        if provider == "ollama":
            # Используем Ollama
            request = LLMChatRequest(
                model=mdl,
                prompt=inputs["user"],
                system=inputs["system"],
                json_schema=schema["schema"],
                temperature=0.2,
                max_tokens=4000
            )
            ollama_response = await generate_with_ollama(request)
            data = json.loads(ollama_response["response"])
        else:
            # Используем OpenAI
            try:
                client = get_client()
            except RuntimeError as e:
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="AI disabled: set OPENAI_API_KEY in environment to enable."
                )
            
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
        
        return {
            "status": "ok",
            "model": mdl,
            "provider": provider,
            "snapshot": {
                "total_value": snapshot.total_value,
                "hhi": snapshot.hhi,
                "top_concentration_pct": snapshot.top_concentration_pct,
                "missing_prices": snapshot.missing_prices,
            },
            "ai": data,
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI call failed: {e}")











