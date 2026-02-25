"""add vc holding status (current vs exited)

Revision ID: d6e7f8a9b0c1
Revises: c4d5e6f7a8b9
Create Date: 2026-02-25

Add holding_status ('current' | 'exited') and optional exited_at to company_vc_holdings.
"""
from alembic import op
import sqlalchemy as sa

revision = "d6e7f8a9b0c1"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "company_vc_holdings",
        sa.Column("holding_status", sa.String(20), nullable=False, server_default="current"),
    )
    op.add_column(
        "company_vc_holdings",
        sa.Column("exited_at", sa.Date(), nullable=True),
    )
    op.create_index(
        "idx_company_vc_holdings_status",
        "company_vc_holdings",
        ["holding_status"],
    )


def downgrade() -> None:
    op.drop_index("idx_company_vc_holdings_status", "company_vc_holdings")
    op.drop_column("company_vc_holdings", "exited_at")
    op.drop_column("company_vc_holdings", "holding_status")
