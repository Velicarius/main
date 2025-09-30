"""add_prices_eod_table

Revision ID: 08ade06df775
Revises: f30eed726612
Create Date: 2025-09-16 13:13:04.884580

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08ade06df775'
down_revision: Union[str, None] = 'f30eed726612'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create prices_eod table
    op.create_table('prices_eod',
        sa.Column('id', sa.CHAR(length=36), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('open', sa.Float(), nullable=True),
        sa.Column('high', sa.Float(), nullable=True),
        sa.Column('low', sa.Float(), nullable=True),
        sa.Column('close', sa.Float(), nullable=False),
        sa.Column('volume', sa.Float(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('ingested_at', sa.DateTime(timezone=False), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_price_eod_symbol_date', 'prices_eod', ['symbol', 'date'], unique=False)
    op.create_index('ix_price_eod_date', 'prices_eod', ['date'], unique=False)
    op.create_index(op.f('ix_prices_eod_symbol'), 'prices_eod', ['symbol'], unique=False)
    
    # Create unique constraint
    op.create_unique_constraint('uq_price_eod_symbol_date', 'prices_eod', ['symbol', 'date'])


def downgrade() -> None:
    # Drop unique constraint
    op.drop_constraint('uq_price_eod_symbol_date', 'prices_eod', type_='unique')
    
    # Drop indexes
    op.drop_index(op.f('ix_prices_eod_symbol'), table_name='prices_eod')
    op.drop_index('ix_price_eod_date', table_name='prices_eod')
    op.drop_index('ix_price_eod_symbol_date', table_name='prices_eod')
    
    # Drop table
    op.drop_table('prices_eod')
