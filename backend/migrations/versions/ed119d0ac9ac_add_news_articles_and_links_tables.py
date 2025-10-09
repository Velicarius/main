"""add_news_articles_and_links_tables

Revision ID: ed119d0ac9ac
Revises: 1e5845412953
Create Date: 2025-10-08 11:41:12.247525

RECONNAISSANCE REPORT:
- Docker Postgres service: 'postgres' (infra-postgres-1)
- Database URL: postgresql://postgres:postgres@postgres:5432/postgres
- Alembic path: backend/migrations/
- Base: app.models.base.Base
- Symbol linking: positions.symbol (String) - no dedicated symbols table
- No existing news tables found - safe to create
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ed119d0ac9ac'
down_revision: Union[str, None] = '1e5845412953'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create news_articles table
    op.execute("""
        CREATE TABLE IF NOT EXISTS news_articles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            provider VARCHAR NOT NULL,
            source_name VARCHAR NOT NULL,
            url TEXT UNIQUE NOT NULL,
            url_hash VARCHAR(40) UNIQUE NOT NULL,
            title TEXT NOT NULL,
            lead TEXT,
            published_at TIMESTAMPTZ NOT NULL,
            lang VARCHAR(5) DEFAULT 'en',
            simhash BIGINT,
            raw_json JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    
    # Create indexes for news_articles
    op.execute("CREATE INDEX IF NOT EXISTS ix_news_articles_published_at ON news_articles (published_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_news_articles_simhash ON news_articles (simhash)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_news_articles_provider ON news_articles (provider)")
    
    # Create article_links table
    op.execute("""
        CREATE TABLE IF NOT EXISTS article_links (
            article_id UUID NOT NULL,
            symbol VARCHAR NOT NULL,
            relevance_score REAL,
            PRIMARY KEY (article_id, symbol),
            FOREIGN KEY (article_id) REFERENCES news_articles(id) ON DELETE CASCADE
        )
    """)
    
    # Create index for article_links
    op.execute("CREATE INDEX IF NOT EXISTS ix_article_links_symbol ON article_links (symbol)")


def downgrade() -> None:
    # Drop tables in reverse order (FK dependencies)
    op.execute("DROP TABLE IF EXISTS article_links")
    op.execute("DROP TABLE IF EXISTS news_articles")

