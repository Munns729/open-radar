"""add_risk_level_to_tracking_alerts

Revision ID: a054567d313e
Revises: 823def1a6467
Create Date: 2026-02-23 22:49:46.804639

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a054567d313e'
down_revision: Union[str, Sequence[str], None] = '823def1a6467'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add risk_level and context_summary to tracking_alerts."""
    op.add_column(
        'tracking_alerts',
        sa.Column('risk_level', sa.String(length=20), server_default='low', nullable=False),
    )
    op.add_column(
        'tracking_alerts',
        sa.Column('context_summary', sa.Text(), nullable=True),
    )
    op.create_index(op.f('ix_tracking_alerts_risk_level'), 'tracking_alerts', ['risk_level'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_tracking_alerts_risk_level'), table_name='tracking_alerts')
    op.drop_column('tracking_alerts', 'context_summary')
    op.drop_column('tracking_alerts', 'risk_level')
