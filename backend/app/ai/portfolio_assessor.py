from __future__ import annotations
from dataclasses import dataclass, asdict
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.position import Position
from app.services.price_eod import PriceEODRepository

@dataclass
class PositionSnapshot:
    symbol: str
    qty: float
    buy_price: Optional[float]
    close: Optional[float]
    value: float
    pl_abs: Optional[float]
    pl_pct: Optional[float]
    weight_pct: float
    as_of: Optional[str]

@dataclass
class PortfolioSnapshot:
    user_id: str
    total_value: float
    positions: List[PositionSnapshot]
    hhi: float
    top_concentration_pct: float
    missing_prices: List[str]
    since_buy_cost: float
    since_buy_pl_abs: float
    since_buy_pl_pct: Optional[float]

def _to_float(x) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except Exception:
        return None

def build_snapshot(db: Session, user_id: UUID) -> PortfolioSnapshot:
    price_repo = PriceEODRepository(db)
    positions = (
        db.query(Position)
        .filter(Position.user_id == user_id)
        .order_by(Position.symbol.asc())
        .all()
    )

    total = 0.0
    missing: List[str] = []
    tmp: List[Dict[str, Any]] = []

    cost_sum = 0.0  # сумма себестоимости по позициям, где buy_price есть
    value_sum_for_cost = 0.0  # сумма текущих стоимостей только по тем, где можно посчитать P/L

    for p in positions:
        sym = (p.symbol or "").strip().lower()
        last = price_repo.get_latest_price(sym)
        close = _to_float(getattr(last, "close", None))
        as_of = getattr(last, "date", None)
        qty = float(p.quantity)
        buy = _to_float(p.buy_price)

        if close is None:
            missing.append(sym)
            value = 0.0
        else:
            value = qty * close
            total += value

        # Use market price as buy price if buy_price is null (for onboarding positions)
        effective_buy = buy if buy is not None else close
        pl_abs = (value - (qty * effective_buy)) if (effective_buy is not None) else None
        pl_pct = ((pl_abs / (qty * effective_buy)) * 100.0) if (pl_abs is not None and effective_buy and qty > 0) else None

        if effective_buy is not None and close is not None:
            cost_sum += qty * effective_buy
            value_sum_for_cost += value

        tmp.append(
            dict(
                symbol=sym,
                qty=qty,
                buy=effective_buy,  # Use effective buy price
                close=close,
                value=value,
                pl_abs=pl_abs,
                pl_pct=pl_pct,
                as_of=str(as_of) if as_of else None,
            )
        )

    snaps: List[PositionSnapshot] = []
    weights: List[float] = []
    for r in tmp:
        w = (r["value"] / total * 100.0) if total > 0 else 0.0
        weights.append(w / 100.0)
        snaps.append(
            PositionSnapshot(
                symbol=r["symbol"],
                qty=r["qty"],
                buy_price=r["buy"],
                close=r["close"],
                value=r["value"],
                pl_abs=r["pl_abs"],
                pl_pct=r["pl_pct"],
                weight_pct=w,
                as_of=r["as_of"],
            )
        )

    hhi = sum(w ** 2 for w in weights)  # индекс Херфиндаля-Хиршмана
    top_concentration = sum(sorted((s.weight_pct for s in snaps), reverse=True)[:3])

    since_buy_pl_abs = (value_sum_for_cost - cost_sum) if cost_sum > 0 else 0.0
    since_buy_pl_pct = (since_buy_pl_abs / cost_sum * 100.0) if cost_sum > 0 else None

    return PortfolioSnapshot(
        user_id=str(user_id),
        total_value=float(total),
        positions=snaps,
        hhi=float(hhi),
        top_concentration_pct=float(top_concentration),
        missing_prices=missing,
        since_buy_cost=float(cost_sum),
        since_buy_pl_abs=float(since_buy_pl_abs),
        since_buy_pl_pct=float(since_buy_pl_pct) if since_buy_pl_pct is not None else None,
    )

