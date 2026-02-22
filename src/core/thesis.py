"""
Investment Thesis Configuration System.

Loads a pluggable investment thesis from YAML that drives:
- Which moat pillars exist and how they're weighted
- What certifications score and how much
- LLM prompt templates for moat analysis and semantic enrichment
- Business filters (revenue range, employee range, sector keywords)
- Tier thresholds

Usage:
    from src.core.thesis import thesis

    thesis.moat_weights["regulatory"]       # 0.30
    thesis.tier_thresholds.tier_1a          # 70
    thesis.get_cert_score("AS9100")         # 50
    thesis.moat_analysis_prompt             # Full prompt string
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import yaml
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


# =============================================================================
# SCHEMA
# =============================================================================

class MoatPillar(BaseModel):
    """Definition of a single moat scoring pillar."""
    name: str
    weight: float = Field(ge=0.0, le=1.0)
    description: str = ""
    max_raw_score: int = 100
    evidence_threshold: int = 30  # Minimum raw score to count as "present"
    prompt_guidance: str = ""     # Injected into LLM prompts


class TierThresholds(BaseModel):
    """Weighted-score thresholds for tier assignment."""
    tier_1a: int = 70
    tier_1b: int = 50
    tier_2: int = 30
    # Below tier_2 = Waitlist


class BusinessFilters(BaseModel):
    """Defines the target universe for discovery."""
    min_revenue: Optional[float] = None
    max_revenue: Optional[float] = None
    min_employees: Optional[int] = None
    max_employees: Optional[int] = None
    target_countries: List[str] = Field(default_factory=list)
    positive_keywords: List[str] = Field(default_factory=list)
    negative_keywords: List[str] = Field(default_factory=list)
    negative_keyword_penalty: int = 5


class PipelineFilters(BaseModel):
    """
    Pre-enrichment pipeline exclusions. Applied before expensive enrichment.
    All values come from config/thesis.yaml — no hardcoding in code.
    """
    exclude_sectors: List[str] = Field(
        default_factory=lambda: [
            "Biotechnology", "Pharmaceuticals", "Mining", "Oil & Gas",
            "Real Estate", "Consumer Goods",
        ],
        description="Sector names to exclude from enrichment/scoring",
    )
    public_listing_keywords: List[str] = Field(
        default_factory=lambda: [
            "publicly traded", "nasdaq:", "nyse:", "lse:", "euronext:",
            "stock exchange", "ticker symbol", "fortune 500", "ftse 100",
            "cac 40", "dax 30",
        ],
        description="Keywords in description indicating public listing (excluded)",
    )
    max_revenue_exclude: Optional[float] = Field(
        default=500_000_000,
        description="Exclude companies with revenue above this (GBP)",
    )
    exclude_plc_by_name: bool = Field(
        default=True,
        description="Exclude companies with 'PLC' in name (UK public listing)",
    )
    enrichment_skip_days: float = Field(
        default=0.5,
        description="Skip companies enriched/updated within this many days (0.5=12h; set 7 for weekly cadence)",
    )
    min_semantic_enrichment_text_chars: int = Field(
        default=2500,
        description="Zone 2 gate: min website text length (chars) for Zone 3 semantic enrichment",
    )


class RiskConfig(BaseModel):
    """Negative signal configuration."""
    keywords: List[str] = Field(default_factory=list)
    max_penalty: int = 20
    declining_revenue_penalty: int = 10


class DealScreening(BaseModel):
    """Deal attractiveness parameters (informational, not in moat score)."""
    revenue_sweet_spot: Tuple[float, float] = (10_000_000, 150_000_000)
    revenue_above_max_score: int = 15
    revenue_in_range_score: int = 25
    strong_margin_threshold: float = 20.0
    strong_margin_score: int = 25
    healthy_margin_threshold: float = 15.0
    healthy_margin_score: int = 15
    ok_margin_threshold: float = 10.0
    ok_margin_score: int = 10


class ThesisConfig(BaseModel):
    """
    Complete investment thesis configuration.

    Drives all scoring, filtering, and LLM analysis in RADAR.
    Load from YAML with ThesisConfig.from_yaml(path).
    """
    # --- Metadata ---
    name: str = "Default Thesis"
    version: str = "1.0"
    description: str = ""

    # --- Moat Pillars ---
    pillars: Dict[str, MoatPillar] = Field(default_factory=dict)

    # --- Certification Evidence ---
    certification_scores: Dict[str, int] = Field(default_factory=dict)
    sovereignty_certs: List[str] = Field(default_factory=list)

    # --- Keywords ---
    sovereignty_keywords: List[str] = Field(default_factory=list)
    known_testing_firms: List[str] = Field(default_factory=list)
    known_platforms: List[str] = Field(default_factory=list)

    # --- Thresholds ---
    tier_thresholds: TierThresholds = Field(default_factory=TierThresholds)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    deal_screening: DealScreening = Field(default_factory=DealScreening)
    business_filters: BusinessFilters = Field(default_factory=BusinessFilters)
    pipeline_filters: PipelineFilters = Field(default_factory=PipelineFilters)

    # --- LLM Prompts ---
    moat_analysis_system_prompt: str = "You are an expert investment analyst. Always respond in valid JSON."
    moat_analysis_prompt_template: str = ""
    semantic_enrichment_prompt_template: str = ""

    # =================================================================
    # COMPUTED PROPERTIES
    # =================================================================

    @property
    def moat_weights(self) -> Dict[str, float]:
        """Flat dict of pillar weights for backward compatibility."""
        return {key: p.weight for key, p in self.pillars.items()}

    @property
    def pillar_names(self) -> List[str]:
        return list(self.pillars.keys())

    def get_cert_score(self, cert_type: str) -> int:
        """Look up the score for a certification type."""
        return self.certification_scores.get(cert_type, 0)

    def is_sovereignty_cert(self, cert_type: str) -> bool:
        return cert_type in self.sovereignty_certs

    @property
    def moat_analysis_prompt(self) -> str:
        """
        Build the full moat analysis prompt by injecting pillar definitions
        into the template. If no template is set, returns a sensible default.
        """
        if self.moat_analysis_prompt_template:
            return self.moat_analysis_prompt_template

        return self._build_default_moat_prompt()

    @property
    def semantic_enrichment_prompt(self) -> str:
        """Build the semantic enrichment prompt from config."""
        if self.semantic_enrichment_prompt_template:
            return self.semantic_enrichment_prompt_template

        return self._build_default_semantic_prompt()

    # =================================================================
    # VALIDATORS
    # =================================================================

    @model_validator(mode="after")
    def validate_weights_sum(self):
        total = sum(p.weight for p in self.pillars.values())
        if self.pillars and abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Pillar weights must sum to 1.0, got {total:.3f}. "
                f"Weights: {self.moat_weights}"
            )
        return self

    # =================================================================
    # LOADERS
    # =================================================================

    @classmethod
    def from_yaml(cls, path: Path) -> "ThesisConfig":
        """Load thesis configuration from a YAML file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Thesis config not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        # Convert pillars from flat dict format
        if "pillars" in raw and isinstance(raw["pillars"], dict):
            for key, val in raw["pillars"].items():
                if isinstance(val, dict) and "name" not in val:
                    val["name"] = key

        return cls(**raw)

    @classmethod
    def load(cls, config_dir: Optional[Path] = None) -> "ThesisConfig":
        """
        Load thesis config with fallback chain:
          1. config/thesis.yaml (private, gitignored)
          2. config/thesis.example.yaml (public, committed)
          3. Built-in defaults
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent.parent / "config"

        private = config_dir / "thesis.yaml"
        example = config_dir / "thesis.example.yaml"

        if private.exists():
            logger.info(f"Loading thesis config from {private}")
            return cls.from_yaml(private)
        elif example.exists():
            logger.info(f"No thesis.yaml found, falling back to {example}")
            return cls.from_yaml(example)
        else:
            logger.warning("No thesis config found, using built-in defaults")
            return cls()

    # =================================================================
    # DEFAULT PROMPT BUILDERS
    # =================================================================

    def _build_default_moat_prompt(self) -> str:
        """Generate a moat analysis prompt from pillar definitions."""
        pillar_sections = []
        for i, (key, pillar) in enumerate(self.pillars.items(), 1):
            section = (
                f"{i}. **{pillar.name}** (0-{pillar.max_raw_score}): {pillar.description}"
            )
            if pillar.prompt_guidance:
                section += f"\n   {pillar.prompt_guidance}"
            pillar_sections.append(section)

        pillar_text = "\n\n".join(pillar_sections)

        # Build expected JSON keys (escape braces for .format() — use {{ }} so they become { } after format)
        json_keys = ", ".join(
            f'"{k}": {{{{ "score": 0-{p.max_raw_score}, "evidence": "Specific evidence" }}}}'
            for k, p in self.pillars.items()
        )

        return f"""You are an investment analyst evaluating a company's competitive moat.

