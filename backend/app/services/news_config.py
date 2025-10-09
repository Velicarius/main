"""
News configuration service with DB-backed flags and version invalidation.

This service provides a thin layer over the existing admin config system
to manage news-related feature flags with Redis-based version invalidation.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.admin.feature_flag import FeatureFlag
from app.models.admin.api_provider import ApiProvider
from app.core.news_cache import get_redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)

# In-process cache for flags
_flags_cache: Optional[Dict[str, Any]] = None
_cache_timestamp: Optional[datetime] = None
_cache_ttl_seconds = 30  # 30 second in-process cache


def get_flags(db: Session) -> Dict[str, Any]:
    """
    Get news configuration flags with in-process caching and Redis version check.
    
    Args:
        db: Database session
        
    Returns:
        Dict with news flags and version
    """
    global _flags_cache, _cache_timestamp
    
    # Check in-process cache first
    if _flags_cache and _cache_timestamp:
        age = (datetime.utcnow() - _cache_timestamp).total_seconds()
        if age < _cache_ttl_seconds:
            return _flags_cache
    
    # Check Redis version for cache invalidation
    try:
        redis_client = get_redis_client()
        redis_version = redis_client.get("config:news:version")
    except Exception as e:
        logger.warning(f"Redis version check failed: {e}")
        redis_version = None
    
    # Build flags from database
    flags = {}
    
    # Get feature flags
    feature_flags = db.query(FeatureFlag).filter(
        and_(
            FeatureFlag.key.like("NEWS_%"),
            FeatureFlag.is_enabled == True
        )
    ).all()
    
    for flag in feature_flags:
        key = flag.key.lower().replace("news_", "").replace("_", "_")
        flags[key] = flag.get_value()
    
    # Get shadow providers from ApiProvider table
    shadow_providers = []
    api_providers = db.query(ApiProvider).filter(
        and_(
            ApiProvider.type == "news",
            ApiProvider.is_shadow_mode == True,
            ApiProvider.is_deleted == False
        )
    ).all()
    
    for provider in api_providers:
        shadow_providers.append(provider.name.lower())
    
    flags["shadow_providers"] = shadow_providers
    
    # Add version
    flags["version"] = redis_version or str(uuid.uuid4())
    
    # Update in-process cache
    _flags_cache = flags
    _cache_timestamp = datetime.utcnow()
    
    logger.debug(f"Loaded news flags: {flags}")
    return flags


def set_shadow_live(db: Session, provider: str, live: bool) -> Dict[str, Any]:
    """
    Set provider shadow mode status and bump version.
    
    Args:
        db: Database session
        provider: Provider name (lowercase)
        live: True to make provider live, False for shadow mode
        
    Returns:
        Updated flags dict
    """
    try:
        # Update ApiProvider shadow mode
        api_provider = db.query(ApiProvider).filter(
            and_(
                ApiProvider.type == "news",
                ApiProvider.name == provider.lower(),
                ApiProvider.is_deleted == False
            )
        ).first()
        
        if api_provider:
            api_provider.is_shadow_mode = not live  # Shadow mode is opposite of live
            api_provider.updated_at = datetime.utcnow()
        else:
            # Create new provider if it doesn't exist
            api_provider = ApiProvider(
                type="news",
                name=provider.lower(),
                is_enabled=True,
                is_shadow_mode=not live,
                priority=100,
                timeout_seconds=10
            )
            db.add(api_provider)
        
        # Bump version in Redis
        new_version = str(uuid.uuid4())
        try:
            redis_client = get_redis_client()
            redis_client.set("config:news:version", new_version, ex=86400)  # 24h TTL
        except Exception as e:
            logger.warning(f"Failed to update Redis version: {e}")
        
        # Clear in-process cache
        global _flags_cache, _cache_timestamp
        _flags_cache = None
        _cache_timestamp = None
        
        db.commit()
        
        logger.info(f"Set provider {provider} live={live}, new version: {new_version}")
        
        # Return updated flags
        return get_flags(db)
        
    except Exception as e:
        logger.error(f"Error setting shadow live for {provider}: {e}")
        db.rollback()
        raise


def get_effective_shadow_providers(db: Session) -> List[str]:
    """
    Get list of providers currently in shadow mode.
    
    Args:
        db: Database session
        
    Returns:
        List of provider names in shadow mode
    """
    flags = get_flags(db)
    return flags.get("shadow_providers", [])


def is_provider_live(db: Session, provider: str) -> bool:
    """
    Check if a provider is live (not in shadow mode).
    
    Args:
        db: Database session
        provider: Provider name
        
    Returns:
        True if provider is live, False if in shadow mode
    """
    shadow_providers = get_effective_shadow_providers(db)
    return provider.lower() not in shadow_providers


def get_config_version() -> Optional[str]:
    """
    Get current config version from Redis.
    
    Returns:
        Version string or None if not available
    """
    try:
        redis_client = get_redis_client()
        return redis_client.get("config:news:version")
    except Exception as e:
        logger.warning(f"Failed to get config version: {e}")
        return None


def clear_config_cache():
    """Clear in-process config cache."""
    global _flags_cache, _cache_timestamp
    _flags_cache = None
    _cache_timestamp = None
    logger.debug("Cleared news config cache")

