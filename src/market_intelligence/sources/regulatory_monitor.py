import logging
import hashlib
import aiohttp
import feedparser
from bs4 import BeautifulSoup
from datetime import date, datetime, timezone
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.market_intelligence.database import RegulatoryChange, NewsSource

logger = logging.getLogger(__name__)


# Registry of regulatory RSS sources, keyed by jurisdiction.
# Each entry: (name, url, regulatory_body, jurisdiction)
REGULATORY_FEEDS = [
    # UK
    ("FCA News", "https://www.fca.org.uk/news/search-results.xml", "FCA", "UK"),
    ("MHRA Updates", "https://www.gov.uk/government/organisations/medicines-and-healthcare-products-regulatory-agency.atom", "MHRA", "UK"),
    ("ICO News", "https://ico.org.uk/about-the-ico/media-centre/news-and-blogs/feed/", "ICO", "UK"),
    ("NCSC Advisories", "https://www.ncsc.gov.uk/api/1/services/v1/report-rss-feed.xml", "NCSC", "UK"),
    # France
    ("ANSSI Actualités", "https://www.ssi.gouv.fr/feed/actualite/", "ANSSI", "FR"),
    ("CNIL Actualités", "https://www.cnil.fr/fr/rss.xml", "CNIL", "FR"),
    # Germany
    ("BSI News", "https://www.bsi.bund.de/SiteGlobals/Functions/RSSFeed/RSSNewsfeed/RSSNewsfeed.xml", "BSI", "DE"),
    # EU
    ("ENISA News", "https://www.enisa.europa.eu/rss.xml", "ENISA", "EU"),
]

# Keywords that indicate a regulatory item is relevant to moat scoring.
# Items without these signals are saved but not flagged for impact analysis.
MOAT_RELEVANCE_KEYWORDS = [
    "certification", "accreditation", "compliance", "mandatory", "requirement",
    "licence", "license", "authorisation", "authorization", "clearance",
    "sovereign", "sovereignty", "data residency", "cloud qualification",
    "critical infrastructure", "essential services", "nis2", "dora",
    "procurement", "framework", "approved supplier", "security cleared",
    "data protection", "ai act", "cyber essentials", "secnumcloud",
    "bsi c5", "kritis", "qualified trust", "eidas",
]


class RegulatoryMonitor:
    """
    Monitors regulatory RSS feeds across fund geographies (UK, FR, DE, EU)
    and saves structured RegulatoryChange records.
    
    Designed to run daily as part of the market intelligence workflow.
    New items are deduplicated by title+source hash before saving.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.headers = {
            'User-Agent': 'RADAR-PE-Intelligence/1.0 (regulatory-monitor)'
        }

    async def fetch_feed(self, url: str) -> Optional[List[Dict]]:
        """Fetch and parse an RSS/Atom feed. Returns list of entry dicts."""
        try:
            async with aiohttp.ClientSession() as http:
                async with http.get(url, headers=self.headers, timeout=30) as response:
                    if response.status != 200:
                        logger.warning(f"Feed returned {response.status}: {url}")
                        return None
                    content = await response.text()
            
            feed = feedparser.parse(content)
            if feed.bozo and not feed.entries:
                logger.warning(f"Malformed feed with no entries: {url}")
                return None
            
            return feed.entries
        except Exception as e:
            logger.error(f"Failed to fetch feed {url}: {e}")
            return None

    def _content_hash(self, title: str, source: str) -> str:
        """Generate dedup hash from title + source."""
        return hashlib.sha256(f"{title}|{source}".encode()).hexdigest()[:32]

    def _extract_date(self, entry: Dict) -> Optional[date]:
        """Extract publication date from feed entry."""
        parsed = entry.get('published_parsed') or entry.get('updated_parsed')
        if parsed:
            try:
                return date(parsed.tm_year, parsed.tm_mon, parsed.tm_mday)
            except (ValueError, AttributeError):
                pass
        return None

    def _extract_content(self, entry: Dict) -> str:
        """Extract text content from feed entry."""
        raw = entry.get('summary', '') or entry.get('description', '')
        if 'content' in entry and entry.content:
            raw = entry.content[0].get('value', raw)
        soup = BeautifulSoup(raw, 'html.parser')
        return soup.get_text(separator=' ', strip=True)[:5000]

    def _classify_change_type(self, title: str, content: str) -> str:
        """Classify the type of regulatory change from title/content."""
        text = (title + " " + content).lower()
        if any(w in text for w in ["new regulation", "new law", "adopted", "enters into force"]):
            return "new_regulation"
        if any(w in text for w in ["amendment", "update", "revision", "amended"]):
            return "amendment"
        if any(w in text for w in ["guidance", "consultation", "proposal", "draft"]):
            return "guidance"
        if any(w in text for w in ["enforcement", "fine", "penalty", "sanction", "breach"]):
            return "enforcement"
        return "guidance"  # Default

    def _is_moat_relevant(self, title: str, content: str) -> bool:
        """Check if item contains keywords suggesting moat-scoring relevance."""
        text = (title + " " + content).lower()
        return any(kw in text for kw in MOAT_RELEVANCE_KEYWORDS)

    async def _save_if_new(self, change_data: dict) -> Optional[RegulatoryChange]:
        """Save a RegulatoryChange if not already present. Returns the saved record or None."""
        # Dedup check by title and regulatory_body
        stmt = select(RegulatoryChange).where(
            RegulatoryChange.title == change_data['title'],
            RegulatoryChange.regulatory_body == change_data['regulatory_body']
        )
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none():
            return None
        
        change = RegulatoryChange(**change_data)
        self.session.add(change)
        await self.session.flush()  # Get ID for downstream use
        logger.info(f"[RegMonitor] New: {change_data['regulatory_body']} — {change_data['title'][:80]}")
        return change

    async def monitor_feed(self, name: str, url: str, regulatory_body: str, jurisdiction: str) -> List[RegulatoryChange]:
        """
        Monitor a single RSS feed. Fetch entries, classify, dedup, save.
        Returns list of newly saved RegulatoryChange records.
        """
        entries = await self.fetch_feed(url)
        if not entries:
            return []
        
        new_changes = []
        for entry in entries[:30]:  # Cap at 30 per feed per run
            title = entry.get('title', '').strip()
            if not title:
                continue
            
            content = self._extract_content(entry)
            pub_date = self._extract_date(entry)
            change_type = self._classify_change_type(title, content)
            moat_relevant = self._is_moat_relevant(title, content)
            
            change_data = {
                "jurisdiction": jurisdiction,
                "regulatory_body": regulatory_body,
                "change_type": change_type,
                "title": title[:500],
                "effective_date": pub_date,
                "description": content[:2000] if content else None,
                "affected_sectors": None,  # Populated by ScoringImpactAnalyzer later
                "impact_assessment": None,
                "creates_barriers_to_entry": moat_relevant,  # Preliminary flag
                "source_url": entry.get('link', ''),
            }
            
            saved = await self._save_if_new(change_data)
            if saved:
                new_changes.append(saved)
        
        await self.session.commit()
        return new_changes

    async def run_all_monitors(self) -> List[RegulatoryChange]:
        """
        Run all registered regulatory feed monitors.
        Returns all newly discovered regulatory changes.
        """
        all_new = []
        for name, url, body, jurisdiction in REGULATORY_FEEDS:
            try:
                new = await self.monitor_feed(name, url, body, jurisdiction)
                all_new.extend(new)
            except Exception as e:
                logger.error(f"Monitor failed for {name}: {e}")
                continue
        
        logger.info(f"[RegMonitor] Total new changes across all feeds: {len(all_new)}")
        return all_new
