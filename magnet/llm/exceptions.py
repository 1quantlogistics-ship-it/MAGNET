"""
magnet/llm/exceptions.py - LLM-specific exceptions

Custom exceptions for LLM operations to enable proper error handling
and fallback behavior.
"""

from __future__ import annotations

from typing import Optional


class LLMError(Exception):
    """Base exception for LLM operations."""

    def __init__(
        self,
        message: str,
        recoverable: bool = False,
        request_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.recoverable = recoverable
        self.request_id = request_id

    def __str__(self) -> str:
        parts = [self.message]
        if self.request_id:
            parts.append(f"[request_id={self.request_id}]")
        return " ".join(parts)


class RateLimitError(LLMError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after_seconds: Optional[float] = None,
        request_id: Optional[str] = None,
    ):
        super().__init__(message, recoverable=True, request_id=request_id)
        self.retry_after_seconds = retry_after_seconds


class CostLimitError(LLMError):
    """Raised when session cost limit is exceeded."""

    def __init__(
        self,
        message: str = "Session cost limit exceeded",
        current_cost: float = 0.0,
        limit: float = 0.0,
        request_id: Optional[str] = None,
    ):
        super().__init__(message, recoverable=False, request_id=request_id)
        self.current_cost = current_cost
        self.limit = limit

    def __str__(self) -> str:
        return f"{self.message} (${self.current_cost:.4f} / ${self.limit:.2f})"


class ProviderUnavailableError(LLMError):
    """Raised when the LLM provider is unavailable."""

    def __init__(
        self,
        provider: str,
        message: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        msg = message or f"LLM provider '{provider}' is unavailable"
        super().__init__(msg, recoverable=True, request_id=request_id)
        self.provider = provider


class ValidationError(LLMError):
    """Raised when LLM response doesn't match expected schema."""

    def __init__(
        self,
        message: str = "Response validation failed",
        raw_response: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        super().__init__(message, recoverable=False, request_id=request_id)
        self.raw_response = raw_response


class TimeoutError(LLMError):
    """Raised when LLM request times out."""

    def __init__(
        self,
        timeout_seconds: float,
        request_id: Optional[str] = None,
    ):
        message = f"Request timed out after {timeout_seconds}s"
        super().__init__(message, recoverable=True, request_id=request_id)
        self.timeout_seconds = timeout_seconds


class TransientError(LLMError):
    """Raised for transient errors that may succeed on retry."""

    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
        request_id: Optional[str] = None,
    ):
        super().__init__(message, recoverable=True, request_id=request_id)
        self.original_error = original_error
