import logging
import json
from datetime import date, timedelta, datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.market_intelligence.database import WeeklyBriefing, IntelligenceItem, RegulatoryChange, MarketTrend
from src.core.ai_client import ai_client

# Import Service Layers
from src.deal_intelligence.service import get_deal_records, get_market_metrics
from src.competitive.service import get_announcements, get_threats_by_level
from src.tracker.service import get_events_for_company, get_unread_alerts

logger = logging.getLogger(__name__)

class WeeklyBriefingGenerator:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def gather_context(self, days_back: int = 7) -> Dict[str, Any]:
        """
        Gather data from all modules for the past N days.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # 1. Deal Activity
        deals = await get_deal_records(limit=10) # Get recent deals
        # Filter for recent if needed, though service returns last 20 by default
        recent_deals = [d for d in deals if d.get('deal_date') and datetime.fromisoformat(str(d['deal_date'])) >= cutoff_date] if deals else []

        # 2. Competitive Threats
        # Note: service.py in competitive needs get_threats_by_level exposed better, 
        # but for now we will use what we have or add what's missing. 
        # Actually, looking at the file plan, I should have updated service.py first if I wanted to be pure.
        # But I can use the direct DB imports if service is lacking, strictly for this class which is an internal synthesizer.
        # Let's stick to the plan: "Import Data Models/Services". 
        # I will use the service functions I saw available or what I can reasonably infer.
        announcements = await get_announcements(limit=10, since=cutoff_date)
        
        # 3. Tracker Events (High Priority)
        # We need to iterate or get a global feed. 
        # The tracker service has `get_events_for_company` but not a global `get_all_recent_events`.
        # I will add a method to get global unread alerts which is a good proxy for "news".
        alerts = await get_unread_alerts(limit=20)

        # 4. Market Intelligence (Internal)
        # Regulatory
        reg_stmt = select(RegulatoryChange).order_by(RegulatoryChange.created_at.desc()).limit(5)
        regs = (await self.session.execute(reg_stmt)).scalars().all()

        # Trends
        trend_stmt = select(MarketTrend).limit(5)
        trends = (await self.session.execute(trend_stmt)).scalars().all()

        return {
            "week_starting": date.today(),
            "deals": recent_deals,
            "announcements": announcements,
            "alerts": alerts,
            "regulations": [r.__dict__ for r in regs], # simplistic serialization
            "trends": [t.__dict__ for t in trends]
        }

    async def generate_briefing(self) -> WeeklyBriefing:
        """
        Generate the full weekly briefing.
        """
        logger.info("Starting Weekly Briefing Generation...")
        data = await self.gather_context()
        
        # Construct Prompt
        prompt = self._construct_prompt(data)
        
        # Call AI
        logger.info("Sending prompt to AI Client...")
        response_text = await ai_client.generate(
            prompt, 
            system_prompt="You are a senior private equity analyst producing a high-stakes weekly intelligence briefing."
        )
        
        # Parse Response (expecting JSON structure ideally, or just parse text sections)
        # For robustness, we will ask for JSON in the prompt or regex parse.
        # Let's simple ask for JSON.
        
        try:
            # Strip markdown code blocks if present
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(cleaned_text)
            
            executive_summary = parsed.get("executive_summary", "No summary generated.")
            thesis_implications = parsed.get("thesis_implications", "No implications generated.")
            action_items = parsed.get("action_items", [])
            
        except json.JSONDecodeError:
            logger.error("Failed to parse AI response as JSON. Falling back to raw text.")
            executive_summary = response_text[:500] + "..."
            thesis_implications = "Analysis failed to parse."
            action_items = ["Check logs for raw AI output"]

        # Save to DB
        briefing = WeeklyBriefing(
            week_starting=date.today(),
            executive_summary=executive_summary,
            thesis_implications=thesis_implications,
            action_items=action_items,
            top_ma_activity=[f"{d.get('target_company_name')} ({d.get('deal_type')})" for d in data['deals'][:5]],
            top_regulatory_changes=[r.get('title') for r in data['regulations'][:3]],
            emerging_trends=[t.get('trend_name') for t in data['trends'][:3]]
        )
        
        self.session.add(briefing)
        await self.session.commit()
        await self.session.refresh(briefing)
        
        logger.info(f"Briefing {briefing.id} generated successfully.")
        return briefing

    def _construct_prompt(self, data: Dict[str, Any]) -> str:
        return f"""
        Analyze the following market data for the week of {data['week_starting']} and produce a briefing.
        
        DATA:
        1. RECENT DEALS: {len(data['deals'])} found.
           {json.dumps(data['deals'], default=str)[:1000]}
           
        2. COMPETITIVE ANNOUNCEMENTS: {len(data['announcements'])} found.
           {json.dumps(data['announcements'], default=str)[:1000]}
           
        3. PORTFOLIO ALERTS: {len(data['alerts'])} found.
           {json.dumps(data['alerts'], default=str)[:1000]}
           
        4. REGULATORY CHANGES: {len(data['regulations'])} found.
           {str([r.get('title') for r in data['regulations']])}

        OUTPUT FORMAT:
        Return a valid JSON object with these keys:
        - "executive_summary": A 2-paragraph synthesis of the most important activity.
        - "thesis_implications": How this impacts our investment thesis (specifically referencing moats).
        - "action_items": A list of 3-5 specific follow-up actions (e.g., "Review deal X", "Monitor competitor Y").
        """

    def render_markdown(self, briefing: WeeklyBriefing) -> str:
        """
        Render the briefing as a readable Markdown string.
        """
        return f"""
