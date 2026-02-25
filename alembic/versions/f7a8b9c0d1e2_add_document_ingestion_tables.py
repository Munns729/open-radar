"""add_document_ingestion_tables

Revision ID: f7a8b9c0d1e2
Revises: a27b3e8c28b5
Create Date: 2026-02-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, Sequence[str], None] = 'a27b3e8c28b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'document_ingestions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('processing_status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'file_hash', name='uq_company_document_hash'),
    )
    op.create_index(op.f('ix_document_ingestions_company_id'), 'document_ingestions', ['company_id'], unique=False)
    op.create_index(op.f('ix_document_ingestions_processing_status'), 'document_ingestions', ['processing_status'], unique=False)
    op.create_index(op.f('ix_document_ingestions_uploaded_at'), 'document_ingestions', ['uploaded_at'], unique=False)

    op.create_table(
        'document_extracts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('moat_evidence', sa.JSON(), nullable=True),
        sa.Column('resilience_evidence', sa.JSON(), nullable=True),
        sa.Column('thesis_elements', sa.JSON(), nullable=True),
        sa.Column('tier_signal', sa.JSON(), nullable=True),
        sa.Column('scarcity_signals', sa.JSON(), nullable=True),
        sa.Column('open_questions_raised', sa.JSON(), nullable=True),
        sa.Column('red_flags', sa.JSON(), nullable=True),
        sa.Column('proposals_generated', sa.Integer(), server_default='0', nullable=False),
        sa.Column('llm_prompt_version', sa.String(length=20), nullable=True),
        sa.Column('extracted_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', name='uq_document_extracts_document_id'),
    )
    op.create_index(op.f('ix_document_extracts_company_id'), 'document_extracts', ['company_id'], unique=False)
    op.create_index(op.f('ix_document_extracts_document_id'), 'document_extracts', ['document_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_document_extracts_document_id'), table_name='document_extracts')
    op.drop_index(op.f('ix_document_extracts_company_id'), table_name='document_extracts')
    op.drop_table('document_extracts')
    op.drop_index(op.f('ix_document_ingestions_uploaded_at'), table_name='document_ingestions')
    op.drop_index(op.f('ix_document_ingestions_processing_status'), table_name='document_ingestions')
    op.drop_index(op.f('ix_document_ingestions_company_id'), table_name='document_ingestions')
    op.drop_table('document_ingestions')
