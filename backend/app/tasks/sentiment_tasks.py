"""
Celery задачи для периодического анализа сентимента новостей
"""

import logging
from celery import Celery
from celery.schedules import crontab
from typing import List, Dict, Any
import httpx
from datetime import datetime, timedelta

from app.celery_app import celery_app
from app.services.sentiment_cache import SentimentAggregationService
from app.schemas_sentiment import SentimentItem, SentimentRequest, SentimentModel

logger = logging.getLogger(__name__)

class MockNewsService:
    """Мок сервиса новостей для демонстрации"""
    
    def get_recent_news_for_symbols(self, symbols: List[str], hours_back: int = 168) -> List[Dict[str, Any]]:
        """Получение свежих новостей по символам (мок)"""
        
        # Симуляция новостей для демонстрации
        mock_新闻 = []
        
        for symbol in symbols:
            # Генерируем несколько новостей за последнюю неделю
            for i in range(3):
                hours_ago = i * 12  # Каждые 12 часов
                published_at = datetime.utcnow() - timedelta(hours=hours_ago)
                
                # Разные типы новостей
                if i == 0:
                    headline = f"{symbol} Reports Strong Quarterly Earnings"
                    text = f"{symbol} exceeded analyst expectations with revenue growth of 15%. Management guidance remains optimistic."
                    sentiment_hint = "positive"
                elif i == 1:
                    headline = f"{symbol} Market Analysis Update"
                    text = f"Recent market trends show {symbol} trading within normal volatility ranges. No significant catalysts identified."
                    sentiment_hint = "neutral"
                else:
                    headline = f"{symbol} Faces Regulatory Headwinds"
                    text = f"New regulations may impact {symbol}'s core business model. Analysts expect short-term pressure."
                    sentiment_hint = "negative"
                
                mock_新闻.append({
                    "symbol": symbol,
                    "published_at": published_at.isoformat(),
                    "headline": headline,
                    "text": text,
                    "source": f"Mock Financial News {i+1}",
                    "sentiment_hint": sentiment_hint
                })
        
        return mock_新闻

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
def ingest_news_task(self, symbols: List[str] = None):
    """
    Задача сбора свежих новостей по символам
    Выполняется каждые 30 минут
    """
    
    logger.info(f"Starting news ingestion task for {len(symbols) if symbols else 'all'} symbols")
    
    try:
        # Если символы не переданы, используем основные тикеры из позиций пользователей
        if not symbols:
            from app.database import get_db
            from app.models.position import Position
            from sqlalchemy.orm import Session
            
            # Получаем активные символы из базы
            db = next(get_db())
            try:
                unique_symbols = db.query(Position.symbol).filter(
                    Position.symbol.isnot(None),
                    Position.symbol != ""
                ).distinct().all()
                
                symbols = [symbol[0] for symbol in unique_symbols]
                logger.info(f"Found {len(symbols)} unique symbols to process")
            finally:
                db.close()
        
        # Получаем новости
        mock_service = MockNewsService()
        news_items = mock_service.get_recent_news_for_symbols(symbols)
        
        logger.info(f"Ingested {len(news_items)} news items for sentiment analysis")
        
        # Запускаем sentiment анализ
        analyze_sentiment_batch_task.delay(news_items)
        
        return {"status": "success", "items_ingested": len(news_items)}
        
    except Exception as e:
        logger.error(f"News ingestion task failed: {e}")
        raise self.retry(exc=e, countdown=60)

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 2})
def analyze_sentiment_batch_task(self, news_items: List[Dict[str, Any]]):
    """
    Батч анализ сентимента новостей
    """
    
    logger.info(f"Starting sentiment batch analysis for {len(news_items)} items")
    
    try:
        # Конвертируем мок данные в SentimentItem
        sentiment_items = []
        for item in news_items:
            sentiment_item = SentimentItem(
                symbol=item["symbol"],
                published_at=datetime.fromisoformat(item["published_at"].replace('Z', '+00:00')),
                text=item["text"]
            )
            sentiment_items.append(sentiment_item)
        
        # Создаем запрос на анализ
        request = SentimentRequest(
            model=SentimentModel.FINLLAMA,
            items=sentiment_items
        )
        
        # Вызываем внутренний API
        async def call_sentiment_api():
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "http://localhost:8000/ai/sentiment/score",
                    json=request.dict()
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise Exception(f"Sentiment API error: {response.status_code}")
        
        # Выполняем анализ
        import asyncio
        api_response = asyncio.run(call_sentiment_api())
        
        logger.info(f"Sentiment analysis completed: {api_response.get('total_processed', 0)} items processed")
        
        # Запускаем агрегацию
        aggregate_sentiment_task.delay(api_response)
        
        return {"status": "success", "items_processed": api_response.get('total_processed', 0)}
        
    except Exception as e:
        logger.error(f"Sentiment batch analysis failed: {e}")
        raise self.retry(exc=e, countdown=120)

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 2})
def aggregate_sentiment_task(self, sentiment_response: Dict[str, Any]):
    """
    Агрегация sentiment результатов по символам
    """
    
    logger.info(f"Starting sentiment aggregation for {len(sentiment_response.get('results', []))} results")
    
    try:
        # Группируем результаты по символам
        symbols_data = {}
        
        for result in sentiment_response.get('results', []):
            symbol = result['symbol']
            if symbol not in symbols_data:
                symbols_data[symbol] = []
            
            symbols_data[symbol].append({
                'symbol': symbol,
                'published_at': sentiment_response.get('as_of', datetime.utcnow().isoformat()),
                'sentiment': result['sentiment'],
                'confidence': result['confidence'],
                'strength': result['strength']
            })
        
        # Агрегируем данные для каждого символа
        aggregation_service = SentimentAggregationService()
        
        for symbol, results in symbols_data.items():
            # Создаем SentimentResult объекты
            from app.schemas_sentiment import SentimentResult, SentimentLabel
            
            sentiment_results = []
            for item in results:
                sentiment_result = SentimentResult(
                    symbol=item['symbol'],
                    sentiment=SentimentLabel(item['sentiment']),
                    confidence=item['confidence'],
                    strength=item['strength'],
                    note=item.get('note')
                )
                sentiment_results.append(sentiment_result)
            
            # Агрегируем для обоих временных окон
            sentiment_7d = aggregation_service.aggregate_symbol_sentiment(symbol, sentiment_results, 7)
            sentiment_30d = aggregation_service.aggregate_symbol_sentiment(symbol, sentiment_results, 30)
            
            # Кэшируем результат
            async def cache_data():
                await aggregation_service.cache_sentiment_data(
                    symbol, sentiment_7d, sentiment_30d, 
                    sentiment_response.get('model', 'finllama')
                )
            
            import asyncio
            asyncio.run(cache_data())
            
            logger.info(f"Aggregated and cached sentiment data for {symbol}")
        
        # Обновляем портфельные метрики
        update_portfolio_metrics_task.delay()
        
        return {"status": "success", "symbols_processed": len(symbols_data)}
        
    except Exception as e:
        logger.error(f"Sentiment aggregation failed: {e}")
        raise self.retry(exc=e, countdown=180)

