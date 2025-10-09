"""admin_002_mark_tables_created

Revision ID: f7a62a0df058
Revises: admin_001
Create Date: 2025-10-08 20:51:07.953468

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a62a0df058'
down_revision: Union[str, None] = 'admin_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # All admin tables were already created manually:
    # - api_providers ✅
    # - api_credentials ✅  
    # - rate_limits ✅
    # - quotas ✅
    # - plans ✅
    # - feature_flags ✅
    # - schedules ✅
    # - cache_policies ✅
    # - audit_log ✅
    # - system_settings ✅
    # 
    # This migration serves as a marker that all admin tables are in place.
    # No DDL operations needed.
    pass


def downgrade() -> None:
    # No downgrade needed - tables were created manually
    pass