Analyze the following company information and identify VERIFIED EVIDENCE of moat strength.
Do NOT assume moats based on industry — only score based on SPECIFIC EVIDENCE found in the provided information.

**Company:** {{company_name}}
**Description:** {{description}}
**Verified Certifications:** {{certifications}}
**Known Business Relationships:** {{relationship_count}}
**Semantic Telemetry (Prior Analysis):** {{semantic_context}}

**WEBSITE CONTENT ANALYSIS:**
{{raw_text}}

Score each dimension based ONLY on verified evidence.

{pillar_text}

Respond ONLY in valid JSON format:
{{{{
    {json_keys},
    "overall_moat_score": "sum of above",
    "recommended_tier": "Tier 1A/1B/2/Waitlist based on score",
    "reasoning": "One sentence summary citing the strongest evidence found"
}}}}
"""

    def _build_default_semantic_prompt(self) -> str:
        """Generate a semantic enrichment prompt from pillar definitions."""
        dimension_lines = []
        for i, (key, pillar) in enumerate(self.pillars.items(), 1):
            dimension_lines.append(
                f"{i}. {pillar.name} (key: \"{key}\"): {pillar.description} "
                f"Score 0-10."
            )
        dimension_text = "\n".join(dimension_lines)

        # Build a realistic JSON example with SHORT justifications (no "..." placeholders)
        # Use a top-level object with "results" key for json_object mode compatibility
        example_justifications = [
            "ISO 27001 certified",
            "No platform dynamics",
            "UK defence clearance",
            "Third-party auditor",
            "On-site maintenance contracts",
        ]
        import json
        example_pillars = {}
        for i, k in enumerate(self.pillars):
            j = example_justifications[i] if i < len(example_justifications) else "No evidence found"
            example_pillars[k] = {"score": 3, "confidence": 0.6, "band": [1, 5], "justification": j}
        json_example = json.dumps(
            {"results": [{"company": "Example Corp", **example_pillars}]},
            indent=2,
        )

        return f"""Score these companies on investment moat dimensions. For each company and each dimension, return:
