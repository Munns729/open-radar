"""
Carveout Scanner Workflow.
Orchestrates the scraping, analysis, and scoring of potential carvecuts.
"""
import asyncio
from datetime import date
from typing import List

# Import our components
from sqlalchemy import select
from src.core.database import async_session_factory, Base, engine
from src.universe.database import CompanyModel, Base as UniverseBase

from .database import CorporateParent, Division, CarveoutSignal
from .scrapers.segment_reporter import SegmentReportScraper
from .scrapers.earnings_call_analyzer import EarningsCallAnalyzer
from .scrapers.activist_tracker import ActivistTracker
from .signal_detector import SignalDetector
from .attractiveness_scorer import AttractivenessScorer
from .relationship_builder import RelationshipBuilder

# Configuration
EUR_TO_GBP_RATE = 0.85


# Configuration
from src.core.currency import currency_service


async def init_db():
    """Initialize database tables for this module and dependencies."""
    async with engine.begin() as conn:
        # Create core tables (Carveout)
        await conn.run_sync(Base.metadata.create_all)
        # Create universe tables (Companies)
        await conn.run_sync(UniverseBase.metadata.create_all)

async def scan_carveouts():
    """
    Main orchestration function.
    """
    print("Starting Carveout Scan (Europe Focused)...")
    await init_db()
    
    # Initialize components
    segment_scraper = SegmentReportScraper(headless=True)
    earnings_analyzer = EarningsCallAnalyzer()
    activist_tracker = ActivistTracker(headless=True)
    signal_detector = SignalDetector()
    attractiveness_scorer = AttractivenessScorer()
    
    targets = []
    
    async with async_session_factory() as session:
        # 1. Target List from Universe Scanner
        print("Fetching targets from Universe Database...")
        try:
            # Query for companies with > £150M Revenue (lowered to capture smaller parents)
            stmt = select(CompanyModel).where(CompanyModel.revenue_gbp > 150000000)
            result = await session.execute(stmt)
            universe_targets = result.scalars().all()
            
            if universe_targets:
                print(f"Found {len(universe_targets)} qualified targets in Universe.")
                for comp in universe_targets:
                    targets.append({
                        "ticker": comp.name,
                        "exchange": "LSE" if comp.hq_country == "GB" else "Euronext",
                        "name": comp.name,
                        "id": comp.id
                    })
            else:
                print("Universe DB empty or no matches. Using fallback demo list.")
                targets = [
                    {"ticker": "BARC", "exchange": "LSE", "name": "Barclays"},
                    {"ticker": "HSBA", "exchange": "LSE", "name": "HSBC"},
                ]
        except Exception as e:
            print(f"Error querying Universe DB: {e}. Using fallback list.")
            targets = [
                {"ticker": "BARC", "exchange": "LSE", "name": "Barclays"},
                {"ticker": "HSBA", "exchange": "LSE", "name": "HSBC"},
            ]
    
    
        # 2. Run Scrapers
        for target in targets:
            print(f"Processing {target['name']}...")
            
            # Scrape Segments
            segments_data = await segment_scraper.scrape_company_segments(target['ticker'], target['exchange'])
            
            # In a real app, we would save these divisions to the DB here.
            # For this demo, we'll create Division objects in memory.
            
            for seg_data in segments_data:
                division = Division(
                    division_name=seg_data['division_name'],
                    revenue_eur=seg_data['revenue_eur'],
                    revenue_gbp=int(await currency_service.convert(seg_data['revenue_eur'], "EUR", "GBP")),
                    ebitda_eur=seg_data['ebitda_eur'],
                    ebitda_gbp=int(await currency_service.convert(seg_data['ebitda_eur'], "EUR", "GBP")),
                    ebitda_margin=seg_data['ebitda_margin'],
                    business_description=seg_data['description'],
                    moat_type="regulatory", # Mocked
                    moat_strength=60, # Mocked
                    autonomy_level="semi_autonomous", # Mocked
                    strategic_autonomy="non_core", # Mocked - this ensures we get a score!
                    market_share=15.0, # Mocked
                    competitor_count=4, # Mocked (<5 for scorer boost)
                    market_growth_rate=6.0 # Mocked (>5 for scorer boost)
                )
                
                # 3. Analyze Signals (Earnings Calls)
                signals_data = await earnings_analyzer.analyze_for_signals("transcript_mock")
                
                # Map signals to Division (Mock mapping)
                div_signals = []
                if division.division_name in signals_data:
                    for s_data in signals_data[division.division_name]:
                        signal = CarveoutSignal(
                            signal_type=s_data['signal_type'],
                            signal_category=s_data['signal_category'],
                            evidence=s_data['evidence'],
                            confidence=s_data['confidence']
                        )
                        div_signals.append(signal)
                
                # 4. Score
                probability = signal_detector.calculate_probability(division, div_signals)
                timeline = signal_detector.determine_timeline(probability)
                att_score = await attractiveness_scorer.score(division)
                
                division.carveout_probability = probability
                division.carveout_timeline = timeline
                division.attractiveness_score = att_score
                
    
                # Link to parent if possible
                # For now, we might not have a CorporateParent record for every target, creates one if needed?
                # Simplified: just save division. In real app, need to manage Parent <-> Division relationship.
                # Let's check if we have a parent for this target.
                
                # (Optional) specific parent lookup logic here...
                
                try:
                    session.add(division)
                    await session.flush() # Get ID
                    
                    # Save signals
                    for sig in div_signals:
                        sig.division_id = division.id
                        session.add(sig)
                    
                    await session.commit()
                    print(f"    [+] Saved division {division.division_name} (ID: {division.id})")
                except Exception as e:
                    print(f"    [!] Error saving division: {e}")
                    await session.rollback()
    
                print(f"  > Division: {division.division_name}")
                print(f"    - Probability: {probability}% ({timeline})")
                print(f"    - Attractiveness Score: {att_score}/100")
                
                if probability > 50:
                     print(f"    [!] Potential Target Found!")
    
        # 5. Check Activist Activity
        print("Checking Activist Activity...")
        activist_campaigns = await activist_tracker.scrape_news_for_activists()
        for campaign in activist_campaigns:
            print(f"  > Campaign: {campaign['activist_name']} vs {campaign['target_company']} ({campaign['demand']})")
    
        print("\nScan Complete.")

if __name__ == "__main__":
    asyncio.run(scan_carveouts())
