"""
LLM-Based Moat Analyzer.
Extracts evidence-based moat signals from company descriptions using
an OpenAI-compatible LLM (Kimi/Moonshot, OpenAI, etc.).

Prompt template is loaded from the active investment thesis config.
"""
import json
import logging
import re
import time
from typing import Dict, Any, Optional
from openai import OpenAI

from src.core.config import settings
from src.core.thesis import thesis
from src.universe.ops.cost_tracker import cost_tracker

logger = logging.getLogger(__name__)


def _get_openai_client() -> OpenAI:
    """Build client for heavy analysis. Respects pipeline_context override; else prefers Moonshot."""
    from src.universe.pipeline_context import get_analysis_model

    override = get_analysis_model()
    if override == "ollama":
        base_url = settings.openai_api_base or "http://localhost:11434/v1"
        return OpenAI(api_key=settings.openai_api_key or "ollama", base_url=base_url)
    if override == "moonshot":
        return OpenAI(
            api_key=settings.moonshot_api_key or settings.openai_api_key,
            base_url=settings.kimi_api_base,
        )

    # Auto: prefer Moonshot when key set
    api_key = settings.moonshot_api_key or settings.openai_api_key or "ollama"
    base_url = settings.kimi_api_base if settings.moonshot_api_key else settings.openai_api_base
    return OpenAI(api_key=api_key, base_url=base_url)


def _temperature_for_model(model: str) -> float:
    """Moonshot kimi-k2.5 requires temperature=1; others use 0.1 for deterministic output."""
    from src.universe.pipeline_context import get_analysis_model

    if get_analysis_model() == "ollama":
        return 0.1
    if settings.moonshot_api_key or (model or "").startswith("kimi"):
        return 1.0
    return 0.1


class LLMMoatAnalyzer:
    """
    Uses LLM to analyze company descriptions and extract evidence-based moat signals.
    Prompt structure is driven by the active thesis config.
    """

    def __init__(self, model: str = None):
        from src.universe.pipeline_context import get_analysis_model

        override = get_analysis_model()
        if override == "ollama":
            self.model = model or settings.browsing_model
        else:
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

        template = thesis.moat_analysis_prompt
        subs = {
            "company_name": company_name,
            "description": description or "No description available",
            "raw_text": raw_text or "No website text available",
            "certifications": cert_str,
            "relationship_count": relationship_count,
            "semantic_context": (
                json.dumps(semantic_context, indent=2) if semantic_context else "None"
            ),
        }
        try:
            prompt = template.format(**subs)
        except KeyError:
            # Custom thesis template may have unescaped JSON braces — use replace
            prompt = template
            for k, v in subs.items():
                prompt = prompt.replace("{" + k + "}", str(v))

        try:
            client = _get_openai_client()
            temp = _temperature_for_model(self.model)
            last_err = None
            create_kw = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": thesis.moat_analysis_system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temp,
                "max_tokens": 4096,  # Enough for full JSON (all pillars + evidence + reasoning); 1500 caused finish_reason=length
            }
            # Request JSON output when supported (reduces markdown/prose and empty replies)
            if settings.moonshot_api_key or (self.model or "").startswith("kimi"):
                create_kw["response_format"] = {"type": "json_object"}
            for attempt in range(3):
                try:
                    try:
                        response = client.chat.completions.create(**create_kw)
                    except Exception as fmt_err:
                        if "response_format" in str(fmt_err).lower() or "json" in str(fmt_err).lower():
                            create_kw.pop("response_format", None)
                            response = client.chat.completions.create(**create_kw)
                        else:
                            raise
                    break
                except Exception as err:
                    status = getattr(err, "status_code", None)
                    if status is None and hasattr(err, "response") and err.response is not None:
                        status = getattr(err.response, "status_code", None)
                    if status in (429, 500, 502, 503) and attempt < 2:
                        wait = 2 ** (attempt + 1)
                        logger.warning(f"LLM error {status} for {company_name}, retry in {wait}s (attempt {attempt + 1}/3)")
                        time.sleep(wait)
                    else:
                        raise

            # Log cost
            if response.usage:
                cost_tracker.log_usage(
                    model=self.model,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    provider="OpenAI/Compatible",
                )

            content = response.choices[0].message.content
            raw_content = content if content is not None else ""

            if not raw_content or not raw_content.strip():
                logger.error(
                    f"LLM returned empty response for {company_name}. "
                    f"finish_reason={getattr(response.choices[0].finish_reason, 'value', response.choices[0].finish_reason)}"
                )
                return self._default_result()

            # Parse JSON response: extract object from markdown or raw text
            json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            else:
                if "```json" in raw_content:
                    content = raw_content.split("```json")[1].split("```")[0]
                elif "```" in raw_content:
                    content = raw_content.split("```")[1].split("```")[0]
                else:
                    content = raw_content

            to_parse = content.strip()
            if not to_parse:
                logger.error(
                    f"LLM response had no extractable JSON for {company_name}. "
                    f"Raw (first 500 chars): {raw_content[:500]!r}"
                )
                return self._default_result()

            result = json.loads(to_parse)

            logger.info(
                f"LLM Moat Analysis for {company_name}: "
                f"Score={result.get('overall_moat_score')}, "
                f"Tier={result.get('recommended_tier')}"
            )
            return result

        except json.JSONDecodeError as e:
            try:
                raw_preview = raw_content[:500] if raw_content else "<empty>"
            except NameError:
                raw_preview = "<unknown>"
            logger.error(
                f"Failed to parse LLM response for {company_name}: {e}. "
                f"Raw response (first 500 chars): {raw_preview!r}"
            )
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