- score (integer 0-10)
- confidence (float 0.0-1.0)
- band: [low, high] plausible range
- justification: MAX 5 WORDS. No full sentences.

Dimensions:
{dimension_text}

Return a JSON object with a "results" key containing an array (same order as input).
Keep justification under 5 words. No markdown. No code fences. Only valid JSON.

{json_example}

COMPANIES TO ANALYZE:
{{companies_data}}
"""


    # =================================================================
    # API SUMMARY
    # =================================================================

    def to_summary(self) -> dict:
        """Return a JSON-safe summary for the /config/thesis API endpoint."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "pillars": {
                key: {
                    "name": p.name,
                    "weight": p.weight,
                    "description": p.description,
                    "max_raw_score": p.max_raw_score,
                    "evidence_threshold": p.evidence_threshold,
                }
                for key, p in self.pillars.items()
            },
            "tier_thresholds": self.tier_thresholds.model_dump(),
            "business_filters": {
                "min_revenue": self.business_filters.min_revenue,
                "max_revenue": self.business_filters.max_revenue,
                "target_countries": self.business_filters.target_countries,
            },
            "pipeline_filters": self.pipeline_filters.model_dump(),
        }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

thesis: ThesisConfig = ThesisConfig.load()

# Alias for backward compat (used by src/web/routers/config.py)
thesis_config = thesis
