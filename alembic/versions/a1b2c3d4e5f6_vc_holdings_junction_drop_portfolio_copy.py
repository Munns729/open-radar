"""vc holdings junction, drop vc_portfolio_companies copy

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-02-25

Option B: single company entity + minimal junction.
- Add VC-related columns to companies (company-level facts).
- Create company_vc_holdings (company_id, vc_firm_id, source_url, last_scraped_at, etc.).
- Migrate vc_portfolio_companies -> companies + company_vc_holdings; vc_exit_signals -> holding_id.
- Drop vc_portfolio_companies.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "c4d5e6f7a8b9"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add VC-related columns to companies (company-level facts)
    op.add_column("companies", sa.Column("first_funding_date", sa.Date(), nullable=True))
    op.add_column("companies", sa.Column("is_dual_use", sa.Boolean(), nullable=True, server_default="false"))
    op.add_column("companies", sa.Column("dual_use_confidence", sa.Float(), nullable=True))
    op.add_column("companies", sa.Column("has_gov_contract", sa.Boolean(), nullable=True, server_default="false"))
    op.add_column("companies", sa.Column("gov_contract_notes", sa.Text(), nullable=True))
    op.add_column("companies", sa.Column("has_export_cert", sa.Boolean(), nullable=True, server_default="false"))
    op.add_column("companies", sa.Column("regulatory_notes", sa.Text(), nullable=True))

    # 2. Create junction table company_vc_holdings
    op.create_table(
        "company_vc_holdings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vc_firm_id", sa.Integer(), sa.ForeignKey("vc_firms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("source", sa.String(100), nullable=True, server_default="website"),
        sa.Column("first_seen_at", sa.DateTime(), nullable=True),
        sa.Column("last_scraped_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "vc_firm_id", name="uq_company_vc_holding"),
    )
    op.create_index("idx_company_vc_holdings_company", "company_vc_holdings", ["company_id"])
    op.create_index("idx_company_vc_holdings_firm", "company_vc_holdings", ["vc_firm_id"])

    # 3. Add holding_id to vc_exit_signals (nullable during migration)
    op.add_column(
        "vc_exit_signals",
        sa.Column("holding_id", sa.Integer(), sa.ForeignKey("company_vc_holdings.id", ondelete="CASCADE"), nullable=True),
    )

    # 4. Data migration: vc_portfolio_companies -> companies + company_vc_holdings
    conn = op.get_bind()
    vpc_rows = conn.execute(text(
        "SELECT id, vc_firm_id, name, website, description, first_funding_date, sector_tags, "
        "is_dual_use, dual_use_confidence, has_gov_contract, gov_contract_notes, has_export_cert, "
        "regulatory_notes, source_url, last_scraped_at, source, universe_company_id, created_at "
        "FROM vc_portfolio_companies ORDER BY id"
    )).fetchall()

    vpc_id_to_holding_id = {}
    for row in vpc_rows:
        (vpc_id, vc_firm_id, name, website, description, first_funding_date, sector_tags,
         is_dual_use, dual_use_confidence, has_gov_contract, gov_contract_notes, has_export_cert,
         regulatory_notes, source_url, last_scraped_at, source, universe_company_id, created_at) = row

        if universe_company_id is not None:
            company_id = universe_company_id
            # Update company VC-related columns from this row (in case we have better data)
            conn.execute(
                text("""
                UPDATE companies SET
                    first_funding_date = COALESCE(:first_funding_date, first_funding_date),
                    is_dual_use = COALESCE(companies.is_dual_use OR :is_dual_use, false),
                    dual_use_confidence = GREATEST(COALESCE(companies.dual_use_confidence, 0), COALESCE(:dual_use_confidence, 0)),
                    has_gov_contract = COALESCE(companies.has_gov_contract OR :has_gov_contract, false),
                    gov_contract_notes = COALESCE(companies.gov_contract_notes, :gov_contract_notes),
                    has_export_cert = COALESCE(companies.has_export_cert OR :has_export_cert, false),
                    regulatory_notes = COALESCE(companies.regulatory_notes, :regulatory_notes)
                WHERE id = :company_id
                """),
                {
                    "company_id": company_id,
                    "first_funding_date": first_funding_date,
                    "is_dual_use": is_dual_use or False,
                    "dual_use_confidence": dual_use_confidence or 0,
                    "has_gov_contract": has_gov_contract or False,
                    "gov_contract_notes": gov_contract_notes,
                    "has_export_cert": has_export_cert or False,
                    "regulatory_notes": regulatory_notes,
                },
            )
        else:
            # Create new company row
            sector = sector_tags[0] if isinstance(sector_tags, list) and sector_tags else None
            r = conn.execute(
                text("""
                INSERT INTO companies (name, website, description, sector, discovered_via,
                    first_funding_date, is_dual_use, dual_use_confidence, has_gov_contract,
                    gov_contract_notes, has_export_cert, regulatory_notes)
                VALUES (:name, :website, :description, :sector, 'vc_portfolio',
                    :first_funding_date, :is_dual_use, :dual_use_confidence, :has_gov_contract,
                    :gov_contract_notes, :has_export_cert, :regulatory_notes)
                RETURNING id
                """),
                {
                    "name": name,
                    "website": website,
                    "description": (description[:2000] if description else None),
                    "sector": sector,
                    "first_funding_date": first_funding_date,
                    "is_dual_use": is_dual_use or False,
                    "dual_use_confidence": dual_use_confidence or 0,
                    "has_gov_contract": has_gov_contract or False,
                    "gov_contract_notes": gov_contract_notes,
                    "has_export_cert": has_export_cert or False,
                    "regulatory_notes": regulatory_notes,
                },
            )
            company_id = r.fetchone()[0]

        cid = company_id if isinstance(company_id, int) else company_id
        # Insert holding (ON CONFLICT update for idempotency)
        conn.execute(
            text("""
            INSERT INTO company_vc_holdings (company_id, vc_firm_id, source_url, source, first_seen_at, last_scraped_at)
            VALUES (:company_id, :vc_firm_id, :source_url, :source, :first_seen_at, :last_scraped_at)
            ON CONFLICT (company_id, vc_firm_id) DO UPDATE SET
                source_url = COALESCE(EXCLUDED.source_url, company_vc_holdings.source_url),
                last_scraped_at = COALESCE(EXCLUDED.last_scraped_at, company_vc_holdings.last_scraped_at)
            """),
            {
                "company_id": cid,
                "vc_firm_id": vc_firm_id,
                "source_url": source_url,
                "source": source or "website",
                "first_seen_at": created_at,
                "last_scraped_at": last_scraped_at,
            },
        )
        hold_result = conn.execute(
            text("SELECT id FROM company_vc_holdings WHERE company_id = :cid AND vc_firm_id = :fid"),
            {"cid": cid, "fid": vc_firm_id},
        ).fetchone()
        holding_id = hold_result[0]
        vpc_id_to_holding_id[vpc_id] = holding_id

    # 5. Backfill vc_exit_signals.holding_id from portfolio_company_id
    for vpc_id, holding_id in vpc_id_to_holding_id.items():
        conn.execute(
            text("UPDATE vc_exit_signals SET holding_id = :holding_id WHERE portfolio_company_id = :vpc_id"),
            {"holding_id": holding_id, "vpc_id": vpc_id},
        )

    # 6. Drop old FK and column, make holding_id non-null and unique
    op.drop_constraint("vc_exit_signals_portfolio_company_id_key", "vc_exit_signals", type_="unique")
    op.drop_constraint(
        "vc_exit_signals_portfolio_company_id_fkey", "vc_exit_signals", type_="foreignkey"
    )
    op.drop_column("vc_exit_signals", "portfolio_company_id")
    op.alter_column(
        "vc_exit_signals", "holding_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_unique_constraint("uq_vc_exit_signal_holding", "vc_exit_signals", ["holding_id"])

    # 7. Drop vc_portfolio_companies
    op.drop_table("vc_portfolio_companies")


def downgrade() -> None:
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

    op.add_column(
        "vc_exit_signals",
        sa.Column("portfolio_company_id", sa.Integer(), sa.ForeignKey("vc_portfolio_companies.id"), nullable=True),
    )
    op.drop_constraint("uq_vc_exit_signal_holding", "vc_exit_signals", type_="unique")
    # Data backfill would be lossy (holdings -> vpc rows); leave portfolio_company_id nullable in downgrade
    op.drop_column("vc_exit_signals", "holding_id")

    op.drop_table("company_vc_holdings")

    op.drop_column("companies", "regulatory_notes")
    op.drop_column("companies", "has_export_cert")
    op.drop_column("companies", "gov_contract_notes")
    op.drop_column("companies", "has_gov_contract")
    op.drop_column("companies", "dual_use_confidence")
    op.drop_column("companies", "is_dual_use")
    op.drop_column("companies", "first_funding_date")
