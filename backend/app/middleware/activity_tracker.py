"""
Activity Tracker Middleware
Logs all user API requests to user_activity_log table for analytics and auditing
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user_activity_log import UserActivityLog
from app.core.jwt_auth import JWTAuth
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class ActivityTrackerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track user API activity

    Features:
    - Logs endpoint, method, status code, response time
    - Extracts user_id from JWT token
    - Identifies provider from endpoint path
    - Non-blocking async logging
    - Skips health checks and static files
    """

    # Endpoints to skip (health checks, static files, etc)
    SKIP_PATHS = {
        '/health',
        '/docs',
        '/openapi.json',
        '/redoc',
        '/ui/',
    }

    # Provider mapping from endpoint patterns
    PROVIDER_MAPPING = {
        '/news': 'news',
        '/crypto': 'crypto',
        '/ai': 'llm',
        '/llm': 'llm',
        '/symbols/external': 'market_data',
        '/prices': 'market_data',
        '/portfolio': 'portfolio_analytics',
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log activity"""
        # Skip tracking for certain paths
        if self._should_skip(request.url.path):
            return await call_next(request)

        # Extract user_id from JWT (if available)
        user_id = self._extract_user_id(request)

        # Only track authenticated requests
        if not user_id:
            return await call_next(request)

        # Track request timing
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)

        # Log activity asynchronously (non-blocking)
        try:
            self._log_activity(
                user_id=user_id,
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                provider=self._detect_provider(request.url.path),
                request_metadata=self._build_metadata(request)
            )
        except Exception as e:
            # Don't let logging errors break the request
            logger.error(f"Failed to log activity: {e}", exc_info=True)

        return response

    def _should_skip(self, path: str) -> bool:
        """Check if path should be skipped"""
        for skip_path in self.SKIP_PATHS:
            if path.startswith(skip_path):
                return True
        return False

    def _extract_user_id(self, request: Request) -> uuid.UUID | None:
        """Extract user_id from JWT token"""
        try:
            # Get Authorization header
            auth_header = request.headers.get('Authorization', '')

            if not auth_header.startswith('Bearer '):
                return None

            token = auth_header[7:]  # Remove 'Bearer ' prefix

            # Decode JWT
            token_data = JWTAuth.decode_token(token)

            return token_data.user_id
        except Exception:
            # Token invalid or not present
            return None

    def _detect_provider(self, path: str) -> str | None:
        """Detect which provider the endpoint belongs to"""
        for pattern, provider in self.PROVIDER_MAPPING.items():
            if path.startswith(pattern):
                return provider
        return None

    def _build_metadata(self, request: Request) -> dict:
        """Build request metadata for logging"""
        return {
            'query_params': dict(request.query_params) if request.query_params else None,
            'user_agent': request.headers.get('user-agent'),
            'ip_address': request.client.host if request.client else None,
        }

    def _log_activity(
        self,
        user_id: uuid.UUID,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: int,
        provider: str | None,
        request_metadata: dict
    ):
        """Log activity to database (synchronous, but fast)"""
        db: Session = SessionLocal()
        try:
            activity_log = UserActivityLog(
                user_id=user_id,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time_ms=response_time_ms,
                provider=provider,
                request_metadata=request_metadata,
                timestamp=datetime.utcnow()
            )

            db.add(activity_log)
            db.commit()

            logger.debug(f"Logged activity for user {user_id}: {method} {endpoint} - {status_code} ({response_time_ms}ms)")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to log activity: {e}", exc_info=True)
        finally:
            db.close()
