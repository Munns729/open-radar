"""add vc portfolio intelligence tables

Revision ID: f1a2b3c4d5e6
Revises: f7a8b9c0d1e2
Create Date: 2026-02-25

Adds:
  - vc_portfolio_companies: portfolio companies per VC fund
  - vc_exit_signals: computed exit-readiness + quality scores
"""
from alembic import op
import sqlalchemy as sa

revision = "f1a2b3c4d5e6"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vc_portfolio_companies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vc_firm_id", sa.Integer(), sa.ForeignKey("vc_firms.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("first_funding_date", sa.Date(), nullable=True),
        sa.Column("latest_funding_date", sa.Date(), nullable=True),
        sa.Column("latest_round_type", sa.String(50), nullable=True),
        sa.Column("total_raised_eur", sa.Float(), nullable=True),
        sa.Column("sector_tags", sa.JSON(), nullable=True),
        sa.Column("is_dual_use", sa.Boolean(), default=False),
        sa.Column("dual_use_confidence", sa.Float(), default=0.0),
        sa.Column("has_gov_contract", sa.Boolean(), default=False),
        sa.Column("gov_contract_notes", sa.Text(), nullable=True),
        sa.Column("has_export_cert", sa.Boolean(), default=False),
        sa.Column("regulatory_notes", sa.Text(), nullable=True),
        sa.Column("universe_company_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(100), default="manual"),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("last_scraped_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_vc_port_firm_name", "vc_portfolio_companies", ["vc_firm_id", "name"])
    op.create_index("idx_vc_port_dual_use", "vc_portfolio_companies", ["is_dual_use"])
    op.create_index("idx_vc_port_first_funding", "vc_portfolio_companies", ["first_funding_date"])

    op.create_table(
        "vc_exit_signals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("portfolio_company_id", sa.Integer(),
                  sa.ForeignKey("vc_portfolio_companies.id"), nullable=False),
        sa.Column("exit_readiness_score", sa.Float(), default=0.0),
        sa.Column("years_held", sa.Float(), nullable=True),
        sa.Column("fund_vintage_year", sa.Integer(), nullable=True),
        sa.Column("fund_exit_pressure", sa.Boolean(), default=False),
        sa.Column("vc_quality_tier", sa.Integer(), default=3),
        sa.Column("nato_lp_backed", sa.Boolean(), default=False),
        sa.Column("eif_lp_backed", sa.Boolean(), default=False),
        sa.Column("co_investor_count", sa.Integer(), default=0),
        sa.Column("top_co_investors", sa.JSON(), nullable=True),
        sa.Column("regulatory_moat_confirmed", sa.Boolean(), default=False),
        sa.Column("diana_cohort", sa.Boolean(), default=False),
        sa.Column("edf_grantee", sa.Boolean(), default=False),
        sa.Column("gov_contract_value_est_eur", sa.Float(), nullable=True),
        sa.Column("deal_quality_score", sa.Float(), default=0.0),
        sa.Column("priority_tier", sa.String(10), default="C"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("scored_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("portfolio_company_id"),
    )
    op.create_index("idx_vc_exit_priority", "vc_exit_signals", ["priority_tier"])
    op.create_index("idx_vc_exit_quality", "vc_exit_signals", ["deal_quality_score"])


def downgrade() -> None:
    op.drop_table("vc_exit_signals")
    op.drop_table("vc_portfolio_companies")
