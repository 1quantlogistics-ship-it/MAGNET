"""
magnet/llm/providers/anthropic.py - Anthropic Claude Provider

Implementation of LLMProviderProtocol for Claude models.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Dict, Optional

from ..protocol import LLMResponse, LLMOptions
from ..exceptions import (
    ProviderUnavailableError,
    TransientError,
)
from .base import BaseProvider

logger = logging.getLogger("llm.anthropic")

# Anthropic-specific error types to handle
TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class AnthropicProvider(BaseProvider):
    """
    Claude provider using the Anthropic API.

    Requires the `anthropic` package to be installed:
        pip install anthropic

    Configuration via environment or LLMConfig:
        - ANTHROPIC_API_KEY or config.api_key
        - Model: claude-sonnet-4-20250514, claude-3-5-sonnet, etc.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        timeout_seconds: int = 120,
        **kwargs: Any,
    ):
        """
        Initialize the Anthropic provider.

        Args:
            model: Claude model to use
            api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
            max_tokens: Default max completion tokens
            temperature: Default temperature
            timeout_seconds: Request timeout
            **kwargs: Additional BaseProvider options
        """
        super().__init__(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            **kwargs,
        )

        self._api_key = api_key
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        """
        Get or create the Anthropic client.

        Lazy initialization to avoid import errors if package not installed.
        """
        if self._client is not None:
            return self._client

        try:
            import anthropic
        except ImportError as e:
            self._available = False
            raise ProviderUnavailableError(
                "anthropic",
                "anthropic package not installed. Run: pip install anthropic",
            ) from e

        try:
            # Client will use ANTHROPIC_API_KEY env var if api_key is None
            self._client = anthropic.AsyncAnthropic(
                api_key=self._api_key,
                timeout=self.timeout_seconds,
            )
            self._available = True
            return self._client

        except Exception as e:
            self._available = False
            raise ProviderUnavailableError(
                "anthropic",
                f"Failed to initialize Anthropic client: {e}",
            ) from e

    async def _raw_complete(
        self,
        prompt: str,
        system_prompt: Optional[str],
        options: LLMOptions,
    ) -> LLMResponse:
        """
        Make the actual Claude API call.

        Args:
            prompt: User message
            system_prompt: System instructions
            options: Completion options

        Returns:
            LLMResponse from Claude
        """
        client = self._get_client()

        try:
            # Build messages
            messages = [{"role": "user", "content": prompt}]

            # Make the API call
            response = await client.messages.create(
                model=self.model,
                max_tokens=options.max_tokens or self.default_max_tokens,
                temperature=options.temperature or self.default_temperature,
                system=system_prompt or "",
                messages=messages,
                timeout=options.timeout_seconds,
            )

            # Extract content
            content = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, "text"):
                        content += block.text

            # Build usage dict
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }

            return LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
                finish_reason=response.stop_reason or "stop",
            )

        except Exception as e:
            # Check if it's a transient error
            if self._is_transient_error(e):
                raise TransientError(str(e), e)
            raise

    async def _raw_stream(
        self,
        prompt: str,
        system_prompt: Optional[str],
        options: LLMOptions,
    ) -> AsyncIterator[str]:
        """
        Stream tokens from Claude.

        Args:
            prompt: User message
            system_prompt: System instructions
            options: Completion options

        Yields:
            Token strings as they arrive
        """
        client = self._get_client()

        try:
            messages = [{"role": "user", "content": prompt}]

            async with client.messages.stream(
                model=self.model,
                max_tokens=options.max_tokens or self.default_max_tokens,
                temperature=options.temperature or self.default_temperature,
                system=system_prompt or "",
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            if self._is_transient_error(e):
                raise TransientError(str(e), e)
            raise

    def _is_transient_error(self, error: Exception) -> bool:
        """
        Check if an error is transient and should be retried.

        Args:
            error: The exception to check

        Returns:
            True if the error is transient
        """
        error_str = str(error).lower()

        # Check for common transient error patterns
        transient_patterns = [
            "rate limit",
            "overloaded",
            "timeout",
            "connection",
            "temporarily unavailable",
            "503",
            "529",
        ]

        for pattern in transient_patterns:
            if pattern in error_str:
                return True

        # Check for status code if available
        if hasattr(error, "status_code"):
            if error.status_code in TRANSIENT_STATUS_CODES:
                return True

        return False

    def is_available(self) -> bool:
        """
        Check if the Anthropic provider is available.

        Attempts to create the client if not already initialized.
        """
        if self._client is None:
            try:
                self._get_client()
            except ProviderUnavailableError:
                return False
        return self._available

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dict with model metadata
        """
        # Model capabilities (approximate)
        model_info = {
            "claude-sonnet-4-20250514": {
                "context_window": 200000,
                "max_output": 8192,
                "supports_vision": True,
                "supports_tools": True,
            },
            "claude-3-5-sonnet-20241022": {
                "context_window": 200000,
                "max_output": 8192,
                "supports_vision": True,
                "supports_tools": True,
            },
            "claude-3-opus-20240229": {
                "context_window": 200000,
                "max_output": 4096,
                "supports_vision": True,
                "supports_tools": True,
            },
            "claude-3-haiku-20240307": {
                "context_window": 200000,
                "max_output": 4096,
                "supports_vision": True,
                "supports_tools": True,
            },
        }

        return model_info.get(
            self.model,
            {
                "context_window": 200000,
                "max_output": 4096,
                "supports_vision": True,
                "supports_tools": True,
            },
        )
