"""
magnet/llm - Unified LLM Provider Layer

Provides a protocol-based abstraction for LLM providers (Claude, Ollama, etc.)
with built-in safety features: caching, rate limiting, cost tracking, and fallbacks.

Usage:
    from magnet.llm import create_llm_provider, LLMProviderProtocol
    from magnet.bootstrap.config import get_config

    config = get_config()
    llm = create_llm_provider(config.llm)

    # With fallback
    response = await llm.complete_with_fallback(
        prompt="Generate a clarification question",
        fallback_fn=lambda: "Please clarify your requirements"
    )
"""

from .protocol import (
    LLMProviderProtocol,
    LLMResponse,
    LLMOptions,
)
from .provider_factory import create_llm_provider
from .exceptions import (
    LLMError,
    RateLimitError,
    CostLimitError,
    ProviderUnavailableError,
)

__all__ = [
    # Protocol
    "LLMProviderProtocol",
    "LLMResponse",
    "LLMOptions",
    # Factory
    "create_llm_provider",
    # Exceptions
    "LLMError",
    "RateLimitError",
    "CostLimitError",
    "ProviderUnavailableError",
]