def make_ai_inputs(snapshot: PortfolioSnapshot, language: str = "ru") -> Dict[str, Any]:
    """
    Даём модели короткие, профессиональные инструкции и контекст портфеля.
    Просим компактные инсайты и структуру по схеме ниже.
    """
    system = (
        "Ты — опытный портфельный аналитик с глубоким пониманием риск-менеджмента и диверсификации.\n"
        "Говори кратко и профессионально, используй точные финансовые термины.\n"
        "Избегай длинных абзацев; выводи тезисно и структурно.\n"
        "Не давай индивидуальных инвестрекомендаций; твой вывод — образовательный и общий.\n"
        "Цифры округляй до 1 знака после запятой, валюту не дублируй, если она указана в KPI.\n"
        "Анализируй риски, диверсификацию, концентрацию и производительность портфеля."
    )
    user_md = (
        f"Язык ответа: {language}.\n"
        "Сформируй краткие, интересные инсайты (one-liners) и структурируй оценку блоками.\n"
        "Проанализируй риски, диверсификацию, концентрацию активов и производительность.\n"
        "Контекст в JSON ниже."
    )
    
    # Дополнительные метрики для анализа
    positions = snapshot.positions
    total_positions = len(positions)
    profitable_positions = len([p for p in positions if p.pl_pct and p.pl_pct > 0])
    loss_positions = len([p for p in positions if p.pl_pct and p.pl_pct < 0])
    
    # Анализ концентрации
    top_5_weight = sum(sorted([p.weight_pct for p in positions], reverse=True)[:5])
    single_stock_max = max([p.weight_pct for p in positions]) if positions else 0
    
    # Анализ производительности
    avg_pl_pct = sum([p.pl_pct for p in positions if p.pl_pct is not None]) / len([p for p in positions if p.pl_pct is not None]) if any(p.pl_pct is not None for p in positions) else None
    
    context = {
        "portfolio": {
            "kpi": {
                "total_value_usd": snapshot.total_value,
                "hhi": snapshot.hhi,
                "top3_pct": snapshot.top_concentration_pct,
                "top5_pct": top_5_weight,
                "single_stock_max_pct": single_stock_max,
                "since_buy_cost": snapshot.since_buy_cost,
                "since_buy_pl_abs": snapshot.since_buy_pl_abs,
                "since_buy_pl_pct": snapshot.since_buy_pl_pct,
                "avg_pl_pct": avg_pl_pct,
            },
            "composition": {
                "total_positions": total_positions,
                "profitable_positions": profitable_positions,
                "loss_positions": loss_positions,
                "win_rate_pct": (profitable_positions / total_positions * 100) if total_positions > 0 else 0,
            },
            "missing_prices": snapshot.missing_prices,
            "positions": [asdict(p) for p in snapshot.positions],
        }
    }
    return {"system": system, "user": user_md, "context": context}

def result_json_schema() -> Dict[str, Any]:
    """
    Расширенная схема: короткая «шапка», категории с оценками, инсайты, риски с важностью,
    перфоманс-комментарий и план действий. Базовые поля остались совместимыми.
    """
    return {
        "name": "portfolio_assessment_v3",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "rating": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "score": {"type": "number", "minimum": 0, "maximum": 10},
                        "label": {"type": "string", "enum": ["conservative", "balanced", "aggressive", "unknown"]},
                        "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                    },
                    "required": ["score", "label", "risk_level"]
                },
                "overview": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "headline": {"type": "string", "maxLength": 120},
                        "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
                        "key_strengths": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
                        "key_concerns": {"type": "array", "items": {"type": "string"}, "maxItems": 3}
                    },
                    "required": ["headline"]
                },
                "categories": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "name": {"type": "string"},
                            "score": {"type": "number", "minimum": 0, "maximum": 10},
                            "note": {"type": "string"},
                            "trend": {"type": "string", "enum": ["improving", "stable", "declining", "unknown"]}
                        },
                        "required": ["name", "score"]
                    }
                },
                "insights": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 8
                },
                "risks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "item": {"type": "string"},
                            "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                            "mitigation": {"type": "string"},
                            "impact": {"type": "string", "enum": ["low", "medium", "high"]}
                        },
                        "required": ["item", "severity"]
                    }
                },
                "performance": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "since_buy_pl_pct": {"type": ["number", "null"]},
                        "comment": {"type": "string"},
                        "win_rate_pct": {"type": ["number", "null"]},
                        "avg_position_return": {"type": ["number", "null"]},
                        "volatility_assessment": {"type": "string", "enum": ["low", "medium", "high"]}
                    },
                    "required": ["since_buy_pl_pct"]
                },
                "diversification": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "score": {"type": "number", "minimum": 0, "maximum": 10},
                        "concentration_risk": {"type": "string", "enum": ["low", "medium", "high"]},
                        "sector_diversity": {"type": "string", "enum": ["excellent", "good", "fair", "poor"]},
                        "recommendations": {"type": "array", "items": {"type": "string"}, "maxItems": 3}
                    },
                    "required": ["score", "concentration_risk"]
                },
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "title": {"type": "string"},
                            "rationale": {"type": "string"},
                            "expected_impact": {"type": "string"},
                            "priority": {"type": "integer", "minimum": 1, "maximum": 5},
                            "timeframe": {"type": "string", "enum": ["immediate", "short_term", "medium_term", "long_term"]}
                        },
                        "required": ["title", "rationale", "priority"]
                    }
                },
                "summary_markdown": {"type": "string"}  # оставляем для совместимости/резюме
            },
            "required": ["rating", "overview", "summary_markdown"]
        },
        "strict": True
    }



