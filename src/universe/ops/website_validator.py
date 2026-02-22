"""
Basic website validation: check that a URL is likely the company's real site.
Used to avoid expensive enrichment on wrong URLs (e.g. Toshiba for GATE SOURCE DRAIN).
"""
import re
import logging
from typing import Optional
from urllib.parse import urlparse

from src.core.utils import normalize_name

logger = logging.getLogger(__name__)

# Institutional/academic/gov domains - never company sites
INSTITUTIONAL_DOMAIN_PATTERNS = (
    ".ac.uk", ".ac.", ".edu", ".edu.", ".gov", ".gov.uk", ".gouv.",
    "wikipedia.org", "wikimedia", ".museum", "archive.org",
    "opencorporates", "companieshouse", "company-information",
)

# URL path patterns that suggest third-party article, not company homepage
ARTICLE_PATH_PATTERNS = ("/articles/", "/article/")

# Nav/link text that suggests a real company site (products, services, about)
REAL_SITE_SIGNALS = frozenset({
    "products", "product", "services", "service", "solutions", "solution",
    "about", "about us", "about-us", "company", "our company",
    "capabilities", "offerings", "what we do", "what we offer",
})

# Tokens that are too generic to prove URL/content belongs to this company.
# Matching only on these (e.g. "electronic" for ZHIJUN → datalink-electronics.co.uk) causes false positives.
GENERIC_COMPANY_TOKENS = frozenset({
    "uk", "eu", "group", "international", "global", "europe", "european",
    "electronic", "electronics", "components", "solutions", "systems",
    "services", "consulting", "technology", "tech", "manufacturing",
    "industrial", "limited", "ltd", "plc", "llp", "company", "co",
    "data", "software", "digital", "solutions", "systems", "network",
})


def is_url_acceptable_for_company(url: str, company_name: str) -> tuple[bool, Optional[str]]:
    """
    Quick URL-level check before navigating. Reject institutional domains and
    URLs whose domain doesn't relate to the company name.
    Returns (True, None) if acceptable, (False, reason) if not.
    """
    if not url or not company_name:
        return False, "Missing URL or company name"
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        if not host:
            return False, "No host in URL"
        # 1. Reject institutional domains
        for pattern in INSTITUTIONAL_DOMAIN_PATTERNS:
            if pattern in host:
                return False, f"Institutional domain ({pattern})"
        # 2. Reject article/news paths (partner writeup, not company site)
        path = (parsed.path or "").lower()
        for pattern in ARTICLE_PATH_PATTERNS:
            if pattern in path:
                return False, f"Article path ({pattern})"
        # 3. Domain must contain at least one distinctive company name token
        # (Avoid false positives: "electronic" matched datalink-electronics for ZHIJUN)
        distinctive = _distinctive_tokens(company_name)
        if not distinctive:
            return True, None  # No distinctive token, can't check
        host_core = re.sub(r"\.(com|co\.uk|org|net|eu|io|uk|de|fr|nl|be)$", "", host)
        host_core = host_core.replace(".", "")
        # Normalise hyphens so for-a.com matches token "fora" (FOR-A), dkwiring matches "wiring"
        host_core_norm = host_core.replace("-", "")
        for t in distinctive:
            if len(t) < 3:
                continue
            t_norm = t.replace("-", "")
            if t_norm in host_core_norm or t in host_core:
                return True, None
        return False, f"Domain doesn't match company name (no distinctive token in domain; checked {distinctive!r})"
    except Exception as e:
        return False, f"URL parse error: {e}"


def _name_tokens(name: str) -> list[str]:
    """Extract significant tokens from company name for matching."""
    norm = normalize_name(name)
    if not norm:
        return []
    # Drop very short words (a, of, the, and)
    tokens = [w for w in norm.split() if len(w) >= 2]
    # Drop generic/geographic tokens (legacy set; GENERIC_COMPANY_TOKENS is the full list)
    common = {"uk", "eu", "group", "international", "global", "europe", "european"}
    return [t for t in tokens if t not in common]


def _distinctive_tokens(name: str) -> list[str]:
    """Tokens that are distinctive to this company (exclude generic industry/legal terms)."""
    tokens = _name_tokens(name)
    return [t for t in tokens if t not in GENERIC_COMPANY_TOKENS]


def is_likely_company_site(company_name: str, html_or_text: str) -> tuple[bool, Optional[str]]:
    """
    Basic check that the page is likely the company's real website.
    Returns (True, None) if valid, (False, reason) if not.

    Checks:
    1. Company name (or significant tokens) appears in content
    2. Page has products/services/about-style nav or links
    """
    if not company_name or not html_or_text:
        return False, "Missing company name or content"

    text = html_or_text.lower()
    if len(text) < 100:
        return False, "Content too short"

    # 1. Name check: at least one distinctive token must appear (avoid wrong-company pages)
    # and enough total tokens to be plausible (e.g. 2 if multiple tokens in name)
    tokens = _name_tokens(company_name)
    if not tokens:
        return False, "No name tokens to match"
    distinctive = _distinctive_tokens(company_name)
    if distinctive:
        # Normalise hyphens so "FOR-A" in content matches token "fora"
        text_norm = text.replace("-", "")
        distinctive_matches = sum(
            1 for t in distinctive
            if t in text or t.replace("-", "") in text_norm
        )
        if distinctive_matches < 1:
            return False, f"Company name not found (no distinctive token; need one of {distinctive!r})"
    matches = sum(1 for t in tokens if t in text or t.replace("-", "") in text.replace("-", ""))
    min_tokens = min(2, len(tokens))
    if matches < min_tokens:
        return False, f"Company name not found (matched {matches}/{len(tokens)} tokens)"

    # 2. Real-site signals: products, services, about, etc.
    for signal in REAL_SITE_SIGNALS:
        # Match in link text, nav, or visible content (common patterns)
        pattern = re.compile(rf'\b{re.escape(signal)}\b', re.IGNORECASE)
        if pattern.search(text):
            return True, None

    # No products/services/about found - might be placeholder or article
    return False, "No products/services/about nav found"
