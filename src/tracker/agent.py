import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from sqlalchemy import select, desc

from src.core.config import settings
from src.core.database import async_session_factory
from src.tracker.database import TrackedCompany, CompanyNote, CompanyEvent, CompanyDocument
from src.universe.database import CompanyModel as UniverseCompany

logger = logging.getLogger(__name__)

# Initialize OpenAI/Moonshot client
client = AsyncOpenAI(
    api_key=settings.moonshot_api_key,
    base_url=settings.kimi_api_base
)

class TrackerAgent:
    """
    AI Agent that answers questions about tracked companies using
    RAG (Retrieval Augmented Generation) on notes, events, and documents.
    """
    
    def __init__(self, model: str = None):
        self.model = model or settings.kimi_model
        
    async def query(self, tracked_id: int, user_question: str) -> Dict[str, Any]:
        """
        Answer a user question about a tracked company.
        """
        context = await self._build_context(tracked_id)
        
        if not context:
            return {
                "answer": "I couldn't find any information about this company.",
                "sources": []
            }
            
        system_prompt = """You are an expert investment analyst assistant.
Answer the user's question based ONLY on the provided context.
If the context doesn't contain the answer, say "I don't have enough information to answer that based on the available data."
Cite your sources (e.g., "According to the Research Note from...") where possible.
Be concise and professional."""

        user_prompt = f"""
Context Information:
{context['text']}

User Question: {user_question}
"""

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content
            
            return {
                "answer": answer,
                "sources": context['sources']
            }
            
        except Exception as e:
            logger.error(f"Agent query failed: {e}")
            return {
                "answer": "Sorry, I encountered an error while processing your request.",
                "sources": []
            }

    async def _build_context(self, tracked_id: int) -> Optional[Dict[str, Any]]:
        """
        Gather context from DB: Profile, Notes, Events, Documents.
        """
        async with async_session_factory() as session:
            # Fetch Company Data
            stmt = select(TrackedCompany, UniverseCompany).join(
                UniverseCompany, TrackedCompany.company_id == UniverseCompany.id
            ).where(TrackedCompany.id == tracked_id)
            
            result = await session.execute(stmt)
            row = result.first()
            
            if not row:
                return None
                
            tracked, company = row
            
            # Fetch Notes
            notes_stmt = select(CompanyNote).where(
                CompanyNote.tracked_company_id == tracked_id
            ).order_by(desc(CompanyNote.created_at)).limit(10)
            notes = (await session.execute(notes_stmt)).scalars().all()
            
            # Fetch Events
            events_stmt = select(CompanyEvent).where(
                CompanyEvent.tracked_company_id == tracked_id
            ).order_by(desc(CompanyEvent.event_date)).limit(10)
            events = (await session.execute(events_stmt)).scalars().all()
            
            # Fetch Document Content
            docs_stmt = select(CompanyDocument).where(
                CompanyDocument.tracked_company_id == tracked_id
            ).limit(5) # Limit to 5 docs for context window safety
            documents = (await session.execute(docs_stmt)).scalars().all()
            
            # Assemble Text
            context_text = f"COMPANY PROFILE:\nName: {company.name}\nDescription: {company.description}\nSector: {company.sector}\nStatus: {tracked.tracking_status}\nPriority: {tracked.priority}\n\n"
            
            sources = ["Company Profile"]
            
            if notes:
                context_text += "RESEARCH NOTES:\n"
                for n in notes:
                    context_text += f"- [{n.created_at.date()} - {n.note_type}]: {n.note_text}\n"
                    sources.append("Research Notes")
                context_text += "\n"
                
            if events:
                context_text += "RECENT EVENTS:\n"
                for e in events:
                    context_text += f"- [{e.event_date} - {e.event_type}]: {e.title} ({e.description})\n"
                    sources.append("Events Timeline")
                context_text += "\n"
                
            if documents:
                context_text += "UPLOADED DOCUMENTS:\n"
                for d in documents:
                    if d.extracted_text:
                        # Truncate large docs to ~2k chars per doc for now
                        snippet = d.extracted_text[:2000]
                        context_text += f"--- Document: {d.filename} ---\n{snippet}\n...\n"
                        sources.append(f"Document: {d.filename}")
            
            return {
                "text": context_text,
                "sources": list(set(sources))
            }
