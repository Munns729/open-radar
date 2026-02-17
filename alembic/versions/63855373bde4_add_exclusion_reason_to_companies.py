"""add_exclusion_reason_to_companies

Revision ID: 63855373bde4
Revises: 1e4c3f8c6a08
Create Date: 2026-02-15 20:11:51.903156

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63855373bde4'
down_revision: Union[str, Sequence[str], None] = '1e4c3f8c6a08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('companies', sa.Column('exclusion_reason', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('companies', 'exclusion_reason')
