"""
magnet/llm/safety/metrics.py - LLM Observability and Logging

Tracks metrics for LLM requests: latency, token usage, errors, etc.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger("llm.metrics")


@dataclass
class RequestMetric:
    """Metrics for a single LLM request."""

    request_id: str
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cached: bool
    success: bool
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class LLMMetrics:
    """
    Collects and aggregates LLM usage metrics.

    Maintains a rolling window of recent requests for analysis.
    """

    def __init__(self, window_size: int = 1000):
        """
        Initialize metrics collector.

        Args:
            window_size: Number of recent requests to keep for analysis
        """
        self.window_size = window_size
        self._requests: Deque[RequestMetric] = deque(maxlen=window_size)
        self._total_requests = 0
        self._total_errors = 0
        self._total_tokens = 0
        self._total_cost = 0.0
        self._total_latency_ms = 0

    def record(
        self,
        request_id: str,
        model: str,
        latency_ms: int,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        cached: bool = False,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """
        Record metrics for a completed request.

        Args:
            request_id: Unique request identifier
            model: Model used
            latency_ms: Request latency in milliseconds
            input_tokens: Input token count
            output_tokens: Output token count
            cost_usd: Cost in USD
            cached: Whether response was from cache
            success: Whether request succeeded
            error: Error message if failed
        """
        metric = RequestMetric(
            request_id=request_id,
            model=model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            cached=cached,
            success=success,
            error=error,
        )

        self._requests.append(metric)
        self._total_requests += 1
        self._total_tokens += metric.total_tokens
        self._total_cost += cost_usd
        self._total_latency_ms += latency_ms

        if not success:
            self._total_errors += 1

        # Log at appropriate level
        if success:
            logger.debug(
                f"LLM request {request_id}: "
                f"latency={latency_ms}ms, "
                f"tokens={metric.total_tokens}, "
                f"cost=${cost_usd:.6f}, "
                f"cached={cached}"
            )
        else:
            logger.warning(
                f"LLM request {request_id} failed: "
                f"error={error}, "
                f"latency={latency_ms}ms"
            )

    def record_from_response(
        self,
        request_id: str,
        model: str,
        latency_ms: int,
        usage: Dict[str, int],
        cost_usd: float,
        cached: bool = False,
    ) -> None:
        """
        Record metrics from an LLM response.

        Args:
            request_id: Unique request identifier
            model: Model used
            latency_ms: Request latency
            usage: Usage dict with prompt_tokens and completion_tokens
            cost_usd: Cost in USD
            cached: Whether response was from cache
        """
        self.record(
            request_id=request_id,
            model=model,
            latency_ms=latency_ms,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            cost_usd=cost_usd,
            cached=cached,
            success=True,
        )

    def record_error(
        self,
        request_id: str,
        model: str,
        latency_ms: int,
        error: str,
    ) -> None:
        """
        Record a failed request.

        Args:
            request_id: Unique request identifier
            model: Model used
            latency_ms: Latency until error
            error: Error message
        """
        self.record(
            request_id=request_id,
            model=model,
            latency_ms=latency_ms,
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            cached=False,
            success=False,
            error=error,
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get aggregated statistics.

        Returns:
            Dict with total and average metrics
        """
        recent = list(self._requests)

        if not recent:
            return {
                "total_requests": 0,
                "total_errors": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "avg_latency_ms": 0,
                "error_rate": 0.0,
                "cache_hit_rate": 0.0,
            }

        successful = [r for r in recent if r.success]
        cached = [r for r in successful if r.cached]

        return {
            "total_requests": self._total_requests,
            "total_errors": self._total_errors,
            "total_tokens": self._total_tokens,
            "total_cost_usd": round(self._total_cost, 6),
            "avg_latency_ms": round(
                self._total_latency_ms / self._total_requests
                if self._total_requests > 0
                else 0
            ),
            "error_rate": round(
                self._total_errors / self._total_requests
                if self._total_requests > 0
                else 0.0,
                3,
            ),
            "cache_hit_rate": round(
                len(cached) / len(recent) if recent else 0.0, 3
            ),
            "recent_window_size": len(recent),
        }

    def get_recent_requests(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent requests for debugging.

        Args:
            count: Number of recent requests to return

        Returns:
            List of request dicts
        """
        recent = list(self._requests)[-count:]
        return [
            {
                "request_id": r.request_id,
                "model": r.model,
                "latency_ms": r.latency_ms,
                "tokens": r.total_tokens,
                "cost_usd": r.cost_usd,
                "cached": r.cached,
                "success": r.success,
                "error": r.error,
                "timestamp": r.timestamp,
            }
            for r in recent
        ]

    def get_latency_percentiles(self) -> Dict[str, int]:
        """
        Calculate latency percentiles from recent requests.

        Returns:
            Dict with p50, p90, p95, p99 latencies in ms
        """
        latencies = sorted(r.latency_ms for r in self._requests if r.success)

        if not latencies:
            return {"p50": 0, "p90": 0, "p95": 0, "p99": 0}

        def percentile(data: List[int], p: float) -> int:
            idx = int(len(data) * p)
            return data[min(idx, len(data) - 1)]

        return {
            "p50": percentile(latencies, 0.50),
            "p90": percentile(latencies, 0.90),
            "p95": percentile(latencies, 0.95),
            "p99": percentile(latencies, 0.99),
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self._requests.clear()
        self._total_requests = 0
        self._total_errors = 0
        self._total_tokens = 0
        self._total_cost = 0.0
        self._total_latency_ms = 0
        logger.info("LLM metrics reset")
