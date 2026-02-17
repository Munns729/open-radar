import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.market_intelligence.database import IntelligenceItem, MarketTrend
from src.core.ai_client import ai_client

logger = logging.getLogger(__name__)

class TrendDetector:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def detect_trends(self, lookback_days: int = 30) -> List[Dict]:
        # 1. Fetch relevant items
        cutoff = datetime.now() - timedelta(days=lookback_days)
        stmt = select(IntelligenceItem).where(
            IntelligenceItem.published_date >= cutoff,
            IntelligenceItem.relevance_score >= 60
        )
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        
        if not items:
            logger.info("No sufficient data for trend detection.")
            return []

        # 2. Construct Prompt
        # Limit to 50 items to avoid context overflow if many
        items_to_analyze = items[:50] 
        articles_context = "\n".join([f"- {item.title} ({item.category})" for item in items_to_analyze])
        
        system_prompt = "You are a market intelligence analyst for a PE firm."
        prompt = f"""
Analyze these articles from the past {lookback_days} days.

Identify emerging trends:
- Technology trends (AI adoption, automation, new platforms)
- Regulatory trends (new compliance requirements, enforcement patterns)
- Business model trends (SaaS migration, consolidation waves)
- Market structure trends (new entrants, incumbents struggling)

Articles:
{articles_context}

Return JSON array of trends object structure:
{{
    "trend_name": "string",
    "sector": "string",
    "trend_type": "string",
    "strength": "emerging|accelerating|mature",
    "supporting_evidence": ["list of titles"],
    "implications_for_thesis": "string",
    "confidence": "high|medium|low"
}}
"""
        try:
            response_text = await ai_client.generate(prompt, system_prompt=system_prompt)
             # Clean generic markdown code blocks
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            trends_data = json.loads(response_text)
            
            created_trends = []
            for t in trends_data:
                # Basic dedup: Check if trend name exists recently (not implemented deep comparison yet)
                # For now just create new entries to show activity
                trend = MarketTrend(
                    trend_name=t['trend_name'],
                    sector=t['sector'],
                    trend_type=t['trend_type'],
                    strength=t['strength'],
                    first_detected=datetime.now().date(),
                    supporting_evidence=t['supporting_evidence'],
                    implications_for_thesis=t['implications_for_thesis'],
                    confidence=t['confidence']
                )
                self.session.add(trend)
                created_trends.append(t)
            
            await self.session.commit()
            return created_trends

        except Exception as e:
            logger.error(f"Trend detection failed: {e}")
            return []
