"""
News ingestion service for storing and deduplicating news articles.

This module provides functions to normalize, deduplicate, and store news articles
from external providers into the news_articles and article_links tables.
"""

import hashlib
import re
from datetime import datetime
from typing import Dict, List, Optional, Union
from sqlalchemy import Float
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from app.models.news import NewsArticle, ArticleLink
from app.dbtypes import GUID


@dataclass
class NormalizedArticle:
    """Normalized article data structure."""
    provider: str
    source_name: Optional[str]
    url: str
    url_canonical: str
    url_hash: str
    title: Optional[str]
    lead: Optional[str]
    published_at: Optional[datetime]
    lang: Optional[str]
    simhash: Optional[int]
    raw_json: Optional[Dict]
    symbols: List[str]


def canonical_url(url: str) -> str:
    """
    Canonicalize URL by removing UTM parameters, sorting query params, 
    removing trailing slashes, and lowercasing host.
    
    Args:
        url: Original URL string
        
    Returns:
        Canonicalized URL string
    """
    if not url:
        return url
        
    try:
        parsed = urlparse(url)
        
        # Lowercase host
        host = parsed.netloc.lower()
        
        # Remove trailing slash from path
        path = parsed.path.rstrip('/')
        
        # Parse and filter query parameters
        query_params = parse_qs(parsed.query)
        
        # Remove UTM parameters
        utm_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content']
        filtered_params = {k: v for k, v in query_params.items() 
                          if k.lower() not in utm_params}
        
        # Sort parameters for consistency
        sorted_params = sorted(filtered_params.items())
        
        # Rebuild query string
        query = urlencode(sorted_params, doseq=True) if sorted_params else ''
        
        # Reconstruct URL
        canonical = urlunparse((
            parsed.scheme.lower(),
            host,
            path,
            parsed.params,
            query,
            ''  # Remove fragment
        ))
        
        return canonical
        
    except Exception:
        # If URL parsing fails, return original
        return url


def sha1_hex(s: str) -> str:
    """
    Generate SHA1 hash of string as 40-character hex string.
    
    Args:
        s: Input string
        
    Returns:
        40-character hex string
    """
    return hashlib.sha1(s.encode('utf-8')).hexdigest()


def simhash(text_content: str) -> int:
    """
    Simple token-based simhash for content deduplication.
    
    Args:
        text_content: Text content to hash
        
    Returns:
        Integer hash value
    """
    if not text_content:
        return 0
        
    # Simple tokenization - split on whitespace and punctuation
    tokens = re.findall(r'\b\w+\b', text_content.lower())
    
    if not tokens:
        return 0
    
    # Simple hash based on token frequencies
    token_counts = {}
    for token in tokens:
        token_counts[token] = token_counts.get(token, 0) + 1
    
    # Create hash from sorted token counts
    hash_input = '|'.join(f"{token}:{count}" for token, count in sorted(token_counts.items()))
    return hash(hash_input) & 0x7FFFFFFFFFFFFFFF  # Ensure positive 64-bit int


def normalize_item(item: Dict) -> NormalizedArticle:
    """
    Normalize a raw provider item into a standardized format.
    
    Args:
        item: Raw provider item dictionary
        
    Returns:
        NormalizedArticle object
    """
    # Extract basic fields
    provider = item.get('provider') or 'unknown'
    source_name = item.get('source_name') or item.get('source', {}).get('name')
    url = item.get('url', '')
    title = item.get('title')
    lead = item.get('lead') or item.get('description') or item.get('summary')
    lang = item.get('lang') or item.get('language')
    
    # Parse published_at
    published_at = None
    pub_date = item.get('published_at') or item.get('publishedAt') or item.get('date')
    if pub_date:
        try:
            if isinstance(pub_date, str):
                # Try ISO format parsing
                published_at = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
            elif isinstance(pub_date, datetime):
                published_at = pub_date
        except (ValueError, AttributeError):
            pass
    
    # Extract symbols from various possible fields
    symbols = []
    symbol_fields = ['symbols', 'tickers', 'symbol', 'ticker', 'related_symbols']
    for field in symbol_fields:
        if field in item and item[field]:
            if isinstance(item[field], list):
                symbols.extend(item[field])
            elif isinstance(item[field], str):
                symbols.append(item[field])
    
    # Canonicalize URL
    url_canonical = canonical_url(url)
    url_hash = sha1_hex(url_canonical)
    
    # Generate simhash from title + lead
    content_text = f"{title or ''} {lead or ''}".strip()
    simhash_value = simhash(content_text) if content_text else None
    
    return NormalizedArticle(
        provider=provider,
        source_name=source_name,
        url=url,
        url_canonical=url_canonical,
        url_hash=url_hash,
        title=title,
        lead=lead,
        published_at=published_at,
        lang=lang,
        simhash=simhash_value,
        raw_json=item,
        symbols=symbols
    )


