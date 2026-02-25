import asyncio
import logging
from typing import List, Dict, Any
from src.universe.scrapers.base import BaseScraper
from src.core.business_filters import QualityFilter

logger = logging.getLogger(__name__)

class GCloudScraper(BaseScraper):
    """
    Scraper for UK Government G-Cloud Digital Marketplace.
    Targets:
    - Lot 3: Cloud Support (High signal for Tech-Enabled Services)
    - Lot 2: Cloud Software (Filtered for vertical SaaS)
    """
    
    BASE_URL = "https://www.digitalmarketplace.service.gov.uk/g-cloud/search"
    
    async def discover_services(self, lot: str = "cloud-support", limit: int = 50) -> List[Dict[str, Any]]:
        """
        Discover companies from a specific G-Cloud lot.
        
        Args:
            lot: "cloud-support" (Lot 3) or "cloud-software" (Lot 2)
            limit: Approx number of companies to fetch
        """
        companies = {} # Dedup by name
        
        # Determine Category ID
        # Lot 2 = Cloud Software, Lot 3 = Cloud Support
        # URL structure: ?lot=cloud-support
        
        url = f"{self.BASE_URL}?lot={lot}"
        
        logger.info(f"Scraping G-Cloud {lot}...")
        
        # Use inline browser context
        browser, context, page = await self.create_browser_context()
        
        try:
            await self.safe_goto_with_retry(page, url)
            
            while len(companies) < limit:
                # Get services on current page
                services = await page.locator("li.app-search-result").all()
                
                if not services:
                    logger.warning("No services found on page. Dumping HTML for debugging...")
                    from pathlib import Path
                    log_dir = Path("logs")
                    log_dir.mkdir(exist_ok=True)
                    content = await page.content()
                    with open(log_dir / "gcloud_debug.html", "w", encoding="utf-8") as f:
                        f.write(content)
                    break
                    
                for service in services:
                    if len(companies) >= limit:
                        break
                        
                    try:
                        # Extract basic info
                        title_el = service.locator("h2.govuk-heading-s a")
                        supplier_el = service.locator("p.app-search-result__item-description")
                        desc_el = service.locator("p.govuk-body")
                        
                        supplier_name = await supplier_el.inner_text()
                        service_title = await title_el.inner_text()
                        description = await desc_el.inner_text()
                        link = await title_el.get_attribute("href")
                        
                        full_link = f"https://www.digitalmarketplace.service.gov.uk{link}" if link else None
                        
                        # Normalize name
                        clean_name = supplier_name.strip()
                        
                        # Lightweight Pre-Filter (Services focus)
                        # If Lot 3, it's likely a service.
                        # If Lot 2, check for 'platform', 'system', not just 'app'
                        
                        # Store One Entry per Supplier (aggregate descriptions)
                        if clean_name not in companies:
                            companies[clean_name] = {
                                "name": clean_name,
                                "source_url": full_link,
                                "description": f"{service_title}: {description}",
                                "hq_country": "GB", # G-Cloud is UK specific mostly
                                "services": [service_title]
                            }
                        else:
                            # Append service to description for richer context
                            companies[clean_name]["description"] += f" | {service_title}"
                            companies[clean_name]["services"].append(service_title)
                            
                    except Exception as e:
                        logger.warning(f"Error parsing service item: {e}")
                        continue
                
                # Next Page
                next_link = page.locator("li.govuk-pagination__item--next a")
                if await next_link.count() > 0 and len(companies) < limit:
                    next_url = await next_link.get_attribute("href")
                    full_next_url = f"https://www.digitalmarketplace.service.gov.uk{next_url}"
                    logger.info(f"Next page: {full_next_url}")
                    await self.safe_goto(page, full_next_url)
                else:
                    break
                    
        finally:
            await self.close_browser_context(context, browser)
            
        # Post-Processing: Convert to list and Apply Quality Filter
        results = []
        for name, data in companies.items():
            # Construct a rich text for filtering
            filter_text = f"{data['name']} {data['description']}"
            
            # Apply QualityFilter (relevance check only here, financials come later/unknown)
            # We assume G-Cloud suppliers have >0 revenue by definition (it's a procurement framework)
            if QualityFilter.score_relevance(filter_text) >= 0:
                 results.append(data)
            else:
                logger.info(f"Filtered out {name} (Low relevance signal)")
                
        return results

    async def scrape(self, target_lots: List[str] = ["cloud-support"], limit_per_lot: int = 20) -> Any:
        # Wrapper for workflow compatibility
        class Result:
            data = []
            
        final_data = []
        for lot in target_lots:
            data = await self.discover_services(lot, limit_per_lot)
            final_data.extend(data)
            
        Result.data = final_data
        return Result

if __name__ == "__main__":
    # Test Run
    async def main():
        logging.basicConfig(level=logging.INFO)
        scraper = GCloudScraper(headless=True)
        # Test Cloud Support (Services)
        results = await scraper.discover_services(lot="cloud-support", limit=10)
        for r in results:
            print(f"- {r['name']}: {r['description'][:100]}...")
            
    asyncio.run(main())
