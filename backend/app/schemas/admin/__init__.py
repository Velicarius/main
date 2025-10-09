"""
Admin Pydantic schemas for API
"""
from .api_provider import (
    ApiProviderBase,
    ApiProviderCreate,
    ApiProviderUpdate,
    ApiProviderSchema,
    ApiCredentialBase,
    ApiCredentialCreate,
    ApiCredentialUpdate,
    ApiCredentialSchema,
)
from .rate_limit import (
    RateLimitBase,
    RateLimitCreate,
    RateLimitUpdate,
    RateLimitSchema,
    QuotaBase,
    QuotaCreate,
    QuotaUpdate,
    QuotaSchema,
)
from .plan import (
    PlanBase,
    PlanCreate,
    PlanUpdate,
    PlanSchema,
)
from .feature_flag import (
    FeatureFlagBase,
    FeatureFlagCreate,
    FeatureFlagUpdate,
    FeatureFlagSchema,
)
from .schedule import (
    ScheduleBase,
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleSchema,
)
from .cache_policy import (
    CachePolicyBase,
    CachePolicyCreate,
    CachePolicyUpdate,
    CachePolicySchema,
)
from .audit_log import (
    AuditLogSchema,
)
from .system_setting import (
    SystemSettingBase,
    SystemSettingCreate,
    SystemSettingUpdate,
    SystemSettingSchema,
)

__all__ = [
    # API Providers
    "ApiProviderBase",
    "ApiProviderCreate",
    "ApiProviderUpdate",
    "ApiProviderSchema",
    "ApiCredentialBase",
    "ApiCredentialCreate",
    "ApiCredentialUpdate",
    "ApiCredentialSchema",
    # Rate Limits
    "RateLimitBase",
    "RateLimitCreate",
    "RateLimitUpdate",
    "RateLimitSchema",
    "QuotaBase",
    "QuotaCreate",
    "QuotaUpdate",
    "QuotaSchema",
    # Plans
    "PlanBase",
    "PlanCreate",
    "PlanUpdate",
    "PlanSchema",
    # Feature Flags
    "FeatureFlagBase",
    "FeatureFlagCreate",
    "FeatureFlagUpdate",
    "FeatureFlagSchema",
    # Schedules
    "ScheduleBase",
    "ScheduleCreate",
    "ScheduleUpdate",
    "ScheduleSchema",
    # Cache Policies
    "CachePolicyBase",
    "CachePolicyCreate",
    "CachePolicyUpdate",
    "CachePolicySchema",
    # Audit Log
    "AuditLogSchema",
    # System Settings
    "SystemSettingBase",
    "SystemSettingCreate",
    "SystemSettingUpdate",
    "SystemSettingSchema",
]
