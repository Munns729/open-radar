"""
European Accreditation (EA) Registry Scraper

Discovers accredited certification bodies and testing labs across Europe.
EA is the umbrella organization for all European accreditation bodies.

Data sources:
- EA member accreditation bodies (UKAS, DAkkS, COFRAC, etc.)
- Direct scraping of national registries
"""
import asyncio
import logging
import re
from typing import Optional, List, Dict
from playwright.async_api import async_playwright

from .base import (
    DiscoverySource,
    DiscoverySourceType,
    DiscoveredCompany,
    MoatDimension,
)

logger = logging.getLogger(__name__)


# European accreditation body registries
EA_MEMBER_REGISTRIES = {
    "GB": {
        "name": "UKAS",
        "url": "https://www.ukas.com/find-an-organisation/",
        "search_url": "https://www.ukas.com/wp-admin/admin-ajax.php",
    },
    "DE": {
        "name": "DAkkS",
        "url": "https://www.dakks.de/en/content/accredited-bodies-dakks",
        "search_url": "https://www.dakks.de/en/akkreditierungsdatenbank",
    },
    "FR": {
        "name": "COFRAC",
        "url": "https://www.cofrac.fr/en/",
        "search_url": "https://www.cofrac.fr/en/rechercher-un-organisme-accredite/",
    },
    "NL": {
        "name": "RvA",
        "url": "https://www.rva.nl/en/",
        "search_url": "https://www.rva.nl/en/accredited-organisations/",
    },
    "IT": {
        "name": "Accredia",
        "url": "https://www.accredia.it/en/",
        "search_url": "https://services.accredia.it/accredia_labsearch.jsp",
    },
    "ES": {
        "name": "ENAC",
        "url": "https://www.enac.es/web/enac/inicio",
        "search_url": "https://www.enac.es/web/enac/entidades-acreditadas",
    },
    "BE": {
        "name": "BELAC",
        "url": "https://economie.fgov.be/en/themes/quality-safety/accreditation-belac",
        "search_url": "https://economie.fgov.be/en/themes/quality-safety/accreditation-belac/accredited-organisations",
    },
    "AT": {
        "name": "Akkreditierung Austria",
        "url": "https://www.bmdw.gv.at/en/Topics/International-and-European-Affairs/Accreditation.html",
        "search_url": None,  # Uses BMDW database
    },
    "CH": {
        "name": "SAS",
        "url": "https://www.sas.admin.ch/sas/en/home.html",
        "search_url": "https://www.sas.admin.ch/sas/en/home/akkreditiertestellen.html",
    },
    "SE": {
        "name": "Swedac",
        "url": "https://www.swedac.se/en/",
        "search_url": "https://www.swedac.se/en/services/accredited-organisations/",
    },
    "DK": {
        "name": "DANAK",
        "url": "https://www.danak.dk/en/",
        "search_url": "https://www.danak.dk/en/find-accredited-organisation/",
    },
    "NO": {
        "name": "Norsk Akkreditering",
        "url": "https://www.akkreditert.no/en/",
        "search_url": "https://www.akkreditert.no/en/find-accredited-organisation/",
    },
    "FI": {
        "name": "FINAS",
        "url": "https://www.finas.fi/sites/en/Pages/default.aspx",
        "search_url": "https://www.finas.fi/sites/en/accreditation/Pages/AccreditedOrganisations.aspx",
    },
    "IE": {
        "name": "INAB",
        "url": "https://www.inab.ie/",
        "search_url": "https://www.inab.ie/Our-Clients/Search-our-Database/",
    },
    "PL": {
        "name": "PCA",
        "url": "https://www.pca.gov.pl/en/",
        "search_url": "https://www.pca.gov.pl/en/accredited-organizations/",
    },
}


