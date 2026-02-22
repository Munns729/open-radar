"""
Revenue band logic for UK (Companies House) and EU (SME definition).

Used to sanity-check LLM revenue and provide band midpoints when actuals unavailable.
"""
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# UK Companies House account type bands (GBP) - conservative caps
UK_BANDS = {
    "micro-entity": (1_500_000, 750_000),   # cap, midpoint
    "micro": (1_500_000, 750_000),
    "small": (20_000_000, 10_000_000),
    "medium": (60_000_000, 30_000_000),
    "full": (None, None),  # No cap
    "dormant": (0, 0),
    "no-accounts": (0, 0),
}

# EU SME definition (EUR) - convert to GBP at ~0.85
# Micro: ≤€2M, Small: ≤€10M, Medium: ≤€50M
EUR_TO_GBP = 0.85
EU_BANDS_GBP = {
    "micro": (int(2_000_000 * EUR_TO_GBP), int(1_000_000 * EUR_TO_GBP)),   # ~£1.7M cap, £850k mid
    "small": (int(10_000_000 * EUR_TO_GBP), int(5_000_000 * EUR_TO_GBP)),  # ~£8.5M cap, £4.25M mid
    "medium": (int(50_000_000 * EUR_TO_GBP), int(25_000_000 * EUR_TO_GBP)),  # ~£42.5M cap, £21.25M mid
    "large": (None, None),
}


def get_uk_band_from_accounts(accounts: dict) -> Optional[Tuple[int, int, str]]:
    """
    Extract UK band from Companies House accounts.
    Returns (cap_gbp, midpoint_gbp, source_label) or None.
    """
    last = accounts.get("last_accounts", {}) or {}
    acct_type = (last.get("type") or "").lower().replace("_", "-").strip()
    band = UK_BANDS.get(acct_type)
    if band is None:
        if acct_type == "full":
            return None  # No cap
        # Unknown: treat as medium
        cap, mid = 60_000_000, 30_000_000
        return (cap, mid, "ch_band_midpoint")
    cap, mid = band
    if cap is None:
        return None
    return (cap, mid, "ch_band_midpoint")


def revenue_plausible_uk(accounts: dict, revenue_gbp: int) -> bool:
    """Check if revenue fits UK account type band."""
    result = get_uk_band_from_accounts(accounts)
    if result is None:
        return True  # full or unknown
    cap, _, _ = result
    return revenue_gbp <= cap


def infer_eu_band_from_employees(employees: int) -> Optional[Tuple[int, int, str]]:
    """
    Infer EU SME band from employee count (EU definition: micro <10, small <50, medium <250).
    Returns (cap_gbp, midpoint_gbp, source_label) or None.
    """
    if employees < 10:
        return EU_BANDS_GBP["micro"] + ("eu_band_midpoint",)
    if employees < 50:
        return EU_BANDS_GBP["small"] + ("eu_band_midpoint",)
    if employees < 250:
        return EU_BANDS_GBP["medium"] + ("eu_band_midpoint",)
    return None  # Large - no cap


def infer_eu_band_from_officers_count(officers_count: int) -> Optional[Tuple[int, int, str]]:
    """
    Rough proxy: officers_count often 1-5% of workforce for SMEs.
    officers 1-5 → micro, 6-20 → small, 21-100 → medium.
    """
    if officers_count <= 5:
        return EU_BANDS_GBP["micro"] + ("eu_band_midpoint",)
    if officers_count <= 20:
        return EU_BANDS_GBP["small"] + ("eu_band_midpoint",)
    if officers_count <= 100:
        return EU_BANDS_GBP["medium"] + ("eu_band_midpoint",)
    return None  # Large


def infer_eu_band_from_tranche_effectif(tranche: str) -> Optional[Tuple[int, int, str]]:
    """
    French SIRENE tranche_effectif_salarie codes.
    00=0, 01=1-2, 02=3-5, 03=6-9, 11=10-19, 12=20-49, 21=50-99, 22=100-199, 31=200-249, 32=250-499, etc.
    """
    MICRO = ("00", "01", "02", "03")  # 0-9
    SMALL = ("11", "12")  # 10-49
    MEDIUM = ("21", "22", "31")  # 50-249
    code = (tranche or "").strip()
    if code in MICRO:
        return EU_BANDS_GBP["micro"] + ("eu_band_midpoint",)
    if code in SMALL:
        return EU_BANDS_GBP["small"] + ("eu_band_midpoint",)
    if code in MEDIUM:
        return EU_BANDS_GBP["medium"] + ("eu_band_midpoint",)
    return None
