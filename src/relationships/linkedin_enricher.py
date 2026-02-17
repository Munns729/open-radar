"""
LinkedIn Enricher for Relationship Manager.

Integrates with the existing LinkedInScraper to enrich contact data.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.relationships.database import Contact
from src.competitive.linkedin_scraper import LinkedInScraper

logger = logging.getLogger(__name__)


class LinkedInEnricher:
    """
    Enriches contact data using LinkedIn information.
    Uses the existing LinkedInScraper from the competitive module.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.scraper: Optional[LinkedInScraper] = None
    
    async def _ensure_scraper(self) -> LinkedInScraper:
        """Initialize scraper if not already done."""
        if self.scraper is None:
            self.scraper = LinkedInScraper(headless=True)
            await self.scraper.setup_session()
        return self.scraper
    
    async def enrich_contact(self, contact_id: int) -> Dict:
        """
        Enrich a contact with LinkedIn data.
        
        Args:
            contact_id: The ID of the contact to enrich
            
        Returns:
            Dict with enriched data (not auto-saved, for user review):
            - job_title: Current job title from LinkedIn
            - location: Location from profile
            - connections_count: Number of LinkedIn connections
            - headline: LinkedIn headline
            - profile_url: LinkedIn profile URL
            - enrichment_status: success/not_found/error
        """
        contact = await self.session.get(Contact, contact_id)
        if not contact:
            return {
                "enrichment_status": "error",
                "message": f"Contact {contact_id} not found"
            }
        
        try:
            scraper = await self._ensure_scraper()
            
            # Build search query
            search_query = contact.full_name
            if contact.company_name:
                search_query += f" {contact.company_name}"
            
            logger.info(f"Searching LinkedIn for: {search_query}")
            
            # Navigate to LinkedIn search
            search_url = f"https://www.linkedin.com/search/results/people/?keywords={search_query}"
            await scraper.page.goto(search_url)
            await scraper.page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(3)  # Wait for dynamic content
            
            # Try to find the first matching profile
            # This is a simplified extraction - LinkedIn's DOM changes frequently
            profile_data = await self._extract_profile_data(scraper.page, contact)
            
            if profile_data:
                return {
                    "enrichment_status": "success",
                    "contact_id": contact_id,
                    "original_name": contact.full_name,
                    **profile_data,
                    "enriched_at": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "enrichment_status": "not_found",
                    "contact_id": contact_id,
                    "message": f"Could not find LinkedIn profile for {contact.full_name}",
                    "suggestion": "Try adding linkedin_url directly to the contact"
                }
                
        except Exception as e:
            logger.error(f"Error enriching contact {contact_id}: {e}")
            return {
                "enrichment_status": "error",
                "contact_id": contact_id,
                "message": str(e)
            }
    
    async def _extract_profile_data(self, page, contact: Contact) -> Optional[Dict]:
        """
        Extract profile data from LinkedIn search results.
        
        Note: LinkedIn's DOM structure changes frequently.
        This is a best-effort extraction.
        """
        try:
            # Wait for search results
            await page.wait_for_selector(".search-results-container", timeout=10000)
            
            # Get first result card
            result_cards = await page.query_selector_all(".entity-result")
            
            if not result_cards:
                return None
            
            first_result = result_cards[0]
            
            # Extract data from the result card
            name_elem = await first_result.query_selector(".entity-result__title-text a")
            headline_elem = await first_result.query_selector(".entity-result__primary-subtitle")
            location_elem = await first_result.query_selector(".entity-result__secondary-subtitle")
            
            profile_url = None
            name = None
            headline = None
            location = None
            
            if name_elem:
                profile_url = await name_elem.get_attribute("href")
                name = await name_elem.inner_text()
                name = name.strip() if name else None
            
            if headline_elem:
                headline = await headline_elem.inner_text()
                headline = headline.strip() if headline else None
            
            if location_elem:
                location = await location_elem.inner_text()
                location = location.strip() if location else None
            
            # Verify this is the right person (basic name match)
            if name and contact.full_name.lower() not in name.lower():
                logger.warning(f"Name mismatch: searched for {contact.full_name}, found {name}")
                # Continue anyway but flag it
            
            # Parse job title from headline (usually "Title at Company")
            job_title = None
            company = None
            if headline and " at " in headline:
                parts = headline.split(" at ", 1)
                job_title = parts[0].strip()
                company = parts[1].strip() if len(parts) > 1 else None
            elif headline:
                job_title = headline
            
            return {
                "linkedin_name": name,
                "linkedin_url": profile_url,
                "job_title": job_title,
                "company_from_linkedin": company,
                "headline": headline,
                "location": location,
                "connections_count": None  # Would need to visit profile page
            }
            
        except Exception as e:
            logger.error(f"Error extracting profile data: {e}")
            return None
    
    async def enrich_contact_from_url(self, contact_id: int, linkedin_url: str) -> Dict:
        """
        Enrich a contact using their LinkedIn profile URL directly.
        More accurate than search-based enrichment.
        """
        contact = await self.session.get(Contact, contact_id)
        if not contact:
            return {
                "enrichment_status": "error",
                "message": f"Contact {contact_id} not found"
            }
        
        try:
            scraper = await self._ensure_scraper()
            
            logger.info(f"Visiting LinkedIn profile: {linkedin_url}")
            await scraper.page.goto(linkedin_url)
            await scraper.page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(3)
            
            # Extract from profile page
            profile_data = await self._extract_from_profile_page(scraper.page)
            
            if profile_data:
                return {
                    "enrichment_status": "success",
                    "contact_id": contact_id,
                    "linkedin_url": linkedin_url,
                    **profile_data,
                    "enriched_at": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "enrichment_status": "partial",
                    "contact_id": contact_id,
                    "message": "Could not extract all profile data",
                    "linkedin_url": linkedin_url
                }
                
        except Exception as e:
            logger.error(f"Error enriching from URL: {e}")
            return {
                "enrichment_status": "error",
                "message": str(e)
            }
    
    async def _extract_from_profile_page(self, page) -> Optional[Dict]:
        """Extract data from a LinkedIn profile page."""
        try:
            # Wait for profile to load
            await page.wait_for_selector(".pv-top-card", timeout=10000)
            
            name = await page.inner_text("h1.text-heading-xlarge")
            headline = await page.inner_text(".text-body-medium.break-words")
            
            # Try to get location
            location = None
            try:
                location = await page.inner_text(".pv-top-card--list-bullet span")
            except:
                pass
            
            # Try to get connection count
            connections = None
            try:
                conn_text = await page.inner_text("li.text-body-small span.t-bold")
                if "connections" in conn_text.lower() or "followers" in conn_text.lower():
                    # Extract number
                    import re
                    match = re.search(r'[\d,]+', conn_text)
                    if match:
                        connections = int(match.group().replace(",", ""))
            except:
                pass
            
            # Parse job title
            job_title = None
            company = None
            if headline and " at " in headline:
                parts = headline.split(" at ", 1)
                job_title = parts[0].strip()
                company = parts[1].strip()
            elif headline:
                job_title = headline
            
            return {
                "full_name": name.strip() if name else None,
                "job_title": job_title,
                "company_from_linkedin": company,
                "headline": headline.strip() if headline else None,
                "location": location.strip() if location else None,
                "connections_count": connections
            }
            
        except Exception as e:
            logger.error(f"Error extracting from profile page: {e}")
            return None
    
    async def apply_enrichment(self, contact_id: int, enrichment_data: Dict) -> Contact:
        """
        Apply enrichment data to a contact after user review.
        
        Args:
            contact_id: The contact to update
            enrichment_data: The enrichment data to apply
            
        Returns:
            Updated Contact object
        """
        contact = await self.session.get(Contact, contact_id)
        if not contact:
            raise ValueError(f"Contact {contact_id} not found")
        
        # Apply fields if they exist in enrichment data
        if enrichment_data.get("job_title"):
            contact.job_title = enrichment_data["job_title"]
        
        if enrichment_data.get("location"):
            contact.location = enrichment_data["location"]
        
        if enrichment_data.get("linkedin_url"):
            contact.linkedin_url = enrichment_data["linkedin_url"]
        
        if enrichment_data.get("company_from_linkedin") and not contact.company_name:
            contact.company_name = enrichment_data["company_from_linkedin"]
        
        # Store full enrichment data
        contact.enrichment_data = enrichment_data
        contact.enriched_at = datetime.utcnow()
        
        await self.session.commit()
        logger.info(f"Applied enrichment to contact {contact_id}")
        
        return contact
    
    async def close(self):
        """Clean up scraper resources."""
        if self.scraper:
            await self.scraper.close()
            self.scraper = None
