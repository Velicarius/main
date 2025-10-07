"""Add asset_class to positions

Revision ID: 20250115_add_asset_class
Revises: f30eed726612
Create Date: 2025-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250115_add_asset_class'
down_revision: Union[str, None] = 'f30eed726612'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add asset_class column with default value (enum already exists)
    op.execute("ALTER TABLE positions ADD COLUMN IF NOT EXISTS asset_class assetclass NOT NULL DEFAULT 'EQUITY'")


def downgrade() -> None:
    # Drop asset_class column
    op.drop_column('positions', 'asset_class')
    
    # Drop enum type
    asset_class_enum = sa.Enum('EQUITY', 'CRYPTO', name='assetclass')
    asset_class_enum.drop(op.get_bind())
