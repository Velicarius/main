"""
Contract tests for LLM news reader service.

These tests ensure that the LLM news reader maintains consistent
API contracts regardless of feature flag changes.

Key features:
- JSON snapshot testing for contract stability
- Feature flag compatibility testing
- Schema validation for response consistency
"""

import json
import os
import pytest
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from app.services.news_reader_llm import NewsRepositoryLLM
from app.database import get_db
from app.core.config import settings


@pytest.fixture
def snapshot_dir():
    """Get snapshot directory path."""
    return Path(__file__).parent.parent / "snapshots"


@pytest.fixture
def llm_repository():
    """Get LLM news repository instance."""
    db = next(get_db())
    try:
        yield NewsRepositoryLLM(db)
    finally:
        db.close()


def save_snapshot(snapshot_dir: Path, filename: str, data: dict):
    """Save JSON snapshot to file."""
    snapshot_path = snapshot_dir / filename
    snapshot_path.parent.mkdir(exist_ok=True)
    
    with open(snapshot_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)


def load_snapshot(snapshot_dir: Path, filename: str) -> dict:
    """Load JSON snapshot from file."""
    snapshot_path = snapshot_dir / filename
    
    if not snapshot_path.exists():
        pytest.skip(f"Snapshot {filename} does not exist. Run tests to generate snapshots.")
    
    with open(snapshot_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_news_list_schema(data: dict):
    """Validate news list response schema."""
    required_fields = ["items", "total", "limit", "offset"]
    
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    
    assert isinstance(data["items"], list), "items must be a list"
    assert isinstance(data["total"], int), "total must be an integer"
    assert isinstance(data["limit"], int), "limit must be an integer"
    assert isinstance(data["offset"], int), "offset must be an integer"
    
    # Validate item schema if items exist
    if data["items"]:
        item = data["items"][0]
        item_required_fields = ["id", "title", "source_name", "url", "provider"]
        
        for field in item_required_fields:
            assert field in item, f"Missing required item field: {field}"
        
        assert isinstance(item["id"], str), "item.id must be a string"
        assert isinstance(item["title"], str), "item.title must be a string"
        assert isinstance(item["source_name"], str), "item.source_name must be a string"
        assert isinstance(item["url"], str), "item.url must be a string"
        assert isinstance(item["provider"], str), "item.provider must be a string"


def validate_news_detail_schema(data: dict):
    """Validate news detail response schema."""
    required_fields = ["id", "title", "source_name", "url", "provider"]
    
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    
    assert isinstance(data["id"], str), "id must be a string"
    assert isinstance(data["title"], str), "title must be a string"
    assert isinstance(data["source_name"], str), "source_name must be a string"
    assert isinstance(data["url"], str), "url must be a string"
    assert isinstance(data["provider"], str), "provider must be a string"


class TestLLMNewsContract:
    """Test LLM news reader contract stability."""
    
    def test_llm_news_list_contract(self, llm_repository: NewsRepositoryLLM, snapshot_dir: Path):
        """Test LLM news list contract with snapshot."""
        # Call LLM repository with fixed parameters
        result = llm_repository.list_news(
            symbol="AAPL",
            limit=3,
            offset=0,
            order="desc"
        )
        
        # Validate schema
        validate_news_list_schema(result)
        
        # Save or compare snapshot
        snapshot_file = "llm_news_list.json"
        
        if not (snapshot_dir / snapshot_file).exists():
            # First run - save snapshot
            save_snapshot(snapshot_dir, snapshot_file, result)
            pytest.skip(f"Generated snapshot {snapshot_file}. Run test again to validate.")
        else:
            # Compare with existing snapshot
            expected = load_snapshot(snapshot_dir, snapshot_file)
            
            # Compare structure and key fields
            assert result["total"] == expected["total"], "Total count changed"
            assert len(result["items"]) == len(expected["items"]), "Item count changed"
            
            # Compare first item structure (if exists)
            if result["items"] and expected["items"]:
                result_item = result["items"][0]
                expected_item = expected["items"][0]
                
                # Check required fields exist
                for field in ["id", "title", "source_name", "url", "provider"]:
                    assert field in result_item, f"Missing field in result: {field}"
                    assert field in expected_item, f"Missing field in expected: {field}"
                
                # Check data types
                assert isinstance(result_item["id"], str), "id must be string"
                assert isinstance(result_item["title"], str), "title must be string"
                assert isinstance(result_item["provider"], str), "provider must be string"
    
    def test_llm_news_detail_contract(self, llm_repository: NewsRepositoryLLM, snapshot_dir: Path):
        """Test LLM news detail contract with snapshot."""
        # First get an article ID from list
        list_result = llm_repository.list_news(limit=1)
        
        if not list_result["items"]:
            pytest.skip("No articles available for detail test")
        
        article_id = list_result["items"][0]["id"]
        
        # Get article detail
        result = llm_repository.get_news_detail(article_id, include_raw=False)
        
        if result is None:
            pytest.skip("Article not found or filtered by shadow mode")
        
        # Validate schema
        validate_news_detail_schema(result)
        
        # Save or compare snapshot
        snapshot_file = "llm_news_detail.json"
        
        if not (snapshot_dir / snapshot_file).exists():
            # First run - save snapshot
            save_snapshot(snapshot_dir, snapshot_file, result)
            pytest.skip(f"Generated snapshot {snapshot_file}. Run test again to validate.")
        else:
            # Compare with existing snapshot
            expected = load_snapshot(snapshot_dir, snapshot_file)
            
            # Compare key fields
            assert result["id"] == expected["id"], "Article ID changed"
            assert result["title"] == expected["title"], "Article title changed"
            assert result["provider"] == expected["provider"], "Article provider changed"
            
            # Check required fields exist
            for field in ["id", "title", "source_name", "url", "provider"]:
                assert field in result, f"Missing field in result: {field}"
                assert field in expected, f"Missing field in expected: {field}"
    
    def test_feature_flag_compatibility(self, llm_repository: NewsRepositoryLLM):
        """Test that feature flags don't break contract."""
        # Test with cache enabled/disabled
        original_cache_setting = settings.news_read_cache_enabled
        
        try:
            # Test with cache enabled
            settings.news_read_cache_enabled = True
            result_with_cache = llm_repository.list_news(symbol="AAPL", limit=2)
            validate_news_list_schema(result_with_cache)
            
            # Test with cache disabled
            settings.news_read_cache_enabled = False
            result_without_cache = llm_repository.list_news(symbol="AAPL", limit=2)
            validate_news_list_schema(result_without_cache)
            
            # Both should have same structure
            assert "items" in result_with_cache
            assert "items" in result_without_cache
            assert "total" in result_with_cache
            assert "total" in result_without_cache
            
        finally:
            # Restore original setting
            settings.news_read_cache_enabled = original_cache_setting
    
    def test_shadow_mode_filtering(self, llm_repository: NewsRepositoryLLM):
        """Test shadow mode filtering doesn't break contract."""
        # Test with shadow mode enabled/disabled
        original_shadow_setting = settings.news_provider_shadow_mode
        original_shadow_providers = settings.news_shadow_providers
        
        try:
            # Test with shadow mode disabled
            settings.news_provider_shadow_mode = False
            result_no_shadow = llm_repository.list_news(limit=5)
            validate_news_list_schema(result_no_shadow)
            
            # Test with shadow mode enabled (but no shadow providers)
            settings.news_provider_shadow_mode = True
            settings.news_shadow_providers = ""
            result_shadow_empty = llm_repository.list_news(limit=5)
            validate_news_list_schema(result_shadow_empty)
            
            # Test with shadow mode enabled (with shadow providers)
            settings.news_shadow_providers = "test_provider"
            result_shadow_filtered = llm_repository.list_news(limit=5)
            validate_news_list_schema(result_shadow_filtered)
            
            # All should have same structure
            for result in [result_no_shadow, result_shadow_empty, result_shadow_filtered]:
                assert "items" in result
                assert "total" in result
                assert isinstance(result["items"], list)
                assert isinstance(result["total"], int)
            
        finally:
            # Restore original settings
            settings.news_provider_shadow_mode = original_shadow_setting
            settings.news_shadow_providers = original_shadow_providers
    
    def test_fail_open_behavior(self, llm_repository: NewsRepositoryLLM):
        """Test fail-open behavior maintains contract."""
        # Test with invalid parameters
        result = llm_repository.list_news(
            symbol="INVALID_SYMBOL_12345",
            limit=10
        )
        
        # Should return valid structure even with no results
        validate_news_list_schema(result)
        assert result["total"] >= 0
        assert isinstance(result["items"], list)
        
        # Test with invalid article ID
        detail_result = llm_repository.get_news_detail("invalid-uuid")
        
        # Should return None, not crash
        assert detail_result is None or isinstance(detail_result, dict)
    
    def test_response_consistency(self, llm_repository: NewsRepositoryLLM):
        """Test response consistency across multiple calls."""
        # Make multiple calls with same parameters
        results = []
        for _ in range(3):
            result = llm_repository.list_news(symbol="AAPL", limit=2)
            validate_news_list_schema(result)
            results.append(result)
        
        # All results should have same structure
        for result in results:
            assert "items" in result
            assert "total" in result
            assert "limit" in result
            assert "offset" in result
        
        # Total should be consistent
        totals = [r["total"] for r in results]
        assert len(set(totals)) <= 1, "Total count should be consistent"
        
        # Item count should be consistent
        item_counts = [len(r["items"]) for r in results]
        assert len(set(item_counts)) <= 1, "Item count should be consistent"


class TestLLMNewsSchema:
    """Test LLM news response schemas."""
    
    def test_news_list_schema_validation(self, llm_repository: NewsRepositoryLLM):
        """Test news list schema validation."""
        result = llm_repository.list_news(limit=1)
        
        # Validate required fields
        required_fields = ["items", "total", "limit", "offset"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        # Validate types
        assert isinstance(result["items"], list)
        assert isinstance(result["total"], int)
        assert isinstance(result["limit"], int)
        assert isinstance(result["offset"], int)
        
        # Validate items if present
        if result["items"]:
            item = result["items"][0]
            item_fields = ["id", "title", "source_name", "url", "provider"]
            
            for field in item_fields:
                assert field in item, f"Missing item field: {field}"
                assert isinstance(item[field], str), f"Item field {field} must be string"
    
    def test_news_detail_schema_validation(self, llm_repository: NewsRepositoryLLM):
        """Test news detail schema validation."""
        # Get an article ID
        list_result = llm_repository.list_news(limit=1)
        
        if not list_result["items"]:
            pytest.skip("No articles available for detail test")
        
        article_id = list_result["items"][0]["id"]
        result = llm_repository.get_news_detail(article_id)
        
        if result is None:
            pytest.skip("Article not found or filtered")
        
        # Validate required fields
        required_fields = ["id", "title", "source_name", "url", "provider"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
            assert isinstance(result[field], str), f"Field {field} must be string"
        
        # Validate optional fields if present
        optional_fields = ["published_at", "lang", "lead", "simhash", "symbols"]
        for field in optional_fields:
            if field in result:
                if field == "symbols":
                    assert isinstance(result[field], list)
                elif field == "simhash":
                    assert isinstance(result[field], (int, type(None)))
                elif field == "published_at":
                    # published_at can be datetime object or string
                    from datetime import datetime
                    assert isinstance(result[field], (str, datetime, type(None)))
                else:
                    assert isinstance(result[field], (str, type(None)))
