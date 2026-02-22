"""add_revenue_source_to_companies

Revision ID: a1b2c3d4e5f6
Revises: 63855373bde4
Create Date: 2026-02-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '408bb192a7ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add revenue_source to track provenance of revenue_gbp."""
    op.add_column(
        'companies',
        sa.Column('revenue_source', sa.String(50), nullable=True)
    )


def downgrade() -> None:
    """Remove revenue_source column."""
    op.drop_column('companies', 'revenue_source')
