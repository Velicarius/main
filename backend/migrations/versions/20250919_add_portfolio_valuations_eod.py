"""add portfolio_valuations_eod table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ревизии
revision = "b1c2d3e4f5a6"
down_revision = "08ade06df775"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_valuations_eod",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("total_value", sa.Numeric(20, 8), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_pv_user_asof", "portfolio_valuations_eod", ["user_id", "as_of"])
    op.create_index("ix_pv_asof", "portfolio_valuations_eod", ["as_of"])
    op.create_unique_constraint(
        "uq_portfolio_valuations_eod_user_asof",
        "portfolio_valuations_eod",
        ["user_id", "as_of"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_portfolio_valuations_eod_user_asof", "portfolio_valuations_eod", type_="unique")
    op.drop_index("ix_pv_asof", table_name="portfolio_valuations_eod")
    op.drop_index("ix_pv_user_asof", table_name="portfolio_valuations_eod")
    op.drop_table("portfolio_valuations_eod")
