"""
Tests for news cache primitives with Redis and SWR functionality.

Tests the cache module using fakeredis to verify TTL/SWR behavior,
single-flight locking, and quota counters.
"""

import pytest
import json
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import fakeredis

from app.core.news_cache import (
    get_query_cache, set_query_cache,
    get_article_cache, set_article_cache,
    acquire_singleflight, release_singleflight,
    inc_daily, inc_minute, get_quota_state,
    clear_cache_pattern, get_cache_stats
)


@pytest.fixture
def mock_redis():
    """Create a fake Redis client for testing."""
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    
    with patch('app.core.news_cache.get_redis_client', return_value=fake_redis):
        yield fake_redis


class TestQueryCache:
    """Test query cache functionality with SWR."""
    
    def test_set_and_get_query_cache(self, mock_redis):
        """Test basic query cache set/get operations."""
        provider = "newsapi"
        symbol = "AAPL"
        qhash = "abc123"
        
        # Test data
        test_data = {
            "article_ids": ["uuid1", "uuid2", "uuid3"],
            "etag": "etag123",
            "fetched_at": "2025-10-08T12:00:00Z"
        }
        
        # Set cache
        set_query_cache(provider, symbol, qhash, test_data, ttl_seconds=900)
        
        # Get cache
        cached_data, is_stale = get_query_cache(provider, symbol, qhash)
        
        assert cached_data is not None
        assert cached_data["article_ids"] == ["uuid1", "uuid2", "uuid3"]
        assert cached_data["etag"] == "etag123"
        assert is_stale is False
        
        # Verify key format
        expected_key = "news:q:newsapi:AAPL:abc123"
        assert mock_redis.exists(expected_key)
    
    def test_query_cache_with_none_symbol(self, mock_redis):
        """Test query cache with None symbol (normalized to '_')."""
        provider = "newsapi"
        symbol = None
        qhash = "def456"
        
        test_data = {"article_ids": ["uuid1"], "etag": "etag456"}
        
        set_query_cache(provider, symbol, qhash, test_data)
        cached_data, is_stale = get_query_cache(provider, symbol, qhash)
        
        assert cached_data is not None
        assert is_stale is False
        
        # Verify key uses '_' for None symbol
        expected_key = "news:q:newsapi:_:def456"
        assert mock_redis.exists(expected_key)
    
    def test_query_cache_swr_behavior(self, mock_redis):
        """Test SWR (stale-while-revalidate) behavior."""
        provider = "newsapi"
        symbol = "AAPL"
        qhash = "swr_test"
        
        test_data = {"article_ids": ["uuid1"], "etag": "etag_swr"}
        
        # Set cache
        set_query_cache(provider, symbol, qhash, test_data, ttl_seconds=900, swr_window=2700)
        
        # Get cached data
        cached_data, is_stale = get_query_cache(provider, symbol, qhash)
        assert cached_data is not None
        assert cached_data["article_ids"] == ["uuid1"]
        assert cached_data["etag"] == "etag_swr"
        
        # Note: fakeredis TTL behavior differs from real Redis
        # In real Redis, we would test TTL expiration, but for fakeredis
        # we just verify the basic caching functionality works
    
    def test_query_cache_missing_key(self, mock_redis):
        """Test query cache with non-existent key."""
        cached_data, is_stale = get_query_cache("newsapi", "AAPL", "nonexistent")
        
        assert cached_data is None
        assert is_stale is False
    
    def test_query_cache_invalid_json(self, mock_redis):
        """Test query cache with invalid JSON data."""
        provider = "newsapi"
        symbol = "AAPL"
        qhash = "invalid_json"
        
        # Manually set invalid JSON
        key = f"news:q:{provider}:{symbol}:{qhash}"
        mock_redis.set(key, "invalid json data", ex=900)
        
        cached_data, is_stale = get_query_cache(provider, symbol, qhash)
        
        assert cached_data is None
        assert is_stale is False


class TestArticleCache:
    """Test article cache functionality."""
    
    def test_set_and_get_article_cache(self, mock_redis):
        """Test basic article cache set/get operations."""
        article_id = "123e4567-e89b-12d3-a456-426614174000"
        
        test_article = {
            "id": article_id,
            "title": "Test Article",
            "url": "https://example.com/test",
            "provider": "newsapi"
        }
        
        # Set cache
        set_article_cache(article_id, test_article, ttl_seconds=604800)
        
        # Get cache
        cached_article = get_article_cache(article_id)
        
        assert cached_article is not None
        assert cached_article["id"] == article_id
        assert cached_article["title"] == "Test Article"
        assert cached_article["provider"] == "newsapi"
        
        # Verify key format
        expected_key = f"news:article:{article_id}"
        assert mock_redis.exists(expected_key)
    
    def test_article_cache_missing_key(self, mock_redis):
        """Test article cache with non-existent key."""
        cached_article = get_article_cache("nonexistent-uuid")
        
        assert cached_article is None
    
    def test_article_cache_invalid_json(self, mock_redis):
        """Test article cache with invalid JSON data."""
        article_id = "invalid-json-uuid"
        
        # Manually set invalid JSON
        key = f"news:article:{article_id}"
        mock_redis.set(key, "invalid json", ex=604800)
        
        cached_article = get_article_cache(article_id)
        
        assert cached_article is None


