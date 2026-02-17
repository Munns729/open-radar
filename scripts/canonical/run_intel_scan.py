import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.market_intelligence.workflow import run_intel_scan

if __name__ == "__main__":
    print("=== Running Market Intel Scan ===")
    print("This will fetch from RSS feeds and populate intelligence_items table.")
    print()
    asyncio.run(run_intel_scan())
    print()
    print("=== Scan Complete ===")
