"""Main workflow orchestration."""

import asyncio
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.core.database import async_session_factory
from .filters import ReportFilters, apply_filters
from .generators.html_generator import HTMLReportGenerator
from .generators.excel_generator import ExcelReportGenerator
from .generators.table_generator import TableReportGenerator
from .database import ReportMetadata


async def generate_report(
    report_type: str = 'targets',
    output_format: str = 'html',
    filters: Optional[ReportFilters] = None,
    output_dir: str = 'outputs'
) -> List[str]:
    """
    Generate investment target reports.
    
    Args:
        report_type: Type of report ('targets', 'hot_targets', 'sector_focus')
        output_format: Output format ('html', 'excel', 'table', 'all')
        filters: ReportFilters object
        output_dir: Output directory path
    
    Returns:
        List of generated file paths
    """
    console = Console()
    
    # Header
    console.print("\n[bold blue]📊 RADAR REPORTING MODULE[/bold blue]\n")
    
    # Default filters
    if filters is None:
        filters = ReportFilters()
    
    # Adjust filters based on report type
    if report_type == 'hot_targets':
        filters.priority = 'hot'
        console.print("[yellow]Report Type: HOT TARGETS (Moat ≥85)[/yellow]")
    elif report_type == 'sector_focus' and not filters.sector:
        console.print("[red]Error: sector_focus requires --sector parameter[/red]")
        return []
    
    # Display filters
    console.print(f"\n[bold]🔍 Filters:[/bold]")
    if filters.tier:
        console.print(f"   • Tier: {filters.tier}")
    if filters.sector:
        console.print(f"   • Sector: {', '.join(filters.sector)}")
    if filters.priority:
        console.print(f"   • Priority: {filters.priority.upper()}")
    console.print(f"   • Moat Range: {filters.min_moat}-{filters.max_moat}")
    
    # Fetch companies from database
    console.print("\n[bold]📊 Fetching companies from database...[/bold]")
    
    try:
        async with async_session_factory() as session:
            companies = await apply_filters(session, filters)
        
        if not companies:
            console.print("[red]No companies found matching filters.[/red]")
            return []
        
        console.print(f"[green]✓ Found {len(companies)} companies[/green]")
        
    except Exception as e:
        console.print(f"[red]Database error: {e}[/red]")
        return []
    
    # Generate reports
    console.print(f"\n[bold]🎨 Generating {output_format.upper()} report(s)...[/bold]\n")
    
    output_files = []
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            # HTML
            if output_format in ['html', 'all']:
                task = progress.add_task("Generating HTML...", total=None)
                html_gen = HTMLReportGenerator(output_dir)
                html_file = html_gen.generate(companies)
                output_files.append(html_file)
                progress.remove_task(task)
                console.print(f"   ✅ HTML:  {html_file}")
            
            # Excel
            if output_format in ['excel', 'all']:
                task = progress.add_task("Generating Excel...", total=None)
                excel_gen = ExcelReportGenerator(output_dir)
                excel_file = excel_gen.generate(companies)
                output_files.append(excel_file)
                progress.remove_task(task)
                console.print(f"   ✅ Excel: {excel_file}")
            
            # Table
            if output_format in ['table', 'all']:
                console.print("\n")
                table_gen = TableReportGenerator()
                table_gen.generate(companies)
                console.print("\n   ✅ Table: Displayed above")
        
        # Summary
        console.print(f"\n[bold green]✨ Report generation complete![/bold green]")
        console.print(f"\n[bold]📈 Summary:[/bold]")
        
        hot_count = sum(1 for c in companies if c.moat_score >= 85)
        high_count = sum(1 for c in companies if 75 <= c.moat_score < 85)
        
        console.print(f"   • Total companies: {len(companies)}")
        console.print(f"   • HOT priorities: {hot_count}")
        console.print(f"   • HIGH priorities: {high_count}")
        
        avg_moat = sum(c.moat_score for c in companies) / len(companies)
        console.print(f"   • Average moat: {avg_moat:.0f}/100")
        
        total_revenue = sum(c.revenue_gbp or 0 for c in companies) / 1_000_000_000
        console.print(f"   • Total market: £{total_revenue:.1f}B")
        
        console.print()
        
        return output_files
        
    except Exception as e:
        console.print(f"\n[red]Error generating reports: {e}[/red]")
        import traceback
        traceback.print_exc()
        return []
