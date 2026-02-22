"""
Scraper for ANSSI (Agence Nationale de la Sécurité des Systèmes d'Information) - French cybersecurity certification.
Discovers companies with ANSSI Qualified or Certified products (strong regulatory moat signal).
Source: https://cyber.gouv.fr/decouvrir-les-solutions-certifiees and decouvrir-les-solutions-qualifiees
Uses Playwright for JS-rendered pages.
"""
import asyncio
import logging
import re
from typing import List, Dict, Any

from src.universe.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# ANSSI certification pages
PAGES = [
    ("https://cyber.gouv.fr/decouvrir-les-solutions-certifiees", "ANSSI_CERTIFIED"),
    ("https://cyber.gouv.fr/decouvrir-les-solutions-qualifiees", "ANSSI_QUALIFIED"),
]


class ANSSIScraper(BaseScraper):
    """
    Scraper for ANSSI certified/qualified products and services.
    Extracts company names from the French cybersecurity certification registry.
    """

    async def discover_companies(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Discover companies from ANSSI certification pages.
        """
        companies = {}

        # Use context manager's browser if available, else create one
        if self.context:
            page = await self.context.new_page()
            own_browser = False
        else:
            browser, context, page = await self.create_browser_context()
            own_browser = True

        try:
            for url, cert_type in PAGES:
                if len(companies) >= limit:
                    break

                logger.info(f"Scraping ANSSI {cert_type} from {url}...")

                if not await self.safe_goto_with_retry(page, url, timeout=15000):
                    logger.warning(f"Failed to load {url}")
                    continue

                await asyncio.sleep(2)

                # ANSSI pages may use various structures: view rows, cards, tables
                # Try common selectors for Drupal/gov sites
                selectors = [
                    "table tbody tr",
                    ".view-content .views-row",
                    ".certification-item",
                    ".product-item",
                    "article",
                    ".field--name-field-titulaire",
                    "[class*='certif']",
                    "[class*='product']",
                ]

                for sel in selectors:
                    try:
                        items = await page.locator(sel).all()
                        if not items:
                            continue

                        for item in items:
                            if len(companies) >= limit:
                                break

                            try:
                                text = await item.inner_text()
                                # Look for company-like names (Title Case, 2+ words often)
                                # ANSSI format often: "Product Name - Company Name" or "Company: Product"
                                lines = [l.strip() for l in text.split("\n") if l.strip()]

                                for line in lines:
                                    # Skip very short or all-caps headers
                                    if len(line) < 4 or len(line) > 120:
                                        continue
                                    # Skip if looks like product name only (e.g. "CSPN-2024-001")
                                    if re.match(r"^[A-Z]{2,6}-\d{4}", line):
                                        continue
                                    # Skip gov/ANSSI text
                                    if any(
                                        x in line.lower()
                                        for x in [
                                            "anssi",
                                            "cyber.gouv",
                                            "certificat",
                                            "qualification",
                                            "décision",
                                            "niveau",
                                        ]
                                    ):
                                        continue

                                    # Could be company name
                                    clean = line.strip()
                                    if clean and clean not in companies:
                                        companies[clean] = {
                                            "name": clean,
                                            "website": None,
                                            "description": f"ANSSI {cert_type.replace('_', ' ')} - French cybersecurity certification",
                                            "address": None,
                                            "hq_country": "FR",
                                            "companies_house_number": None,
                                            "registration_number": None,
                                            "certification_type": cert_type,
                                            "certification_number": None,
                                            "scope": "Cybersecurity",
                                            "issuing_body": "ANSSI",
                                            "source_url": url,
                                        }
                            except Exception as e:
                                continue

                        if companies:
                            break
                    except Exception as e:
                        continue

                # Fallback: extract from any links that look like company/product pages
                if not companies:
                    links = await page.locator("a[href*='cyber.gouv']").all()
                    for link in links[:50]:
                        try:
                            href = await link.get_attribute("href")
                            text = await link.inner_text()
                            if (
                                href
                                and "/decouvrir" in href
                                and text
                                and len(text) > 3
                                and len(text) < 80
                            ):
                                clean = text.strip()
                                if clean and clean not in companies:
                                    companies[clean] = {
                                        "name": clean,
                                        "website": None,
                                        "description": f"ANSSI certified/qualified - French cybersecurity",
                                        "address": None,
                                        "hq_country": "FR",
                                        "companies_house_number": None,
                                        "registration_number": None,
                                        "certification_type": "ANSSI_CERTIFIED",
                                        "certification_number": None,
                                        "scope": "Cybersecurity",
                                        "issuing_body": "ANSSI",
                                        "source_url": href if href.startswith("http") else f"https://cyber.gouv.fr{href}",
                                    }
                        except Exception:
                            continue

        finally:
            if own_browser:
                await self.close_browser_context(context, browser)
            else:
                await page.close()

        results = list(companies.values())[:limit]
        logger.info(f"ANSSI discovered {len(results)} companies")
        return results

    async def scrape(self, limit: int = 100) -> Any:
        """Scrape ANSSI. Returns object with .data for workflow."""
        class Result:
            data = []

        Result.data = await self.discover_companies(limit)
        return Result


if __name__ == "__main__":
    async def main():
        logging.basicConfig(level=logging.INFO)
        scraper = ANSSIScraper(headless=True)
        results = await scraper.discover_companies(limit=10)
        for r in results:
            print(f"  - {r['name']} ({r.get('certification_type', '')})")
        print(f"Total: {len(results)} companies")

    asyncio.run(main())
