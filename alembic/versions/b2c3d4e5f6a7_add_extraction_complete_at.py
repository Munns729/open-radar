"""add_extraction_complete_at_to_companies

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add extraction_complete_at to mark companies that have completed Extraction & Enrichment."""
    op.add_column(
        'companies',
        sa.Column('extraction_complete_at', sa.DateTime(), nullable=True)
    )
    # Backfill: companies with raw_website_text have already been through extraction
    op.execute("""
        UPDATE companies
        SET extraction_complete_at = last_updated
        WHERE raw_website_text IS NOT NULL AND extraction_complete_at IS NULL
    """)


def downgrade() -> None:
    """Remove extraction_complete_at column."""
    op.drop_column('companies', 'extraction_complete_at')
