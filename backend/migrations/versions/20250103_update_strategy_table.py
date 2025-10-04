"""update strategy table with new fields

Revision ID: 20250103_update_strategy_table
Revises: f274e7ea9f79
Create Date: 2025-01-03 19:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20250103_update_strategy_table'
down_revision: Union[str, None] = 'f274e7ea9f79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update strategy table with new fields for manual strategy mode"""
    
    # Add new columns to existing strategies table
    op.add_column('strategies', sa.Column('base_currency', sa.String(length=3), nullable=True, default='USD'))
    
    # Goal settings
    op.add_column('strategies', sa.Column('target_value', sa.Numeric(precision=18, scale=2), nullable=True))
    op.add_column('strategies', sa.Column('target_date', sa.Date(), nullable=True))
    
    # Risk and return parameters
    op.add_column('strategies', sa.Column('risk_level', sa.String(), nullable=True))
    op.add_column('strategies', sa.Column('expected_return', sa.Numeric(precision=6, scale=3), nullable=True))
    op.add_column('strategies', sa.Column('volatility', sa.Numeric(precision=6, scale=3), nullable=True))
    op.add_column('strategies', sa.Column('max_drawdown', sa.Numeric(precision=6, scale=3), nullable=True))
    
    # Contribution and rebalancing
    op.add_column('strategies', sa.Column('monthly_contribution', sa.Numeric(precision=18, scale=2), nullable=True))
    op.add_column('strategies', sa.Column('rebalancing_frequency', sa.String(), nullable=False, server_default='none'))
    
    # Portfolio allocation and constraints (JSONB)
    op.add_column('strategies', sa.Column('allocation', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'))
    op.add_column('strategies', sa.Column('constraints', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'))
    
    # Create unique index on user_id
    op.create_index('idx_strategies_user_id', 'strategies', ['user_id'], unique=True)


def downgrade() -> None:
    """Remove new fields from strategy table"""
    
    # Drop index
    op.drop_index('idx_strategies_user_id', table_name='strategies')
    
    # Drop added columns
    op.drop_column('strategies', 'constraints')
    op.drop_column('strategies', 'allocation')
    op.drop_column('strategies', 'rebalancing_frequency')
    op.drop_column('strategies', 'monthly_contribution')
    op.drop_column('strategies', 'max_drawdown')
    op.drop_column('strategies', 'volatility')
    op.drop_column('strategies', 'expected_return')
    op.drop_column('strategies', 'risk_level')
    op.drop_column('strategies', 'target_date')
    op.drop_column('strategies', 'target_value')
    op.drop_column('strategies', 'base_currency')
    
