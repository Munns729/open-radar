"""
Moat Scoring Algorithm for Universe Scanner.
Implements configurable investment thesis scoring via ThesisConfig.

All pillar definitions, weights, certification scores, and tier thresholds
are loaded from config/thesis.yaml (or config/thesis.example.yaml).
"""
import asyncio
import logging
from typing import List, Any, Dict, Optional

from src.core.models import CompanyTier
from src.core.thesis import thesis
from src.universe.llm_moat_analyzer import LLMMoatAnalyzer

logger = logging.getLogger(__name__)


class MoatScorer:
    """
    Calculates 0-100 moat score based on the active investment thesis.

    Pillar definitions, weights, certifications, and tier thresholds are
    all driven by ``src.core.thesis.thesis`` (loaded from YAML config).

    Scoring combines:
      - Hard evidence: certifications, known firms/platforms, graph signals
      - LLM evidence: extracted from company description + website text
      - Penalties: risk keywords, declining revenue
    """

    @classmethod
    async def score_with_llm(
        cls,
        company: Any,
        certifications: List[Any],
        graph_signals: Dict[str, Any] = None,
        raw_website_text: str = ""
    ) -> int:
        """Score a company using LLM analysis combined with objective signals."""

        # Snapshot previous scores for audit trail
        company._previous_moat_score = company.moat_score
        company._previous_moat_attributes = company.moat_attributes

        # --- Gather inputs ---
        cert_types = [c.certification_type for c in certifications if c.certification_type]
        description = company.description or ""
        name_lower = (company.name or "").lower()
        relationship_count = (
            len(getattr(company, 'relationships_as_a', []))
            + len(getattr(company, 'relationships_as_b', []))
        )

        # --- Semantic prior ---
        semantic_data = (
            company.moat_analysis.get("semantic")
            if isinstance(company.moat_analysis, dict)
            else None
        )

        # --- LLM analysis ---
        logger.debug(f"Deep Analysis via LLM (Context: {'Semantic' if semantic_data else 'None'}) for {company.name}")
        analyzer = LLMMoatAnalyzer()
        llm_result = await analyzer.analyze(
            company_name=company.name,
            description=description,
            raw_text=raw_website_text,
            certifications=cert_types,
            relationship_count=relationship_count,
            semantic_context=semantic_data,
        )

        # --- Build moat_attrs from thesis pillars ---
        moat_attrs = {
            key: {"present": False, "justification": "", "score": 0}
            for key in thesis.pillar_names
        }
        moat_attrs["deal_screening"] = {
            "financial_fit": {"score": 0, "factors": []},
            "competitive_position": {"score": 0, "factors": []},
        }

        raw_scores: Dict[str, int] = {}
        combined_text = (description + " " + raw_website_text).lower()

        for pillar_key, pillar in thesis.pillars.items():
            # --- Collect hard evidence per pillar ---
            hard_score = 0

            if pillar_key == "regulatory":
                for cert in cert_types:
                    hard_score = max(hard_score, thesis.get_cert_score(cert))

            elif pillar_key == "network":
                if graph_signals and graph_signals.get("is_central_hub"):
                    hard_score = max(hard_score, 60)
                if any(p in name_lower for p in thesis.known_platforms):
                    hard_score = max(hard_score, 70)

            elif pillar_key == "geographic":
                # Sovereignty certifications
                for cert in cert_types:
                    if thesis.is_sovereignty_cert(cert):
                        hard_score = max(hard_score, thesis.get_cert_score(cert))
                # Sovereignty keywords
                if any(kw in combined_text for kw in thesis.sovereignty_keywords):
                    hard_score = max(hard_score, 50)

            elif pillar_key == "liability":
                if any(t in name_lower for t in thesis.known_testing_firms):
                    hard_score = max(hard_score, 60)

            # Physical and any custom pillars: LLM-only (hard_score stays 0)

            # --- LLM evidence ---
            llm_pillar = llm_result.get(pillar_key, {})
            llm_score = llm_pillar.get("score", 0)

            # --- Combine: best of hard evidence or LLM ---
            pillar_score = max(hard_score, llm_score)
            raw_scores[pillar_key] = pillar_score

            if pillar_score >= pillar.evidence_threshold:
                moat_attrs[pillar_key] = {
                    "present": True,
                    "justification": llm_pillar.get("evidence", "Evidence found"),
                    "score": pillar_score,
                }

        # === DEAL SCREENING (informational, not in moat score) ===
        ds = thesis.deal_screening
        fin_score, fin_factors = 0, []
        rev = getattr(company, "revenue_gbp", None)
        if rev:
            lo, hi = ds.revenue_sweet_spot
            if lo <= rev <= hi:
                fin_score += ds.revenue_in_range_score
                fin_factors.append(f"Revenue fit (£{rev / 1e6:.1f}M)")
            elif rev > hi:
                fin_score += ds.revenue_above_max_score
                fin_factors.append(f"Revenue >£{hi / 1e6:.0f}M")

        margin = getattr(company, "ebitda_margin", None)
        if margin:
            margin = float(margin)
            if margin >= ds.strong_margin_threshold:
                fin_score += ds.strong_margin_score
                fin_factors.append(f"Strong margins ({margin}%)")
            elif margin >= ds.healthy_margin_threshold:
                fin_score += ds.healthy_margin_score
                fin_factors.append(f"Healthy margins ({margin}%)")
            elif margin >= ds.ok_margin_threshold:
                fin_score += ds.ok_margin_score

        if fin_score > 0:
            moat_attrs["deal_screening"]["financial_fit"] = {
                "score": fin_score,
                "factors": fin_factors,
            }

        comp_score, comp_factors = 0, []
        mkt_share = getattr(company, "market_share", None)
        if mkt_share and float(mkt_share) >= 20:
            comp_score += 10
            comp_factors.append("Market Leader (>20%)")
        comp_count = getattr(company, "competitor_count", None)
        if comp_count is not None and int(comp_count) < 5:
            comp_score += 5
            comp_factors.append("Niche/Concentrated")
        growth = getattr(company, "market_growth_rate", None)
        if growth and float(growth) > 5:
            comp_score += 5
            comp_factors.append("Tailwind Growth")
        if comp_score > 0:
            moat_attrs["deal_screening"]["competitive_position"] = {
                "score": comp_score,
                "factors": comp_factors,
            }

        # === WEIGHTED SCORING AGGREGATION ===
        score = 0.0
        weights = thesis.moat_weights
        for pillar_key, raw in raw_scores.items():
            pillar = thesis.pillars[pillar_key]
            if raw < pillar.evidence_threshold:
                continue
            weight = weights[pillar_key]
            max_contribution = weight * 100
            score += min(raw * weight, max_contribution)

        # === PENALTIES ===
        risk = thesis.risk
        penalties = 0
        risk_factors = []

        rev_growth = getattr(company, "revenue_growth", None)
        if rev_growth and rev_growth < 0:
            penalties += risk.declining_revenue_penalty
            risk_factors.append("Declining Revenue")

        text_lower = (raw_website_text or "").lower()[:10000]
        for kw in risk.keywords:
            if kw in text_lower:
                penalties += 10
                risk_factors.append(f"Risk keyword: {kw}")
                if penalties >= risk.max_penalty:
                    penalties = risk.max_penalty
                    break

        penalties = min(penalties, risk.max_penalty)
        if penalties > 0:
            score -= penalties
            moat_attrs["risk_penalty"] = {
                "present": True,
                "justification": ", ".join(risk_factors),
                "score": -penalties,
            }
            logger.info(f"Applied penalty of {penalties} to {company.name}: {risk_factors}")

        # === ASSIGN ===
        score = min(int(score), 100)
        company.moat_score = score
        company.moat_attributes = moat_attrs
        company.moat_analysis = {
            "llm_result": llm_result,
            "reasoning": llm_result.get("reasoning", ""),
            "thesis": thesis.name,
            "thesis_version": thesis.version,
            "weights_applied": dict(weights),
            "raw_dimension_scores": raw_scores,
            "weighted_contributions": {
                k: round(min(raw * weights[k], weights[k] * 100), 1)
                for k, raw in raw_scores.items()
            },
            "penalties_applied": penalties,
            "weighted_score": score,
            "deal_screening_total": (
                moat_attrs["deal_screening"]["financial_fit"]["score"]
                + moat_attrs["deal_screening"]["competitive_position"]["score"]
            ),
            "dimension_sum": sum(raw_scores.values()),
        }

        cls._assign_tier(company, score)
        logger.debug(f"Classification -> Tier {company.tier} (Score: {score})")
        return score

    @staticmethod
    def _assign_tier(company: Any, score: int):
        """Assign tier based on thesis thresholds."""
        t = thesis.tier_thresholds
        if score >= t.tier_1a:
            company.tier = CompanyTier.TIER_1A
        elif score >= t.tier_1b:
            company.tier = CompanyTier.TIER_1B
        elif score >= t.tier_2:
            company.tier = CompanyTier.TIER_2
        else:
            company.tier = CompanyTier.WAITLIST
