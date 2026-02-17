"""Console table generator using Rich."""

from typing import List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from src.universe.database import CompanyModel as Company
from .base import BaseGenerator
from ..filters import get_priority_emoji


class TableReportGenerator(BaseGenerator):
    """Generate console table reports using Rich."""
    
    def __init__(self):
        """Initialize without output dir (prints to console)."""
        self.console = Console()
    
    def generate(self, companies: List[Company], filename: str = None) -> str:
        """Generate and print table report."""
        
        # Print header
        self.console.print("\n[bold blue]📊 RADAR Investment Targets[/bold blue]\n")
        
        # Print statistics
        self._print_stats(companies)
        
        # Print Tier 1A table
        tier_1a = [c for c in companies if c.tier == 'TIER_1A']
        if tier_1a:
            self.console.print("\n[bold]🎯 Tier 1A Targets (Top 30)[/bold]\n")
            self._print_table(tier_1a[:30])
        
        # Print Tier 1B table
        tier_1b = [c for c in companies if c.tier == 'TIER_1B']
        if tier_1b:
            self.console.print("\n[bold]🎯 Tier 1B Targets (Top 20)[/bold]\n")
            self._print_table(tier_1b[:20])
        
        # Print sector breakdown
        self._print_sector_breakdown(companies)
        
        return "Console output"
    
    def _print_stats(self, companies: List[Company]):
        """Print statistics panel."""
        hot = sum(1 for c in companies if c.moat_score >= 85)
        high = sum(1 for c in companies if 75 <= c.moat_score < 85)
        med = sum(1 for c in companies if 65 <= c.moat_score < 75)
        low = sum(1 for c in companies if c.moat_score < 65)
        
        tier_1a = sum(1 for c in companies if c.tier == 'TIER_1A')
        tier_1b = sum(1 for c in companies if c.tier == 'TIER_1B')
        
        avg_moat = sum(c.moat_score for c in companies) / len(companies) if companies else 0
        
        stats_text = f"""
[bold]Total Companies:[/bold] {len(companies)}
[bold]Tier 1A:[/bold] {tier_1a}  [bold]Tier 1B:[/bold] {tier_1b}

[bold]Priority Breakdown:[/bold]
  🔴 HOT (85+):   {hot:3d}  {"█" * min(hot // 2, 40)}
  🟠 HIGH (75-84): {high:3d}  {"█" * min(high // 2, 40)}
  🟡 MED (65-74):  {med:3d}  {"█" * min(med // 2, 40)}
  ⚪ LOW (<65):    {low:3d}  {"█" * min(low // 2, 40)}

[bold]Average Moat Score:[/bold] {avg_moat:.1f}/100
        """
        
        self.console.print(Panel(stats_text, title="📈 Summary", border_style="blue"))
    
    def _print_table(self, companies: List[Company]):
        """Print company table."""
        table = Table(show_header=True, header_style="bold magenta")
        
        table.add_column("Pri", justify="center", width=4)
        table.add_column("Company Name", width=40)
        table.add_column("Moat", justify="center", width=5)
        table.add_column("Sector", width=20)
        table.add_column("Revenue", justify="right", width=12)
        table.add_column("Moat Type", width=20)
        
        for company in companies:
            emoji = get_priority_emoji(company.moat_score)
            
            table.add_row(
                emoji,
                company.name[:40],
                str(company.moat_score),
                (company.sector or "N/A")[:20],
                self._format_revenue(company.revenue_gbp),
                (company.moat_type or "N/A")[:20]
            )
        
        self.console.print(table)
    
    def _print_sector_breakdown(self, companies: List[Company]):
        """Print sector breakdown."""
        self.console.print("\n[bold]📊 Sector Breakdown[/bold]\n")
        
        sectors = self._get_sector_counts(companies)
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Sector", width=30)
        table.add_column("Count", justify="right", width=8)
        table.add_column("Distribution", width=40)
        
        total = len(companies)
        for sector, count in list(sectors.items())[:10]:
            pct = (count / total) * 100
            bar = "█" * int(pct / 2)
            table.add_row(sector, str(count), f"{bar} {pct:.1f}%")
        
        self.console.print(table)
