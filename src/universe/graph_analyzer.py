"""
Graph Analysis for Company Relationships.
"""
import logging
from typing import List, Tuple, Dict, Any
import networkx as nx
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.universe.database import CompanyModel, CompanyRelationshipModel

logger = logging.getLogger(__name__)

class GraphAnalyzer:
    """
    Analyzes company data to find relationships (subsidiaries, partners, competitors).
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.graph = nx.Graph()

    async def build_graph(self):
        """
        Load companies and relationships into NetworkX graph.
        """
        result = await self.db.execute(select(CompanyModel))
        companies = result.scalars().all()
        
        result = await self.db.execute(select(CompanyRelationshipModel))
        relationships = result.scalars().all()
        
        for c in companies:
            self.graph.add_node(c.id, name=c.name, sector=c.sector)
            
        for r in relationships:
            self.graph.add_edge(r.company_a_id, r.company_b_id, type=r.relationship_type, confidence=r.confidence)
            
        logger.info(f"Graph built: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")

    def find_related_companies(self, company_id: int) -> List[Dict[str, Any]]:
        """
        Find directly connected companies.
        """
        if company_id not in self.graph:
            return []
            
        related = []
        for neighbor in self.graph[company_id]:
            edge_data = self.graph.get_edge_data(company_id, neighbor)
            related.append({
                "company_id": neighbor,
                "relationship": edge_data.get("type"),
                "confidence": edge_data.get("confidence")
            })
        return related

    def identify_networks(self) -> List[List[int]]:
        """
        Identify isolated subgraphs (company groups).
        """
        return [list(c) for c in nx.connected_components(self.graph)]

    def calculate_centrality(self):
        """
        Calculate and cache centrality metrics on the graph.
        """
        if self.graph.number_of_nodes() == 0:
            return
            
        self.degree_centrality = nx.degree_centrality(self.graph)
        try:
            self.eigenvector_centrality = nx.eigenvector_centrality(self.graph, max_iter=500)
        except:
            self.eigenvector_centrality = {n: 0 for n in self.graph.nodes()}
            
        logger.info("Graph centrality calculated.")
        
    def get_moat_signals(self, company_id: int) -> Dict[str, Any]:
        """
        Return graph signals for moat scoring.
        """
        signals = {
            "is_central_hub": False,
            "is_critical_supplier": False,
            "degree_score": 0.0
        }
        
        if not hasattr(self, "degree_centrality"):
            self.calculate_centrality()
            
        if company_id in self.graph:
            # Check Centrality
            score = self.degree_centrality.get(company_id, 0)
            signals["degree_score"] = score
            
            # Heuristic: Top 10% are hubs
            all_scores = list(self.degree_centrality.values())
            if all_scores and score > sorted(all_scores)[-max(1, int(len(all_scores)*0.1))]:
                signals["is_central_hub"] = True
            
        return signals

    async def suggest_relationships(self, threshold: float = 0.85):
        """
        Heuristic-based relationship discovery.
        - Shared Address (High confidence)
        """
        result = await self.db.execute(select(CompanyModel))
        companies = result.scalars().all()
        
        # Group by address
        address_map = {}
        for c in companies:
            if c.hq_address:
                norm_addr = c.hq_address.lower().strip()
                if norm_addr not in address_map:
                    address_map[norm_addr] = []
                address_map[norm_addr].append(c)
        
        # Analyze groups
        new_relationships = []
        
        # 1. Shared Address
        for addr, group in address_map.items():
            if len(group) > 1:
                # Create edges between all pairs in group
                for i in range(len(group)):
                    for j in range(i + 1, len(group)):
                        c1 = group[i]
                        c2 = group[j]
                        await self._add_relationship(c1, c2, "shared_address", 0.9)
                        
        return new_relationships

    async def _add_relationship(self, c1: CompanyModel, c2: CompanyModel, rel_type: str, conf: float):
        """Helper to safely add relationship to DB"""
        result = await self.db.execute(
            select(CompanyRelationshipModel).where(
                CompanyRelationshipModel.company_a_id == c1.id,
                CompanyRelationshipModel.company_b_id == c2.id,
                CompanyRelationshipModel.relationship_type == rel_type
            )
        )
        exists = result.scalars().first()
        
        if not exists:
            # Also check reverse direction if undirected
            result = await self.db.execute(
                select(CompanyRelationshipModel).where(
                    CompanyRelationshipModel.company_a_id == c2.id,
                    CompanyRelationshipModel.company_b_id == c1.id,
                    CompanyRelationshipModel.relationship_type == rel_type
                )
            )
            reverse = result.scalars().first()
            
            if not reverse:
                rel = CompanyRelationshipModel(
                    company_a_id=c1.id,
                    company_b_id=c2.id,
                    relationship_type=rel_type,
                    confidence=conf,
                    discovered_via="graph_analyzer"
                )
                self.db.add(rel)
                logger.info(f"Found relationship: {c1.name} <-> {c2.name} ({rel_type})")

