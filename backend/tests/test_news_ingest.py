"""
Tests for news ingestion functionality.

Tests the news ingestion service and API endpoint for storing
and deduplicating news articles from external providers.
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.news_ingest import (
    canonical_url, sha1_hex, simhash, normalize_item, 
    upsert_article, link_symbols, ingest_articles
)
from app.models.news import NewsArticle, ArticleLink


class TestNewsIngestService:
    """Test the news ingestion service functions."""
    
    def test_canonical_url(self):
        """Test URL canonicalization."""
        # Test UTM parameter removal
        url = "https://example.com/article?utm_source=google&utm_medium=cpc&param=value"
        canonical = canonical_url(url)
        assert canonical == "https://example.com/article?param=value"
        
        # Test trailing slash removal
        url = "https://example.com/article/"
        canonical = canonical_url(url)
        assert canonical == "https://example.com/article"
        
        # Test host lowercasing
        url = "https://EXAMPLE.COM/Article"
        canonical = canonical_url(url)
        assert canonical == "https://example.com/Article"
        
        # Test parameter sorting
        url = "https://example.com/article?z=last&a=first"
        canonical = canonical_url(url)
        assert canonical == "https://example.com/article?a=first&z=last"
        
        # Test fragment removal
        url = "https://example.com/article#section"
        canonical = canonical_url(url)
        assert canonical == "https://example.com/article"
    
    def test_sha1_hex(self):
        """Test SHA1 hash generation."""
        result = sha1_hex("test string")
        assert len(result) == 40
        assert result == "661295c9cbf9d6b2f6428414504a8deed3020641"
        
        # Test empty string
        result = sha1_hex("")
        assert len(result) == 40
        assert result == "da39a3ee5e6b4b0d3255bfef95601890afd80709"
    
    def test_simhash(self):
        """Test simhash generation."""
        # Test basic functionality
        result = simhash("Apple reports strong earnings")
        assert isinstance(result, int)
        assert result > 0
        
        # Test identical content produces same hash
        text = "Apple reports strong earnings"
        hash1 = simhash(text)
        hash2 = simhash(text)
        assert hash1 == hash2
        
        # Test different content produces different hash
        hash3 = simhash("Microsoft reports weak earnings")
        assert hash1 != hash3
        
        # Test empty string
        result = simhash("")
        assert result == 0
    
    def test_normalize_item(self):
        """Test article normalization."""
        item = {
            "provider": "newsapi",
            "source_name": "Reuters",
            "url": "https://example.com/news/1?utm_source=google",
            "title": "Apple Reports Strong Q4 Results",
            "lead": "Apple exceeded expectations with strong iPhone sales",
            "published_at": "2024-01-15T10:30:00Z",
            "lang": "en",
            "symbols": ["AAPL", "MSFT"]
        }
        
        normalized = normalize_item(item)
        
        assert normalized.provider == "newsapi"
        assert normalized.source_name == "Reuters"
        assert normalized.url == "https://example.com/news/1?utm_source=google"
        assert normalized.url_canonical == "https://example.com/news/1"
        assert normalized.url_hash == sha1_hex("https://example.com/news/1")
        assert normalized.title == "Apple Reports Strong Q4 Results"
        assert normalized.lead == "Apple exceeded expectations with strong iPhone sales"
        assert isinstance(normalized.published_at, datetime)
        assert normalized.lang == "en"
        assert isinstance(normalized.simhash, int)
        assert normalized.symbols == ["AAPL", "MSFT"]
        assert normalized.raw_json == item
    
    def test_upsert_article(self, db_session: Session):
        """Test article upsert functionality."""
        # Create normalized article
        normalized = normalize_item({
            "provider": "test",
            "url": "https://example.com/test",
            "title": "Test Article",
            "published_at": "2024-01-15T10:30:00Z"
        })
        
        # First insert should succeed
        article_id1 = upsert_article(db_session, normalized)
        assert article_id1 is not None
        
        # Verify article was inserted
        article = db_session.query(NewsArticle).filter(NewsArticle.id == article_id1).first()
        assert article is not None
        assert article.title == "Test Article"
        assert article.url == "https://example.com/test"
        
        # Second insert with same URL should return existing ID
        article_id2 = upsert_article(db_session, normalized)
        assert article_id1 == article_id2
        
        # Verify only one article exists
        count = db_session.query(NewsArticle).count()
        assert count == 1
    
    def test_link_symbols(self, db_session: Session):
        """Test symbol linking functionality."""
        # Create an article first
        normalized = normalize_item({
            "provider": "test",
            "url": "https://example.com/test",
            "title": "Test Article"
        })
        article_id = upsert_article(db_session, normalized)
        
        # Link symbols
        symbols = ["AAPL", "MSFT", "GOOGL"]
        links_created = link_symbols(db_session, article_id, symbols)
        assert links_created == 3
        
        # Verify links were created
        links = db_session.query(ArticleLink).filter(ArticleLink.article_id == article_id).all()
        assert len(links) == 3
        
        symbol_list = [link.symbol for link in links]
        assert set(symbol_list) == {"AAPL", "MSFT", "GOOGL"}
        
        # Test duplicate linking (should be ignored)
        links_created2 = link_symbols(db_session, article_id, ["AAPL", "NVDA"])
        assert links_created2 == 1  # Only NVDA should be added
        
        # Verify total links
        links = db_session.query(ArticleLink).filter(ArticleLink.article_id == article_id).all()
        assert len(links) == 4
    
    def test_ingest_articles(self, db_session: Session):
        """Test full article ingestion."""
        items = [
            {
                "url": "https://example.com/news/1",
                "title": "Apple Reports Strong Results",
                "published_at": "2024-01-15T10:30:00Z",
                "symbols": ["AAPL"]
            },
            {
                "url": "https://example.com/news/2",
                "title": "Microsoft Earnings Beat",
                "published_at": "2024-01-15T11:00:00Z",
                "symbols": ["MSFT"]
            }
        ]
        
        result = ingest_articles(
            db_session, 
            "test_provider", 
            items, 
            default_symbols=["NVDA"]
        )
        
        assert result["inserted"] == 2
        assert result["linked"] == 2
        assert result["duplicates"] == 0
        
        # Verify articles were inserted
        articles = db_session.query(NewsArticle).all()
        assert len(articles) == 2
        
        # Verify links were created
        links = db_session.query(ArticleLink).all()
        assert len(links) == 2
        
        # Test duplicate ingestion
        result2 = ingest_articles(
            db_session, 
            "test_provider", 
            items[:1],  # Same first item
            default_symbols=["NVDA"]
        )
        
        assert result2["inserted"] == 0
        assert result2["linked"] == 0
        assert result2["duplicates"] == 1
        
        # Verify no new articles were created
        articles = db_session.query(NewsArticle).all()
        assert len(articles) == 2


class TestNewsIngestAPI:
    """Test the news ingestion API endpoint."""
    
    def test_ingest_endpoint_success(self, client):
        """Test successful news ingestion via API."""
        payload = {
            "provider": "test_provider",
            "items": [
                {
                    "url": "https://example.com/news/1",
                    "title": "Apple Reports Strong Results",
                    "lead": "Apple exceeded expectations",
                    "published_at": "2024-01-15T10:30:00Z",
                    "source_name": "Reuters",
                    "symbols": ["AAPL"]
                }
            ],
            "default_symbols": ["NVDA"]
        }
        
        response = client.post("/internal/news/ingest", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["inserted"] == 1
        assert data["linked"] == 1
        assert data["duplicates"] == 0
        assert data["total_processed"] == 1
    
    def test_ingest_endpoint_duplicate(self, client):
        """Test duplicate article handling via API."""
        payload = {
            "provider": "test_provider",
            "items": [
                {
                    "url": "https://example.com/news/1",
                    "title": "Apple Reports Strong Results",
                    "symbols": ["AAPL"]
                }
            ]
        }
        
        # First request
        response1 = client.post("/internal/news/ingest", json=payload)
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["inserted"] == 1
        assert data1["duplicates"] == 0
        
        # Second request with same URL
        response2 = client.post("/internal/news/ingest", json=payload)
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["inserted"] == 0
        assert data2["duplicates"] == 1
    
    def test_ingest_endpoint_canonicalization(self, client):
        """Test URL canonicalization via API."""
        payload = {
            "provider": "test_provider",
            "items": [
                {
                    "url": "https://example.com/news/1?utm_source=google",
                    "title": "First Article",
                    "symbols": ["AAPL"]
                },
                {
                    "url": "https://example.com/news/1?utm_medium=cpc",
                    "title": "Second Article",
                    "symbols": ["MSFT"]
                }
            ]
        }
        
        response = client.post("/internal/news/ingest", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        # Should be treated as duplicates due to canonicalization
        assert data["inserted"] == 1
        assert data["duplicates"] == 1
    
    def test_ingest_endpoint_default_symbols(self, client):
        """Test default symbols fallback via API."""
        payload = {
            "provider": "test_provider",
            "items": [
                {
                    "url": "https://example.com/news/1",
                    "title": "Article without symbols"
                }
            ],
            "default_symbols": ["NVDA", "AMD"]
        }
        
        response = client.post("/internal/news/ingest", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["inserted"] == 1
        assert data["linked"] == 2  # Should link to both default symbols
    
    def test_ingest_endpoint_validation(self, client):
        """Test input validation via API."""
        # Test empty URL
        payload = {
            "provider": "test_provider",
            "items": [
                {
                    "url": "",
                    "title": "Invalid Article"
                }
            ]
        }
        
        response = client.post("/internal/news/ingest", json=payload)
        assert response.status_code == 422
        
        # Test invalid URL
        payload = {
            "provider": "test_provider",
            "items": [
                {
                    "url": "not-a-url",
                    "title": "Invalid Article"
                }
            ]
        }
        
        response = client.post("/internal/news/ingest", json=payload)
        assert response.status_code == 422
        
        # Test too many items
        payload = {
            "provider": "test_provider",
            "items": [{"url": f"https://example.com/news/{i}", "title": f"Article {i}"} 
                     for i in range(201)]  # Exceeds 200 limit
        }
        
        response = client.post("/internal/news/ingest", json=payload)
        assert response.status_code == 422
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/internal/news/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "news-ingest"

