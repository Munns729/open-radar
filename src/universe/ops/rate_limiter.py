"""
Rate limiter for free-tier API sources.
"""
import asyncio
import logging
import time
from collections import defaultdict
from typing import Dict, List

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Manages rate limits for free-tier APIs.
    """

    LIMITS = {
        "companies_house": {"limit": 600, "period": 300},   # 600/5min
        "google_search":   {"limit": 100, "period": 3600},  # 100/hour (conservative)
        "epo":             {"limit": 1000, "period": 3600},  # 1000/hour
        "esma":            {"limit": 100, "period": 60},     # 100/min
        "generic_scrape":  {"limit": 60,  "period": 60},    # 1/sec average
    }

    def __init__(self):
        self.usage: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def acquire(self, source: str) -> None:
        """Wait until the rate limit allows a request."""
        if source not in self.LIMITS:
            return

        config = self.LIMITS[source]

        async with self._lock:
            while True:
                now = time.time()
                self.usage[source] = [
                    t for t in self.usage[source]
                    if t > now - config["period"]
                ]

                if len(self.usage[source]) < config["limit"]:
                    self.usage[source].append(now)
                    return

                oldest = min(self.usage[source])
                wait_time = oldest + config["period"] - now + 0.1
                logger.debug(f"Rate limited on {source}, waiting {wait_time:.1f}s")
                await asyncio.sleep(min(wait_time, 5))

    def get_usage(self, source: str) -> Dict[str, int]:
        """Return current usage stats for a source."""
        if source not in self.LIMITS:
            return {"used": 0, "limit": 0}

        config = self.LIMITS[source]
        now = time.time()
        recent = [t for t in self.usage[source] if t > now - config["period"]]
        return {
            "used": len(recent),
            "limit": config["limit"],
            "period": config["period"],
        }


# Global singleton
rate_limiter = RateLimiter()