def upsert_article(db: Session, normalized: NormalizedArticle) -> GUID:
    """
    Insert or update article in news_articles table.
    
    Args:
        db: Database session
        normalized: Normalized article data
        
    Returns:
        Article UUID (existing or newly created)
    """
    try:
        # Try to insert new article
        article = NewsArticle(
            provider=normalized.provider,
            source_name=normalized.source_name or 'Unknown',
            url=normalized.url,
            url_hash=normalized.url_hash,
            title=normalized.title or 'Untitled',
            lead=normalized.lead,
            published_at=normalized.published_at or datetime.utcnow(),
            lang=normalized.lang,
            simhash=normalized.simhash,
            raw_json=normalized.raw_json
        )
        
        db.add(article)
        db.flush()  # Get the ID without committing
        return article.id
        
    except IntegrityError:
        # Article already exists, get existing ID
        db.rollback()
        
        # Find existing article by url or url_hash
        existing = db.query(NewsArticle).filter(
            (NewsArticle.url == normalized.url) | 
            (NewsArticle.url_hash == normalized.url_hash)
        ).first()
        
        if existing:
            return existing.id
        else:
            # This shouldn't happen, but handle gracefully
            raise


def link_symbols(db: Session, article_id: GUID, symbols: List[str]) -> int:
    """
    Link article to symbols in article_links table.
    
    Args:
        db: Database session
        article_id: Article UUID
        symbols: List of symbol strings
        
    Returns:
        Number of links created (excluding duplicates)
    """
    if not symbols:
        return 0
    
    links_created = 0
    
    for symbol in symbols:
        if not symbol or not symbol.strip():
            continue
            
        symbol = symbol.strip().upper()
        
        try:
            link = ArticleLink(
                article_id=article_id,
                symbol=symbol,
                relevance_score=1.0
            )
            
            db.add(link)
            db.flush()
            links_created += 1
            
        except IntegrityError:
            # Link already exists, ignore
            db.rollback()
            continue
    
    return links_created


def ingest_articles(
    db: Session, 
    provider: str, 
    items: List[Dict], 
    default_symbols: Optional[List[str]] = None
) -> Dict[str, int]:
    """
    Ingest multiple articles from a provider.
    
    Args:
        db: Database session
        provider: Provider name
        items: List of raw provider items
        default_symbols: Fallback symbols if item has none
        
    Returns:
        Summary dictionary with counts
    """
    inserted = 0
    linked = 0
    duplicates = 0
    
    for item in items:
        # Add provider to item if not present
        if 'provider' not in item:
            item['provider'] = provider
        
        try:
            # Normalize the item
            normalized = normalize_item(item)
            
            # Use default symbols if none provided
            if not normalized.symbols and default_symbols:
                normalized.symbols = default_symbols.copy()
            
            # Upsert article
            article_id = upsert_article(db, normalized)
            
            # Check if this was a duplicate by checking if article was just created
            # If the article was created in the last few seconds, it's new
            from datetime import timedelta
            import pytz
            
            # Make both datetimes timezone-aware for comparison
            utc = pytz.UTC
            recent_threshold = utc.localize(datetime.utcnow() - timedelta(seconds=5))
            
            existing_article = db.query(NewsArticle).filter(
                NewsArticle.id == article_id
            ).first()
            
            if existing_article and existing_article.created_at < recent_threshold:
                # Article existed before this operation
                duplicates += 1
            else:
                inserted += 1
            
            # Link symbols
            links_created = link_symbols(db, article_id, normalized.symbols)
            linked += links_created
            
        except Exception as e:
            # Log error but continue processing other items
            print(f"Error processing item: {e}")
            continue
    
    return {
        "inserted": inserted,
        "linked": linked,
        "duplicates": duplicates
    }
