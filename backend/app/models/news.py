"""
News articles and links models for auto-curated news feature.

RECONNAISSANCE REPORT:
- Docker Postgres service: 'postgres' (infra-postgres-1)
- Database URL: postgresql://postgres:postgres@postgres:5432/postgres
- Alembic path: backend/migrations/
- Base: app.models.base.Base
- Symbol linking: positions.symbol (String) - no dedicated symbols table
- No existing news tables found - safe to create
"""

from sqlalchemy import Column, String, Text, DateTime, BigInteger, Index, ForeignKey, Float, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import TIMESTAMP
from sqlalchemy.orm import relationship
from app.dbtypes import GUID
import uuid
from datetime import datetime
from .base import Base


class NewsArticle(Base):
    """
    News articles from various providers.
    
    Stores normalized news articles with deduplication via url_hash and simhash.
    """
    __tablename__ = "news_articles"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    provider = Column(String, nullable=False)  # e.g., "newsapi", "alphavantage"
    source_name = Column(String, nullable=False)  # e.g., "Reuters", "Bloomberg"
    url = Column(Text, unique=True, nullable=False)  # Original article URL
    url_hash = Column(String(40), unique=True, nullable=False)  # SHA1 of canonical URL
    title = Column(Text, nullable=False)
    lead = Column(Text, nullable=True)  # Article summary/lead
    published_at = Column(TIMESTAMP(timezone=True), nullable=False)
    lang = Column(String(5), nullable=True, default="en")  # ISO language code
    simhash = Column(BigInteger, nullable=True)  # For content deduplication
    raw_json = Column(JSONB, nullable=True)  # Original provider response
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.utcnow())

    # Relationships
    article_links = relationship("ArticleLink", back_populates="article", cascade="all, delete-orphan")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_news_articles_published_at", "published_at"),
        Index("ix_news_articles_simhash", "simhash"),
        Index("ix_news_articles_provider", "provider"),
    )


class ArticleLink(Base):
    """
    Links between news articles and portfolio symbols.
    
    Establishes relevance relationships between articles and symbols
    found in user positions.
    """
    __tablename__ = "article_links"

    article_id = Column(GUID(), ForeignKey("news_articles.id", ondelete="CASCADE"), primary_key=True)
    symbol = Column(String, nullable=False)  # References positions.symbol
    relevance_score = Column(Float, nullable=True)  # 0.0-1.0 relevance score

    # Relationships
    article = relationship("NewsArticle", back_populates="article_links")

    # Composite primary key
    __table_args__ = (
        UniqueConstraint("article_id", "symbol", name="uq_article_links_article_symbol"),
        Index("ix_article_links_symbol", "symbol"),
    )