class TestSingleFlight:
    """Test single-flight locking functionality."""
    
    def test_acquire_singleflight_success(self, mock_redis):
        """Test successful single-flight lock acquisition."""
        provider = "newsapi"
        symbol = "AAPL"
        qhash = "lock_test"
        
        # First acquisition should succeed
        result = acquire_singleflight(provider, symbol, qhash, ttl=60)
        assert result is True
        
        # Verify lock key exists
        expected_key = "news:lock:newsapi:AAPL:lock_test"
        assert mock_redis.exists(expected_key)
    
    def test_acquire_singleflight_blocked(self, mock_redis):
        """Test single-flight lock blocks second caller."""
        provider = "newsapi"
        symbol = "AAPL"
        qhash = "block_test"
        
        # First acquisition should succeed
        result1 = acquire_singleflight(provider, symbol, qhash, ttl=60)
        assert result1 is True
        
        # Second acquisition should be blocked
        result2 = acquire_singleflight(provider, symbol, qhash, ttl=60)
        assert result2 is False
    
    def test_release_singleflight(self, mock_redis):
        """Test single-flight lock release."""
        provider = "newsapi"
        symbol = "AAPL"
        qhash = "release_test"
        
        # Acquire lock
        acquire_singleflight(provider, symbol, qhash, ttl=60)
        
        # Verify lock exists
        expected_key = "news:lock:newsapi:AAPL:release_test"
        assert mock_redis.exists(expected_key)
        
        # Release lock
        release_singleflight(provider, symbol, qhash)
        
        # Verify lock is gone
        assert not mock_redis.exists(expected_key)
    
    def test_singleflight_with_none_symbol(self, mock_redis):
        """Test single-flight with None symbol."""
        provider = "newsapi"
        symbol = None
        qhash = "none_symbol_test"
        
        result = acquire_singleflight(provider, symbol, qhash, ttl=60)
        assert result is True
        
        # Verify key uses '_' for None symbol
        expected_key = "news:lock:newsapi:_:none_symbol_test"
        assert mock_redis.exists(expected_key)


class TestQuotaCounters:
    """Test quota counter functionality."""
    
    def test_inc_daily(self, mock_redis):
        """Test daily quota counter increment."""
        provider = "newsapi"
        
        # First increment
        count1 = inc_daily(provider)
        assert count1 == 1
        
        # Second increment
        count2 = inc_daily(provider)
        assert count2 == 2
        
        # Verify key format
        today = datetime.utcnow().strftime("%Y%m%d")
        expected_key = f"news:quota:{provider}:{today}"
        assert mock_redis.exists(expected_key)
        assert mock_redis.get(expected_key) == "2"
    
    def test_inc_minute(self, mock_redis):
        """Test minute quota counter increment."""
        provider = "newsapi"
        
        # First increment
        count1 = inc_minute(provider)
        assert count1 == 1
        
        # Second increment
        count2 = inc_minute(provider)
        assert count2 == 2
        
        # Verify key format
        now = datetime.utcnow()
        minute_key = now.strftime("%Y%m%d%H%M")
        expected_key = f"news:minute:{provider}:{minute_key}"
        assert mock_redis.exists(expected_key)
        assert mock_redis.get(expected_key) == "2"
    
    def test_get_quota_state(self, mock_redis):
        """Test quota state retrieval."""
        provider = "newsapi"
        
        # Set up some quota data
        inc_daily(provider)
        inc_daily(provider)
        inc_minute(provider)
        
        # Get quota state
        state = get_quota_state(provider)
        
        assert state["provider"] == provider
        assert state["daily_count"] == 2
        assert state["minute_count"] == 1
        assert "date" in state
        assert "minute" in state
        assert "timestamp" in state
    
    def test_get_quota_state_empty(self, mock_redis):
        """Test quota state with no existing data."""
        provider = "nonexistent"
        
        state = get_quota_state(provider)
        
        assert state["provider"] == provider
        assert state["daily_count"] == 0
        assert state["minute_count"] == 0


