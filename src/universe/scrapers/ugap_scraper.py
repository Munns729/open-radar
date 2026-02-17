import asyncio
import logging
from typing import List, Dict, Any
from src.core.base_scraper import BaseScraper
from src.core.business_filters import QualityFilter

logger = logging.getLogger(__name__)

class UGAPScraper(BaseScraper):
    """
    Scraper for UGAP (France Public Procurement).
    Targets:
    - Multi-Editeurs Software Catalog
    - IT Services (Prestations intellectuelles) - if accessible
    """
    
    # Main catalog entry for software
    BASE_URL = "https://www.ugap.fr/catalogue-marche-public/logiciels-multi-editeurs_40622.html"
    
    async def discover_companies(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Discover companies from UGAP catalog.
        """
        companies = {}
        
        logger.info(f"Scraping UGAP Software Catalog...")
        
        # Use context manager pattern for simplicity here as it's a single flow
        async with self as scraper:
            # We need to use the internal browser from the context manager
            if not self.context:
                await self.__aenter__()
                
            page = await self.context.new_page()
            
            try:
                await self.safe_goto_with_retry(page, self.BASE_URL)
                
                # UGAP structure: Categories -> Lists of Editors
                # We might need to traverse sub-categories or search
                # Selector strategy: Look for "Editeurs" list or products
                
                # Check for "Voir tous les éditeurs" or similar listing
                # Note: UGAP site structure varies. We'll look for product cards which usually list the "Titulaire" or "Editeur"
                
                # Wait for product grid
                await page.wait_for_selector(".product-item", timeout=10000)
                
                while len(companies) < limit:
                    products = await page.locator(".product-item").all()
                    
                    if not products:
                        break
                        
                    for prod in products:
                        if len(companies) >= limit:
                            break
                            
                        try:
                            # Extract Editor/Brand
                            brand_el = prod.locator(".product-brand")
                            name_el = prod.locator(".product-name a")
                            
                            brand = await brand_el.inner_text() if await brand_el.count() > 0 else "Unknown"
                            product_name = await name_el.inner_text()
                            link = await name_el.get_attribute("href")
                            full_link = f"https://www.ugap.fr{link}" if link else None
                            
                            # Clean Name (often "EDITEUR : MICROSOFT" or just "MICROSOFT")
                            clean_brand = brand.replace("EDITEUR :", "").strip()
                            
                            if clean_brand and clean_brand not in companies:
                                companies[clean_brand] = {
                                    "name": clean_brand,
                                    "source_url": full_link,
                                    "description": f"Software/Service: {product_name}", # Initial desc
                                    "hq_country": "FR",
                                    "products": [product_name]
                                }
                            elif clean_brand in companies:
                                companies[clean_brand]["products"].append(product_name)
                                if len(companies[clean_brand]["products"]) < 5:
                                    companies[clean_brand]["description"] += f" | {product_name}"
                        except Exception as e:
                            continue
                            
                    # Pagination
                    next_el = page.locator("a.next")
                    if await next_el.count() > 0 and len(companies) < limit:
                        url = await next_el.get_attribute("href")
                        await self.safe_goto(page, url)
                    else:
                        break
                        
            except Exception as e:
                logger.error(f"UGAP scrape error: {e}")
                
        # Post-Processing
        results = []
        for name, data in companies.items():
            # Apply Filter
            # For UGAP, we are already in a "Software/Service" catalog.
            # We filter out big US corp if possible (Microsoft, Oracle) via business logic later or here.
            # QualityFilter checks keywords.
            
            # Simple heuristic: Skip if name is too famous? (Optional, skipping for now to let later stages handle tiering)
            
            if QualityFilter.score_relevance(data['description']) > -5: # Allow slightly more broad, just filter strict negatives
                 results.append(data)
                 
        return results

    async def scrape(self, limit: int = 50) -> Any:
        class Result:
            data = []
        
        data = await self.discover_companies(limit)
        Result.data = data
        return Result

if __name__ == "__main__":
    async def main():
        logging.basicConfig(level=logging.INFO)
        scraper = UGAPScraper(headless=True)
        results = await scraper.discover_companies(limit=10)
        for r in results:
            print(f"- {r['name']}")
    asyncio.run(main())
