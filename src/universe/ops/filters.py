
"""
Operational filters to optimize the enrichment pipeline.
"""
import logging
from typing import Dict, Any, List, Optional

from src.core.models import CompanyTier
from src.core.utils import normalize_name

logger = logging.getLogger(__name__)

class PreEnrichmentFilter:
    """
    Filters companies BEFORE expensive enrichment steps.
    
    Criteria for exclusion:
    1. Too large (Revenue > £500M)
    2. Publicly Listed (PLC, Inc, AG often imply this if large, but we look for keywords)
    3. Wrong Sector (if known)
    4. Already PE Backed (keywords)
    """
    
    # Keywords indicating public listing or massive scale
    PUBLIC_KEYWORDS = [
        "publicly traded", "nasdaq:", "nyse:", "lse:", "euronext:", 
        "stock exchange", "ticker symbol", "fortune 500", "ftse 100",
        "cac 40", "dax 30"
    ]
    
    # Keywords indicating existing PE backing (skip if looking for primary)
    PE_KEYWORDS = [
        "portfolio company", "owned by private equity", "backed by",  
        "investment from", "acquired by", "private equity backed"
    ]
    
    # Sectors to exclude if explicitly tagged
    EXCLUDE_SECTORS = [
        "Biotechnology", "Pharmaceuticals", "Mining", "Oil & Gas", 
        "Real Estate", "Consumer Goods" # If strict B2B focus
    ]

    @classmethod
    def should_process(cls, company_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Returns (True, None) if company should be processed, (False, reason) if it should be skipped.
        Used for raw data before database insertion or initial scraping.
        """
        # 1. Revenue Check (if available in raw data)
        rev = company_data.get("revenue_gbp") or company_data.get("revenue")
        if rev and isinstance(rev, (int, float)):
             if rev > 500_000_000:
                 reason = "Revenue > £500M"
                 logger.info(f"Skipping {company_data.get('name')}: {reason}")
                 return False, reason
                 
        # 2. Description Checks
        desc = (company_data.get("description") or "").lower()
        if desc:
            if any(k in desc for k in cls.PUBLIC_KEYWORDS):
                reason = "Public listing signal in description"
                logger.info(f"Skipping {company_data.get('name')}: {reason}")
                return False, reason
                
            if any(k in desc for k in cls.PE_KEYWORDS):
                 # This is tricky - might be 'not backed by'. simple keyword check is aggressive but requested.
                 if "not backed by" not in desc:
                     reason = "PE backing signal in description"
                     logger.info(f"Skipping {company_data.get('name')}: {reason}")
                     return False, reason
        
        # 3. Name Checks for Public Listing (Aggressive)
        name = (company_data.get("name") or "").lower()
        # " PLC" is a strong signal in UK
        if name.endswith(" plc") or " plc " in name:
             reason = "PLC detected by name"
             logger.info(f"Skipping {company_data.get('name')}: {reason}")
             return False, reason

        return True, None

    @classmethod
    def should_enrich(cls, company: Any) -> tuple[bool, Optional[str]]:
        """
        Returns (True, None) if DB company object should be enriched, (False, reason) if it should be skipped.
        """
        # 1. Revenue
        # Fix: Ignore high revenue if description is a placeholder (likely bad data/phone number)
        is_placeholder = company.description and company.description.startswith("Discovered on")
        if company.revenue_gbp and company.revenue_gbp > 500_000_000 and not is_placeholder:
            return False, "Revenue > £500M"
            
        # 2. Sector
        if company.sector and company.sector in cls.EXCLUDE_SECTORS:
            return False, f"Excluded Sector: {company.sector}"
            
        # 3. Description (re-check if enriched previously but not filtered)
        desc = (company.description or "").lower()
        if any(k in desc for k in cls.PUBLIC_KEYWORDS):
            return False, "Public listing signal in description"

        return True, None
