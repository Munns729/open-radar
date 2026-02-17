"""
Discovery Infrastructure - Core Components

Provides:
- DiscoverySource interface
- DeduplicationEngine with multi-stage matching
- RateLimiter for free-tier API management
- EnrichmentStateMachine for tracking company state
- FieldRegistry as the contract between discovery and scoring
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Optional, List, Dict, Any, Callable
from collections import defaultdict
import asyncio
import logging
import re
import time
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND DATA STRUCTURES
# =============================================================================

class MoatDimension(Enum):
    """The five moat dimensions."""
    REGULATORY = "regulatory"
    NETWORK = "network"
    LIABILITY = "liability"
    PHYSICAL = "physical"
    IP = "ip"


class DiscoverySourceType(Enum):
    """Types of discovery sources."""
    ACCREDITATION_REGISTRY = "accreditation_registry"
    FINANCIAL_REGULATOR = "financial_regulator"
    AUDITOR_REGISTRY = "auditor_registry"
    PATENT_DATABASE = "patent_database"
    AEROSPACE_REGISTRY = "aerospace_registry"
    PLATFORM_DATABASE = "platform_database"
    COMPANY_REGISTRY = "company_registry"


class EnrichmentState(IntEnum):
    """
    State machine for company enrichment.
    Companies progress through these states as data is added.
    """
    DISCOVERED = 1            # Minimal fields from discovery source
    BASIC_POPULATED = 2       # Name, country, sector confirmed
    WEBSITE_FOUND = 3         # URL identified
    WEBSITE_SCRAPED = 4       # Content extracted
    SEMANTICALLY_ENRICHED = 5 # LLM analysis complete
    SCORABLE = 6              # Has required fields for active theses


@dataclass
class DiscoveredCompany:
    """A company discovered from a source."""
    name: str
    country: str  # ISO 3166-1 alpha-2
    
    # Identifiers for deduplication
    lei: Optional[str] = None
    vat_id: Optional[str] = None
    registration_number: Optional[str] = None
    
    # Source tracking
    source: str = ""
    source_type: Optional[DiscoverySourceType] = None
    source_url: Optional[str] = None
    
    # Fields populated by discovery
    website: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[str] = None
    certifications: List[str] = field(default_factory=list)
    regulatory_licenses: List[str] = field(default_factory=list)
    patent_count: Optional[int] = None
    
    # Moat signals discovered
    moat_signals: Dict[str, List[str]] = field(default_factory=dict)
    
    # Data sources tracking (which source provided which field)
    data_sources: Dict[str, str] = field(default_factory=dict)
    
    # Raw data for debugging
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Match:
    """A potential match during deduplication."""
    company_id: int
    company_name: str
    confidence: float
    method: str  # 'lei', 'vat', 'name_fuzzy', 'website'


# =============================================================================
# FIELD REGISTRY - Contract between discovery and scoring
# =============================================================================

FIELD_REGISTRY = {
    "certifications": {
        "type": "list",
        "values": [
            "AS9100", "ISO17025", "UKAS", "Nadcap", "Part145", "Part21",
            "ISO9001", "ISO14001", "ISO27001", "ISO45001",
            "DAkkS", "COFRAC", "Accredia", "ENAC", "BELAC",
        ],
        "sources": ["european_accreditation", "nadcap", "website_scrape"],
    },
    "regulatory_licenses": {
        "type": "list",
        "values": [
            "MiFID", "AIFMD", "UCITS", "PRA", "FCA", "BaFin", "AMF", "CONSOB",
            "CRA",  # Credit Rating Agency
        ],
        "sources": ["esma", "fca", "website_scrape"],
    },
    "patent_count": {
        "type": "int",
        "sources": ["epo", "website_scrape"],
    },
    "revenue_gbp": {
        "type": "float",
        "sources": ["companies_house", "website_scrape"],
    },
    "employee_count": {
        "type": "int",
        "sources": ["companies_house", "website_scrape"],
    },
    "sector": {
        "type": "enum",
        "values": [
            "aerospace", "defence", "testing", "certification", "financial_services",
            "healthcare", "software", "industrial", "energy", "retail", "professional_services",
        ],
        "sources": ["discovery_source", "website_scrape"],
    },
}


# Source field mappings (how to map source fields to registry fields)
SOURCE_FIELD_MAPPING = {
    "esma": {
        "mifid_authorized": ("regulatory_licenses", lambda x: ["MiFID"] if x else []),
        "lei": ("lei", lambda x: x),
    },
    "european_accreditation": {
        "accreditation_body": ("certifications", lambda body: [body] if body else []),
        "accreditation_type": ("certifications", lambda t: [t] if t else []),
    },
    "nadcap": {
        "special_processes": ("certifications", lambda procs: [f"Nadcap:{p}" for p in procs]),
    },
    "epo": {
        "patent_count": ("patent_count", lambda x: int(x) if x else 0),
    },
}


# =============================================================================
# SOURCE PRIORITY RESOLUTION
# =============================================================================

SOURCE_PRIORITY = {
    "revenue_gbp": ["companies_house", "website_scrape"],
    "website": ["discovery_source", "google_search", "dns_guess"],
    "certifications": ["source_registry", "website_scrape"],
    "description": ["website_scrape", "discovery_source"],
    "employee_count": ["companies_house", "website_scrape"],
    "sector": ["discovery_source", "website_scrape"],
}


def resolve_field_conflict(field_name: str, values_by_source: Dict[str, Any]) -> Any:
    """Resolve conflicts when multiple sources provide the same field."""
    if field_name not in SOURCE_PRIORITY:
        # No priority defined, take first non-None
        for val in values_by_source.values():
            if val is not None:
                return val
        return None
    
    for priority_source in SOURCE_PRIORITY[field_name]:
        if priority_source in values_by_source:
            val = values_by_source[priority_source]
            if val is not None:
                return val
    
    return None


# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimiter:
    """
    Manages rate limits for free-tier APIs.
    """
    
    LIMITS = {
        "companies_house": {"limit": 600, "period": 300},    # 600/5min
        "google_search": {"limit": 100, "period": 3600},      # 100/hour (conservative)
        "epo": {"limit": 1000, "period": 3600},               # 1000/hour
        "esma": {"limit": 100, "period": 60},                  # 100/min
        "generic_scrape": {"limit": 60, "period": 60},         # 1/sec average
    }
    
    def __init__(self):
        self.usage: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def acquire(self, source: str) -> None:
        """Wait until rate limit allows a request."""
        if source not in self.LIMITS:
            return
        
        config = self.LIMITS[source]
        
        async with self._lock:
            while True:
                now = time.time()
                # Remove old requests outside the window
                self.usage[source] = [
                    t for t in self.usage[source]
                    if t > now - config["period"]
                ]
                
                if len(self.usage[source]) < config["limit"]:
                    self.usage[source].append(now)
                    return
                
                # Calculate wait time
                oldest = min(self.usage[source])
                wait_time = oldest + config["period"] - now + 0.1
                logger.debug(f"Rate limited on {source}, waiting {wait_time:.1f}s")
                
                # Release lock while waiting
                await asyncio.sleep(min(wait_time, 5))
    
    def get_usage(self, source: str) -> Dict[str, int]:
        """Get current usage stats for a source."""
        if source not in self.LIMITS:
            return {"used": 0, "limit": 0}
        
        config = self.LIMITS[source]
        now = time.time()
        recent = [t for t in self.usage[source] if t > now - config["period"]]
        return {
            "used": len(recent),
            "limit": config["limit"],
            "period": config["period"],
        }


# Global rate limiter instance
rate_limiter = RateLimiter()


# =============================================================================
# DEDUPLICATION ENGINE
# =============================================================================

class DeduplicationEngine:
    """
    Multi-stage deduplication with confidence scoring.
    
    Stages (in order of confidence):
    1. LEI exact match (1.0)
    2. VAT + Country (0.95)
    3. Normalized name + country + Levenshtein (similarity score)
    4. Website domain (0.75)
    """
    
    CONFIDENCE_THRESHOLDS = {
        "auto_merge": 0.95,     # Merge automatically
        "manual_review": 0.75,  # Queue for manual review
        "create_new": 0.0,      # Below 0.75, create new company
    }
    
    def __init__(self, db_session):
        self.db = db_session
    
    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize company name for matching."""
        name = name.upper()
        # Remove common suffixes
        suffixes = [
            r'\s+(LIMITED|LTD|PLC|LLP|GMBH|AG|SA|SAS|SARL|BV|NV|AB|AS|OY|SRL|SPA|INC|CORP)\.?$',
            r'\s+(HOLDINGS?|GROUP|INTERNATIONAL|UK|EUROPE|GLOBAL)\.?$',
            r'\s+&\s+CO\.?$',
        ]
        for suffix in suffixes:
            name = re.sub(suffix, '', name, flags=re.IGNORECASE)
        # Remove punctuation and normalize spaces
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name
    
    @staticmethod
    def extract_domain(url: str) -> Optional[str]:
        """Extract base domain from URL."""
        if not url:
            return None
        match = re.search(r'(?:https?://)?(?:www\.)?([^/]+)', url.lower())
        return match.group(1) if match else None
    
    @staticmethod
    def string_similarity(a: str, b: str) -> float:
        """Compute string similarity using SequenceMatcher."""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    async def find_matches(self, company: DiscoveredCompany) -> List[Match]:
        """Find potential matches for a company."""
        from sqlalchemy import text
        
        matches = []
        
        # Stage 1: LEI exact match (confidence: 1.0)
        if company.lei:
            result = (await self.db.execute(
                text("SELECT id, name FROM companies WHERE lei = :lei"),
                {"lei": company.lei}
            )).fetchone()
            if result:
                matches.append(Match(
                    company_id=result[0],
                    company_name=result[1],
                    confidence=1.0,
                    method="lei"
                ))
                return matches  # LEI is definitive
        
        # Stage 2: VAT + Country (confidence: 0.95)
        if company.vat_id:
            result = (await self.db.execute(
                text("SELECT id, name FROM companies WHERE vat_id = :vat AND country = :country"),
                {"vat": company.vat_id, "country": company.country}
            )).fetchone()
            if result:
                matches.append(Match(
                    company_id=result[0],
                    company_name=result[1],
                    confidence=0.95,
                    method="vat"
                ))
        
        # Stage 3: Normalized name + country (confidence: similarity score)
        normalized = self.normalize_name(company.name)
        candidates = (await self.db.execute(
            text("""
                SELECT id, name, normalized_name FROM companies 
                WHERE country = :country AND normalized_name IS NOT NULL
            """),
            {"country": company.country}
        )).fetchall()
        
        for c in candidates:
            c_normalized = c[2] or self.normalize_name(c[1])
            similarity = self.string_similarity(normalized, c_normalized)
            if similarity > 0.85:
                matches.append(Match(
                    company_id=c[0],
                    company_name=c[1],
                    confidence=similarity,
                    method="name_fuzzy"
                ))
        
        # Stage 4: Website domain (confidence: 0.75)
        if company.website:
            domain = self.extract_domain(company.website)
            if domain:
                result = (await self.db.execute(
                    text("SELECT id, name FROM companies WHERE website LIKE :domain"),
                    {"domain": f"%{domain}%"}
                )).fetchone()
                if result:
                    # Only add if not already matched
                    if not any(m.company_id == result[0] for m in matches):
                        matches.append(Match(
                            company_id=result[0],
                            company_name=result[1],
                            confidence=0.75,
                            method="website"
                        ))
        
        return sorted(matches, key=lambda m: m.confidence, reverse=True)
    
    def merge_or_create(
        self, 
        company: DiscoveredCompany, 
        matches: List[Match]
    ) -> Dict[str, Any]:
        """
        Decide whether to merge with existing or create new.
        
        Returns:
            {"action": "merged"|"created"|"queued", "company_id": int, "match": Match|None}
        """
        if not matches:
            return {"action": "create", "company_id": None, "match": None}
        
        best = matches[0]
        
        if best.confidence >= self.CONFIDENCE_THRESHOLDS["auto_merge"]:
            return {"action": "merge", "company_id": best.company_id, "match": best}
        
        elif best.confidence >= self.CONFIDENCE_THRESHOLDS["manual_review"]:
            return {"action": "queue_review", "company_id": best.company_id, "match": best}
        
        else:
            return {"action": "create", "company_id": None, "match": None}


