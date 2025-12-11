"""
magnet/llm/safety/cost_tracker.py - Per-Session Cost Tracking

Tracks LLM API costs and enforces per-session spending limits.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger("llm.cost_tracker")


# Claude pricing per 1M tokens (as of 2024)
PRICING: Dict[str, Dict[str, float]] = {
    # Claude 4 models
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    # Claude 3.5 models
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    # Claude 3 models
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    # Default fallback
    "default": {"input": 3.00, "output": 15.00},
}


@dataclass
class CostTracker:
    """
    Tracks LLM API costs for a session.

    Enforces a per-session spending limit to prevent runaway costs.
    """

    max_cost_usd: float = 5.0
    _session_cost: float = field(default=0.0, init=False)
    _request_count: int = field(default=0, init=False)
    _total_input_tokens: int = field(default=0, init=False)
    _total_output_tokens: int = field(default=0, init=False)

    def estimate(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int = 0,
    ) -> float:
        """
        Estimate cost for a request.

        Args:
            model: Model identifier
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens (or estimate)

        Returns:
            Estimated cost in USD
        """
        pricing = PRICING.get(model, PRICING["default"])
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def estimate_prompt_cost(
        self,
        model: str,
        prompt: str,
        max_completion_tokens: int = 1000,
    ) -> float:
        """
        Estimate cost for a prompt string.

        Uses rough token estimation (4 chars per token).

        Args:
            model: Model identifier
            prompt: The prompt text
            max_completion_tokens: Expected max completion tokens

        Returns:
            Estimated cost in USD
        """
        # Rough estimation: ~4 characters per token
        estimated_input_tokens = len(prompt) // 4
        return self.estimate(model, estimated_input_tokens, max_completion_tokens)

    def would_exceed(self, estimated_cost: float) -> bool:
        """
        Check if a request would exceed the budget.

        Args:
            estimated_cost: Estimated cost of the request

        Returns:
            True if request would exceed budget
        """
        return (self._session_cost + estimated_cost) > self.max_cost_usd

    def add(
        self,
        cost: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        """
        Record a completed request's cost.

        Args:
            cost: Actual cost in USD
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
        """
        self._session_cost += cost
        self._request_count += 1
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens

        logger.debug(
            f"Request cost: ${cost:.6f}, "
            f"session total: ${self._session_cost:.4f} / ${self.max_cost_usd:.2f}"
        )

        if self._session_cost > self.max_cost_usd * 0.8:
            logger.warning(
                f"Approaching cost limit: ${self._session_cost:.4f} / ${self.max_cost_usd:.2f} "
                f"({self._session_cost / self.max_cost_usd * 100:.1f}%)"
            )

    def get_remaining_budget(self) -> float:
        """
        Get remaining budget for this session.

        Returns:
            Remaining budget in USD
        """
        return max(0.0, self.max_cost_usd - self._session_cost)

    def get_usage_percent(self) -> float:
        """
        Get percentage of budget used.

        Returns:
            Percentage (0-100+)
        """
        return (self._session_cost / self.max_cost_usd) * 100 if self.max_cost_usd > 0 else 0.0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cost tracking statistics.

        Returns:
            Dict with session_cost, remaining_budget, request_count, etc.
        """
        return {
            "session_cost_usd": round(self._session_cost, 6),
            "max_cost_usd": self.max_cost_usd,
            "remaining_budget_usd": round(self.get_remaining_budget(), 6),
            "usage_percent": round(self.get_usage_percent(), 1),
            "request_count": self._request_count,
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "total_tokens": self._total_input_tokens + self._total_output_tokens,
        }

    def reset(self) -> None:
        """Reset the cost tracker for a new session."""
        self._session_cost = 0.0
        self._request_count = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        logger.info("Cost tracker reset")


def get_model_pricing(model: str) -> Dict[str, float]:
    """
    Get pricing for a specific model.

    Args:
        model: Model identifier

    Returns:
        Dict with input and output pricing per 1M tokens
    """
    return PRICING.get(model, PRICING["default"])
