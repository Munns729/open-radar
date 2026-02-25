"""add_canon_proposals

Revision ID: a27b3e8c28b5
Revises: e661f8adf73e
Create Date: 2026-02-24 22:44:44.576762

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a27b3e8c28b5'
down_revision: Union[str, Sequence[str], None] = 'e661f8adf73e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add canon_proposals table only."""
    op.create_table('canon_proposals',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.Column('proposed_field', sa.String(length=100), nullable=False),
    sa.Column('current_value', sa.Text(), nullable=True),
    sa.Column('proposed_value', sa.Text(), nullable=False),
    sa.Column('rationale', sa.Text(), nullable=True),
    sa.Column('signals', sa.JSON(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('source_module', sa.String(length=100), nullable=True),
    sa.Column('triggered_by', sa.String(length=255), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(), nullable=True),
    sa.Column('reviewer_note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_canon_proposals_company_id'), 'canon_proposals', ['company_id'], unique=False)
    op.create_index(op.f('ix_canon_proposals_created_at'), 'canon_proposals', ['created_at'], unique=False)
    op.create_index(op.f('ix_canon_proposals_status'), 'canon_proposals', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema: drop canon_proposals table."""
    op.drop_index(op.f('ix_canon_proposals_status'), table_name='canon_proposals')
    op.drop_index(op.f('ix_canon_proposals_created_at'), table_name='canon_proposals')
    op.drop_index(op.f('ix_canon_proposals_company_id'), table_name='canon_proposals')
    op.drop_table('canon_proposals')
