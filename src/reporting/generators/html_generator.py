"""HTML report generator with interactive filtering."""

from typing import List
from datetime import datetime
from src.universe.database import CompanyModel as Company
from .base import BaseGenerator
from ..filters import get_priority_level, get_priority_color


class HTMLReportGenerator(BaseGenerator):
    """Generate interactive HTML reports."""
    
    def generate(self, companies: List[Company], filename: str = None) -> str:
        """Generate HTML report."""
        output_file = self.output_dir / self._get_filename("radar_targets", "html", filename)
        
        # Calculate statistics
        stats = self._calculate_stats(companies)
        sector_counts = self._get_sector_counts(companies)
        
        # Generate HTML
        html = self._generate_html(companies, stats, sector_counts)
        
        # Write to file
        output_file.write_text(html, encoding='utf-8')
        
        return str(output_file)
    
    def _calculate_stats(self, companies: List[Company]) -> dict:
        """Calculate report statistics."""
        hot_count = sum(1 for c in companies if c.moat_score >= 70)
        high_count = sum(1 for c in companies if 50 <= c.moat_score < 70)
        med_count = sum(1 for c in companies if 30 <= c.moat_score < 50)
        low_count = sum(1 for c in companies if c.moat_score < 30)
        
        tier_1a = sum(1 for c in companies if c.tier == 'TIER_1A')
        tier_1b = sum(1 for c in companies if c.tier == 'TIER_1B')
        
        avg_moat = sum(c.moat_score for c in companies) / len(companies) if companies else 0
        
        total_revenue = sum(c.revenue_gbp or 0 for c in companies)
        
        return {
            'total': len(companies),
            'tier_1a': tier_1a,
            'tier_1b': tier_1b,
            'hot': hot_count,
            'high': high_count,
            'med': med_count,
            'low': low_count,
            'avg_moat': avg_moat,
            'total_revenue': total_revenue
        }
    
    def _generate_html(self, companies: List[Company], stats: dict, sectors: dict) -> str:
        """Generate complete HTML document."""
        
        # Generate table rows
        rows_html = ""
        for company in companies:
            priority = get_priority_level(company.moat_score)
            bg_color, text_color = get_priority_color(company.moat_score)
            
            rows_html += f"""
            <tr class="data-row" data-priority="{priority}">
                <td>
                    <span class="priority-badge" style="background-color: {bg_color}; color: {text_color};">
                        {priority.upper()}
                    </span>
                </td>
                <td class="company-name">{company.name}</td>
                <td class="text-center font-bold">{company.moat_score}</td>
                <td>{company.sector or 'N/A'}</td>
                <td>{self._format_revenue(company.revenue_gbp)}</td>
                <td>{company.moat_type or 'N/A'}</td>
                <td class="text-center">{company.tier or 'N/A'}</td>
            </tr>
            """
        
        # Generate sector cards
        sector_cards_html = ""
        for sector, count in list(sectors.items())[:8]:
            sector_cards_html += f"""
            <div class="sector-card">
                <div class="sector-name">{sector}</div>
                <div class="sector-count">{count} companies</div>
            </div>
            """
        
        # Complete HTML template
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RADAR Investment Targets - {datetime.now().strftime('%Y-%m-%d')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            color: #1a202c;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            padding: 2rem;
        }}
        
        header {{
            text-align: center;
            margin-bottom: 2rem;
            padding-bottom: 2rem;
            border-bottom: 2px solid #e2e8f0;
        }}
        
        h1 {{
            font-size: 2.5rem;
            color: #2d3748;
            margin-bottom: 0.5rem;
        }}
        
        .subtitle {{
            color: #718096;
            font-size: 1.1rem;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .stat-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        
        .stat-label {{
            font-size: 0.875rem;
            opacity: 0.9;
            margin-bottom: 0.5rem;
        }}
        
        .stat-value {{
            font-size: 2rem;
            font-weight: bold;
        }}
        
        .filters {{
            display: flex;
            gap: 0.75rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }}
        
        .filter-btn {{
            padding: 0.75rem 1.5rem;
            border: 2px solid #e2e8f0;
            background: white;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            transition: all 0.2s;
        }}
        
        .filter-btn:hover {{
            background: #f7fafc;
            transform: translateY(-2px);
        }}
        
        .filter-btn.active {{
            background: #667eea;
            color: white;
            border-color: #667eea;
        }}
        
        .table-wrapper {{
            overflow-x: auto;
            margin-bottom: 2rem;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        thead {{
            background: #f7fafc;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        
        th {{
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            color: #2d3748;
            border-bottom: 2px solid #e2e8f0;
        }}
        
        td {{
            padding: 1rem;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        tr:hover {{
            background: #f7fafc;
        }}
        
        .priority-badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
        }}
        
        .company-name {{
            font-weight: 600;
            color: #2d3748;
        }}
        
        .text-center {{
            text-align: center;
        }}
        
        .font-bold {{
            font-weight: 700;
        }}
        
        .sectors-section {{
            margin-top: 2rem;
        }}
        
        .sectors-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }}
        
        .sector-card {{
            background: #f7fafc;
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        
        .sector-name {{
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 0.25rem;
        }}
        
        .sector-count {{
            color: #718096;
            font-size: 0.875rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 RADAR Investment Targets</h1>
            <p class="subtitle">Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        </header>
        
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-label">Total Companies</div>
                <div class="stat-value">{stats['total']}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Tier 1A</div>
                <div class="stat-value">{stats['tier_1a']}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">HOT Priorities</div>
                <div class="stat-value">{stats['hot']}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Avg Moat Score</div>
                <div class="stat-value">{stats['avg_moat']:.0f}</div>
            </div>
        </div>
        
        <div class="filters">
            <button class="filter-btn active" onclick="filterTable('all')">All ({stats['total']})</button>
            <button class="filter-btn" onclick="filterTable('hot')">🔴 HOT ({stats['hot']})</button>
            <button class="filter-btn" onclick="filterTable('high')">🟠 HIGH ({stats['high']})</button>
            <button class="filter-btn" onclick="filterTable('med')">🟡 MED ({stats['med']})</button>
            <button class="filter-btn" onclick="filterTable('low')">⚪ LOW ({stats['low']})</button>
        </div>
        
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>Priority</th>
                        <th>Company Name</th>
                        <th class="text-center">Moat Score</th>
                        <th>Sector</th>
                        <th>Revenue</th>
                        <th>Moat Type</th>
                        <th class="text-center">Tier</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        
        <div class="sectors-section">
            <h2 style="color: #2d3748; margin-bottom: 1rem;">📊 Sector Breakdown</h2>
            <div class="sectors-grid">
                {sector_cards_html}
            </div>
        </div>
    </div>
    
    <script>
        function filterTable(priority) {{
            const rows = document.querySelectorAll('.data-row');
            const buttons = document.querySelectorAll('.filter-btn');
            
            // Update button states
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            // Filter rows
            rows.forEach(row => {{
                if (priority === 'all' || row.dataset.priority === priority) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                }}
            }});
        }}
    </script>
</body>
</html>
        """
        
        return html
