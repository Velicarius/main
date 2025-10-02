"""
Insights v2 - Component: insights_prepare
Чистая детерминированная логика подготовки чисел для UI и LLM
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import date
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.position import Position
from app.models.user import User
from app.services.price_eod import PriceEODRepository
from app.schemas_insights_v2 import (
    PreparedInsights, PortfolioSummary, PositionPrepared, GroupingData
)


class IndustryData:
    """Вспомогательный класс для метаданных индустрий"""
    
    # Маппинг символов на индустрии (можно расширить)
    INDUSTRY_MAPPING = {
        'AAPL': 'Consumer Electronics',
        'MSFT': 'Software', 
        'GOOGL': 'Internet Services',
        'AMZN': 'E-commerce',
        'TSLA': 'Auto Manufacturers',
        'META': 'Social Media',
        'NVDA': 'Semiconductors',
        'JPM': 'Banking',
        'JNJ': 'Pharmaceuticals',
        'V': 'Payment Processing',
        'MA': 'Payment Processing',
        'PG': 'Consumer Goods',
        'KO': 'Beverages',
        'PFE': 'Pharmaceuticals',
        'WMT': 'Retail',
        'DIS': 'Entertainment',
        'CMCSA': 'Media',
        'VZ': 'Telecommunications',
        'T': 'Telecommunications',
        'UNH': 'Healthcare Services',
        'BAC': 'Banking',
        'HD': 'Home Improvement',
        'NFLX': 'Streaming Services',
        'CRM': 'Software',
        'ADBE': 'Software',
    }
    
    # Дополнительные метаданные компаний
    COMPANY_NAMES = {
        'AAPL': 'Apple Inc.',
        'MSFT': 'Microsoft Corporation',
        'GOOGL': 'Google (Alphabet)',
        'AMZN': 'Amazon.com',
        'TSLA': 'Tesla, Inc.',
        'META': 'Meta Platforms',
        'NVDA': 'NVIDIA Corporation',
        'JPM': 'JPMorgan Chase',
        'JNJ': 'Johnson & Johnson',
        'V': 'Visa Inc.',
        'MA': 'Mastercard',
        'PG': 'Procter & Gamble',
        'KO': 'Coca-Cola Company',
        'PFE': 'Pfizer Inc.',
        'WMT': 'Walmart Inc.',
        'DIS': 'Walt Disney Company',
        'CMCSA': 'Comcast',
        'VZ': 'Verizon',
        'T': 'AT&T',
        'UNH': 'UnitedHealth Group',
        'BAC': 'Bank of America',
        'HD': 'Home Depot',
        'NFLX': 'Netflix',
        'CRM': 'Salesforce',
        'ADBE': 'Adobe Inc.',
    }
    
    @classmethod
    def get_industry(cls, symbol: str) -> str:
        """Получить индустрию по символу"""
        return cls.INDUSTRY_MAPPING.get(symbol.upper(), 'Other')
    
    @classmethod
    def get_company_name(cls, symbol: str) -> str:
        """Получить название компании по символу"""
        return cls.COMPANY_NAMES.get(symbol.upper(), f"{symbol} Corp.")


class MetricsCalculator:
    """Калькулятор метрик риска и доходности"""
    
    @staticmethod
    def calculate_risk_from_volatility(volatility_pct: Optional[float], weight_pct: float) -> int:
        """Рассчитываем оценку риска на основе волатильности и веса позиции"""
        if not volatility_pct:
            return 50  # Средний риск если нет данных
        
        # Базовый риск от волатильности
        base_risk = min(100, max(0, volatility_pct / 2))
        
        # Корректировка на вес позиции (концентрация риска)
        if weight_pct > 20:
            # Высокая концентрация повышает риск
            concentration_multiplier = 1 + (weight_pct - 20) / 50
            base_risk *= concentration_multiplier
        
        return min(100, int(base_risk))
    
    @staticmethod
    def estimate_growth_forecast(symbol: str, weight_pct: float) -> Optional[float]:
        """Примерная оценка прогноза роста на основе символа и веса"""
        # Консервативный подход - используем исторические данные
        # По актуальности моделей (можно заменить реальными данными)
        
        growth_estimates = {
            # Tech giants - высокий рост
            'AAPL': 8.5, 'MSFT': 7.2, 'GOOGL': 9.1, 'AMZN': 12.3,
            'NVDA': 18.7, 'META': 6.8, 'TSLA': 25.0,
            
            # Financial - умеренный рост  
            'JPM': 4.2, 'BAC': 3.8, 'V': 7.5, 'MA': 8.1,
            
            # Healthcare - стабильный рост
            'JNJ': 5.5, 'UNH': 6.8, 'PFE': 2.1,
            
            # Consumer - медленный рост
            'PG': 4.1, 'KO': 3.2, 'WMT': 3.5, 'HD': 4.8,
            
            # Media/Comm - переменный рост
            'DIS': 3.8, 'NFLX': 15.2, 'VZ': 2.5, 'T': 2.1,
        }
        
        base_growth = growth_estimates.get(symbol.upper())
        if not base_growth:
            return None
        
        # Корректировка на вес (диверсификация снижает риск конкретного роста)
        if weight_pct > 15:
            # Концентрация снижает стабильность прогноза
            base_growth *= 0.8
        
        return round(base_growth, 1)
    
    @staticmethod
    def estimate_volatility(symbol: str) -> Optional[float]:
        """Оценка волатильности символа на основе исторических данных"""
        volatility_estimates = {
            # High volatility tech
            'TSLA': 65.2, 'NVDA': 42.8, 'AMZN': 38.1,
            
            # Moderate volatility tech
            'AAPL': 24.3, 'MSFT': 28.7, 'GOOGL': 31.2, 'META': 35.6,
            
            # Lower volatility blue chips
            'JNJ': 18.2, 'PG': 16.8, 'JPM': 22.1, 'BAC': 28.4,
            'V': 25.6, 'MA': 27.3, 'KO': 15.2, 'VZ': 20.3,
        }
        
        return volatility_estimates.get(symbol.upper())


class GroupingsCalculator:
    """Калькулятор группировок портфеля"""
    
    @staticmethod
    def calculate_industry_groupings(positions: List[PositionPrepared]) -> List[GroupingData]:
        """Группировка по индустриям"""
        industry_map = {}
        
        for pos in positions:
            industry = pos.industry
            if industry not in industry_map:
                industry_map[industry] = {
                    'weight': 0.0,
                    'returns': [],
                    'risks': [],
                    'positions': []
                }
            
            industry_map[industry]['weight'] += pos.weight_pct
            industry_map[industry]['positions'].append(pos.symbol)
            
            if pos.expected_return_horizon_pct is not None:
                industry_map[industry]['returns'].append(pos.expected_return_horizon_pct)
            if pos.risk_score_0_100 is not None:
                industry_map[industry]['risks'].append(pos.risk_score_0_100)
        
        groupings = []
        for industry, data in industry_map.items():
            avg_return = sum(data['returns']) / len(data['returns']) if data['returns'] else None
            avg_risk = sum(data['risks']) / len(data['risks']) if data['risks'] else None
            
            groupings.append(GroupingData(
                name=industry,
                weight_pct=round(data['weight'], 1),
                avg_expected_return_pct=round(avg_return, 1) if avg_return else None,
                avg_risk_score=round(avg_risk, 1) if avg_risk else None,
                positions=data['positions']
            ))
        
        return sorted(groupings, key=lambda g: g.weight_pct, reverse=True)
    
    @staticmethod
    def calculate_growth_buckets(positions: List[PositionPrepared]) -> List[GroupingData]:
        """Группировка по прогнозам роста"""
        high_growth = {'weight': 0.0, 'positions': [], 'returns': []}
        mid_growth = {'weight': 0.0, 'positions': [], 'returns': []}
        low_growth = {'weight': 0.0, 'positions': [], 'returns': []}
        
        for pos in positions:
            growth = pos.growth_forecast_pct
            
            if growth is None or growth < 5:
                bucket = low_growth
                category = 'Low/Unknown'
            elif growth < 15:
                bucket = mid_growth
                category = 'Mid growth'
            else:
                bucket = high_growth
                category = 'High growth'
            
            bucket['weight'] += pos.weight_pct
            bucket['positions'].append(pos.symbol)
            bucket['returns'].append(pos.expected_return_horizon_pct)
        
        groupings = []
        for bucket_name, bucket_data, category in [
            ('High Growth', high_growth, 'High growth'),
            ('Mid Growth', mid_growth, 'Mid growth'),
            ('Low/Unknown', low_growth, 'Low/Value')
        ]:
            if bucket_data['positions']:
                avg_return = sum(bucket_data['returns']) / len(bucket_data['returns']) if bucket_data['returns'] else None
                groupings.append(GroupingData(
                    name=category,
                    weight_pct=round(bucket_data['weight'], 1),
                    avg_expected_return_pct=round(avg_return, 1) if avg_return else None,
                    avg_risk_score=None,
                    positions=bucket_data['positions']
                ))
        
        return groupings
    
    @staticmethod
    def calculate_risk_buckets(positions: List[PositionPrepared]) -> List[GroupingData]:
        """Группировка по уровням риска"""
        low_risk = {'weight': 0.0, 'positions': [], 'risks': [], 'returns': []}
        medium_risk = {'weight': 0.0, 'positions': [], 'risks': [], 'returns': []}
        high_risk = {'weight': 0.0, 'positions': [], 'risks': [], 'returns': []}
        
        for pos in positions:
            risk_score = pos.risk_score_0_100
            
            if risk_score is None:
                bucket = medium_risk
            elif risk_score <= 33:
                bucket = low_risk
            elif risk_score <= 66:
                bucket = medium_risk
            else:
                bucket = high_risk
            
            bucket['weight'] += pos.weight_pct
            bucket['positions'].append(pos.symbol)
            bucket['risks'].append(risk_score) if risk_score is not None else None
            bucket['returns'].append(pos.expected_return_horizon_pct)
        
        groupings = []
        for bucket_name, bucket_data, category in [
            ('Low Risk', low_risk, 'Low'),
            ('Medium Risk', medium_risk, 'Moderate'),
            ('High Risk', high_risk, 'High')
        ]:
            if bucket_data['positions']:
                avg_risk = sum(bucket_data['risks']) / len(bucket_data['risks']) if bucket_data['risks'] else None
                avg_return = sum(bucket_data['returns']) / len(bucket_data['returns']) if bucket_data['returns'] else None
                
                groupings.append(GroupingData(
                    name=category,
                    weight_pct=round(bucket_data['weight'], 1),
                    avg_expected_return_pct=round(avg_return, 1) if avg_return else None,
                    avg_risk_score=round(avg_risk, 1) if avg_risk else None,
                    positions=bucket_data['positions']
                ))
        
        return groupings


class InsightsPrepareService:
    """Основной сервис подготовки данных"""
    
    def __init__(self, db: Session):
        self.db = db
        self.price_repo = PriceEODRepository(db)
        self.metrics_calc = MetricsCalculator()
        self.groupings_calc = GroupingsCalculator()
    
    async def prepare_insights(self, user_id: UUID) -> PreparedInsights:
        """
        Шаг A: Подготовка чистых чисел
        Детерминированная логика без сбоев LLM
        """
        
        # 1. Получаем пользователя и позиции
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        positions = (
            self.db.query(Position)
            .filter(Position.user_id == user_id)
            .filter(Position.symbol != 'USD')  # Исключаем валютный баланс
            .order_by(Position.symbol)
            .all()
        )
        
        if not positions:
            raise ValueError("No positions found for analysis")
        
        # 2. Рассчитываем общую стоимость портфеля
        total_portfolio_value = 0.0
        
        prepared_positions = []
        for position in positions:
            symbol = position.symbol
            
            # Получаем текущую цену
            latest_price = self.price_repo.get_latest_price(symbol)
            current_price = float(latest_price.close) if latest_price else None
            
            if not current_price:
                continue  # Пропускаем позиции без цен
            
            # Стоимость позиции
            position_value = float(position.quantity) * current_price
            
            # Метаданные позиции
            industry = IndustryData.get_industry(symbol)
            company_name = IndustryData.get_company_name(symbol)
            
            # Метрики
            growth_forecast = self.metrics_calc.estimate_growth_forecast(symbol, 0)  # вес будет обновлен позже
            volatility = self.metrics_calc.estimate_volatility(symbol)
            
            # Ожидаемая доходность (консервативная оценка 6 месяцев)
            horizon_months = 6
            annualized_return = growth_forecast or 8.0  # по умолчанию 8% годовых
            horizon_return = (annualized_return * horizon_months) / 12
            
            prepared_positions.append(PositionPrepared(
                symbol=symbol,
                name=company_name,
                industry=industry,
                weight_pct=0.0,  # пересчитаем ниже
                growth_forecast_pct=growth_forecast,
                risk_score_0_100=self.metrics_calc.calculate_risk_from_volatility(volatility, 0),
                expected_return_horizon_pct=round(horizon_return, 1),
                volatility_pct=volatility
            ))
            
            total_portfolio_value += position_value
        
        # 3. Обновляем веса позиций с учетом общей стоимости
        for pos in prepared_positions:
            symbol_positions = [p for p in positions if p.symbol == pos.symbol]
            if symbol_positions:
                position_value = sum(float(p.quantity) * float(self.price_repo.get_latest_price(p.symbol).close) 
                                  for p in symbol_positions if self.price_repo.get_latest_price(p.symbol))
                pos.weight_pct = round((position_value / total_portfolio_value) * 100, 1)
                
                # Обновляем оценку риска с учетом реального веса
                pos.risk_score_0_100 = self.metrics_calc.calculate_risk_from_volatility(
                    pos.volatility_pct, pos.weight_pct
                )
        
        # 4. Рассчитываем сводные метрики портфеля
        total_equity = total_portfolio_value + float(user.usd_balance)
        avg_expected_return = sum(p.expected_return_horizon_pct * p.weight_pct for p in prepared_positions) / 100
        avg_risk_score = sum(p.risk_score_0_100 * p.weight_pct for p in prepared_positions 
                           if p.risk_score_0_100) / sum(p.weight_pct for p in prepared_positions)
        
        portfolio_summary = PortfolioSummary(
            total_equity_usd=round(total_equity, 2),
            free_usd=float(user.usd_balance),
            portfolio_value_usd=round(total_portfolio_value, 2),
            expected_return_horizon_pct=round(avg_expected_return, 1),
            volatility_annualized_pct=round(sum(p.volatility_pct * p.weight_pct for p in prepared_positions 
                                              if p.volatility_pct) / 100, 1),
            risk_score_0_100=round(avg_risk_score, 1),
            risk_class='Low' if avg_risk_score <= 33 else 'Moderate' if avg_risk_score <= 66 else 'High',
            as_of=date.today().isoformat()
        )
        
        # 5. Рассчитываем группировки
        industry_groups = self.groupings_calc.calculate_industry_groupings(prepared_positions)
        growth_groups = self.groupings_calc.calculate_growth_buckets(prepared_positions)
        risk_groups = self.groupings_calc.calculate_risk_buckets(prepared_positions)
        
        return PreparedInsights(
            summary=portfolio_summary,
            grouping={
                'by_industry': industry_groups,
                'by_growth_bucket': growth_groups,
                'by_risk_bucket': risk_groups
            },
            positions=prepared_positions
        )
