import logging
import json
import asyncio
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.market_intelligence.database import IntelligenceItem
from src.core.ai_client import ai_client

logger = logging.getLogger(__name__)

class RelevanceScorer:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def score_items_batch(self, items: List[IntelligenceItem]):
        """
        Score a batch of items. 
        """
        for item in items:
            await self.score_item(item)

    async def score_item(self, item: IntelligenceItem):
        if not item.content:
            return

        system_prompt = "You are a market intelligence analyst."
        prompt = f"""
You are analyzing intelligence for a UK private equity firm investing in B2B tech (£15-100M revenue) with regulatory moats.

Article Title: {item.title}
Content: {item.content[:2000]}... [truncated]

Score this article's relevance (0-100) based on:
- Direct impact on aerospace/healthcare/fintech sectors: 40 points max
- Regulatory changes creating barriers to entry: 30 points max
- M&A activity relevant to thesis: 20 points max
- Emerging technology disrupting moats: -20 points (threat)
- General business news: 10 points max

Also extract:
- Key points (3-5 bullets)
- Implications for investment thesis
- Action items (if any)

Return JSON:
{{
  "relevance_score": 0-100,
  "key_points": ["point 1", "point 2", ...],
  "implications": "text",
  "action_items": ["action 1", ...]
}}
"""
        try:
            response_text = await ai_client.generate(prompt, system_prompt=system_prompt)
            
            # Clean generic markdown code blocks if present
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(response_text)
            
            stmt = update(IntelligenceItem).where(IntelligenceItem.id == item.id).values(
                relevance_score=data.get('relevance_score', 0),
                key_points=data.get('key_points', []),
                implications=data.get('implications', ''),
                summary=data.get('implications', '') # Using implications as summary for now
            )
            await self.session.execute(stmt)
            await self.session.commit()
        except Exception as e:
            logger.error(f"Error scoring item {item.id}: {e}")

    async def process_unscored_items(self, limit: int = 50):
        stmt = select(IntelligenceItem).where(IntelligenceItem.relevance_score == None).limit(limit)
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        
        if items:
            logger.info(f"Scoring {len(items)} items...")
            await self.score_items_batch(list(items))