class EuropeanAccreditationScraper(DiscoverySource):
    """
    Scrapes European accreditation registries to discover certified
    testing labs, certification bodies, and inspection organizations.
    
    These companies have strong regulatory moats because:
    1. Accreditation is mandatory for certain testing/certification
    2. Multi-year processes to achieve accreditation
    3. Ongoing surveillance audits maintain barriers
    """
    
    def __init__(self, countries: Optional[List[str]] = None):
        """
        Initialize the scraper.
        
        Args:
            countries: List of ISO country codes to scrape (default: all)
        """
        all_countries = list(EA_MEMBER_REGISTRIES.keys())
        super().__init__(
            name="European Accreditation Registry",
            source_type=DiscoverySourceType.ACCREDITATION_REGISTRY,
            countries=countries or all_countries,
        )
        self.headless = True
    
    async def is_available(self) -> bool:
        """Check if at least one registry is accessible."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                # Try UKAS as it's usually reliable
                await page.goto("https://www.ukas.com", timeout=10000)
                await browser.close()
                return True
        except Exception as e:
            self.logger.error(f"Availability check failed: {e}")
            return False
    
    async def discover(self, limit: Optional[int] = None) -> List[DiscoveredCompany]:
        """
        Discover accredited organizations from European registries.
        
        Args:
            limit: Maximum total companies to return
            
        Returns:
            List of discovered companies with regulatory moat signals
        """
        all_companies = []
        
        for country in self.countries:
            if country not in EA_MEMBER_REGISTRIES:
                continue
                
            registry = EA_MEMBER_REGISTRIES[country]
            self.logger.info(f"Scraping {registry['name']} ({country})...")
            
            try:
                if country == "GB":
                    companies = await self._scrape_ukas(limit)
                elif country == "DE":
                    companies = await self._scrape_dakks(limit)
                elif country == "FR":
                    companies = await self._scrape_cofrac(limit)
                else:
                    # Generic scraper for other countries
                    companies = await self._scrape_generic(country, registry, limit)
                
                all_companies.extend(companies)
                self.logger.info(f"  Found {len(companies)} from {registry['name']}")
                
                if limit and len(all_companies) >= limit:
                    break
                    
            except Exception as e:
                self.logger.error(f"  Error scraping {registry['name']}: {e}")
                continue
        
        if limit:
            all_companies = all_companies[:limit]
            
        return all_companies
    
    async def _scrape_ukas(self, limit: Optional[int] = None) -> List[DiscoveredCompany]:
        """Scrape UKAS (United Kingdom Accreditation Service) registry."""
        companies = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            try:
                # UKAS search page
                await page.goto(
                    "https://www.ukas.com/find-an-organisation/",
                    timeout=30000
                )
                await page.wait_for_timeout(2000)
                
                # Search for all accredited organizations
                # UKAS uses a form-based search - we'll search with empty criteria
                search_button = await page.query_selector('input[type="submit"], button[type="submit"]')
                if search_button:
                    await search_button.click()
                    await page.wait_for_timeout(3000)
                
                # Parse results
                results = await page.query_selector_all('.organisation-result, .search-result, tr[data-id]')
                
                for result in results[:limit] if limit else results:
                    try:
                        name_el = await result.query_selector('.org-name, h3, td:first-child a')
                        if not name_el:
                            continue
                            
                        name = await name_el.inner_text()
                        name = name.strip()
                        
                        if not name:
                            continue
                        
                        # Try to get accreditation number
                        acc_num = None
                        acc_el = await result.query_selector('.acc-number, .accreditation-number')
                        if acc_el:
                            acc_num = await acc_el.inner_text()
                        
                        # Try to get scope/type
                        scope = None
                        scope_el = await result.query_selector('.scope, .type')
                        if scope_el:
                            scope = await scope_el.inner_text()
                        
                        company = DiscoveredCompany(
                            name=name,
                            country="GB",
                            source=self.name,
                            source_type=self.source_type,
                            source_url="https://www.ukas.com/find-an-organisation/",
                        )
                        
                        # Add regulatory moat signals
                        company.add_moat_signal(
                            MoatDimension.REGULATORY,
                            "UKAS Accredited"
                        )
                        if acc_num:
                            company.certifications.append(f"UKAS: {acc_num}")
                        if scope:
                            company.sector = scope
                        
                        # Also add liability moat for testing labs
                        if scope and any(x in scope.lower() for x in ['testing', 'laboratory', 'calibration']):
                            company.add_moat_signal(
                                MoatDimension.LIABILITY,
                                "ISO 17025 Testing Laboratory"
                            )
                        
                        companies.append(company)
                        
                    except Exception as e:
                        self.logger.debug(f"Error parsing result: {e}")
                        continue
                
            except Exception as e:
                self.logger.error(f"UKAS scrape error: {e}")
            finally:
                await browser.close()
        
        return companies
    
    async def _scrape_dakks(self, limit: Optional[int] = None) -> List[DiscoveredCompany]:
        """Scrape DAkkS (Deutsche Akkreditierungsstelle) registry."""
        companies = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            try:
                # DAkkS accreditation database
                await page.goto(
                    "https://www.dakks.de/en/content/accredited-bodies-dakks",
                    timeout=30000
                )
                await page.wait_for_timeout(2000)
                
                # Parse organization listings
                results = await page.query_selector_all('.view-content .views-row, table tbody tr')
                
                for result in results[:limit] if limit else results:
                    try:
                        name_el = await result.query_selector('a, td:first-child')
                        if not name_el:
                            continue
                            
                        name = await name_el.inner_text()
                        name = name.strip()
                        
                        if not name or len(name) < 3:
                            continue
                        
                        company = DiscoveredCompany(
                            name=name,
                            country="DE",
                            source=self.name,
                            source_type=self.source_type,
                            source_url="https://www.dakks.de/",
                        )
                        
                        company.add_moat_signal(
                            MoatDimension.REGULATORY,
                            "DAkkS Accredited (Germany)"
                        )
                        company.certifications.append("DAkkS Accreditation")
                        
                        companies.append(company)
                        
                    except Exception as e:
                        self.logger.debug(f"Error parsing DAkkS result: {e}")
                        continue
                        
            except Exception as e:
                self.logger.error(f"DAkkS scrape error: {e}")
            finally:
                await browser.close()
        
        return companies
    
    async def _scrape_cofrac(self, limit: Optional[int] = None) -> List[DiscoveredCompany]:
        """Scrape COFRAC (Comité français d'accréditation) registry."""
        companies = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            try:
                await page.goto(
                    "https://www.cofrac.fr/en/rechercher-un-organisme-accredite/",
                    timeout=30000
                )
                await page.wait_for_timeout(2000)
                
                # COFRAC has a search form - submit empty to get all
                search_btn = await page.query_selector('button[type="submit"], input[type="submit"]')
                if search_btn:
                    await search_btn.click()
                    await page.wait_for_timeout(3000)
                
                # Parse results
                results = await page.query_selector_all('.result-item, .organisme, table tbody tr')
                
                for result in results[:limit] if limit else results:
                    try:
                        name_el = await result.query_selector('h3, .name, td:first-child a')
                        if not name_el:
                            continue
                            
                        name = await name_el.inner_text()
                        name = name.strip()
                        
                        if not name or len(name) < 3:
                            continue
                        
                        company = DiscoveredCompany(
                            name=name,
                            country="FR",
                            source=self.name,
                            source_type=self.source_type,
                            source_url="https://www.cofrac.fr/",
                        )
                        
                        company.add_moat_signal(
                            MoatDimension.REGULATORY,
                            "COFRAC Accredited (France)"
                        )
                        company.certifications.append("COFRAC Accreditation")
                        
                        companies.append(company)
                        
                    except Exception as e:
                        self.logger.debug(f"Error parsing COFRAC result: {e}")
                        continue
                        
            except Exception as e:
                self.logger.error(f"COFRAC scrape error: {e}")
            finally:
                await browser.close()
        
        return companies
    
    async def _scrape_generic(
        self, 
        country: str, 
        registry: Dict, 
        limit: Optional[int] = None
    ) -> List[DiscoveredCompany]:
        """Generic scraper for countries without specific implementation."""
        companies = []
        
        if not registry.get("search_url"):
            self.logger.warning(f"No search URL for {registry['name']}")
            return companies
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            try:
                await page.goto(registry["search_url"], timeout=30000)
                await page.wait_for_timeout(2000)
                
                # Try common result selectors
                selectors = [
                    'table tbody tr',
                    '.result-item',
                    '.search-result',
                    '.organisation',
                    '.list-item',
                ]
                
                results = []
                for selector in selectors:
                    results = await page.query_selector_all(selector)
                    if results:
                        break
                
                for result in results[:limit] if limit else results:
                    try:
                        # Try common name selectors
                        name = None
                        for name_sel in ['a', 'h3', '.name', 'td:first-child']:
                            name_el = await result.query_selector(name_sel)
                            if name_el:
                                name = await name_el.inner_text()
                                name = name.strip()
                                if name and len(name) > 3:
                                    break
                        
                        if not name:
                            continue
                        
                        company = DiscoveredCompany(
                            name=name,
                            country=country,
                            source=self.name,
                            source_type=self.source_type,
                            source_url=registry["search_url"],
                        )
                        
                        company.add_moat_signal(
                            MoatDimension.REGULATORY,
                            f"{registry['name']} Accredited ({country})"
                        )
                        company.certifications.append(f"{registry['name']} Accreditation")
                        
                        companies.append(company)
                        
                    except Exception as e:
                        continue
                        
            except Exception as e:
                self.logger.error(f"Generic scrape error for {registry['name']}: {e}")
            finally:
                await browser.close()
        
        return companies
