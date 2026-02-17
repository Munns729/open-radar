"""
Core enums for RADAR system.

NOTE: These are NOT database models. For SQLAlchemy ORM models, see each module's database.py:
  - Company/Certification/Relationship → src/universe/database.py
  - PEFirm/PEInvestment → src/capital/database.py  
  - DealRecord/MarketMetrics → src/deal_intelligence/database.py
  - TrackedCompany/CompanyEvent → src/tracker/database.py

The enums below (CompanyTier, ThreatLevel) are used across modules
for consistent enum values in database columns and business logic.

NOTE: MoatType was removed in favour of thesis-driven pillar names.
Moat types are now free-form strings derived from the active thesis config
(see config/thesis.yaml). The strongest pillar name is stored in
CompanyModel.moat_type as a plain string.
"""
from enum import Enum


class CompanyTier(str, Enum):
    TIER_1A = "1A"
    TIER_1B = "1B"
    TIER_2 = "2"
    WAITLIST = "waitlist"


class ThreatLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"
