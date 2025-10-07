"""merge_heads

Revision ID: ef7c9bbbced4
Revises: 20250103_update_strategy_table, b1c2d3e4f5a6, f4a3d8b9c123_add_usd_balance
Create Date: 2025-10-03 23:32:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef7c9bbbced4'
down_revision: Union[str, None] = ('20250103_update_strategy_table', 'b1c2d3e4f5a6', 'f4a3d8b9c123_add_usd_balance')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass


