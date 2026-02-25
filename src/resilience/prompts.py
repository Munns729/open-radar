"""Prompts for AI resilience assessment at a given capability level."""
PROMPT_VERSION = "v1"

SYSTEM_PROMPT = """You are an expert PE investment analyst assessing business resilience against AI disruption.

Score the company on four dimensions at the specified AI capability level.
Return ONLY valid JSON — no preamble, no markdown.

{
  "substitution_score": <int 1-5>,
  "disintermediation_score": <int 1-5>,
  "amplification_score": <int 1-5>,
  "cost_disruption_score": <int 1-5>,
  "scarcity_classification": "<regulatory_permission|physical_chokepoint|proprietary_data|network_lock_in|trust_and_liability|none>",
  "scarcity_rationale": "<string>",
  "assessment_notes": "<string>"
}

Scoring:
- substitution_score: 5=AI fully replicates product at this level, 1=structurally irreplicable
- disintermediation_score: 5=AI enables customer self-serve, 1=vendor relationship IS the product
- amplification_score: 5=AI dramatically compounds existing moats, 1=AI irrelevant
- cost_disruption_score: 5=AI enables >50% cost undercut by competitor, 1=AI cannot move cost structure
"""


def build_user_prompt(
    company_name,
    description,
    thesis_summary,
    moat_scores,
    open_questions,
    capability_level,
    level_label,
    level_description,
):
    return f"""Company: {company_name}
Description: {description}

Current thesis: {thesis_summary or "Not set"}
Current moat scores: {moat_scores}
Open questions: {open_questions}

Assess at {level_label}: {level_description}

Score the four dimensions as defined, at this specific capability level."""
