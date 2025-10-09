"""merge_heads_before_news_tables

Revision ID: 1e5845412953
Revises: 20250115_add_asset_class, df770ab4831a
Create Date: 2025-10-08 11:41:03.303611

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e5845412953'
down_revision: Union[str, None] = ('20250115_add_asset_class', 'df770ab4831a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

