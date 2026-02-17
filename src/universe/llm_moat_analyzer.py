"""
LLM-Based Moat Analyzer.
Extracts evidence-based moat signals from company descriptions using
an OpenAI-compatible LLM (Kimi/Moonshot, OpenAI, etc.).

Prompt template is loaded from the active investment thesis config.
"""
import logging
import json
import re
from typing import Dict, Any, Optional
from openai import OpenAI

from src.core.config import settings
from src.core.thesis import thesis
from src.universe.ops.cost_tracker import cost_tracker

logger = logging.getLogger(__name__)

# OpenAI-compatible client setup
client = OpenAI(
    api_key=settings.moonshot_api_key,
    base_url=settings.kimi_api_base,
)


class LLMMoatAnalyzer:
    """
    Uses LLM to analyze company descriptions and extract evidence-based moat signals.
    Prompt structure is driven by the active thesis config.
    """

    def __init__(self, model: str = None):
        self.model = model or settings.kimi_model

    async def analyze(
        self,
        company_name: str,
        description: str = "",
        raw_text: str = "",
        certifications: list = None,
        relationship_count: int = 0,
        semantic_context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a company's moat using LLM.
        Returns structured moat analysis with scores and evidence.
        """
        certifications = certifications or []
        cert_str = ", ".join(certifications) if certifications else "None known"

        # Truncate raw_text to fit model context
        raw_text = (raw_text or "")[:25000]

        prompt = thesis.moat_analysis_prompt.format(
            company_name=company_name,
            description=description or "No description available",
            raw_text=raw_text or "No website text available",
            certifications=cert_str,
            relationship_count=relationship_count,
            semantic_context=(
                json.dumps(semantic_context, indent=2) if semantic_context else "None"
            ),
        )

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": thesis.moat_analysis_system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1500,
            )

            # Log cost
            if response.usage:
                cost_tracker.log_usage(
                    model=self.model,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    provider="Moonshot/Kimi",
                )

            content = response.choices[0].message.content

            # Parse JSON response
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            else:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

            result = json.loads(content.strip())

            logger.info(
                f"LLM Moat Analysis for {company_name}: "
                f"Score={result.get('overall_moat_score')}, "
                f"Tier={result.get('recommended_tier')}"
            )
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response for {company_name}: {e}", exc_info=True)
            return self._default_result()
        except Exception as e:
            logger.error(f"LLM analysis failed for {company_name}: {e}", exc_info=True)
            return self._default_result()

    def _default_result(self) -> Dict[str, Any]:
        """Return default result on failure, with keys matching thesis pillars."""
        result = {
            key: {"score": 0, "evidence": "Analysis failed"}
            for key in thesis.pillar_names
        }
        result["overall_moat_score"] = 0
        result["recommended_tier"] = "Waitlist"
        result["reasoning"] = "LLM analysis failed"
        return result


# Convenience function
async def analyze_company_moat(
    company_name: str,
    description: str = "",
    raw_text: str = "",
    certifications: list = None,
    relationship_count: int = 0,
) -> Dict[str, Any]:
    """Convenience function to analyze a company's moat."""
    analyzer = LLMMoatAnalyzer()
    return await analyzer.analyze(
        company_name=company_name,
        description=description,
        raw_text=raw_text,
        certifications=certifications,
        relationship_count=relationship_count,
    )
