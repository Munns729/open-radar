"""
Generate Grading Report (Read-Only).
Calculates scores in-memory to avoid DB locks.
"""
import asyncio
import logging
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.universe.database import CompanyModel, CertificationModel
from src.universe.moat_scorer import MoatScorer
from src.core.config import settings

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_URL = "sqlite:///radar_report.db"
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)

TARGET_NAMES = [
    "BAE Systems", "Meggitt", "Rolls-Royce",
    "Rightmove", "Auto Trader Group", "Deliveroo",
    "Rotork", "Spirax-Sarco Engineering", "Halma",
    "Intertek Group", "Bureau Veritas UK",
    "Darktrace", "Softcat", "Greggs", "Trainline"
]

def generate_report():
    session = SessionLocal()
    try:
        companies = session.query(CompanyModel).filter(CompanyModel.name.in_(TARGET_NAMES)).all()
        
        with open("outputs/picard_grading_report.md", "w", encoding="utf-8") as f:
            f.write("# Picard Moat Scoring - Grading Report\n\n")
            f.write("| Company | Tier | Score | Moat Attributes Found | Financials (Est) |\n")
            f.write("|---|---|---|---|---|\n")
            
            for c in companies:
                # Run Scorer In-Memory
                certs = session.query(CertificationModel).filter(CertificationModel.company_id == c.id).all()
                # Mock Graph Signals (since we can't run analysis easily read-only if it relies on writing result)
                # But we can assume some defaults or infer from relationships if loaded.
                
                # Use stored score and attributes directly
                # MoatScorer.score_picard_defensibility(c, certs) <-- REMOVED (Sync scorer deprecated)
                
                # Format Attributes
                attrs = []
                if c.moat_attributes:
                    # Parse JSON string if needed (SQLite stores JSON as string)
                    import json
                    ma = c.moat_attributes
                    if isinstance(ma, str):
                        try:
                            ma = json.loads(ma)
                        except:
                            ma = {}
                            
                    for k, v in ma.items():
                        if isinstance(v, dict) and v.get("present"):
                            attrs.append(f"**{k.title()}**: {v.get('justification')}")
                        elif k.startswith("keyword_"):
                            # attrs.append(f"Keyword: {k}")
                            pass
                
                attr_str = "<br>".join(attrs) if attrs else "None"
                
                # Format Financials
                fin_str = f"Rev: {c.revenue_gbp or 'N/A'}<br>Emp: {c.employees or 'N/A'}<br>Margin: {c.ebitda_margin or 'N/A'}"
                
                f.write(f"| {c.name} | **{c.tier.value}** | {c.moat_score} | {attr_str} | {fin_str} |\n")
                
        logger.info("Report generated: outputs/picard_grading_report.md")
        
    except Exception as e:
        logger.error(f"Failed: {e}", exc_info=True)
    finally:
        session.close()

if __name__ == "__main__":
    generate_report()
