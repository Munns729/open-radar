"""CLI entry point for reporting module."""

import asyncio
import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.reporting.workflow import generate_report
from src.reporting.filters import ReportFilters


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description='Generate RADAR investment target reports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate HTML report for Tier 1A
  python -m src.reporting --format html --tier 1A

  # Generate all formats for HOT priorities
  python -m src.reporting --format all --hot-only

  # Generate Excel for Defence sector
  python -m src.reporting --format excel --sector Defence Aerospace

  # Quick console table view
  python -m src.reporting --format table --tier both
        """
    )
    
    # Output format
    parser.add_argument(
        '--format',
        choices=['html', 'excel', 'table', 'all'],
        default='html',
        help='Output format (default: html)'
    )
    
    # Report type
    parser.add_argument(
        '--type',
        choices=['targets', 'hot_targets', 'sector_focus'],
        default='targets',
        help='Report type (default: targets)'
    )
    
    # Filters
    parser.add_argument(
        '--tier',
        choices=['1A', '1B', 'both', 'all'],
        default='1A',
        help='Company tier filter (default: 1A)'
    )
    
    parser.add_argument(
        '--sector',
        nargs='+',
        help='Sector filter (space-separated list)'
    )
    
    parser.add_argument(
        '--min-moat',
        type=int,
        default=50,
        help='Minimum moat score (default: 50)'
    )
    
    parser.add_argument(
        '--max-moat',
        type=int,
        default=100,
        help='Maximum moat score (default: 100)'
    )
    
    parser.add_argument(
        '--min-revenue',
        type=float,
        help='Minimum revenue in GBP millions'
    )
    
    parser.add_argument(
        '--max-revenue',
        type=float,
        help='Maximum revenue in GBP millions'
    )
    
    parser.add_argument(
        '--priority',
        choices=['hot', 'high', 'med', 'low', 'all'],
        help='Priority filter'
    )
    
    parser.add_argument(
        '--hot-only',
        action='store_true',
        help='Only HOT priorities (moat ≥85) - shortcut for --priority hot'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of results'
    )
    
    parser.add_argument(
        '--output-dir',
        default='outputs',
        help='Output directory (default: outputs)'
    )
    
    args = parser.parse_args()
    
    # Build filters
    filters = ReportFilters(
        tier=args.tier,
        sector=args.sector,
        min_moat=args.min_moat,
        max_moat=args.max_moat,
        min_revenue=args.min_revenue,
        max_revenue=args.max_revenue,
        priority='hot' if args.hot_only else args.priority,
        limit=args.limit
    )
    
    # Run async workflow
    try:
        asyncio.run(generate_report(
            report_type=args.type,
            output_format=args.format,
            filters=filters,
            output_dir=args.output_dir
        ))
    except KeyboardInterrupt:
        print("\n\nReport generation cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
