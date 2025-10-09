"""add_date_added_column

Revision ID: b6fa8d7a469d
Revises: e5d50769eb01
Create Date: 2025-10-03 23:34:30.372342

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6fa8d7a469d'
down_revision: Union[str, None] = 'e5d50769eb01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add date_added column to positions table
    op.add_column('positions', sa.Column('date_added', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))


def downgrade() -> None:
    # Remove date_added column from positions table
    op.drop_column('positions', 'date_added')



