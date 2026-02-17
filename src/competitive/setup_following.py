"""Setup script to follow target VCs on LinkedIn"""
import asyncio
import logging
from rich.console import Console

from src.competitive.linkedin_scraper import LinkedInScraper
from src.competitive.threat_scorer import ThreatScorer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_following():
    """Follow all Tier A VCs defined in ThreatScorer"""
    console = Console()
    console.print("[bold blue]Starting VC Follower setup...[/bold blue]")
    
    scraper = LinkedInScraper(headless=False)
    
    try:
        await scraper.setup_session()
        await scraper.login_manual()
        
        target_vcs = ThreatScorer.TIER_A_VCS
        console.print(f"[green]Found {len(target_vcs)} target VCs to follow: {', '.join(target_vcs)}[/green]")
        
        for vc in target_vcs:
            console.print(f"Processing: [bold]{vc}[/bold]")
            await scraper.follow_company(vc)
            # Random delay to be safe
            await asyncio.sleep(2)
            
        console.print("[bold green]Finished following VCs![/bold green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(setup_following())
