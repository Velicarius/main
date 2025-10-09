"""
Система кэширования с fingerprinting для оптимизации LLM вызовов
Использует SHA-256 отпечатки для детерминированных ключей кэша
"""

import json
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

# === Конфигурация версионности ===

PROMPT_VERSION = "2025-10-02"  # Ручное обновление при изменении промпта
SCHEMA_VERSION = "insights"    # Версия схемы данных

# === Структуры для fingerprinting ===

@dataclass 
class InsightsFingerprintData:
    """Данные для создания отпечатка LLM запроса"""
    schema: str = SCHEMA_VERSION
    prompt_version: str = PROMPT_VERSION  
    model: str = "llama-3.1-8b"
    horizon_months: int = 12
    risk_profile: str = "balanced"
    locale: str = "en"
    
    # Детерминированные позиции (отсортированные)
    positions: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.positions is None:
            self.positions = []

class CacheFingerprintService:
    """Сервис для создания и отображения отпечатков кэша"""
    
    @staticmethod
    def create_insights_fingerprint(
        positions: List[Dict[str, Any]],
        horizon_months: int = 12,
        risk_profile: str = "balanced", 
后locale: str = "en",
        model: str = "llama-3.1-8b"
    ) -> str:
        """
        Создает SHA-256 отпечаток для LLM запроса
        
        Args:
            positions: Список позиций с нормализованными данными
            horizon_months: Временной горизонт в месяцах
            risk_profile: Профиль риска (conservative/balanced/aggressive)
            locale: Язык интерфейса
            model: Модель LLM
            
        Returns:
            base64-encoded SHA-256 хеш отпечатка
        """
        
        # Нормализуем позиции
        normalized_positions = CacheFingerprintService._normalize_positions(positions)
        
        # Создаем структуру для хеширования
        fingerprdata = InsightsFingerprintData(
            positions=normalized_positions,
            horizon_months=horizon_months,
            risk_profile=risk_profile,
            locale=locale,
            model=model
        )
        
        # Каноническое представление JSON
        canonical_json = CacheFingerprintService._to_canonical_json(fingerprdata)
        
        # Хешируем
        fingerprint_hash = hashlib.sha256(canonical_json.encode('utf-8')).digest()
        
        # Возвращаем base64 для использования в ключах кэша
        import base64
        return base64.urlsafe_b64encode(fingerprint_hash).decode('ascii').rstrip('=')
    
    @staticmethod
    def create_position_mini_fingerprint(
        symbol: str,
        position_data: Dict[str, Any],
        common_params: Dict[str, Any]
    ) -> str:
        """
        Создает мини-отпечаток для отдельной позиции
        
        Args:
            symbol: Символ позиции
            position_data: Данные позиции (вес, риски, прогнозы)
            common_params: Общие параметры (horizon_months, risk_profile, locale)
            
        Returns:
            SHA-256 hash для позиции
        """
        
        # Нормализуем данные позиции
        normalized_position = CacheFingerprintService._normalize_position_data(position_data)
        
        # Создаем структуру для хеширования
        mini_fp_data = {
            "schema": SCHEMA_VERSION,
            "prompt_version": PROMPT_VERSION,
            "model": common_params.get("model", "llama-3.1-8b"),
            "symbol": symbol,
            "position": normalized_position,
            "common_params": common_params
        }
        
        # Каноническое представление
        canonical_json = json.dumps(mini_fp_data, sort_keys=True, separators=(',', ':'))
        
        # Хешируем
        fingerprint_hash = hashlib.sha256(canonical_json.encode('utf-8')).digest()
        
        import base64
        return base64.urlsafe_b64encode(fingerprint_hash).decode('ascii').rstrip('=')
    
    @staticmethod
    def _normalize_positions(positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Нормализация списка позиций для консистентности"""
        
        normalized = []
        
        for pos in positions:
            normalized_pos = CacheFingerprintService._normalize_position_data(pos)
            normalized.append(normalized_pos)
        
        # Сортируем по символу для детерминированности
        normalized.sort(key=lambda x: x.get('symbol', ''))
        
        return normalized
    
    @staticmethod 
    def _normalize_position_data(position: Dict[str, Any]) -> Dict[str, Any]:
        """нормализация данных позиции"""
        
        return {
            "symbol": str(position.get("symbol", "")).upper(),
            "weight_pct": round(float(position.get("weight_pct", 0.0)), 2),
            "growth_forecast_pct": round(float(position.get("growth_forecast_pct", 0.0)), 1),
            "risk_score_0_100": int(position.get("risk_score_0_100", 0)),
            "expected_return_horizon_pct": round(float(position.get("expected_return_horizon_pct", 0.0)), 1),
            "volatility_pct": round(float(position.get("volatility_pct", 0.0)), 1)
        }
    
    @staticmethod
    def _to_canonical_json(data: InsightsFingerprintData) -> str:
        """Создает каноническое JSON представление"""
        
        return json.dumps({
            "schema": data.schema,
            "prompt_version": data.prompt_version,
            "model": data.model,
            "horizon_months": data.horizon_months,
            "risk_profile": data.risk_profile,
            "positions": data.positions,
            "locale": data.locale
        }, sort_keys=True, separators=(',', ':'))

# === Анализ изменений для дельта-вызовов ===

@dataclass
class PositionChange:
    """Детектирование изменений в позиции"""
    symbol: str
    change_type: str  # "weight", "bucket", "locale", "version"
    old_value: Any
    new_value: Any
    material_flag: bool  # Материальное ли изменение

class ChangeDetector:
    """Детектор изменений для определения необходимости LLM вызова"""
    
    @staticmethod
    def detect_position_changes(
        old_positions: List[{str: Any}],
        new_positions: List[{str: Any}],
        old_params: Dict[str, Any],
        new_params: Dict[str, Any]
    ) -> List[PositionChange]:
        """
        Определяет изменения между старым и новым состоянием позиций
        
        Returns:
            Список изменений с флагами материальности
        """
        
        changes = []
        
        # Создаем словари для быстрого поиска
        old_dict = {pos.get("symbol"): pos for pos in old_positions}
        new_dict = {pos.get("symbol"): pos for pos in new_positions}
        
        # Проверяем изменения в параметрах
        param_changes = ChangeDetector._detect_param_changes(old_params, new_params)
        changes.extend(param_changes)
        
        # Проверяем все символы
        all_symbols = set(old_dict.keys()) | set(new_dict.keys())
        
        for symbol in all_symbols:
            old_pos = old_dict.get(symbol)
            new_pos = new_dict.get(symbol)
            
            if old_pos is None:
                # Новая позиция
                change = PositionChange(
                    symbol=symbol,
                    change_type="added",
                    old_value=None,
                    new_value=new_pos,
                    material_flag=True
                )
                changes.append(change)
                
            elif new_pos is None:
                # Удаленная позиция
                change = PositionChange(
                    symbol=symbol,
                    change_type="removed",
                    old_value=old_pos,
                    new_value=None,
                    material_flag=True
                )
                changes.append(change)
                
            else:
                # Измененная позиция
                pos_changes = ChangeDetector._detect_position_detail_changes(symbol, old_pos, new_pos)
                changes.extend(pos_changes)
        
        return changes
    
    @staticmethod
    def has_material_changes(changes: List[PositionChange]) -> bool:
        """Проверяет есть ли материальные изменения требующие LLM"""
        
        return any(change.material_flag for change in changes)
    
    @staticmethod
    def get_changed_symbols(changes: List[PositionChange]) -> set[str]:
        """Получает список символов с материальными изменениями"""
        
        changed_symbols = set()
        
        for change in changes:
            if change.material_flag:
                changed_symbols.add(change.symbol)
        
        return changed_symbols
    
    @staticmethod
    def _detect_param_changes(old_params: Dict[str, Any], new_params: Dict[str, Any]) -> List[PositionChange]:
        """Обнаружение изменений в общих параметрах"""
        
        changes = []
        
        # Критические параметры которые влияют на все позиции
        critical_params = ["horizon_months", "risk_profile", "locale", "model", "prompt_version"]
        
        for param in critical_params:
            if old_params.get(param) != new_params.get(param):
                change = PositionChange(
                    symbol="*",  # Все символы
                    change_type=f"param_{param}",
                    old_value=old_params.get(param),
                    new_value=new_params.get(param),
                    material_flag=True
                )
                changes.append(change)
        
        return changes
    
    @staticmethod
    def _detect_position_detail_changes(
        symbol: str,
        old_pos: Dict[str, Any],
        new_pos: Dict[str, Any]
    ) -> List[PositionChange]:
        """Определение изменений в конкретной позиции"""
        
        changes = []
        
        # Проверка изменения веса >= 5 п.п.
        old_weight = float(old_pos.get("weight_pct", 0.0))
        new_weight = float(new_pos.get("weight_pct", 0.0))
        weight_delta = abs(new_weight - old_weight)
        
        if weight_delta >= 5.0:
            change = PositionChange(
                symbol=symbol,
                change_type="weight",
                old_value=old_weight,
                new_value=new_weight,
                material_flag=True
            )
            changes.append(change)
        
        # Проверка изменения risk/growth bucket
        risk_bucket_old = ChangeDetector._get_risk_bucket(old_pos)
        risk_bucket_new = ChangeDetector._get_risk_bucket(new_pos)
        
        if risk_bucket_old != risk_bucket_new:
            change = PositionChange(
                symbol=symbol,
                change_type="risk_bucket",
                old_value=risk_bucket_old,
                new_value=risk_bucket_new,
                material_flag=True
            )
            changes.append(change)
        
        growth_bucket_old = ChangeDetector._get_growth_bucket(old_pos)
        growth_bucket_new = ChangeDetector._get_growth_bucket(new_pos)
        
        if growth_bucket_old != growth_bucket_new:
            change = PositionChange(
                symbol=symbol,
                change_type="growth_bucket",
                old_value=growth_bucket_old,
                new_value=growth_bucket_new,
                material_flag=True
            )
            changes.append(change)
        
        return changes
    
    @staticmethod
    def _get_risk_bucket(position: Dict[str, Any]) -> str:
        """Определение buckета риска"""
        
        risk_score = int(position.get("risk_score_0_100", 50))
        
        if risk_score <= 33:
            return "low"
        elif risk_score <= 66:
            return "moderate"
        else:
            return "high"
    
    @staticmethod
    def _get_growth_bucket(position: Dict[str, Any]) -> str:
        """Определение buckета роста"""
        
        growth = float(position.get("growth_forecast_pct", 0.0))
        
        if growth >= 10.0:
            return "high"
        elif growth >= 5.0:
            return "moderate"
        else:
            return "low"

# === Утилиты для работы с кэшем ===

class CacheKeyBuilder:
    """Построитель ключей для различных типов кэша"""
    
    @staticmethod
    def insights_llm_key(user_id: str, fingerprint: str) -> str:
        """Полный ключ для LLM кэша"""
        return f"insights:llm:{user_id}:{fingerprint}"
    
    @staticmethod
    def insights_positions_key(user_id: str, symbol: str, mini_fp: str) -> str:
        """Ключ для кэша отдельной позиции"""
        return f"insights:llmpos:{user_id}:{symbol}:{mini_fp}"
    
    @staticmethod
    def insights_lock_key(fingerprint: str) -> str:
        """Ключ для распределенного лока"""
        return f"insights:lock:{fingerprint}"
    
    @staticmethod
    def insights_prepared_key(user_id: str, fp_hash: str) -> str:
        """Ключ для кэша Prepared данные"""
        return f"insights:prepared:{user_id}:{fp_hash}"
    
    @staticmethod
    def insights_sentiment_key(user_id: str, window: str, news_fp: str) -> str:
        """Ключ для кэша сентимента"""
        return f"insights:sent:{user_id}:{window}:{news_fp}"










