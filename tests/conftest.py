"""
Shared pytest fixtures for RADAR test suite.
"""
import pytest
import asyncio
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, configure_mappers
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from fastapi.testclient import TestClient

from src.universe.database import Base as UniverseBase, CompanyModel, CertificationModel
from src.competitive.database import Base as CompetitiveBase
from src.capital.database import Base as CapitalBase
from src.deal_intelligence.database import Base as IntelligenceBase
from src.carveout.database import Base as CarveoutBase
from src.core.models import CompanyTier


# --- Database Fixtures ---

@pytest.fixture
def db_session():
    """Synchronous in-memory SQLite session for testing."""
    configure_mappers()
    engine = create_engine("sqlite:///:memory:")
    # Create all tables from all modules
    # Most share the same Core Base, so we use their metadata
    bases = [UniverseBase, CompetitiveBase, CapitalBase, IntelligenceBase, CarveoutBase]
    unique_metadatas = []
    for b in bases:
        if b.metadata not in unique_metadatas:
            unique_metadatas.append(b.metadata)
            
    for metadata in unique_metadatas:
        metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
async def async_db_session():
    """Async in-memory SQLite session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    async with engine.begin() as conn:
        bases = [UniverseBase, CompetitiveBase, CapitalBase, IntelligenceBase, CarveoutBase]
        unique_metadatas = []
        for b in bases:
            if b.metadata not in unique_metadatas:
                unique_metadatas.append(b.metadata)
                
        for metadata in unique_metadatas:
            await conn.run_sync(metadata.create_all)
    
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session_factory() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def test_client():
    """FastAPI TestClient for API endpoint testing."""
    from src.web.app import app
    return TestClient(app)


# --- Mock Data Fixtures ---

@pytest.fixture
def mock_llm_response():
    """Standard mock LLM response for moat analysis — matches thesis.example.yaml pillars."""
    return {
        "regulatory": {"score": 70, "evidence": "Holds AS9100 certification for aerospace manufacturing"},
        "network": {"score": 0, "evidence": "No network effects detected"},
        "switching_costs": {"score": 40, "evidence": "Deep ERP integration with customer workflows"},
        "ip": {"score": 45, "evidence": "3 granted patents in testing methodology"},
        "brand": {"score": 30, "evidence": "Sole-source supplier to 2 defence primes"},
        "overall_moat_score": 185,
        "recommended_tier": "Tier 1B",
        "reasoning": "Strong regulatory moat via AS9100 with IP and switching cost defensibility"
    }


@pytest.fixture
def mock_llm_no_moats():
    """LLM returns zero scores — tests hard evidence logic in isolation."""
    return {
        "regulatory": {"score": 0, "evidence": "No evidence found"},
        "network": {"score": 0, "evidence": "No evidence found"},
        "switching_costs": {"score": 0, "evidence": "No evidence found"},
        "ip": {"score": 0, "evidence": "No evidence found"},
        "brand": {"score": 0, "evidence": "No evidence found"},
        "overall_moat_score": 0,
        "recommended_tier": "Waitlist",
        "reasoning": "No moat evidence found"
    }


@pytest.fixture
def sample_company(db_session):
    """Factory fixture for creating test companies."""
    def _create_company(
        name="Test Company Ltd",
        revenue_gbp=10_000_000,
        employees=150,
        hq_country="GB",
        sector="Aerospace",
        description="Test aerospace manufacturing company",
        tier=None,
        moat_score=0,
        moat_analysis=None,
        moat_attributes=None,
        ebitda_margin=None,
        market_share=None,
        competitor_count=None,
        market_growth_rate=None,
        revenue_growth=None,
        raw_website_text=None,
    ):
        company = CompanyModel(
            name=name,
            revenue_gbp=revenue_gbp,
            employees=employees,
            hq_country=hq_country,
            sector=sector,
            description=description,
            tier=tier,
            moat_score=moat_score,
            moat_analysis=moat_analysis,
            moat_attributes=moat_attributes,
            ebitda_margin=ebitda_margin,
            market_share=market_share,
            competitor_count=competitor_count,
            market_growth_rate=market_growth_rate,
            revenue_growth=revenue_growth,
            raw_website_text=raw_website_text,
            created_at=datetime.utcnow()
        )
        db_session.add(company)
        db_session.commit()
        db_session.refresh(company)
        return company
    
    return _create_company


@pytest.fixture
def sample_certifications(db_session):
    """Factory fixture for creating test certifications."""
    def _create_certifications(company_id, cert_types):
        """
        Create certifications for a company.
        
        Args:
            company_id: ID of the company
            cert_types: List of certification type strings (e.g., ["AS9100", "ISO9001"])
        
        Returns:
            List of CertificationModel instances
        """
        certs = []
        for cert_type in cert_types:
            cert = CertificationModel(
                company_id=company_id,
                certification_type=cert_type,
                certification_number=f"{cert_type}-{company_id}-001",
                issuing_body="Test Certification Body",
                issue_date=datetime.utcnow()
            )
            db_session.add(cert)
            certs.append(cert)
        
        db_session.commit()
        for cert in certs:
            db_session.refresh(cert)
        
        return certs
    
    return _create_certifications


# --- Event Loop Fixture for Async Tests ---

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
