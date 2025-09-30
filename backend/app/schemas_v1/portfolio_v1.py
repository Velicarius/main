"""
Portfolio Analysis Schema v1
Зачем: Централизуем JSON Schema для анализа портфеля через LLM
"""

from typing import Dict, Any


def get_portfolio_schema_v1() -> Dict[str, Any]:
    """
    Возвращает JSON Schema для анализа портфеля v1
    Зачем: Обеспечиваем структурированный ответ от LLM с валидацией
    
    Returns:
        Dict[str, Any]: JSON Schema для валидации ответа LLM
    """
    return {
        "type": "object",
        "properties": {
            "overall_score": {
                "type": "number",
                "minimum": 0,
                "maximum": 100
            },
            "risk_level": {
                "type": "string",
                "enum": ["Conservative", "Balanced", "Aggressive"]
            },
            "summary": {
                "type": "string"
            },
            "expected_return": {
                "type": "object",
                "properties": {
                    "horizon": {
                        "type": "string",
                        "enum": ["1m", "3m", "6m", "1y"]
                    },
                    "annualized_pct_range": {
                        "type": "object",
                        "properties": {
                            "low": {"type": "number"},
                            "base": {"type": "number"},
                            "high": {"type": "number"}
                        },
                        "required": ["base"]
                    },
                    "rationale": {"type": "string"}
                },
                "required": ["horizon", "annualized_pct_range"]
            },
            "key_risks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "severity": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 5
                        },
                        "why": {"type": "string"},
                        "hedge": {"type": ["string", "null"]}
                    },
                    "required": ["name", "severity", "why"]
                }
            },
            "suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "reason": {"type": "string"},
                        "priority": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 3
                        }
                    },
                    "required": ["action", "reason"]
                }
            },
            "allocation_changes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string"},
                        "current_pct": {"type": ["number", "null"]},
                        "target_pct": {"type": "number"},
                        "note": {"type": ["string", "null"]}
                    },
                    "required": ["ticker", "target_pct"]
                }
            },
            "diversification": {
                "type": "object",
                "properties": {
                    "herfindahl": {"type": ["number", "null"]},
                    "sector_gaps": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            },
            "warnings": {
                "type": "array",
                "items": {"type": "string"}
            },
            "assumptions": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": [
            "overall_score",
            "risk_level", 
            "summary",
            "expected_return",
            "key_risks",
            "suggestions"
        ]
    }
