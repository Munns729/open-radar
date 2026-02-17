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

from .base import compute_input_quality
from src.core.thesis import thesis
from src.universe.ops.cost_tracker import cost_tracker

logger = logging.getLogger(__name__)


@dataclass
class SemanticScore:
    """
    Score for a single semantic dimension.
    Matches thesis architecture requirements.
    """
    score: float                    # 0-10
    confidence: float               # LLM self-reported (0-1)
    band: tuple[float, float]       # Plausible range
    justification: str
    input_quality: float            # Computed PRE-LLM
    effective_confidence: float     # min(confidence, input_quality)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "confidence": self.confidence,
            "band": self.band,
            "justification": self.justification,
            "input_quality": self.input_quality,
            "effective_confidence": self.effective_confidence
        }


@dataclass
class SemanticEnrichmentResult:
    """
    Complete semantic enrichment for a company.

    Pillar scores are stored in a dynamic dict keyed by thesis pillar name,
    so this works with any thesis configuration (not just Picard 5-pillar).
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
            "error": self.error
        }


# Cost estimates (Claude Haiku pricing)
HAIKU_INPUT_COST = 0.00025 / 1000   # $0.00025 per 1K input tokens
HAIKU_OUTPUT_COST = 0.00125 / 1000  # $0.00125 per 1K output tokens
AVG_INPUT_TOKENS = 800              # Per company in batch
AVG_OUTPUT_TOKENS = 400             # Per company in batch


def estimate_batch_cost(num_companies: int, batch_size: int = 10) -> float:
    """Estimate cost for enriching N companies."""
    num_batches = (num_companies + batch_size - 1) // batch_size

    input_tokens = num_batches * batch_size * AVG_INPUT_TOKENS
    output_tokens = num_batches * batch_size * AVG_OUTPUT_TOKENS

    cost = (input_tokens * HAIKU_INPUT_COST) + (output_tokens * HAIKU_OUTPUT_COST)
    return round(cost, 2)


def _get_batch_prompt_template() -> str:
    """Load the semantic enrichment prompt from the active thesis config."""
    return thesis.semantic_enrichment_prompt


def format_company_for_prompt(company: Dict[str, Any]) -> str:
    """Format a company's data for the enrichment prompt."""
    parts = [f"**{company.get('name', 'Unknown')}** ({company.get('country', 'Unknown')})"]

    if company.get('sector'):
        parts.append(f"Sector: {company['sector']}")

    if company.get('description'):
        desc = company['description'][:500]
        parts.append(f"Description: {desc}")

    if company.get('website_text'):
        text = company['website_text'][:800]
        parts.append(f"Website content: {text}")

    if company.get('certifications'):
        certs = ", ".join(company['certifications'][:10])
        parts.append(f"Certifications: {certs}")

    if company.get('regulatory_licenses'):
        licenses = ", ".join(company['regulatory_licenses'][:10])
        parts.append(f"Regulatory licenses: {licenses}")

    if company.get('patent_count'):
        parts.append(f"Patents: {company['patent_count']}")

    if company.get('revenue_gbp'):
        parts.append(f"Revenue: £{company['revenue_gbp']:,.0f}")

    return "\n".join(parts)


def parse_score_from_response(score_data: Dict, input_quality: float) -> SemanticScore:
    """Parse a single score from LLM response."""
    score = float(score_data.get("score", 0))
    confidence = float(score_data.get("confidence", 0.5))
    band = score_data.get("band", [score - 1, score + 1])
    justification = score_data.get("justification", "")

    return SemanticScore(
        score=score,
        confidence=confidence,
        band=(float(band[0]), float(band[1])),
        justification=justification,
        input_quality=input_quality,
        effective_confidence=min(confidence, input_quality),
    )


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


async def enrich_batch(
    companies: List[Dict[str, Any]],
    anthropic_client: Optional[Anthropic] = None,
    openai_client: Optional[Any] = None,
) -> List[SemanticEnrichmentResult]:
    """
    Enrich a batch of companies (up to 10) in one API call.

    Cost: ~$0.001 per company when batched.
    """
    if not companies:
        return []

    # Compute input quality for each company
    input_qualities = {
        c.get('id', i): compute_input_quality(c)
        for i, c in enumerate(companies)
    }

    # Format companies for prompt
    companies_data = "\n\n---\n\n".join(
        f"[Company {i+1}]\n{format_company_for_prompt(c)}"
        for i, c in enumerate(companies)
    )

    prompt_template = _get_batch_prompt_template()
    prompt = prompt_template.format(companies_data=companies_data)

    temperature = 0.3
    max_tokens = 4000

    try:
        # Prefer Anthropic if available
        if anthropic_client and anthropic_client.api_key:
            response = anthropic_client.messages.create(
                model="claude-haiku-4-20250514",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.content[0].text

            if response.usage:
                cost_tracker.log_usage(
                    model="claude-3-haiku-20240307",
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    provider="Anthropic"
                )

        # Fallback to OpenAI/Moonshot
        elif openai_client:
            response = await openai_client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=[
                    {"role": "system", "content": "You are a financial analyst. Return ONLY JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature
            )
            content = response.choices[0].message.content

        else:
            logger.warning("Skipping semantic enrichment for batch: No Valid LLM Client")
            return []

        # Find JSON array in response
        json_match = content.find('[')
        json_end = content.rfind(']') + 1
        if json_match == -1 or json_end == 0:
            raise ValueError("No JSON array found in response")

        results_json = json.loads(content[json_match:json_end])

        # Parse results — pillar keys come from thesis config
        results = []
        for i, company in enumerate(companies):
            company_id = company.get('id', i)
            input_quality = input_qualities.get(company_id, 0.5)

            if i < len(results_json):
                r = results_json[i]
                pillar_scores = _parse_company_result(r, input_quality)
                results.append(SemanticEnrichmentResult(
                    company_id=company_id,
                    pillar_scores=pillar_scores,
                    enrichment_successful=True,
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
        logger.error(f"Batch enrichment failed: {e}")
        return [
            SemanticEnrichmentResult(
                company_id=c.get('id', i),
                pillar_scores={k: None for k in thesis.pillar_names},
                enrichment_successful=False,
                error=str(e),
            )
            for i, c in enumerate(companies)
        ]


async def enrich_companies_batched(
    companies: List[Dict[str, Any]],
    anthropic_client: Optional[Anthropic] = None,
    openai_client: Optional[Any] = None,
    batch_size: int = 10,
) -> List[SemanticEnrichmentResult]:
    """
    Enrich a list of companies in batches.

    Args:
        companies: List of company dicts with enrichment data
        anthropic_client: Anthropic client instance
        batch_size: Companies per API call (default: 10)

    Returns:
        List of SemanticEnrichmentResult for each company
    """
    all_results = []

    for i in range(0, len(companies), batch_size):
        batch = companies[i:i + batch_size]
        logger.info(f"Enriching batch {i//batch_size + 1}/{(len(companies) + batch_size - 1)//batch_size}")

        results = await enrich_batch(batch, anthropic_client, openai_client)
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
    3. Not recently enriched (TODO: add caching)
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
