"""
magnet/llm/protocol.py - LLM Provider Protocol Definition

Defines the abstract protocol for LLM providers, enabling easy swapping
between Claude, OpenAI, Ollama, and other providers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Optional,
    Protocol,
    Type,
    TypeVar,
    Union,
    runtime_checkable,
)
import uuid

from pydantic import BaseModel


T = TypeVar("T")


@dataclass
class LLMResponse:
    """Response from an LLM completion request."""

    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: str = "stop"
    latency_ms: int = 0
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    cached: bool = False
    estimated_cost_usd: float = 0.0

    def __post_init__(self):
        """Ensure usage has expected keys."""
        if "prompt_tokens" not in self.usage:
            self.usage["prompt_tokens"] = 0
        if "completion_tokens" not in self.usage:
            self.usage["completion_tokens"] = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.usage.get("prompt_tokens", 0) + self.usage.get("completion_tokens", 0)


@dataclass
class LLMOptions:
    """Options for LLM completion requests."""

    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stop_sequences: Optional[list] = None
    cache_ttl_seconds: int = 3600
    timeout_seconds: int = 30

    def merge_with_defaults(
        self,
        default_max_tokens: int = 4096,
        default_temperature: float = 0.7,
    ) -> "LLMOptions":
        """Return new options with defaults filled in."""
        return LLMOptions(
            max_tokens=self.max_tokens or default_max_tokens,
            temperature=self.temperature if self.temperature is not None else default_temperature,
            stop_sequences=self.stop_sequences,
            cache_ttl_seconds=self.cache_ttl_seconds,
            timeout_seconds=self.timeout_seconds,
        )


@runtime_checkable
class LLMProviderProtocol(Protocol):
    """
    Protocol for LLM providers.

    All providers must implement these methods to be interchangeable.
    The protocol enables dependency injection and easy testing with mocks.
    """

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        options: Optional[LLMOptions] = None,
    ) -> LLMResponse:
        """
        Generate a completion for the given prompt.

        Args:
            prompt: The user prompt to complete
            system_prompt: Optional system instructions
            options: Optional completion options

        Returns:
            LLMResponse with content and metadata
        """
        ...

    async def complete_json(
        self,
        prompt: str,
        response_model: Type[BaseModel],
        system_prompt: Optional[str] = None,
        options: Optional[LLMOptions] = None,
    ) -> BaseModel:
        """
        Generate a JSON-structured completion validated against a Pydantic model.

        Args:
            prompt: The user prompt (should request JSON output)
            response_model: Pydantic model class for validation
            system_prompt: Optional system instructions
            options: Optional completion options

        Returns:
            Validated Pydantic model instance

        Raises:
            ValidationError: If response doesn't match schema
        """
        ...

    async def complete_with_fallback(
        self,
        prompt: str,
        fallback_fn: Callable[[], T],
        system_prompt: Optional[str] = None,
        options: Optional[LLMOptions] = None,
    ) -> Union[LLMResponse, T]:
        """
        Generate completion with automatic fallback on failure.

        If the LLM call fails (rate limit, cost limit, timeout, etc.),
        the fallback function is called instead.

        Args:
            prompt: The user prompt to complete
            fallback_fn: Function to call if LLM fails
            system_prompt: Optional system instructions
            options: Optional completion options

        Returns:
            LLMResponse on success, or fallback result on failure
        """
        ...

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        options: Optional[LLMOptions] = None,
    ) -> AsyncIterator[str]:
        """
        Stream completion tokens as they're generated.

        Args:
            prompt: The user prompt to complete
            system_prompt: Optional system instructions
            options: Optional completion options

        Yields:
            String chunks as they're generated
        """
        ...

    def is_available(self) -> bool:
        """
        Check if the provider is configured and reachable.

        Returns:
            True if the provider can accept requests
        """
        ...

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for the current session.

        Returns:
            Dict with keys: total_requests, total_tokens, total_cost_usd,
                           cache_hits, cache_misses, errors
        """
        ...

    def estimate_cost(self, prompt: str, max_completion_tokens: int = 1000) -> float:
        """
        Estimate the cost of a completion request.

        Args:
            prompt: The prompt to estimate
            max_completion_tokens: Expected max completion length

        Returns:
            Estimated cost in USD
        """
        ...
