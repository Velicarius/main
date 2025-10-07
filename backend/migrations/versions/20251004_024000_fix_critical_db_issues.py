"""Fix critical database issues

Revision ID: df770ab4831a
Revises: b6fa8d7a469d
Create Date: 2025-10-04 02:40:00.000000

Changes:
1. Fix prices_eod.id type from CHAR(36) to UUID
2. Add index on positions.user_id for better JOIN performance
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'df770ab4831a'
down_revision = 'b6fa8d7a469d'
branch_labels = None
depends_on = None


def upgrade():
    """Fix critical database issues"""
    
    # 1. Исправить тип prices_eod.id: CHAR(36) -> UUID
    op.alter_column(
        'prices_eod',
        'id',
        type_=postgresql.UUID(),
        postgresql_using='id::uuid',
        existing_nullable=False
    )
    
    # 2. Добавить индекс на positions.user_id для улучшения производительности JOIN
    op.create_index(
        'ix_positions_user_id',
        'positions',
        ['user_id'],
        unique=False
    )


def downgrade():
    """Rollback critical database fixes"""
    
    # Откат в обратном порядке
    
    # 2. Удалить индекс
    op.drop_index('ix_positions_user_id', table_name='positions')
    
    # 1. Вернуть CHAR(36)
    op.alter_column(
        'prices_eod',
        'id',
        type_=sa.CHAR(36),
        postgresql_using='id::text',
        existing_nullable=False
    )


