"""
Operational filters to optimize the enrichment pipeline.
All exclusion criteria come from config/thesis.yaml (pipeline_filters).
"""
import logging
from typing import Dict, Any, Optional

from src.core.thesis import thesis

logger = logging.getLogger(__name__)


def _pf():
    """Pipeline filters from thesis config."""
    return thesis.pipeline_filters


class PreEnrichmentFilter:
    """
    Filters companies BEFORE expensive enrichment steps.
    All criteria read from thesis.pipeline_filters (config/thesis.yaml).
    """

    @classmethod
    def should_process(cls, company_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Returns (True, None) if company should be processed, (False, reason) if it should be skipped.
        Used for raw data before database insertion or initial scraping.
        """
        pf = _pf()
        # 1. Revenue Check (if available in raw data)
        max_rev = pf.max_revenue_exclude
        if max_rev is not None:
            rev = company_data.get("revenue_gbp") or company_data.get("revenue")
            if rev and isinstance(rev, (int, float)) and rev > max_rev:
                reason = f"Revenue > £{max_rev/1e6:.0f}M"
                logger.info(f"Skipping {company_data.get('name')}: {reason}")
                return False, reason

        # 2. Description Checks (public listing keywords from config)
        desc = (company_data.get("description") or "").lower()
        if desc and pf.public_listing_keywords:
            if any(k.lower() in desc for k in pf.public_listing_keywords):
                reason = "Public listing signal in description"
                logger.info(f"Skipping {company_data.get('name')}: {reason}")
                return False, reason

        # 3. Name Checks for PLC (UK public listing, configurable)
        if pf.exclude_plc_by_name:
            name = (company_data.get("name") or "").lower()
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
        pf = _pf()
        # 1. Revenue (from config)
        if pf.max_revenue_exclude is not None and company.revenue_gbp:
            is_placeholder = company.description and company.description.startswith("Discovered on")
            if company.revenue_gbp > pf.max_revenue_exclude and not is_placeholder:
                return False, f"Revenue > £{pf.max_revenue_exclude/1e6:.0f}M"

        # 2. Sector (from config)
        if company.sector and pf.exclude_sectors and company.sector in pf.exclude_sectors:
            return False, f"Excluded Sector: {company.sector}"

        # 3. Description (public listing keywords from config)
        desc = (company.description or "").lower()
        if pf.public_listing_keywords and any(k.lower() in desc for k in pf.public_listing_keywords):
            return False, "Public listing signal in description"

        return True, None

    @classmethod
    def should_semantic_enrich(cls, company: Any) -> tuple[bool, Optional[str]]:
        """
        Returns (True, None) if company should get Zone 3 semantic enrichment, (False, reason) if skipped.
        Gate: only run expensive semantic enrichment on companies with good enough Zone 2 data.
        """
        # 1. Same exclusions as enrichment (revenue, sector, public listing)
        should_enr, reason = cls.should_enrich(company)
        if not should_enr:
            return False, reason

        # 2. Must have raw website text
        text = (company.raw_website_text or "").strip()
        if not text:
            return False, "No website text for semantic enrichment"

        # 3. Minimum content length (filter placeholder/junk pages)
        min_chars = _pf().min_semantic_enrichment_text_chars
        if len(text) < min_chars:
            return False, f"Website text too short ({len(text)} < {min_chars} chars)"

        return True, None

    @classmethod
    def should_score(cls, company: Any) -> tuple[bool, Optional[str]]:
        """
        Returns (True, None) if company should be scored, (False, reason) if skipped.
        Only score companies that have been enriched and meet minimum criteria.
        """
        # 1. Same exclusions as enrichment (revenue, sector, public listing)
        should_enr, reason = cls.should_enrich(company)
        if not should_enr:
            return False, reason

        # 2. Must have substantive content for meaningful LLM analysis.
        # Website text is preferred; description is only useful if it's not a bare SIC code string.
        has_web = bool(company.raw_website_text and company.raw_website_text.strip())
        desc = (company.description or "").strip()
        # Reject descriptions that are purely SIC codes ("SIC 62012; SIC 62020") — no moat signal.
        is_sic_only = bool(desc) and all(
            part.strip().upper().startswith("SIC") or part.strip().isdigit()
            for part in desc.replace(";", ",").split(",")
            if part.strip()
        )
        has_real_desc = bool(desc) and not is_sic_only

        if not has_web and not has_real_desc:
            return False, "Insufficient data for scoring (no website text; description is SIC-only or empty)"

        return True, None
