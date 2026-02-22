"""
Scraper for BSI (Bundesamt für Sicherheit in der Informationstechnik) - German Federal Office for Information Security.
Discovers companies with BSI Common Criteria certifications (strong regulatory moat signal for DE).
Source: https://www.bsi.bund.de/EN/.../zertifizierte-produkte-nach-cc_node.html
"""
import asyncio
import logging
import re
import ssl
from typing import List, Dict, Any, Optional

import aiohttp

from src.core.config import settings

logger = logging.getLogger(__name__)

# BSI CC certification category pages (applicant = company name)
CC_CATEGORY_URLS = [
    "https://www.bsi.bund.de/EN/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/Zertifizierung-und-Anerkennung/Zertifizierung-von-Produkten/Zertifizierung-nach-CC/Zertifizierte-Produkte-nach-CC/zertifizierte-produkte-nach-cc_node.html",
    "https://www.bsi.bund.de/EN/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/Zertifizierung-und-Anerkennung/Zertifizierung-von-Produkten/Zertifizierung-nach-CC/Zertifizierte-Produkte-nach-CC/Sonstiges/Sonstiges_node.html",
    "https://www.bsi.bund.de/EN/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/Zertifizierung-und-Anerkennung/Zertifizierung-von-Produkten/Zertifizierung-nach-CC/Zertifizierte-Produkte-nach-CC/Serveranwendungen/Serveranwendungen_node.html",
    "https://www.bsi.bund.de/EN/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/Zertifizierung-und-Anerkennung/Zertifizierung-von-Produkten/Zertifizierung-nach-CC/Zertifizierte-Produkte-nach-CC/Betriebssysteme/Betriebssystem_node.html",
    "https://www.bsi.bund.de/EN/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/Zertifizierung-und-Anerkennung/Zertifizierung-von-Produkten/Zertifizierung-nach-CC/Zertifizierte-Produkte-nach-CC/Netzwerkprodukte/Netzwerkprodukte_node.html",
]


class BSIScraper:
    """
    Client for BSI Common Criteria certified products list.
    Extracts applicant (company) names from certification tables.
    """

    def __init__(self, rate_limit_delay: float = 0.8):
        self.rate_limit_delay = rate_limit_delay
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        kwargs = {
            "headers": {
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en,de;q=0.9",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
            },
        }
        if settings.ignore_ssl_errors:
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            kwargs["connector"] = aiohttp.TCPConnector(ssl=ssl_ctx)
        self.session = aiohttp.ClientSession(**kwargs)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _rate_limit(self):
        await asyncio.sleep(self.rate_limit_delay)

    def _extract_applicants_from_html(self, html: str, source_url: str) -> List[Dict[str, Any]]:
        """
        Parse BSI HTML for applicant names in certification tables.
        Table structure: | cert link | cert number | product name | applicant | date |
        """
        companies = {}

        # Match table rows - BSI uses various patterns
        # Look for applicant column (typically 4th column in table)
        # Pattern: <td>...Applicant Name...</td> often before date
        # Or: text like "Secunet Security Networks AG" | "11.02.2026"
        applicant_pattern = re.compile(
            r"<td[^>]*>([^<]*(?:AG|GmbH|Inc\.|LLC|Corporation|Ltd\.|SA|SAS|SARL)[^<]*)</td>",
            re.IGNORECASE,
        )

        # Also try: | Product | Applicant | Date | structure
        # BSI table: certificate number, product name, applicant, date
        rows = re.findall(
            r"<tr[^>]*>.*?</tr>",
            html,
            re.DOTALL | re.IGNORECASE,
        )

        for row in rows:
            tds = re.findall(r"<td[^>]*>([^<]*(?:<[^>]+>[^<]*)*)</td>", row, re.DOTALL)
            if len(tds) >= 3:
                # Applicant is typically 3rd column (0-indexed: 2)
                for i, cell in enumerate(tds):
                    text = re.sub(r"<[^>]+>", "", cell).strip()
                    # Applicant: company name with legal form
                    if (
                        text
                        and len(text) > 4
                        and len(text) < 100
                        and any(
                            x in text
                            for x in ["AG", "GmbH", "Inc", "LLC", "Corp", "Ltd", "SA", "SAS"]
                        )
                    ):
                        # Skip if it looks like a date (dd.mm.yyyy)
                        if re.match(r"\d{1,2}\.\d{1,2}\.\d{4}", text):
                            continue
                        # Skip cert numbers
                        if re.match(r"^(BSI|EUCC)-\d", text):
                            continue
                        if text not in companies:
                            companies[text] = {
                                "name": text,
                                "website": None,
                                "description": "BSI Common Criteria certified product - German cybersecurity certification",
                                "address": None,
                                "hq_country": "DE",
                                "companies_house_number": None,
                                "registration_number": None,
                                "certification_type": "BSI_CC",
                                "certification_number": None,
                                "scope": "Common Criteria",
                                "issuing_body": "BSI",
                                "source_url": source_url,
                            }

        return list(companies.values())

    async def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch HTML page."""
        if not self.session:
            raise RuntimeError("Scraper context not entered.")

        for attempt in range(3):
            try:
                await self._rate_limit()
                async with self.session.get(url, timeout=30) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 429:
                        logger.warning(f"BSI rate limited. Waiting 60s. Attempt {attempt + 1}")
                        await asyncio.sleep(60)
                    else:
                        logger.error(f"BSI fetch error {response.status} for {url}")
                        return None
            except Exception as e:
                logger.error(f"BSI request failed for {url}: {e}")
                await asyncio.sleep(2)
        return None

    async def discover(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Discover companies from BSI CC certification pages.
        """
        all_companies = {}
        seen = set()

        for url in CC_CATEGORY_URLS:
            if len(all_companies) >= limit:
                break

            html = await self._fetch_page(url)
            if not html:
                continue

            companies = self._extract_applicants_from_html(html, url)
            for c in companies:
                name = c["name"]
                if name not in seen:
                    seen.add(name)
                    all_companies[name] = c

        result = list(all_companies.values())[:limit]
        logger.info(f"BSI discovered {len(result)} companies")
        return result

    async def scrape(self, limit: int = 100) -> Any:
        """Scrape BSI. Returns object with .data for workflow."""
        class Result:
            data = []

        try:
            Result.data = await self.discover(limit)
        except Exception as e:
            logger.warning(f"BSI scrape failed: {e}")

        return Result


if __name__ == "__main__":
    async def main():
        logging.basicConfig(level=logging.INFO)
        async with BSIScraper() as scraper:
            print("Testing BSI discovery (limit=10)...")
            results = await scraper.discover(limit=10)
            for r in results:
                print(f"  - {r['name']}")
            print(f"Total: {len(results)} companies")

    asyncio.run(main())
