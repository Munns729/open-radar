"""
Relationship Intelligence Analyzer for Module 5.

Provides:
- Warm intro path finding (BFS through network graph)
- Relationship strength calculation
- Follow-up suggestions
"""
import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from collections import deque

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.relationships.database import (
    Contact, Interaction, NetworkConnection,
    RelationshipStrength, InteractionOutcome
)

logger = logging.getLogger(__name__)


class RelationshipAnalyzer:
    """
    Analyzes relationship data to provide actionable insights.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def find_warm_intro_path(
        self, 
        target_contact_id: int,
        min_strength: int = 50
    ) -> List[Dict]:
        """
        Find the shortest path from your strong contacts to a target contact.
        Uses BFS through the NetworkConnection graph.
        
        Args:
            target_contact_id: The contact you want to reach
            min_strength: Minimum relationship strength to consider as "your" contact (default 50)
            
        Returns:
            List of dicts representing the path, each with:
            - contact_id, contact_name, company
            - connection_strength to next node
            - connection_type
        """
        # Get all "my contacts" - those with high relationship strength
        my_contacts_stmt = select(Contact.id).where(
            Contact.relationship_score >= min_strength
        )
        result = await self.session.execute(my_contacts_stmt)
        my_contact_ids = set(row[0] for row in result.all())
        
        if not my_contact_ids:
            logger.warning("No strong contacts found to start warm intro path")
            return []
        
        if target_contact_id in my_contact_ids:
            # Already have direct relationship
            contact = await self.session.get(Contact, target_contact_id)
            return [{
                "contact_id": contact.id,
                "contact_name": contact.full_name,
                "company": contact.company_name,
                "relationship_score": contact.relationship_score,
                "is_direct": True,
                "message": "You already have a strong relationship with this contact!"
            }]
        
        # BFS to find shortest path
        # Build adjacency list from network connections
        connections_stmt = select(NetworkConnection)
        result = await self.session.execute(connections_stmt)
        connections = result.scalars().all()
        
        # Build graph
        graph: Dict[int, List[Tuple[int, int, str]]] = {}  # contact_id -> [(neighbor_id, strength, type)]
        for conn in connections:
            if conn.contact_a_id not in graph:
                graph[conn.contact_a_id] = []
            if conn.contact_b_id not in graph:
                graph[conn.contact_b_id] = []
            
            graph[conn.contact_a_id].append((conn.contact_b_id, conn.strength, conn.connection_type))
            graph[conn.contact_b_id].append((conn.contact_a_id, conn.strength, conn.connection_type))
        
        # BFS from all my contacts
        queue = deque()
        visited = set()
        parent: Dict[int, Tuple[int, int, str]] = {}  # child -> (parent, strength, type)
        
        for contact_id in my_contact_ids:
            queue.append(contact_id)
            visited.add(contact_id)
            parent[contact_id] = None
        
        target_found = False
        while queue and not target_found:
            current = queue.popleft()
            
            if current == target_contact_id:
                target_found = True
                break
            
            for neighbor, strength, conn_type in graph.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    parent[neighbor] = (current, strength, conn_type)
                    queue.append(neighbor)
        
        if not target_found:
            return [{
                "message": "No warm intro path found to this contact",
                "suggestion": "Consider reaching out directly or finding mutual connections on LinkedIn"
            }]
        
        # Reconstruct path
        path = []
        current = target_contact_id
        while parent.get(current) is not None:
            prev, strength, conn_type = parent[current]
            path.append({
                "contact_id": current,
                "from_contact_id": prev,
                "connection_strength": strength,
                "connection_type": conn_type
            })
            current = prev
        
        # Add starting contact
        path.append({
            "contact_id": current,
            "from_contact_id": None,
            "connection_strength": None,
            "connection_type": None,
            "is_start": True
        })
        
        path.reverse()
        
        # Enrich path with contact details
        contact_ids = [p["contact_id"] for p in path]
        contacts_stmt = select(Contact).where(Contact.id.in_(contact_ids))
        result = await self.session.execute(contacts_stmt)
        contacts_map = {c.id: c for c in result.scalars().all()}
        
        enriched_path = []
        for i, p in enumerate(path):
            contact = contacts_map.get(p["contact_id"])
            enriched_path.append({
                "step": i + 1,
                "contact_id": p["contact_id"],
                "contact_name": contact.full_name if contact else "Unknown",
                "company": contact.company_name if contact else None,
                "job_title": contact.job_title if contact else None,
                "relationship_score": contact.relationship_score if contact else 0,
                "connection_strength": p.get("connection_strength"),
                "connection_type": p.get("connection_type"),
                "is_start": p.get("is_start", False),
                "is_target": p["contact_id"] == target_contact_id
            })
        
        # Calculate overall path strength (minimum link)
        min_link_strength = min(
            (p["connection_strength"] for p in enriched_path if p["connection_strength"] is not None),
            default=0
        )
        
        # Find best introducer (the contact just before target with highest strength)
        if len(enriched_path) >= 2:
            introducer = enriched_path[-2]
        else:
            introducer = None
        
        return {
            "path": enriched_path,
            "path_length": len(enriched_path) - 1,  # Number of hops
            "min_link_strength": min_link_strength,
            "suggested_introducer": introducer,
            "success": True
        }

    async def calculate_relationship_strength(self, contact_id: int) -> int:
        """
        Calculate relationship strength score (0-100) based on:
        - Interaction frequency (especially recent ones)
        - Interaction outcomes
        - Response rate
        
        Formula: recent_interactions × outcome_quality × response_rate
        """
        contact = await self.session.get(Contact, contact_id)
        if not contact:
            return 0
        
        # Get interactions from last 365 days
        cutoff_date = date.today() - timedelta(days=365)
        interactions_stmt = select(Interaction).where(
            and_(
                Interaction.contact_id == contact_id,
                Interaction.interaction_date >= cutoff_date
            )
        ).order_by(Interaction.interaction_date.desc())
        
        result = await self.session.execute(interactions_stmt)
        interactions = result.scalars().all()
        
        if not interactions:
            return 0
        
        # Calculate components
        
        # 1. Recency-weighted interaction count (more recent = higher weight)
        recency_score = 0
        for interaction in interactions:
            days_ago = (date.today() - interaction.interaction_date).days
            if days_ago <= 30:
                recency_score += 10  # Very recent
            elif days_ago <= 90:
                recency_score += 5   # Recent
            elif days_ago <= 180:
                recency_score += 2   # Moderate
            else:
                recency_score += 1   # Old
        
        # Cap at 40 points
        recency_score = min(recency_score, 40)
        
        # 2. Outcome quality (0-30 points)
        outcome_weights = {
            InteractionOutcome.POSITIVE.value: 1.0,
            InteractionOutcome.NEUTRAL.value: 0.5,
            InteractionOutcome.NEGATIVE.value: 0.1,
            InteractionOutcome.NO_RESPONSE.value: 0.2,
            None: 0.3
        }
        
        total_outcome = sum(
            outcome_weights.get(i.outcome, 0.3) 
            for i in interactions
        )
        avg_outcome = total_outcome / len(interactions)
        outcome_score = int(avg_outcome * 30)
        
        # 3. Response rate (0-30 points)
        responded_count = sum(
            1 for i in interactions 
            if i.outcome and i.outcome != InteractionOutcome.NO_RESPONSE.value
        )
        response_rate = responded_count / len(interactions) if interactions else 0
        response_score = int(response_rate * 30)
        
        # Total score
        total_score = min(recency_score + outcome_score + response_score, 100)
        
        return total_score

    async def suggest_follow_ups(
        self, 
        days_threshold: int = 90,
        min_strength: int = 50,
        limit: int = 20
    ) -> List[Dict]:
        """
        Find contacts that need follow-up based on:
        - Last contact date > threshold days ago
        - Relationship strength > min_strength
        
        Returns ranked list for re-engagement.
        """
        cutoff_date = date.today() - timedelta(days=days_threshold)
        
        stmt = select(Contact).where(
            and_(
                or_(
                    Contact.last_contact_date < cutoff_date,
                    Contact.last_contact_date.is_(None)
                ),
                Contact.relationship_score >= min_strength
            )
        ).order_by(
            Contact.relationship_score.desc(),
            Contact.last_contact_date.asc()
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        contacts = result.scalars().all()
        
        follow_ups = []
        for contact in contacts:
            days_since = None
            if contact.last_contact_date:
                days_since = (date.today() - contact.last_contact_date).days
            
            follow_ups.append({
                "contact_id": contact.id,
                "full_name": contact.full_name,
                "company": contact.company_name,
                "job_title": contact.job_title,
                "email": contact.email,
                "relationship_score": contact.relationship_score,
                "relationship_strength": contact.relationship_strength,
                "last_contact_date": contact.last_contact_date.isoformat() if contact.last_contact_date else None,
                "days_since_contact": days_since,
                "priority": "high" if contact.relationship_score >= 70 else "medium",
                "suggested_action": self._suggest_action(contact)
            })
        
        return follow_ups

    def _suggest_action(self, contact: Contact) -> str:
        """Generate a suggested follow-up action based on contact type."""
        action_map = {
            "founder": "Schedule a catch-up call to discuss business progress",
            "ceo": "Send a relevant industry article or intro opportunity",
            "cfo": "Share market insights or financial trends",
            "advisor": "Request their perspective on a current deal",
            "banker": "Discuss deal pipeline and market activity",
            "lawyer": "Check in about regulatory changes or deal structures",
            "investor": "Share deal flow or co-investment opportunities"
        }
        return action_map.get(contact.contact_type, "Send a brief check-in email")

    async def update_all_relationship_scores(self) -> int:
        """
        Recalculate relationship_score for all contacts.
        Returns the number of contacts updated.
        """
        stmt = select(Contact)
        result = await self.session.execute(stmt)
        contacts = result.scalars().all()
        
        updated_count = 0
        for contact in contacts:
            new_score = await self.calculate_relationship_strength(contact.id)
            
            # Update strength category based on score
            if new_score >= 70:
                new_strength = RelationshipStrength.HOT.value
            elif new_score >= 40:
                new_strength = RelationshipStrength.WARM.value
            else:
                new_strength = RelationshipStrength.COLD.value
            
            if contact.relationship_score != new_score or contact.relationship_strength != new_strength:
                contact.relationship_score = new_score
                contact.relationship_strength = new_strength
                updated_count += 1
        
        await self.session.commit()
        logger.info(f"Updated relationship scores for {updated_count} contacts")
        
        return updated_count

    async def get_network_stats(self) -> Dict:
        """Get statistics about the relationship network."""
        contact_count = await self.session.scalar(select(func.count(Contact.id)))
        connection_count = await self.session.scalar(select(func.count(NetworkConnection.id)))
        interaction_count = await self.session.scalar(select(func.count(Interaction.id)))
        
        hot_contacts = await self.session.scalar(
            select(func.count(Contact.id)).where(
                Contact.relationship_strength == RelationshipStrength.HOT.value
            )
        )
        
        return {
            "total_contacts": contact_count or 0,
            "total_connections": connection_count or 0,
            "total_interactions": interaction_count or 0,
            "hot_contacts": hot_contacts or 0,
            "avg_connections_per_contact": round(
                (connection_count * 2) / contact_count, 2
            ) if contact_count else 0
        }