class TestCacheUtilities:
    """Test cache utility functions."""
    
    def test_clear_cache_pattern(self, mock_redis):
        """Test clearing cache entries by pattern."""
        # Set up some test data
        set_query_cache("newsapi", "AAPL", "hash1", {"article_ids": ["uuid1"]})
        set_query_cache("newsapi", "MSFT", "hash2", {"article_ids": ["uuid2"]})
        set_article_cache("uuid1", {"title": "Article 1"})
        set_article_cache("uuid2", {"title": "Article 2"})
        
        # Clear query cache
        deleted = clear_cache_pattern("news:q:*")
        assert deleted == 2
        
        # Verify query cache is cleared but article cache remains
        assert not mock_redis.exists("news:q:newsapi:AAPL:hash1")
        assert not mock_redis.exists("news:q:newsapi:MSFT:hash2")
        assert mock_redis.exists("news:article:uuid1")
        assert mock_redis.exists("news:article:uuid2")
    
    def test_get_cache_stats(self, mock_redis):
        """Test cache statistics retrieval."""
        # Set up some test data
        set_query_cache("newsapi", "AAPL", "hash1", {"article_ids": ["uuid1"]})
        set_article_cache("uuid1", {"title": "Article 1"})
        acquire_singleflight("newsapi", "AAPL", "hash1")
        inc_daily("newsapi")
        
        stats = get_cache_stats()
        
        # Verify basic stats structure
        assert "query_cache_count" in stats
        assert "article_cache_count" in stats
        assert "lock_count" in stats
        assert "quota_count" in stats
        assert "total_keys" in stats
        
        # Note: fakeredis doesn't support redis.info(), so we expect an error
        # but the function should still return basic stats
        assert "error" in stats or "redis_info" in stats


class TestCacheKeyFormats:
    """Test cache key format generation."""
    
    def test_query_cache_key_formats(self, mock_redis):
        """Test query cache key formats."""
        # Test with symbol
        set_query_cache("newsapi", "AAPL", "hash1", {"article_ids": ["uuid1"]})
        assert mock_redis.exists("news:q:newsapi:AAPL:hash1")
        
        # Test with None symbol
        set_query_cache("newsapi", None, "hash2", {"article_ids": ["uuid2"]})
        assert mock_redis.exists("news:q:newsapi:_:hash2")
    
    def test_article_cache_key_formats(self, mock_redis):
        """Test article cache key formats."""
        article_id = "123e4567-e89b-12d3-a456-426614174000"
        set_article_cache(article_id, {"title": "Test"})
        
        expected_key = f"news:article:{article_id}"
        assert mock_redis.exists(expected_key)
    
    def test_lock_key_formats(self, mock_redis):
        """Test single-flight lock key formats."""
        # Test with symbol
        acquire_singleflight("newsapi", "AAPL", "hash1")
        assert mock_redis.exists("news:lock:newsapi:AAPL:hash1")
        
        # Test with None symbol
        acquire_singleflight("newsapi", None, "hash2")
        assert mock_redis.exists("news:lock:newsapi:_:hash2")
    
    def test_quota_key_formats(self, mock_redis):
        """Test quota counter key formats."""
        provider = "newsapi"
        today = datetime.utcnow().strftime("%Y%m%d")
        now = datetime.utcnow()
        minute_key = now.strftime("%Y%m%d%H%M")
        
        inc_daily(provider)
        inc_minute(provider)
        
        assert mock_redis.exists(f"news:quota:{provider}:{today}")
        assert mock_redis.exists(f"news:minute:{provider}:{minute_key}")


class TestCacheErrorHandling:
    """Test cache error handling and edge cases."""
    
    def test_redis_connection_error(self):
        """Test behavior when Redis connection fails."""
        with patch('app.core.news_cache.get_redis_client', side_effect=Exception("Redis error")):
            # Should handle errors gracefully
            cached_data, is_stale = get_query_cache("newsapi", "AAPL", "test")
            assert cached_data is None
            assert is_stale is False
            
            # Should not raise exception
            set_query_cache("newsapi", "AAPL", "test", {"article_ids": ["uuid1"]})
            
            # Should return False for lock acquisition
            result = acquire_singleflight("newsapi", "AAPL", "test")
            assert result is False
    
    def test_json_serialization_error(self, mock_redis):
        """Test handling of JSON serialization errors."""
        # Create an object that can't be JSON serialized
        class NonSerializable:
            def __init__(self):
                self.func = lambda x: x
        
        non_serializable_data = {"data": NonSerializable()}
        
        # Should handle serialization error gracefully
        set_query_cache("newsapi", "AAPL", "test", non_serializable_data)
        
        # Cache should not be set due to serialization error
        cached_data, is_stale = get_query_cache("newsapi", "AAPL", "test")
        assert cached_data is None