# =============================================================================
# INPUT QUALITY CALCULATOR
# =============================================================================

def compute_input_quality(company: Dict[str, Any]) -> float:
    """
    Compute input quality score (0-1) for a company.
    Used to determine if semantic enrichment is worthwhile.
    """
    weights = {
        "website_text": 0.30,     # Most important for semantic analysis
        "certifications": 0.20,
        "revenue_gbp": 0.15,
        "description": 0.15,
        "sector": 0.10,
        "employee_count": 0.10,
    }
    
    score = 0.0
    for field, weight in weights.items():
        val = company.get(field)
        if val is not None:
            # For lists, count as present if non-empty
            if isinstance(val, list):
                if len(val) > 0:
                    score += weight
            # For strings, count if non-empty
            elif isinstance(val, str):
                if len(val) > 10:  # Meaningful content
                    score += weight
            # For numbers, count if positive
            elif isinstance(val, (int, float)):
                if val > 0:
                    score += weight
            else:
                score += weight
    
    return round(score, 2)


# =============================================================================
# DISCOVERY SOURCE INTERFACE
# =============================================================================

class DiscoverySource(ABC):
    """Abstract base class for all discovery sources."""
    
    def __init__(
        self, 
        name: str, 
        source_type: DiscoverySourceType, 
        countries: List[str]
    ):
        self.name = name
        self.source_type = source_type
        self.countries = countries
        self.logger = logging.getLogger(f"discovery.{name.lower().replace(' ', '_')}")
    
    @abstractmethod
    async def discover(self, limit: Optional[int] = None) -> List[DiscoveredCompany]:
        """Discover companies from this source."""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the source is accessible."""
        pass
    
    def get_field_mapping(self) -> Dict[str, tuple]:
        """Get the field mapping for this source."""
        source_key = self.name.lower().replace(" ", "_")
        return SOURCE_FIELD_MAPPING.get(source_key, {})
