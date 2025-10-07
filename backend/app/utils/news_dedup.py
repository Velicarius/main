"""
News deduplication utility using canonical keys
"""
import hashlib
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def generate_canonical_hash(canonical_key: str) -> str:
    """
    Generate SHA-1 hash from canonical key

    Args:
        canonical_key: Deduplication key (e.g., "title|domain")

    Returns:
        SHA-1 hash string (40 characters)
    """
    return hashlib.sha1(canonical_key.encode("utf-8")).hexdigest()


def deduplicate_articles(
    articles: List[Dict[str, Any]],
    preserve_order: bool = True
) -> List[Dict[str, Any]]:
    """
    Deduplicate articles using canonical_key field

    Args:
        articles: List of normalized article dicts with 'canonical_key' field
        preserve_order: If True, keep first occurrence; if False, arbitrary order

    Returns:
        Deduplicated list of articles with 'id' field set to SHA-1 hash
    """
    seen_hashes = set()
    deduplicated = []

    for article in articles:
        canonical_key = article.get("canonical_key", "")

        if not canonical_key:
            logger.warning("Article missing canonical_key, skipping")
            continue

        # Generate SHA-1 hash
        article_hash = generate_canonical_hash(canonical_key)

        # Skip if already seen
        if article_hash in seen_hashes:
            logger.debug(f"Duplicate article found: {article.get('title', '')[:50]}")
            continue

        # Add to result
        seen_hashes.add(article_hash)
        article["id"] = article_hash
        deduplicated.append(article)

    logger.info(f"Deduplication: {len(articles)} → {len(deduplicated)} articles")
    return deduplicated


def merge_provider_results(
    provider_results: Dict[str, List[Dict[str, Any]]],
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Merge and deduplicate results from multiple providers

    Args:
        provider_results: Dict mapping provider name to list of normalized articles
        limit: Maximum number of articles to return after deduplication

    Returns:
        Deduplicated and sorted list of articles (newest first)
    """
    # Flatten all articles
    all_articles = []
    for provider, articles in provider_results.items():
        all_articles.extend(articles)

    # Deduplicate
    deduplicated = deduplicate_articles(all_articles)

    # Sort by published_at (newest first)
    deduplicated.sort(
        key=lambda x: x.get("published_at", ""),
        reverse=True
    )

    # Limit results
    return deduplicated[:limit]
