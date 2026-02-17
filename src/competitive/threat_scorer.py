"""Competitive Threat Scoring Algorithm"""
from typing import Dict, List, Any
from src.core.models import ThreatLevel
from src.core.data_types import ThreatScore
from datetime import datetime

class ThreatScorer:
    # Tier Lists (simplified for MVP)
    TIER_A_VCS = [
        "Sequoia", "Andreessen Horowitz", "a16z", "Bessemer", "Index Ventures", 
        "Accel", "Benchmark", "Founders Fund", "Lightspeed", "Greylock"
    ]
    
    # Categories of interest
    SECTORS = ['aerospace', 'healthcare', 'fintech', 'compliance', 'regulatory']
    DISRUPTION_KEYWORDS = ['ai', 'artificial intelligence', 'automation', 'machine learning', 'llm', 'generative']

    def score_announcement(self, announcement: Dict[str, Any]) -> ThreatScore:
        """Calculate threat score for an announcement"""
        score = 0
        reasoning = []

        # 1. VC Tier Analysis (Max 30)
        vc_name = announcement.get('vc_firm', '').strip()
        if any(tier_a in vc_name for tier_a in self.TIER_A_VCS):
            score += 30
            reasoning.append(f"Backed by Tier A VC: {vc_name} (+30)")
        elif vc_name: # Assume others are Tier B for now if identified
            score += 20
            reasoning.append(f"Backed by Tier B VC: {vc_name} (+20)")
        else:
            score += 10
            reasoning.append("Unknown VC Tier (+10)")

        # 2. Round Size Analysis (Max 25)
        amount = announcement.get('amount_raised_gbp', 0) or 0
        if amount > 20_000_000:
            score += 25
            reasoning.append(f"Large round >£20M (+25)")
        elif amount > 10_000_000:
            score += 20
            reasoning.append(f"Significant round £10-20M (+20)")
        elif amount > 5_000_000:
            score += 15
            reasoning.append(f"Moderate round £5-10M (+15)")
        else:
            # Covers known small rounds and undisclosed amounts
            score += 10
            reasoning.append(f"Seed/Small/Undisclosed round <£5M (+10)")

        # 3. Sector Match (Max 30)
        description = (announcement.get('description') or "").lower()
        sector = (announcement.get('sector') or "").lower()
        full_text = f"{description} {sector}"
        
        sector_matches = [s for s in self.SECTORS if s in full_text]
        if sector_matches:
            match_score = min(len(sector_matches) * 6, 30)
            score += match_score
            reasoning.append(f"Sector match: {', '.join(sector_matches)} (+{match_score})")

        # 4. Disruption Keywords (Max 15)
        keyword_matches = [k for k in self.DISRUPTION_KEYWORDS if k in full_text]
        if keyword_matches:
            ai_score = min(len(keyword_matches) * 5, 15)
            score += ai_score
            reasoning.append(f"AI/Disruption keywords: {', '.join(keyword_matches)} (+{ai_score})")

        # Determine Level
        if score >= 80:
            level = ThreatLevel.HIGH  # Mapping logic: 80+ is Critical/High
            # Note: Model supports HIGH/MEDIUM/LOW. We can map Critical to High conceptually or add it to Enum.
            # Requirement says "CRITICAL", but Enum has "HIGH". Let's stick to Enum for safety or update Enum.
            # Enum has HIGH, MEDIUM, LOW. Let's use HIGH for Critical/High for now.
            level = ThreatLevel.HIGH # "CRITICAL" in text
            level_str = "CRITICAL"
        elif score >= 60:
            level = ThreatLevel.HIGH
            level_str = "HIGH"
        elif score >= 40:
            level = ThreatLevel.MEDIUM
            level_str = "MEDIUM"
        else:
            level = ThreatLevel.LOW
            level_str = "LOW"

        return ThreatScore(
            company_id=0, # Placeholder, not linked to internal entity yet
            threat_level=level,
            competitor_name=announcement.get('company_name', 'Unknown'),
            details=f"Score: {score}/100 ({level_str}). Reasoning: {'; '.join(reasoning)}",
            score_date=datetime.now()
        )
