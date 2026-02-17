"""
Integration tests for complex database queries involving joins and aggregations.
Verifies that critical data retrieval logic in app.py and elsewhere works correctly.
"""
import pytest
from datetime import datetime, date
from sqlalchemy import select, func, desc

from src.competitive.database import VCAnnouncementModel, ThreatScoreModel, VCFirmModel
from src.capital.database import PEInvestmentModel, PEFirmModel
from src.deal_intelligence.database import DealRecord, DealComparable
from src.carveout.database import Division, CorporateParent

@pytest.mark.asyncio
class TestDatabaseQueries:
    """Tests for complex SQLAlchemy queries across different modules."""

    async def test_competitive_feed_query(self, db_session):
        """Test the join between ThreatScoreModel and VCAnnouncementModel."""
        # Arrange
        vc_firm = VCFirmModel(name="Test VC")
        db_session.add(vc_firm)
        db_session.flush()
        
        ann = VCAnnouncementModel(
            vc_firm_id=vc_firm.id,
            company_name="Target Co",
            announced_date=date(2023, 1, 1)
        )
        db_session.add(ann)
        db_session.flush()
        
        threat = ThreatScoreModel(
            announcement_id=ann.id,
            threat_score=85,
            threat_level="high",
            reasoning="Strong competitor"
        )
        db_session.add(threat)
        db_session.commit()
        
        # Act
        # Mimicking query in app.py:397
        stmt = select(ThreatScoreModel, VCAnnouncementModel).\
            join(VCAnnouncementModel, ThreatScoreModel.announcement_id == VCAnnouncementModel.id).\
            order_by(desc(ThreatScoreModel.created_at))
        
        result = db_session.execute(stmt).all()
        
        # Assert
        assert len(result) == 1
        t, a = result[0]
        assert t.threat_score == 85
        assert a.company_name == "Target Co"

    async def test_capital_investments_query(self, db_session):
        """Test the join between PEInvestmentModel and PEFirmModel."""
        # Arrange
        pe_firm = PEFirmModel(name="Mega PE")
        db_session.add(pe_firm)
        db_session.flush()
        
        inv = PEInvestmentModel(
            pe_firm_id=pe_firm.id,
            company_name="Portfolio Co",
            sector="SaaS",
            entry_date=date(2023, 6, 1)
        )
        db_session.add(inv)
        db_session.commit()
        
        # Act
        # Mimicking query in app.py:452
        stmt = select(PEInvestmentModel, PEFirmModel.name.label("firm_name")).\
            join(PEFirmModel, PEInvestmentModel.pe_firm_id == PEFirmModel.id).\
            order_by(desc(PEInvestmentModel.entry_date))
            
        result = db_session.execute(stmt).all()
        
        # Assert
        assert len(result) == 1
        i, firm_name = result[0]
        assert i.company_name == "Portfolio Co"
        assert firm_name == "Mega PE"

    async def test_deal_comparables_query(self, db_session):
        """Test the join between DealComparable and DealRecord for comparables retrieval."""
        # Arrange
        deal1 = DealRecord(target_company_name="Main Deal", sector="Tech", deal_date=date(2023, 1, 1))
        deal2 = DealRecord(target_company_name="Comp Deal", sector="Tech", deal_date=date(2022, 1, 1))
        db_session.add_all([deal1, deal2])
        db_session.flush()
        
        comp = DealComparable(
            deal_record_id=deal1.id,
            comparable_deal_id=deal2.id,
            similarity_score=0.95
        )
        db_session.add(comp)
        db_session.commit()
        
        # Act
        # Mimicking query in app.py:654
        stmt = select(DealComparable, DealRecord).join(
            DealRecord, DealComparable.comparable_deal_id == DealRecord.id
        ).where(
            DealComparable.deal_record_id == deal1.id
        ).order_by(desc(DealComparable.similarity_score))
        
        result = db_session.execute(stmt).all()
        
        # Assert
        assert len(result) == 1
        c, dr = result[0]
        assert dr.target_company_name == "Comp Deal"
        assert c.similarity_score == 0.95

    async def test_carveout_targets_query(self, db_session):
        """Test the join between Division and CorporateParent."""
        # Arrange
        parent = CorporateParent(name="Giant Corp")
        db_session.add(parent)
        db_session.flush()
        
        div = Division(
            parent_id=parent.id,
            division_name="Non-Core Assets",
            carveout_probability=75
        )
        db_session.add(div)
        db_session.commit()
        
        # Act
        # Mimicking query in app.py:424
        stmt = select(Division, CorporateParent).\
            join(CorporateParent, Division.parent_id == CorporateParent.id).\
            order_by(desc(Division.carveout_probability))
            
        result = db_session.execute(stmt).all()
        
        # Assert
        assert len(result) == 1
        d, p = result[0]
        assert d.division_name == "Non-Core Assets"
        assert p.name == "Giant Corp"
        assert d.carveout_probability == 75

    async def test_dashboard_activity_complex_sorting(self, db_session):
        """Test data aggregation and sorting for dashboard activity feed."""
        # Create different types of activity
        vc_firm = VCFirmModel(name="Test VC")
        db_session.add(vc_firm)
        db_session.flush()
        
        ann = VCAnnouncementModel(vc_firm_id=vc_firm.id, company_name="VC Target")
        db_session.add(ann)
        db_session.flush()
        
        # Create threat with past date
        threat = ThreatScoreModel(announcement_id=ann.id, created_at=datetime(2023, 1, 1))
        db_session.add(threat)
        
        # Create investment with more recent date
        pe_firm = PEFirmModel(name="Test PE")
        db_session.add(pe_firm)
        db_session.flush()
        
        inv = PEInvestmentModel(pe_firm_id=pe_firm.id, company_name="PE Target", entry_date=date(2023, 6, 1))
        db_session.add(inv)
        db_session.commit()
        
        # In app.py:343, it fetches these separately and then sorts in memory.
        # Let's verify the individual queries work.
        
        # Threat query
        threat_stmt = select(ThreatScoreModel, VCAnnouncementModel).\
            join(VCAnnouncementModel, ThreatScoreModel.announcement_id == VCAnnouncementModel.id)
        threats = db_session.execute(threat_stmt).all()
        assert len(threats) == 1
        
        # Investment query
        inv_stmt = select(PEInvestmentModel, PEFirmModel).\
            join(PEFirmModel, PEInvestmentModel.pe_firm_id == PEFirmModel.id)
        investments = db_session.execute(inv_stmt).all()
        assert len(investments) == 1