# 🌍 RADAR Weekly Intelligence Briefing
**Week of {briefing.week_starting}**

## 🚨 Executive Summary
{briefing.executive_summary}

## 🧠 Thesis Implications
{briefing.thesis_implications}

## ⚡ Action Items
{chr(10).join([f"- {item}" for item in (briefing.action_items or [])])}

## 📊 Key Activity
**M&A Activity**: {', '.join(briefing.top_ma_activity or [])}
**Regulatory**: {', '.join(briefing.top_regulatory_changes or [])}
**Trends**: {', '.join(briefing.emerging_trends or [])}
        """

    def render_html(self, briefing: WeeklyBriefing) -> str:
        """
        Render the briefing as an HTML string for email.
        """
        styles = """
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }
            h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
            h2 { color: #34495e; margin-top: 30px; }
            ul { padding-left: 20px; }
            li { margin-bottom: 5px; }
            .section { background: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
            .highlight { color: #e74c3c; font-weight: bold; }
        """
        
        # Helper to format lists
        def format_list(items):
            if not items: return "<em>None</em>"
            return "<ul>" + "".join([f"<li>{item}</li>" for item in items]) + "</ul>"

        return f"""
        <html>
        <head>
            <style>{styles}</style>
        </head>
        <body>
            <h1>🌍 RADAR Weekly Intelligence Briefing</h1>
            <p><strong>Week of {briefing.week_starting}</strong></p>

            <div class="section">
                <h2>🚨 Executive Summary</h2>
                <p>{briefing.executive_summary}</p>
            </div>

            <div class="section">
                <h2>🧠 Thesis Implications</h2>
                <p>{briefing.thesis_implications}</p>
            </div>

            <div class="section">
                <h2>⚡ Action Items</h2>
                {format_list(briefing.action_items)}
            </div>

            <div class="section">
                <h2>📊 Key Activity</h2>
                <p><strong>M&A Activity</strong></p>
                {format_list(briefing.top_ma_activity)}
                
                <p><strong>Regulatory</strong></p>
                {format_list(briefing.top_regulatory_changes)}
                
                <p><strong>Trends</strong></p>
                {format_list(briefing.emerging_trends)}
            </div>
        </body>
        </html>
        """

