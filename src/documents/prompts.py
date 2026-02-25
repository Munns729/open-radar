"""LLM prompts for document extraction."""

EXTRACT_PROMPT_VERSION = "v1"

EXTRACTION_SYSTEM_PROMPT = """You are a senior PE investment analyst. Extract structured intelligence from the document.

Return ONLY valid JSON — no preamble, no markdown fences.

{
  "moat_evidence": {
    "<pillar_name>": {
      "direction": "<strengthens|weakens|neutral>",
      "evidence": "<1-2 sentences>",
      "confidence": <0.0-1.0>,
      "key_quote": "<exact quote max 100 chars>"
    }
  },
  "resilience_evidence": {
    "<1|2|3|4>": {
      "substitution": {"direction": "<resilient|vulnerable|neutral>", "confidence": <0.0-1.0>},
      "disintermediation": {"direction": "<resilient|vulnerable|neutral>", "confidence": <0.0-1.0>}
    }
  },
  "thesis_elements": ["<string>"],
  "tier_signal": {
    "direction": "<upgrade|downgrade|maintain>",
    "rationale": "<string>",
    "confidence": <0.0-1.0>
  },
  "scarcity_signals": ["<string>"],
  "open_questions_raised": ["<string>"],
  "red_flags": ["<string>"]
}

Rules:
- Only populate moat_evidence for pillars explicitly evidenced in the document
- Confidence = how strongly the document supports this assessment (not general knowledge)
- red_flags: regulatory risk, customer concentration >30%, key-person dependency, declining metrics, litigation
- Use null for fields with no evidence (not empty dict/list)
"""


def build_extraction_prompt(
    company_name: str,
    document_type: str,
    raw_text: str | None,
    current_thesis: str | None,
    current_moat_scores: dict,
    open_questions: list | None,
    max_text_chars: int = 80000,
) -> str:
    truncated = (raw_text or "")[:max_text_chars]
    return f"""Company: {company_name}
Document type: {document_type}

Current thesis: {current_thesis or "Not set"}
Current moat scores: {current_moat_scores}
Open questions: {open_questions or []}

--- DOCUMENT ---
{truncated}
--- END ---

Extract intelligence as specified."""
