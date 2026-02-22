"""
Batch Semantic Enrichment using LLM.

Enriches multiple companies per API call for cost efficiency.
Pillar dimensions are driven by the active thesis config — no hardcoded pillar names.
"""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from anthropic import Anthropic

from src.core.config import settings
from src.core.thesis import thesis
from src.universe.ops.cost_tracker import cost_tracker

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Input-quality helper (previously in discovery/base.py)
# ---------------------------------------------------------------------------

def compute_input_quality(company: Dict[str, Any]) -> float:
    """
    Compute input quality score (0-1) for a company.
    Used to determine if semantic enrichment is worthwhile.
    """
    weights = {
        "website_text":   0.30,
        "certifications": 0.20,
        "revenue_gbp":    0.15,
        "description":    0.15,
        "sector":         0.10,
        "employee_count": 0.10,
    }

    score = 0.0
    for field_name, weight in weights.items():
        val = company.get(field_name)
        if val is not None:
            if isinstance(val, list):
                if len(val) > 0:
                    score += weight
            elif isinstance(val, str):
                if len(val) > 10:
                    score += weight
            elif isinstance(val, (int, float)):
                if val > 0:
                    score += weight
            else:
                score += weight

    return round(score, 2)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SemanticScore:
    """
    Score for a single semantic dimension.
    Matches thesis architecture requirements.
    """
    score: float
    confidence: float
    band: tuple[float, float]
    justification: str
    input_quality: float
    effective_confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "confidence": self.confidence,
            "band": self.band,
            "justification": self.justification,
            "input_quality": self.input_quality,
            "effective_confidence": self.effective_confidence,
        }


@dataclass
class SemanticEnrichmentResult:
    """
    Complete semantic enrichment for a company.

    Pillar scores are stored in a dynamic dict keyed by thesis pillar name,
    so this works with any thesis configuration.
    """
    company_id: int
    pillar_scores: Dict[str, Optional[SemanticScore]] = field(default_factory=dict)
    enrichment_successful: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company_id": self.company_id,
            "pillar_scores": {
                k: v.to_dict() if v else None
                for k, v in self.pillar_scores.items()
            },
            "enrichment_successful": self.enrichment_successful,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Cost estimates (Claude Haiku pricing)
# ---------------------------------------------------------------------------

HAIKU_INPUT_COST  = 0.00025 / 1000  # $0.00025 per 1K input tokens
HAIKU_OUTPUT_COST = 0.00125 / 1000  # $0.00125 per 1K output tokens
AVG_INPUT_TOKENS  = 800             # Per company in batch
AVG_OUTPUT_TOKENS = 400             # Per company in batch


def estimate_batch_cost(num_companies: int, batch_size: int = 10) -> float:
    """Estimate cost for enriching N companies."""
    num_batches = (num_companies + batch_size - 1) // batch_size
    input_tokens  = num_batches * batch_size * AVG_INPUT_TOKENS
    output_tokens = num_batches * batch_size * AVG_OUTPUT_TOKENS
    cost = (input_tokens * HAIKU_INPUT_COST) + (output_tokens * HAIKU_OUTPUT_COST)
    return round(cost, 2)


# ---------------------------------------------------------------------------
# JSON parsing helpers
# ---------------------------------------------------------------------------

