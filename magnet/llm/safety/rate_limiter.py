"""
magnet/llm/safety/rate_limiter.py - Token Bucket Rate Limiting

Prevents exceeding API rate limits by tracking requests per minute.
Uses token bucket algorithm for smooth rate limiting.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Any

logger = logging.getLogger("llm.rate_limiter")


@dataclass
class RateLimiter:
    """
    Token bucket rate limiter for LLM requests.

    Allows bursting up to bucket capacity, then enforces
    a steady rate of requests per minute.
    """

    requests_per_minute: int = 60
    burst_capacity: int = 10
    _tokens: float = field(init=False)
    _last_refill: float = field(init=False)
    _total_requests: int = field(default=0, init=False)
    _denied_requests: int = field(default=0, init=False)

    def __post_init__(self):
        """Initialize token bucket."""
        self._tokens = float(self.burst_capacity)
        self._last_refill = time.time()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_refill
        self._last_refill = now

        # Calculate tokens to add (rate per second)
        tokens_per_second = self.requests_per_minute / 60.0
        tokens_to_add = elapsed * tokens_per_second

        # Cap at burst capacity
        self._tokens = min(self.burst_capacity, self._tokens + tokens_to_add)

    def allow(self) -> bool:
        """
        Check if a request is allowed and consume a token.

        Returns:
            True if request is allowed, False if rate limited
        """
        self._refill()
        self._total_requests += 1

        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True

        self._denied_requests += 1
        logger.warning(
            f"Rate limit exceeded: {self._denied_requests} denied, "
            f"tokens={self._tokens:.2f}"
        )
        return False

    def wait_time(self) -> float:
        """
        Calculate time to wait before next request is allowed.

        Returns:
            Seconds to wait (0 if request would be allowed now)
        """
        self._refill()

        if self._tokens >= 1.0:
            return 0.0

        # Time to generate 1 token
        tokens_needed = 1.0 - self._tokens
        tokens_per_second = self.requests_per_minute / 60.0
        return tokens_needed / tokens_per_second

    def get_stats(self) -> Dict[str, Any]:
        """
        Get rate limiter statistics.

        Returns:
            Dict with total_requests, denied_requests, current_tokens, denial_rate
        """
        denial_rate = (
            self._denied_requests / self._total_requests
            if self._total_requests > 0
            else 0.0
        )

        return {
            "total_requests": self._total_requests,
            "denied_requests": self._denied_requests,
            "current_tokens": round(self._tokens, 2),
            "denial_rate": round(denial_rate, 3),
            "requests_per_minute": self.requests_per_minute,
        }

    def reset(self) -> None:
        """Reset the rate limiter to initial state."""
        self._tokens = float(self.burst_capacity)
        self._last_refill = time.time()
        self._total_requests = 0
        self._denied_requests = 0
        logger.info("Rate limiter reset")


class AdaptiveRateLimiter(RateLimiter):
    """
    Rate limiter that adapts to API responses.

    Reduces rate when receiving 429 errors, increases when successful.
    """

    min_rpm: int = 10
    max_rpm: int = 120
    _consecutive_successes: int = field(default=0, init=False)

    def on_success(self) -> None:
        """Called when a request succeeds."""
        self._consecutive_successes += 1

        # Increase rate after 10 consecutive successes
        if self._consecutive_successes >= 10:
            new_rpm = min(self.max_rpm, int(self.requests_per_minute * 1.1))
            if new_rpm > self.requests_per_minute:
                logger.info(f"Increasing rate limit: {self.requests_per_minute} -> {new_rpm}")
                self.requests_per_minute = new_rpm
            self._consecutive_successes = 0

    def on_rate_limit(self, retry_after: float = 0) -> None:
        """
        Called when receiving a rate limit error.

        Args:
            retry_after: Suggested wait time from API
        """
        self._consecutive_successes = 0

        # Reduce rate by 25%
        new_rpm = max(self.min_rpm, int(self.requests_per_minute * 0.75))
        if new_rpm < self.requests_per_minute:
            logger.warning(f"Reducing rate limit: {self.requests_per_minute} -> {new_rpm}")
            self.requests_per_minute = new_rpm

        # Drain tokens if we hit a rate limit
        self._tokens = 0
