"""Competitive Radar Workflow Orchestration"""
import asyncio
import logging
import re
from datetime import datetime
from rich.console import Console
from rich.table import Table

from src.competitive.database import init_db, create_announcement
from src.competitive.linkedin_scraper import LinkedInScraper
from src.competitive.kimi_analyzer import KimiAnalyzer
from src.competitive.threat_scorer import ThreatScorer

logger = logging.getLogger(__name__)

async def run_competitive_radar(headless: bool = True):
    """Run the end-to-end competitive radar workflow"""
    console = Console()
    console.print(f"[bold blue]Starting Competitive Radar (Headless: {headless})...[/bold blue]")

    # 1. Initialize Database
    await init_db()
    
    # 2. Scrape LinkedIn
    scraper = LinkedInScraper(headless=headless)
    screenshots = []
    try:
        await scraper.setup_session()
        await scraper.login()
        
        # Scrape feed (default 30 scrolls ~ 60 posts)
        output = await scraper.scrape_feed(scrolls=30)
        screenshots = [item['image'] for item in output.data]
        console.print(f"[green]Scraped {len(screenshots)} screenshots[/green]")
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}", exc_info=True)
        console.print(f"[red]Scraping failed: {e}[/red]")
        return
    finally:
        await scraper.close()

    if not screenshots:
        console.print("[yellow]No screenshots capture. Exiting.[/yellow]")
        return

    # 3. Analyze with AI
    analyzer = KimiAnalyzer()
    console.print("[blue]Analyzing screenshots with Kimi (Moonshot)...[/blue]")
    try:
        analysis_output = await analyzer.analyze_screenshots(screenshots)
        announcements = analysis_output.result.get('announcements', [])
        console.print(f"[green]Found {len(announcements)} potential announcements[/green]")
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        console.print(f"[red]Analysis failed: {e}[/red]")
        return

    # 4. Score and Save
    from src.core.database import get_async_db
    
    scorer = ThreatScorer()
    new_threats = []
    
    async with get_async_db() as session:
        for ann in announcements:
            try:
                # Score
                threat_score = scorer.score_announcement(ann)
                
                # Extract score safely
                score_match = re.search(r'(\d+)/100', threat_score.details)
                score_val = int(score_match.group(1)) if score_match else 0
    
                # Save to DB
                await create_announcement(
                    session=session,
                    announcement_data={
                        "company_name": ann['company_name'],
                        "vc_firm_id": None, # Link if firm exists, skipping for now
                        "round_type": ann.get('round_type'),
                        "amount_gbp": ann.get('amount_raised_gbp'),
                        "announced_date": datetime.now().date(),
                        "description": ann.get('description'),
                        "source_url": "linkedin_feed",
                        "linkedin_post_url": ""
                    },
                    threat_data={
                        "category": ann.get('sector'),
                        "threat_score": score_val,
                        "threat_level": threat_score.threat_level.value if hasattr(threat_score.threat_level, 'value') else threat_score.threat_level,
                        "reasoning": threat_score.details
                    }
                )
                await session.commit()
                
                # Keep track for report
                if threat_score.threat_level in ["high", "critical", "medium"]: # Adjust based on enum values
                     new_threats.append({
                         "company": ann['company_name'],
                         "vc": ann.get('vc_firm', 'Unknown'),
                         "amount": ann.get('amount_raised_gbp', 0),
                         "score": threat_score.details
                     })
                     
            except Exception as e:
                logger.error(f"Error processing announcement {ann.get('company_name')}: {e}", exc_info=True)

    # 5. Generate Report
    print_report(console, new_threats, len(announcements))
    
    return {
        "processed": len(screenshots),
        "announcements": len(announcements),
        "threats": len(new_threats)
    }

def print_report(console, threats, total_anns):
    """Print summary report to console"""
    console.print("\n[bold]RADAR COMPETITIVE INTELLIGENCE REPORT[/bold]")
    console.print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    console.print(f"Total Announcements Processed: {total_anns}")
    
    if not threats:
        console.print("\n[green]No significant threats detected.[/green]")
        return

    table = Table(title="Detected Threats")
    table.add_column("Company", style="cyan")
    table.add_column("VC Firm", style="magenta")
    table.add_column("Amount", justify="right")
    table.add_column("Score/Reasoning", style="red")

    for t in threats:
        table.add_row(
            t['company'],
            t['vc'],
            f"£{t['amount']:,.0f}" if t['amount'] else "N/A",
            t['score']
        )

    console.print(table)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Competitive Radar Workflow")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (default: False for manual run, True via function default)")
    parser.add_argument("--no-headless", action="store_false", dest="headless", help="Run in visible mode (default)")
    parser.set_defaults(headless=False) # Default to visible when running manually for safety/debugging
    
    args = parser.parse_args()
    
    asyncio.run(run_competitive_radar(headless=args.headless))
