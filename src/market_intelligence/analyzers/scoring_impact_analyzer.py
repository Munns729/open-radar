"""
Analyzes regulatory changes for impact on RADAR's moat scoring configuration.

Takes RegulatoryChange items flagged as moat-relevant and uses LLM analysis
to determine if they warrant updates to thesis config (certification scores,
sovereignty keywords, sovereignty certs, or moat weights).

Outputs structured ScoringConfigRecommendation records for human review.
"""
import json
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.market_intelligence.database import RegulatoryChange, ScoringConfigRecommendation
from src.core.ai_client import ai_client
from src.core.thesis import thesis

logger = logging.getLogger(__name__)


def _current_config_snapshot() -> dict:
    """Build a snapshot of the current scoring config for LLM context."""
    return {
        "certification_scores": dict(thesis.certification_scores),
        "sovereignty_keywords": list(thesis.sovereignty_keywords),
        "sovereignty_certs": list(thesis.sovereignty_certs),
        "moat_weights": dict(thesis.moat_weights),
        "pillar_names": thesis.pillar_names,
    }


class ScoringImpactAnalyzer:
    """
    Analyzes regulatory changes and generates structured recommendations
    to update moat scoring configuration.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def analyze_change(self, change: RegulatoryChange) -> List[ScoringConfigRecommendation]:
        """
        Analyze a single regulatory change for scoring impact.
        May produce 0, 1, or multiple recommendations (e.g. add cert + add keyword).
        """
        config = _current_config_snapshot()

        # Build pillar description from thesis config
        pillar_descriptions = []
        for key, pillar in thesis.pillars.items():
            pillar_descriptions.append(f"- {pillar.name} (weight: {pillar.weight}): {pillar.description}")
        pillar_text = "\n".join(pillar_descriptions)

        system_prompt = (
            "You are a regulatory intelligence analyst for a European private equity fund. "
            f"The fund uses the '{thesis.name}' investment thesis which evaluates companies "
            f"based on {len(thesis.pillars)} structural moat pillars:\n{pillar_text}\n\n"
            "Your job is to determine if a regulatory change warrants updating the fund's "
            "moat scoring configuration."
        )

        prompt = f"""Analyze this regulatory change for impact on our moat scoring system.

## Regulatory Change
- **Title**: {change.title}
- **Jurisdiction**: {change.jurisdiction}
- **Body**: {change.regulatory_body}
- **Type**: {change.change_type}
- **Date**: {change.effective_date}
- **Description**: {(change.description or '')[:3000]}
- **Source**: {change.source_url}

## Current Scoring Configuration
```json
{json.dumps(config, indent=2)}
```

## Your Task
Determine if this regulatory change creates, strengthens, weakens, or removes a compliance barrier that functions as a competitive moat for incumbent vendors.

For each recommendation, specify:
1. **config_target**: Which config section to update (certification_scores, sovereignty_keywords, sovereignty_certs, or moat_weights)
2. **action**: "add", "modify", or "remove"
3. **key**: The specific cert name, keyword, or weight key
4. **recommended_value**: The proposed value (score 0-50 for certs, null for keywords/sovereignty set, weight for moat_weights)
5. **sovereignty_relevant**: If true, the cert is jurisdiction-locked and should ALSO be in sovereignty_certs
6. **reasoning**: Why this change matters for moat scoring
7. **confidence**: "high" (regulation is enacted/enforced), "medium" (regulation is adopted but not yet enforced), "low" (proposal/consultation stage)

Rules:
- Only recommend changes that affect structural defensibility, not routine enforcement actions.
- If a certification already exists in certification_scores at an appropriate level, do not recommend a change.
- If a keyword already exists in sovereignty_keywords, do not recommend adding it.
- moat_weights changes should be extremely rare — only if a pillar's fundamental importance has shifted.
- It is perfectly valid to return zero recommendations if the change has no scoring impact.

Return JSON:
{{
    "has_scoring_impact": true/false,
    "recommendations": [
        {{
            "config_target": "certification_scores",
            "action": "add",
            "key": "DORA Compliant",
            "recommended_value": "45",
            "sovereignty_relevant": true,
            "reasoning": "DORA mandatory for EU financial entities from Jan 2025...",
            "confidence": "high"
        }}
    ]
}}

If there is no scoring impact, return:
{{
    "has_scoring_impact": false,
    "recommendations": []
}}"""

        try:
            response_text = await ai_client.generate(prompt, system_prompt=system_prompt, temperature=0.2)
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response for change {change.id}: {e}")
            return []
        except Exception as e:
            logger.error(f"LLM call failed for change {change.id}: {e}")
            return []

        if not data.get("has_scoring_impact"):
            logger.debug(f"No scoring impact for change {change.id}: {change.title[:60]}")
            return []

        recommendations = []
        valid_targets = {"certification_scores", "sovereignty_keywords", "sovereignty_certs", "moat_weights"}

        for rec_data in data.get("recommendations", []):
            if rec_data.get("config_target") not in valid_targets:
                logger.warning(f"Invalid config_target: {rec_data.get('config_target')}")
                continue

            if rec_data.get("action") not in {"add", "modify", "remove"}:
                logger.warning(f"Invalid action: {rec_data.get('action')}")
                continue

            # Check for duplicates
            existing = await self.session.execute(
                select(ScoringConfigRecommendation).where(
                    ScoringConfigRecommendation.config_target == rec_data["config_target"],
                    ScoringConfigRecommendation.key == rec_data["key"],
                    ScoringConfigRecommendation.status == "pending",
                )
            )
            if existing.scalar_one_or_none():
                logger.info(f"Skipping duplicate pending recommendation: {rec_data['action']} {rec_data['key']}")
                continue

            # Look up current value if modifying
            current_value = None
            if rec_data["action"] == "modify":
                if rec_data["config_target"] == "certification_scores":
                    current_value = str(config["certification_scores"].get(rec_data["key"], ""))
                elif rec_data["config_target"] == "moat_weights":
                    current_value = str(config["moat_weights"].get(rec_data["key"], ""))

            rec = ScoringConfigRecommendation(
                regulatory_change_id=change.id,
                config_target=rec_data["config_target"],
                action=rec_data["action"],
                key=rec_data["key"],
                current_value=current_value,
                recommended_value=str(rec_data.get("recommended_value")) if rec_data.get("recommended_value") is not None else None,
                sovereignty_relevant=rec_data.get("sovereignty_relevant"),
                reasoning=rec_data.get("reasoning", "No reasoning provided"),
                confidence=rec_data.get("confidence", "low"),
                status="pending",
            )
            self.session.add(rec)
            recommendations.append(rec)
            logger.info(f"[ScoringImpact] Recommendation: {rec_data['action']} '{rec_data['key']}' in {rec_data['config_target']} (confidence: {rec_data.get('confidence')})")

        if recommendations:
            await self.session.flush()

        return recommendations

    async def analyze_new_changes(self, changes: List[RegulatoryChange]) -> List[ScoringConfigRecommendation]:
        """
        Analyze a batch of new regulatory changes.
        Only analyses items flagged as moat-relevant (creates_barriers_to_entry = True).
        """
        relevant = [c for c in changes if c.creates_barriers_to_entry]

        if not relevant:
            logger.info("[ScoringImpact] No moat-relevant changes to analyze")
            return []

        logger.info(f"[ScoringImpact] Analyzing {len(relevant)} moat-relevant changes...")

        all_recs = []
        for change in relevant:
            recs = await self.analyze_change(change)
            all_recs.extend(recs)

        await self.session.commit()
        logger.info(f"[ScoringImpact] Generated {len(all_recs)} recommendations")
        return all_recs
