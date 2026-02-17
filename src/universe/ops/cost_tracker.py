"""
Cost tracking for RADAR operations.
Aggregates estimated costs from LLM calls and other paid APIs.
"""
import logging
import threading
from typing import Dict, Any

logger = logging.getLogger(__name__)

class CostTracker:
    """
    Thread-safe singleton to track estimated costs.
    """
    _instance = None
    _lock = threading.Lock()
    
    # Cost per 1k tokens (approximate, USD)
    COSTS = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "moonshot": {"input": 0.004, "output": 0.004}, # Kimi/Moonshot
        "kimi": {"input": 0.0004, "output": 0.0004}, # Kimi latest (cheap)
    }

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CostTracker, cls).__new__(cls)
                    cls._instance.total_cost_usd = 0.0
                    cls._instance.usage_log = []
        return cls._instance

    def log_usage(self, model: str, input_tokens: int, output_tokens: int, provider: str = "unknown"):
        """
        Log token usage and update total cost.
        """
        model_key = next((k for k in self.COSTS.keys() if k in model.lower()), None)
        cost = 0.0
        
        if model_key:
            rates = self.COSTS[model_key]
            cost = (input_tokens / 1000 * rates["input"]) + (output_tokens / 1000 * rates["output"])
        
        with self._lock:
            self.total_cost_usd += cost
            self.usage_log.append({
                "model": model,
                "input": input_tokens,
                "output": output_tokens,
                "cost": cost,
                "provider": provider
            })
            
        # Log periodically or if cost is significant
        if cost > 0.10: # > 10 cents
            logger.info(f"High cost LLM call ({model}): ${cost:.4f}. Total session: ${self.total_cost_usd:.4f}")

    def get_total_cost(self) -> float:
        return self.total_cost_usd

    def reset(self):
        with self._lock:
            self.total_cost_usd = 0.0
            self.usage_log = []

# Global instance
cost_tracker = CostTracker()
