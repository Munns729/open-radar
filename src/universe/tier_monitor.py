"""
Tier Change Monitor.

Detects when companies cross tier thresholds during scoring and
generates alerts + a structured change log for downstream consumers
(briefings, notifications, dashboard).
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

from src.core.models import CompanyTier

logger = logging.getLogger(__name__)

# Tier ordering for comparison (higher index = better tier)
TIER_RANK = {
    CompanyTier.WAITLIST: 0,
    CompanyTier.TIER_2: 1,
    CompanyTier.TIER_1B: 2,
    CompanyTier.TIER_1A: 3,
}


@dataclass
class TierChange:
    """A single tier transition for one company."""
    company_id: int
    company_name: str
    old_tier: Optional[str]
    new_tier: str
    old_score: Optional[int]
    new_score: int
    direction: str  # "promoted", "demoted", "new_entry"
    top_pillar: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_promotion(self) -> bool:
        return self.direction == "promoted"

    @property
    def is_notable(self) -> bool:
        """Promotions into Tier 1A/1B are always notable."""
        return self.new_tier in ("1A", "1B") and self.direction in ("promoted", "new_entry")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company_id": self.company_id,
            "company_name": self.company_name,
            "old_tier": self.old_tier,
            "new_tier": self.new_tier,
            "old_score": self.old_score,
            "new_score": self.new_score,
            "direction": self.direction,
            "top_pillar": self.top_pillar,
            "timestamp": self.timestamp.isoformat(),
        }

    def summary(self) -> str:
        arrow = "⬆️" if self.is_promotion else "⬇️"
        old = self.old_tier or "unscored"
        return f"{arrow} {self.company_name}: {old} -> {self.new_tier} (score {self.new_score})"


@dataclass
class TierChangeReport:
    """Aggregated tier changes from a scoring run."""
    changes: List[TierChange] = field(default_factory=list)
    run_timestamp: datetime = field(default_factory=datetime.utcnow)
    companies_scored: int = 0

    @property
    def promotions(self) -> List[TierChange]:
        return [c for c in self.changes if c.is_promotion]

    @property
    def demotions(self) -> List[TierChange]:
        return [c for c in self.changes if c.direction == "demoted"]

    @property
    def new_entries(self) -> List[TierChange]:
        return [c for c in self.changes if c.direction == "new_entry"]

    @property
    def notable_changes(self) -> List[TierChange]:
        return [c for c in self.changes if c.is_notable]

    @property
    def has_changes(self) -> bool:
        return len(self.changes) > 0

    def render_markdown(self) -> str:
        if not self.changes:
            return f"# Tier Changes — {self.run_timestamp:%Y-%m-%d %H:%M}\n\nNo tier changes detected across {self.companies_scored} companies.\n"

        lines = [
            f"# Tier Changes — {self.run_timestamp:%Y-%m-%d %H:%M}",
            f"**{self.companies_scored}** companies scored, **{len(self.changes)}** tier changes detected.\n",
        ]

        if self.promotions:
            lines.append("## Promotions")
            for c in sorted(self.promotions, key=lambda x: TIER_RANK.get(_parse_tier(x.new_tier), 0), reverse=True):
                lines.append(f"- **{c.company_name}** -> Tier {c.new_tier} (score {c.new_score})")
                if c.top_pillar:
                    lines.append(f"  - Strongest pillar: {c.top_pillar}")
            lines.append("")

        if self.demotions:
            lines.append("## Demotions")
            for c in self.demotions:
                lines.append(f"- **{c.company_name}** -> Tier {c.new_tier} (score {c.new_score}, was {c.old_tier})")
            lines.append("")

        if self.new_entries:
            lines.append("## New Entries")
            for c in self.new_entries:
                lines.append(f"- **{c.company_name}** -> Tier {c.new_tier} (score {c.new_score})")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_timestamp": self.run_timestamp.isoformat(),
            "companies_scored": self.companies_scored,
            "total_changes": len(self.changes),
            "promotions": len(self.promotions),
            "demotions": len(self.demotions),
            "new_entries": len(self.new_entries),
            "changes": [c.to_dict() for c in self.changes],
        }


def _parse_tier(tier_str: str) -> Optional[CompanyTier]:
    """Parse a tier string back to enum."""
    mapping = {"1A": CompanyTier.TIER_1A, "1B": CompanyTier.TIER_1B, "2": CompanyTier.TIER_2, "waitlist": CompanyTier.WAITLIST}
    return mapping.get(tier_str)


def detect_tier_change(
    company_id: int,
    company_name: str,
    old_tier: Optional[CompanyTier],
    new_tier: CompanyTier,
    old_score: Optional[int],
    new_score: int,
    moat_attributes: Optional[Dict] = None,
) -> Optional[TierChange]:
    """
    Compare old and new tier for a single company.
    Returns a TierChange if the tier changed, else None.
    """
    old_tier_val = old_tier.value if old_tier else None
    new_tier_val = new_tier.value if new_tier else None

    if old_tier_val == new_tier_val:
        return None

    # Determine direction
    old_rank = TIER_RANK.get(old_tier, -1) if old_tier else -1
    new_rank = TIER_RANK.get(new_tier, 0)

    if old_tier is None or old_rank == -1:
        direction = "new_entry"
    elif new_rank > old_rank:
        direction = "promoted"
    else:
        direction = "demoted"

    # Find strongest pillar
    top_pillar = None
    if moat_attributes and isinstance(moat_attributes, dict):
        best_score = 0
        for key, val in moat_attributes.items():
            if isinstance(val, dict) and val.get("score", 0) > best_score:
                best_score = val["score"]
                top_pillar = key

    change = TierChange(
        company_id=company_id,
        company_name=company_name,
        old_tier=old_tier_val,
        new_tier=new_tier_val,
        old_score=old_score,
        new_score=new_score,
        direction=direction,
        top_pillar=top_pillar,
    )

    logger.info(change.summary())
    return change