def _parse_json_lenient(raw: str) -> list:
    """
    Parse JSON with tolerance for common LLM output errors:
    trailing commas, missing commas between objects, markdown fences.
    """
    import re

    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    try:
        from json_repair import repair_json
        repaired = repair_json(raw)
        parsed = json.loads(repaired)
        if isinstance(parsed, list):
            return parsed
        return [parsed] if isinstance(parsed, dict) else parsed
    except ImportError:
        logger.warning("json_repair not installed — pip install json-repair")
    except Exception as e:
        logger.debug(f"json_repair also failed: {e}")

    cleaned = re.sub(r",\s*([\]\}])", r"\1", raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    cleaned = re.sub(r"\}\s*\{", "},{", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    cleaned = re.sub(r'"\s*\n\s*"', '", "', cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    objects = []
    depth = 0
    start = None
    for i, ch in enumerate(cleaned):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                fragment = cleaned[start:i + 1]
                try:
                    obj = json.loads(fragment)
                    objects.append(obj)
                except json.JSONDecodeError:
                    try:
                        from json_repair import repair_json
                        obj = json.loads(repair_json(fragment))
                        objects.append(obj)
                    except Exception:
                        logger.debug(f"Could not parse object fragment (chars {start}-{i})")
                start = None

    if objects:
        return objects

    logger.error(f"Could not parse JSON from LLM response (length {len(raw)}): {raw[:300]}")
    raise ValueError(f"Could not parse JSON from LLM response (length {len(raw)})")


# ---------------------------------------------------------------------------
# Prompt / formatting helpers
# ---------------------------------------------------------------------------

def _get_batch_prompt_template() -> str:
    """Load the semantic enrichment prompt from the active thesis config."""
    return thesis.semantic_enrichment_prompt


def format_company_for_prompt(company: Dict[str, Any]) -> str:
    """Format a company's data for the enrichment prompt."""
    parts = [f"**{company.get('name', 'Unknown')}** ({company.get('country', 'Unknown')})"]

    if company.get("sector"):
        parts.append(f"Sector: {company['sector']}")
    if company.get("description"):
        parts.append(f"Description: {company['description'][:500]}")
    if company.get("website_text"):
        parts.append(f"Website content: {company['website_text'][:800]}")
    if company.get("certifications"):
        parts.append(f"Certifications: {', '.join(company['certifications'][:10])}")
    if company.get("regulatory_licenses"):
        parts.append(f"Regulatory licenses: {', '.join(company['regulatory_licenses'][:10])}")
    if company.get("patent_count"):
        parts.append(f"Patents: {company['patent_count']}")
    if company.get("revenue_gbp"):
        parts.append(f"Revenue: £{company['revenue_gbp']:,.0f}")

    return "\n".join(parts)


def parse_score_from_response(score_data: Dict, input_quality: float) -> SemanticScore:
    """Parse a single score from LLM response."""
    score       = float(score_data.get("score", 0))
    confidence  = float(score_data.get("confidence", 0.5))
    band        = score_data.get("band", [score - 1, score + 1])
    justification = score_data.get("justification", "")

    return SemanticScore(
        score=score,
        confidence=confidence,
        band=(float(band[0]), float(band[1])),
        justification=justification,
        input_quality=input_quality,
        effective_confidence=min(confidence, input_quality),
    )


def _normalize_company_result(r: Any) -> Optional[Dict[str, Any]]:
    """Normalise LLM response: accept dict or list-of-dicts (merge by pillar key)."""
    if isinstance(r, dict):
        return r
    if isinstance(r, list):
        if len(r) == 1 and isinstance(r[0], dict):
            return r[0]
        merged: Dict[str, Any] = {}
        for item in r:
            if isinstance(item, dict):
                for k, v in item.items():
                    if k not in merged:
                        merged[k] = v if isinstance(v, dict) else {"score": v} if isinstance(v, (int, float)) else {}
        return merged if merged else None
    return None


def _parse_company_result(
    response_data: Dict[str, Any],
    input_quality: float,
) -> Dict[str, Optional[SemanticScore]]:
    """Parse LLM response for one company into thesis-driven pillar scores."""
    pillar_scores: Dict[str, Optional[SemanticScore]] = {}
    for pillar_key in thesis.pillar_names:
        pillar_data = response_data.get(pillar_key, {})
        if pillar_data and isinstance(pillar_data, dict) and pillar_data.get("score", 0) > 0:
            pillar_scores[pillar_key] = parse_score_from_response(pillar_data, input_quality)
        else:
            pillar_scores[pillar_key] = None
    return pillar_scores


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

async def enrich_batch(
    companies: List[Dict[str, Any]],
    anthropic_client: Optional[Anthropic] = None,
    openai_client: Optional[Any] = None,
    openai_model: Optional[str] = None,
    _retry_single: bool = False,
) -> List[SemanticEnrichmentResult]:
    """
    Enrich a batch of companies (up to 10) in one API call.

    Cost: ~$0.001 per company when batched.
    """
    if not companies:
        return []

    content = None

    input_qualities = {
        c.get("id", i): compute_input_quality(c)
        for i, c in enumerate(companies)
    }

    companies_data = "\n\n---\n\n".join(
        f"[Company {i+1}]\n{format_company_for_prompt(c)}"
        for i, c in enumerate(companies)
    )

    prompt_template = _get_batch_prompt_template()
    prompt = prompt_template.replace("{companies_data}", companies_data)

    max_tokens = 4000

    try:
        if anthropic_client and anthropic_client.api_key:
            temperature = 0.3
            response = anthropic_client.messages.create(
                model="claude-haiku-4-20250514",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text

            if response.usage:
                cost_tracker.log_usage(
                    model="claude-3-haiku-20240307",
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    provider="Anthropic",
                )

        elif openai_client:
            model = openai_model or settings.kimi_model
            model_lower = (model or "").lower()
            is_moonshot = model_lower.startswith("kimi")
            is_k2_5 = "k2.5" in model_lower or "k2-5" in model_lower
            temperature = 1.0 if is_k2_5 else (0.5 if is_moonshot else 0.3)
            system_content = (
                "You are a financial analyst. Return ONLY valid JSON. No markdown, no explanations. "
                "Rules: Every object property must be followed by a comma except the last. "
                "Every array element must be followed by a comma except the last. "
                "Double-check your output is valid JSON before responding."
            )
            create_kw: Dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_content},
                    {"role": "user",   "content": prompt},
                ],
                "temperature": temperature,
            }
            if is_moonshot:
                create_kw["response_format"] = {"type": "json_object"}
            try:
                response = await openai_client.chat.completions.create(**create_kw)
            except Exception as e:
                if "response_format" in str(e).lower() or "json" in str(e).lower():
                    create_kw.pop("response_format", None)
                    response = await openai_client.chat.completions.create(**create_kw)
                else:
                    raise
            content = response.choices[0].message.content

        else:
            logger.warning("Skipping semantic enrichment for batch: No Valid LLM Client")
            return []

        json_match = content.find("[")
        json_end   = content.rfind("]") + 1
        if json_match >= 0 and json_end > json_match:
            raw_json = content[json_match:json_end]
            results_json = _parse_json_lenient(raw_json)
        else:
            try:
                parsed = _parse_json_lenient(content)
                if isinstance(parsed, list):
                    results_json = parsed
                elif isinstance(parsed, dict):
                    for v in parsed.values():
                        if isinstance(v, list) and v:
                            results_json = v
                            break
                    else:
                        results_json = [v for v in parsed.values() if isinstance(v, dict)]
                    if not results_json:
                        raise ValueError("No JSON array found in response")
                else:
                    raise ValueError("No JSON array found in response")
            except (ValueError, json.JSONDecodeError):
                raise ValueError("No JSON array found in response")

        results = []
        for i, company in enumerate(companies):
            company_id    = company.get("id", i)
            input_quality = input_qualities.get(company_id, 0.5)

            if i < len(results_json):
                r = results_json[i]
                normalized = _normalize_company_result(r)
                if normalized:
                    pillar_scores = _parse_company_result(normalized, input_quality)
                    results.append(SemanticEnrichmentResult(
                        company_id=company_id,
                        pillar_scores=pillar_scores,
                        enrichment_successful=True,
                    ))
                else:
                    logger.debug("Could not normalize company result: %s", str(r)[:200])
                    results.append(SemanticEnrichmentResult(
                        company_id=company_id,
                        pillar_scores={k: None for k in thesis.pillar_names},
                        enrichment_successful=False,
                        error=f"Unexpected response shape (got {type(r).__name__})",
                    ))
            else:
                results.append(SemanticEnrichmentResult(
                    company_id=company_id,
                    pillar_scores={k: None for k in thesis.pillar_names},
                    enrichment_successful=False,
                    error="Missing from LLM response",
                ))

        return results

    except Exception as e:
        raw_content = content or "<no response>"
        logger.error(
            f"Batch enrichment failed: {e}\n"
            f"  Model: {openai_model or settings.kimi_model}\n"
            f"  Companies: {[c.get('name', '?') for c in companies]}\n"
            f"  Raw response (first 500 chars): {str(raw_content)[:500]}"
        )
        if _retry_single or len(companies) == 1:
            return [
                SemanticEnrichmentResult(
                    company_id=c.get("id", i),
                    pillar_scores={k: None for k in thesis.pillar_names},
                    enrichment_successful=False,
                    error=str(e),
                )
                for i, c in enumerate(companies)
            ]
        logger.warning(f"Batch enrichment failed ({e}), retrying each company individually")
        results = []
        for i, c in enumerate(companies):
            single_result = await enrich_batch(
                [c], anthropic_client, openai_client, openai_model, _retry_single=True
            )
            if single_result and single_result[0].enrichment_successful:
                results.append(single_result[0])
            else:
                err = single_result[0].error if single_result else str(e)
                results.append(SemanticEnrichmentResult(
                    company_id=c.get("id", i),
                    pillar_scores={k: None for k in thesis.pillar_names},
                    enrichment_successful=False,
                    error=err,
                ))
            if i + 1 < len(companies):
                await asyncio.sleep(0.3)
        return results


async def enrich_companies_batched(
    companies: List[Dict[str, Any]],
    anthropic_client: Optional[Anthropic] = None,
    openai_client: Optional[Any] = None,
    openai_model: Optional[str] = None,
    batch_size: int = None,
) -> List[SemanticEnrichmentResult]:
    """
    Enrich a list of companies in batches.

    Args:
        companies: List of company dicts with enrichment data.
        batch_size: Companies per API call. Auto-detected if None
                    (10 for Anthropic, 2 for Moonshot/OpenAI).
    """
    if batch_size is None:
        if anthropic_client and anthropic_client.api_key:
            batch_size = 10
        else:
            batch_size = 2
        logger.info(f"Auto-selected batch_size={batch_size}")

    all_results = []

    for i in range(0, len(companies), batch_size):
        batch = companies[i:i + batch_size]
        logger.info(
            f"Enriching batch {i // batch_size + 1}/"
            f"{(len(companies) + batch_size - 1) // batch_size}"
        )
        results = await enrich_batch(batch, anthropic_client, openai_client, openai_model)
        all_results.extend(results)

        if i + batch_size < len(companies):
            await asyncio.sleep(0.5)

    return all_results


def should_enrich(
    company: Dict[str, Any],
    thesis_filters: Optional[Dict] = None,
    min_input_quality: float = 0.3,
) -> bool:
    """
    Decide if a company should be semantically enriched.

    Only enrich if:
    1. Passes thesis filters (if provided)
    2. Has sufficient input quality (> min_input_quality)
    """
    input_quality = compute_input_quality(company)
    if input_quality < min_input_quality:
        return False

    if thesis_filters:
        if "countries" in thesis_filters:
            if company.get("country") not in thesis_filters["countries"]:
                return False
        if "sectors" in thesis_filters:
            if company.get("sector") not in thesis_filters["sectors"]:
                return False
        if "min_revenue" in thesis_filters:
            revenue = company.get("revenue_gbp", 0)
            if revenue and revenue < thesis_filters["min_revenue"]:
                return False

    return True
