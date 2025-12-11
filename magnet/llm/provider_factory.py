"""
magnet/llm/provider_factory.py - LLM Provider Factory

Factory function to create LLM providers based on configuration.
Supports easy switching between Anthropic (Claude) and local (Ollama) providers.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Union

from .protocol import LLMProviderProtocol
from .providers.anthropic import AnthropicProvider
from .providers.local import LocalProvider
from .exceptions import ProviderUnavailableError

logger = logging.getLogger("llm.factory")

# Provider type aliases
PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_LOCAL = "local"
PROVIDER_OLLAMA = "ollama"  # Alias for local

# Environment variable names
ENV_PROVIDER = "MAGNET_LLM_PROVIDER"
ENV_MODEL = "MAGNET_LLM_MODEL"
ENV_API_KEY = "MAGNET_LLM_API_KEY"
ENV_BASE_URL = "MAGNET_LLM_BASE_URL"
ENV_ANTHROPIC_API_KEY = "ANTHROPIC_API_KEY"


def create_llm_provider(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    timeout_seconds: int = 120,
    fallback_to_deterministic: bool = True,
    retry_attempts: int = 2,
    retry_delay_ms: int = 1000,
    max_requests_per_minute: int = 60,
    max_cost_per_session_usd: float = 5.0,
    cache_ttl_seconds: int = 3600,
    enable_caching: bool = True,
    **kwargs: Any,
) -> LLMProviderProtocol:
    """
    Create an LLM provider based on configuration.

    Configuration priority:
    1. Explicit parameters
    2. Environment variables
    3. Defaults

    Args:
        provider: Provider type ("anthropic" or "local"/"ollama")
        model: Model identifier
        api_key: API key (for Anthropic)
        base_url: Base URL (for local/Ollama)
        max_tokens: Default max completion tokens
        temperature: Default temperature
        timeout_seconds: Request timeout
        fallback_to_deterministic: Use fallback on failure
        retry_attempts: Number of retry attempts
        retry_delay_ms: Delay between retries
        max_requests_per_minute: Rate limit
        max_cost_per_session_usd: Cost cap
        cache_ttl_seconds: Cache TTL
        enable_caching: Enable response caching
        **kwargs: Additional provider-specific options

    Returns:
        Configured LLMProviderProtocol instance

    Raises:
        ProviderUnavailableError: If provider cannot be initialized
        ValueError: If unknown provider type specified

    Examples:
        # Use environment variables
        provider = create_llm_provider()

        # Explicit Anthropic
        provider = create_llm_provider(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            api_key="sk-ant-..."
        )

        # Local Ollama
        provider = create_llm_provider(
            provider="local",
            model="llama3",
            base_url="http://localhost:11434"
        )
    """
    # Resolve provider from env if not specified
    resolved_provider = provider or os.getenv(ENV_PROVIDER, PROVIDER_ANTHROPIC)
    resolved_provider = resolved_provider.lower()

    # Normalize provider aliases
    if resolved_provider == PROVIDER_OLLAMA:
        resolved_provider = PROVIDER_LOCAL

    logger.info(f"Creating LLM provider: {resolved_provider}")

    # Common options for all providers
    common_options = {
        "max_tokens": max_tokens,
        "temperature": temperature,
        "timeout_seconds": timeout_seconds,
        "fallback_to_deterministic": fallback_to_deterministic,
        "retry_attempts": retry_attempts,
        "retry_delay_ms": retry_delay_ms,
        "max_requests_per_minute": max_requests_per_minute,
        "max_cost_per_session_usd": max_cost_per_session_usd,
        "cache_ttl_seconds": cache_ttl_seconds,
        "enable_caching": enable_caching,
        **kwargs,
    }

    if resolved_provider == PROVIDER_ANTHROPIC:
        return _create_anthropic_provider(
            model=model,
            api_key=api_key,
            **common_options,
        )

    elif resolved_provider == PROVIDER_LOCAL:
        return _create_local_provider(
            model=model,
            base_url=base_url,
            **common_options,
        )

    else:
        raise ValueError(
            f"Unknown provider: {resolved_provider}. "
            f"Supported: {PROVIDER_ANTHROPIC}, {PROVIDER_LOCAL}"
        )


def _create_anthropic_provider(
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> AnthropicProvider:
    """
    Create an Anthropic (Claude) provider.

    Args:
        model: Claude model (default: claude-sonnet-4-20250514)
        api_key: API key (from env ANTHROPIC_API_KEY if not specified)
        **kwargs: Additional options

    Returns:
        Configured AnthropicProvider
    """
    # Resolve model
    resolved_model = model or os.getenv(ENV_MODEL, "claude-sonnet-4-20250514")

    # Resolve API key
    resolved_key = api_key or os.getenv(ENV_API_KEY) or os.getenv(ENV_ANTHROPIC_API_KEY)

    if not resolved_key:
        logger.warning(
            "No Anthropic API key found. Set ANTHROPIC_API_KEY or MAGNET_LLM_API_KEY"
        )

    logger.info(f"Creating Anthropic provider with model: {resolved_model}")

    return AnthropicProvider(
        model=resolved_model,
        api_key=resolved_key,
        **kwargs,
    )


def _create_local_provider(
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs: Any,
) -> LocalProvider:
    """
    Create a local (Ollama) provider.

    Args:
        model: Model name (default: llama3)
        base_url: Ollama server URL (default: http://localhost:11434)
        **kwargs: Additional options

    Returns:
        Configured LocalProvider
    """
    # Resolve model
    resolved_model = model or os.getenv(ENV_MODEL, "llama3")

    # Resolve base URL
    resolved_url = base_url or os.getenv(ENV_BASE_URL, "http://localhost:11434")

    logger.info(
        f"Creating local provider with model: {resolved_model} at {resolved_url}"
    )

    return LocalProvider(
        model=resolved_model,
        base_url=resolved_url,
        **kwargs,
    )


def get_available_providers() -> Dict[str, bool]:
    """
    Check which providers are available.

    Returns:
        Dict mapping provider names to availability status
    """
    availability = {}

    # Check Anthropic
    try:
        import anthropic  # noqa: F401
        api_key = os.getenv(ENV_API_KEY) or os.getenv(ENV_ANTHROPIC_API_KEY)
        availability[PROVIDER_ANTHROPIC] = bool(api_key)
    except ImportError:
        availability[PROVIDER_ANTHROPIC] = False

    # Check local (Ollama)
    try:
        import httpx  # noqa: F401
        # Just check if httpx is available, actual server check is async
        availability[PROVIDER_LOCAL] = True
    except ImportError:
        availability[PROVIDER_LOCAL] = False

    return availability


def get_recommended_provider() -> str:
    """
    Get the recommended provider based on availability.

    Returns:
        Provider name to use
    """
    availability = get_available_providers()

    # Prefer Anthropic if API key is available
    if availability.get(PROVIDER_ANTHROPIC):
        return PROVIDER_ANTHROPIC

    # Fall back to local if available
    if availability.get(PROVIDER_LOCAL):
        return PROVIDER_LOCAL

    # Default to Anthropic (will fail with helpful error)
    return PROVIDER_ANTHROPIC
