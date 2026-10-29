"""
orchestrator/api_meter.py — Real API Spend Meter & Token Accounting
-------------------------------------------------------------------
Enforces strict spending guardrails:
  - Tracks every input and output token across Groq LLM calls.
  - Calculates real/standard dollar cost per model.
  - Enforces MAX_REAL_API_SPEND_USD (default $2.00). If exceeded, fails loudly.
  - Thread-safe accounting with persistent logging.
"""
import os
import threading
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

MAX_REAL_API_SPEND_USD = float(os.getenv("MAX_REAL_API_SPEND_USD", "2.00"))

# Standard reference pricing per 1M tokens (USD)
# (Used for precise accounting across worker and judge models)
MODEL_PRICING_PER_1M = {
    "openai/gpt-oss-120b": {"input": 0.50, "output": 1.50},
    "qwen/qwen3.8-27b":    {"input": 0.20, "output": 0.60},
    "default":             {"input": 0.30, "output": 1.00},
}


class SpendLimitExceededError(Exception):
    """Raised loudly when cumulative API spend crosses MAX_REAL_API_SPEND_USD."""
    pass


class ApiMeter:
    def __init__(self, max_spend_usd: float = MAX_REAL_API_SPEND_USD):
        self.max_spend_usd = max_spend_usd
        self._lock = threading.Lock()
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_spend_usd = 0.0
        self.call_count = 0
        self.history = []

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = MODEL_PRICING_PER_1M.get(model, MODEL_PRICING_PER_1M["default"])
        cost = (input_tokens * pricing["input"] / 1_000_000.0) + (output_tokens * pricing["output"] / 1_000_000.0)
        return round(cost, 6)

    def record_usage(self, model: str, input_tokens: int, output_tokens: int, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Record token usage from a live LLM call.
        Fails loudly if the call would exceed the configured spending cap.
        """
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        with self._lock:
            new_total_spend = self.total_spend_usd + cost
            if new_total_spend > self.max_spend_usd:
                raise SpendLimitExceededError(
                    f"CRITICAL: API spend cap of ${self.max_spend_usd:.2f} exceeded! "
                    f"Current spend: ${self.total_spend_usd:.4f}, Attempted call cost: ${cost:.4f}, "
                    f"Projected total: ${new_total_spend:.4f}. Call rejected by Spend Guard."
                )

            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.total_spend_usd = new_total_spend
            self.call_count += 1

            record = {
                "call_index": self.call_count,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
                "cumulative_spend_usd": round(self.total_spend_usd, 6),
                "metadata": metadata or {},
            }
            self.history.append(record)

        return record

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "max_spend_usd": self.max_spend_usd,
                "total_spend_usd": round(self.total_spend_usd, 6),
                "remaining_spend_usd": round(max(0.0, self.max_spend_usd - self.total_spend_usd), 6),
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens,
                "total_tokens": self.total_input_tokens + self.total_output_tokens,
                "call_count": self.call_count,
            }

    def reset(self):
        """Reset meters (used in tests)."""
        with self._lock:
            self.total_input_tokens = 0
            self.total_output_tokens = 0
            self.total_spend_usd = 0.0
            self.call_count = 0
            self.history = []


# Global singleton instance
GLOBAL_API_METER = ApiMeter()
