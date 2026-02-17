"""
Business Logic Filters for Discovery.
Implements configurable filtering driven by the active thesis config.
"""
import logging
from typing import Dict, Optional

from src.core.thesis import thesis

logger = logging.getLogger(__name__)


class QualityFilter:
    """
    Filters companies based on quality criteria from the active thesis:
    - Financials (Revenue, Employees)
    - Business Model keywords (positive/negative)
    
    All thresholds and keyword lists are loaded from config/thesis.yaml.
    """

    @classmethod
    def check_financials(cls, revenue: Optional[float] = None, employees: Optional[int] = None) -> bool:
        """
        Check if company meets financial size criteria.
        Returns True if criteria met or if data is missing (lenient).
        """
        bf = thesis.business_filters

        if revenue is not None:
            if bf.min_revenue is not None and revenue < bf.min_revenue:
                return False
            if bf.max_revenue is not None and revenue > bf.max_revenue:
                return False

        if employees is not None:
            if bf.min_employees is not None and employees < bf.min_employees:
                return False
            if bf.max_employees is not None and employees > bf.max_employees:
                return False

        return True

    @classmethod
    def score_relevance(cls, text: str) -> int:
        """
        Score text relevance based on thesis keyword lists.
        Positive for target keywords, negative for exclusion keywords.
        """
        if not text:
            return 0

        bf = thesis.business_filters
        text_lower = text.lower()
        score = 0

        for kw in bf.positive_keywords:
            if kw in text_lower:
                score += 1

        for kw in bf.negative_keywords:
            if kw in text_lower:
                score -= bf.negative_keyword_penalty

        return score

    @classmethod
    def is_target(cls, company_data: Dict) -> bool:
        """Master filter function."""
        # 1. Financials
        rev = company_data.get("revenue_gbp")
        emp = company_data.get("employees")
        if not cls.check_financials(rev, emp):
            return False

        # 2. Country filter (if thesis specifies target countries)
        bf = thesis.business_filters
        if bf.target_countries:
            country = company_data.get("country", "")
            if country and country not in bf.target_countries:
                return False

        # 3. Text Relevance
        desc = company_data.get("description", "")
        if desc:
            score = cls.score_relevance(desc)
            if score < 0:
                logger.debug(
                    f"Filtered out {company_data.get('name')} "
                    f"due to negative relevance score ({score})"
                )
                return False

        return True