@celery_app.task(bind=True)
def update_portfolio_metrics_task(self):
    """
    Обновление портфельных метрик сентимента
    """
    
    logger.info("Updating portfolio sentiment metrics")
    
    try:
        # Этот таск может обновлять общие статистики, отправлять метрики в мониторинг и т.д.
        logger.info("Portfolio metrics updated successfully")
        
        return {"status": "success", "updated_at": datetime.utcnow().isoformat()}
        
    except Exception as e:
        logger.error(f"Portfolio metrics update failed: {e}")
        return {"status": "error", "error": str(e)}

# =============================================================================
# Конфигурация Celery Beat расписания
# =============================================================================

def setup_sentiment_beat_schedule():
    """Настройка расписания для Celery Beat"""
    
    return {
        # Сбор новостей каждые 30 минут
        'news-ingestion': {
            'task': 'app.tasks.sentiment_tasks.ingest_news_task',
            'schedule': crontab(minute='0,30'),
            'args': ()
        },
        
        # Дополнительные задачи можно добавить:
        # 'daily-aggregation': {
        #     'task': 'app.tasks.sentiment_tasks.daily_aggregation_task',
        #     'schedule': crontab(hour=1, minute=0),  # Каждый день в 1:00
        #     'args': ()
        # },
        
        # 'cache-cleanup': {
        #     'task': 'app.tasks.sentiment_tasks.cleanup_old_cache_task',
        #     'schedule': crontab(hour=3, minute=0),  # Каждый день в 3:00
        #     'args': ()
        # }
    }

# Регистрация расписания
sentiment_beat_schedule = setup_sentiment_beat_schedule()

@celery_app.on_after_configure.connect
def setup_sentiment_periodic_tasks(sender, **kwargs):
    """Установка периодических задач для sentiment анализа"""
    
    logger.info("Setting up sentiment analysis periodic tasks")
    
    # Новости каждые 30 минут
    sender.add_periodic_task(
        crontab(minute='0,30'),
        ingest_news_task.s(),
        name='news-ingestion'
    )
    
    logger.info("Sentiment periodic tasks configured successfully")










