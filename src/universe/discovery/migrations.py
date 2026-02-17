"""
Database migrations for discovery infrastructure.

Adds:
- Enrichment state tracking
- LEI/VAT identifiers for deduplication
- Data sources tracking
- Manual review queue table
- Merge candidates table
"""

DISCOVERY_SCHEMA_MIGRATIONS = """
-- ============================================================================
-- COMPANY TABLE EXTENSIONS
-- ============================================================================

-- Add deduplication identifiers
ALTER TABLE companies ADD COLUMN IF NOT EXISTS lei VARCHAR(20);
ALTER TABLE companies ADD COLUMN IF NOT EXISTS vat_id VARCHAR(20);
ALTER TABLE companies ADD COLUMN IF NOT EXISTS normalized_name VARCHAR(255);

-- Add enrichment state tracking
ALTER TABLE companies ADD COLUMN IF NOT EXISTS enrichment_state INTEGER DEFAULT 1;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS enrichment_blockers TEXT;  -- JSON array
ALTER TABLE companies ADD COLUMN IF NOT EXISTS last_enrichment_attempt TIMESTAMP;

-- Add data sources tracking (which source provided which field)
ALTER TABLE companies ADD COLUMN IF NOT EXISTS data_sources TEXT;  -- JSON object

-- Add semantic enrichment fields (matching SemanticScore structure)
ALTER TABLE companies ADD COLUMN IF NOT EXISTS semantic_regulatory TEXT;  -- JSON SemanticScore
ALTER TABLE companies ADD COLUMN IF NOT EXISTS semantic_network TEXT;     -- JSON SemanticScore
ALTER TABLE companies ADD COLUMN IF NOT EXISTS semantic_switching TEXT;   -- JSON SemanticScore
ALTER TABLE companies ADD COLUMN IF NOT EXISTS semantic_liability TEXT;   -- JSON SemanticScore
ALTER TABLE companies ADD COLUMN IF NOT EXISTS semantic_ip TEXT;          -- JSON SemanticScore

-- Add input quality score
ALTER TABLE companies ADD COLUMN IF NOT EXISTS input_quality FLOAT;

-- Indexes for deduplication
CREATE INDEX IF NOT EXISTS idx_companies_lei ON companies(lei);
CREATE INDEX IF NOT EXISTS idx_companies_vat ON companies(vat_id, country);
CREATE INDEX IF NOT EXISTS idx_companies_normalized_name ON companies(normalized_name, country);
CREATE INDEX IF NOT EXISTS idx_companies_enrichment_state ON companies(enrichment_state);

-- ============================================================================
-- MANUAL REVIEW QUEUE
-- ============================================================================

CREATE TABLE IF NOT EXISTS manual_review_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER REFERENCES companies(id),
    task_type VARCHAR(50) NOT NULL,      -- find_website, confirm_merge, validate_sector
    priority INTEGER DEFAULT 5,          -- 1-10, higher = more important
    context TEXT,                        -- JSON with additional context
    status VARCHAR(20) DEFAULT 'pending',-- pending, in_progress, completed, skipped
    assigned_to VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    resolution VARCHAR(255)              -- What was done
);

CREATE INDEX IF NOT EXISTS idx_review_status ON manual_review_queue(status);
CREATE INDEX IF NOT EXISTS idx_review_priority ON manual_review_queue(priority DESC);

-- ============================================================================
-- MERGE CANDIDATES (for ambiguous deduplication)
-- ============================================================================

CREATE TABLE IF NOT EXISTS merge_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_a_id INTEGER REFERENCES companies(id),
    company_b_id INTEGER REFERENCES companies(id),
    confidence FLOAT,
    match_method VARCHAR(50),            -- lei, vat, name_fuzzy, website
    status VARCHAR(20) DEFAULT 'pending',-- pending, confirmed, rejected
    reviewed_at TIMESTAMP,
    reviewed_by VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_merge_status ON merge_candidates(status);

-- ============================================================================
-- DISCOVERY SOURCE TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS discovery_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name VARCHAR(100) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    companies_discovered INTEGER DEFAULT 0,
    companies_new INTEGER DEFAULT 0,
    companies_merged INTEGER DEFAULT 0,
    companies_queued_review INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'running', -- running, completed, failed
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_discovery_runs_source ON discovery_runs(source_name);
"""



def run_migrations() -> None:
    """Run the discovery schema migrations."""
    import logging
    from sqlalchemy import text
    from src.core.database import sync_engine
    
    logger = logging.getLogger(__name__)
    
    # Split migrations and run each statement
    raw_statements = [
        stmt.strip() 
        for stmt in DISCOVERY_SCHEMA_MIGRATIONS.split(';')
        if stmt.strip() and not stmt.strip().startswith('--')
    ]
    
    with sync_engine.connect() as conn:
        dialect = sync_engine.dialect.name
        logger.info(f"Running migrations on dialect: {dialect}")
        
        # Prepare statements based on dialect
        statements = []
        for stmt in raw_statements:
            if dialect == 'postgresql':
                # Replace SQLite AUTOINCREMENT with Postgres SERIAL
                # Regex might be safer, but simple replacement works for this specific schema
                if "INTEGER PRIMARY KEY AUTOINCREMENT" in stmt:
                    stmt = stmt.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
                # Postgres uses used generated by default identity for standard SQL identity columns but SERIAL is fine
            statements.append(stmt)

        for stmt in statements:
            try:
                conn.execute(text(stmt))
                logger.debug(f"Executed: {stmt[:50]}...")
            except Exception as e:
                # Ignore "column already exists" errors - broad catch effectively
                # Postgres error code 42701 is duplicate_column
                # SQLite error is somewhat generic OperationalError
                err_str = str(e).lower()
                if "duplicate column" in err_str or "already exists" in err_str:
                    continue
                logger.warning(f"Migration warning/error: {e}\nStatement: {stmt[:100]}")
        
        conn.commit()
    
    logger.info("Discovery schema migrations complete")


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    # db_path arg is legacy/ignored now as we use app config
    run_migrations()

