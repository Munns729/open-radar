import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
import feedparser
import aiohttp
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from src.market_intelligence.database import NewsSource, IntelligenceItem

logger = logging.getLogger(__name__)

class NewsAggregator:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    async def add_source(self, name: str, url: str, category: str, source_type: str = 'rss', check_frequency: str = 'daily'):
        """Register a new news source."""
        source = NewsSource(
            name=name,
            url=url,
            category=category,
            source_type=source_type,
            check_frequency=check_frequency
        )
        self.session.add(source)
        await self.session.commit()
        return source

    async def fetch_rss_feed(self, source: NewsSource) -> List[Dict]:
        """Fetch items from an RSS feed."""
        logger.info(f"Fetching RSS feed for {source.name}: {source.url}")
        # feedparser is blocking, run in executor if needed, but for now direct call might be acceptable if fast enough or wrapped
        # Better to non-block the async loop for network IO, but feedparser handles URL fetching.
        # To be truly async, we should fetch content via aiohttp and pass to feedparser.parse
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(source.url, headers=self.headers, timeout=30) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch {source.url}: Status {response.status}")
                        return []
                    raw = await response.read()
                    content = raw.decode('utf-8', errors='replace')
            
            feed = feedparser.parse(content)
            items = []
            
            for entry in feed.entries:
                published_parsed = entry.get('published_parsed') or entry.get('updated_parsed')
                published_date = datetime.fromtimestamp(datetime(*published_parsed[:6]).timestamp(), tz=timezone.utc) if published_parsed else datetime.now(timezone.utc)
                
                content_txt = entry.get('summary', '') or entry.get('description', '')
                if 'content' in entry:
                    content_txt = entry.content[0].value
                
                # Cleanup html from content if needed, for now keep raw or basic text
                soup = BeautifulSoup(content_txt, 'html.parser')
                text_content = soup.get_text(separator=' ', strip=True)

                items.append({
                    'source_id': source.id,
                    'title': entry.get('title', 'No Title'),
                    'url': entry.get('link', ''),
                    'published_date': published_date,
                    'content': text_content,
                    'category': source.category,
                    'relevance_score': 50 # Initial default
                })
            return items
        except Exception as e:
            logger.error(f"Error parseing RSS for {source.name}: {str(e)}")
            return []

    async def fetch_website(self, source: NewsSource) -> List[Dict]:
        """Scrape a non-RSS website (placeholder for specific scraper logic)."""
        # This would require site-specific logic or a generic extractor.
        # For this task, we will implementation a simple generic fallback or just return empty if not implemented specificly
        logger.warning(f"Website scraping for {source.name} not fully implemented genericly.")
        return []

    async def deduplicate(self, items: List[Dict]) -> List[Dict]:
        """Remove duplicates based on content hash."""
        unique_items = []
        seen_hashes = set()

        for item in items:
            # Create hash
            content_str = f"{item['title']}{item['url']}{item['content'][:200]}"
            content_hash = hashlib.sha256(content_str.encode('utf-8')).hexdigest()
            item['content_hash'] = content_hash
            
            if content_hash in seen_hashes:
                continue

            # Check db
            stmt = select(IntelligenceItem).where(IntelligenceItem.content_hash == content_hash)
            result = await self.session.execute(stmt)
            if not result.scalar_one_or_none():
                unique_items.append(item)
                seen_hashes.add(content_hash)
        
        return unique_items

    async def save_items(self, items: List[Dict]):
        """Save items to database. Skips duplicates (content_hash UNIQUE) on re-run."""
        saved = 0
        for item_data in items:
            stmt = select(IntelligenceItem).where(IntelligenceItem.content_hash == item_data['content_hash'])
            result = await self.session.execute(stmt)
            if result.scalar_one_or_none():
                continue
            item = IntelligenceItem(**item_data)
            self.session.add(item)
            try:
                await self.session.commit()
                saved += 1
            except IntegrityError:
                await self.session.rollback()
                logger.debug(f"Skipped duplicate content_hash: {item_data.get('content_hash', '')[:16]}...")
        if saved and saved < len(items):
            logger.info(f"Saved {saved}/{len(items)} items (duplicates skipped)")

    async def process_source(self, source: NewsSource):
        """Orchestrate fetch, dedupe, save for a single source."""
        if source.source_type == 'rss':
            items = await self.fetch_rss_feed(source)
        else:
            items = await self.fetch_website(source)
        
        if items:
            unique_items = await self.deduplicate(items)
            if unique_items:
                await self.save_items(unique_items)
                logger.info(f"Saved {len(unique_items)} new items from {source.name}")
        
        # Update last_checked
        source.last_checked = datetime.now(timezone.utc)
        await self.session.commit() # Should be safe as we are attached to session

