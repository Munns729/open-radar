"""
Pipeline context for model selection.

Allows the pipeline to override which LLM is used for analysis (semantic enrichment,
moat scoring) without changing global settings. Used when --analysis-model is set.
"""
import contextvars
from typing import Optional

# "ollama" | "moonshot" | None (use settings)
_analysis_model: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "pipeline_analysis_model", default=None
)


def set_analysis_model(mode: Optional[str]) -> None:
    """Set analysis model override for this context. None = use settings."""
    _analysis_model.set(mode)


def get_analysis_model() -> Optional[str]:
    """Get current analysis model override."""
    try:
        return _analysis_model.get()
    except LookupError:
        return None
