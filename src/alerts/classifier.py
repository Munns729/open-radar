"""
Alert classifier: assigns risk_level and context_summary for investment relevance.
"""
from datetime import datetime

from src.canon.service import get_canon
from src.core.ai_client import ai_client


HIGH_PHRASES = ["Series B", "Series C", "Series D", "acquisition"]
RELEVANT_ALERT_TYPES = ("funding", "leadership_change")


async def classify_alert(alert_type: str, message: str, company_id: int) -> tuple[str, str]:
    """
    Returns (risk_level, context_summary).
    risk_level: "low" | "elevated" | "high"
    """
    canon = await get_canon(company_id)
    msg_lower = message.lower()

    # --- Risk level (priority order) ---
    risk_level = "low"

    if canon is None and alert_type in RELEVANT_ALERT_TYPES:
        risk_level = "high"
    elif canon is not None and canon.coverage_status == "stale" and alert_type in RELEVANT_ALERT_TYPES:
        risk_level = "high"
    elif any(phrase.lower() in msg_lower for phrase in HIGH_PHRASES):
        risk_level = "high"
    elif alert_type == "leadership_change":
        risk_level = "elevated"
    elif canon is not None and canon.last_refreshed_at:
        if (datetime.utcnow() - canon.last_refreshed_at).days <= 30:
            risk_level = "elevated"

    # --- Context summary via AI ---
    system_prompt = (
        "You are an investment intelligence assistant. In 1-2 sentences, "
        "explain why this alert is relevant to the investment thesis for this company. "
        "Be specific and concrete. Do not repeat the alert verbatim."
    )
    prompt_parts = [f"Alert type: {alert_type}", f"Message: {message}"]
    if canon is not None:
        if canon.thesis_summary:
            prompt_parts.append(f"Thesis summary: {canon.thesis_summary}")
        if canon.current_tier:
            prompt_parts.append(f"Current tier: {canon.current_tier}")
        if canon.open_questions:
            first_three = (canon.open_questions or [])[:3]
            prompt_parts.append(f"Open questions: {first_three}")
    prompt = "\n".join(prompt_parts)

    try:
        context_summary = await ai_client.generate(prompt, system_prompt=system_prompt, temperature=0.3)
        context_summary = (context_summary or "").strip() or None
    except Exception:
        context_summary = message[:200] if message else None

    return risk_level, context_summary
