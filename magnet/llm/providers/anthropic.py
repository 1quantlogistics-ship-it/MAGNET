"""
magnet/llm/providers/anthropic.py - Anthropic Claude Provider

Implementation of LLMProviderProtocol for Claude models.
"""

from __future__ import annotations

import logging
import os
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
            # Cursor/tool sandboxes may block reading system CA bundles (certifi / openssl certs)
            # which manifests as PermissionError: [Errno 1] Operation not permitted during
            # ssl context initialization. In that scenario, optionally fall back to an
            # insecure TLS client for local development.
            insecure_ok = (os.getenv("MAGNET_LLM_INSECURE_TLS", "true").strip().lower() in ("1", "true", "yes"))
            if insecure_ok:
                try:
                    import httpx
                    logger.warning(
                        "Anthropic client init failed due to SSL/cert permissions. "
                        "Falling back to insecure TLS (verify=False). "
                        "Set MAGNET_LLM_INSECURE_TLS=false to disable this fallback."
                    )
                    self._client = anthropic.AsyncAnthropic(
                        api_key=self._api_key,
                        timeout=self.timeout_seconds,
                        http_client=httpx.AsyncClient(verify=False, timeout=self.timeout_seconds),
                    )
                    self._available = True
                    return self._client
                except Exception:
                    # If fallback fails, surface the original exception below.
                    pass

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

    async def complete_with_image(
        self,
        prompt: str,
        image_data: bytes,
        image_media_type: str = "image/png",
        system_prompt: Optional[str] = None,
        options: Optional[LLMOptions] = None,
    ) -> LLMResponse:
        """
        Generate completion with image input (vision).
        
        Claude models support vision for analyzing images, sketches, diagrams.
        Used by VisionInterpreter for sketch-to-geometry translation.
        
        Args:
            prompt: Text prompt to accompany the image
            image_data: Raw image bytes
            image_media_type: MIME type (image/png, image/jpeg, image/gif, image/webp)
            system_prompt: System instructions
            options: Completion options
        
        Returns:
            LLMResponse from Claude with image analysis
        """
        import base64
        
        client = self._get_client()
        opts = options or LLMOptions()
        
        # Encode image to base64
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        
        # Build message with image content
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": image_media_type,
                            "data": image_base64,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ]
        
        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=opts.max_tokens or self.default_max_tokens,
                temperature=opts.temperature or self.default_temperature,
                system=system_prompt or "",
                messages=messages,
                timeout=opts.timeout_seconds or self.timeout_seconds,
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

    def _is_transient_error(self, error: Exception) -> bool:
        """
        Check if an error is transient and should be retried.
        
        TASK-026: Handles rate limits, server errors, and timeouts.
        
        Args:
            error: The exception to check
            
        Returns:
            True if the error is transient and should be retried
        """
        error_str = str(error).lower()
        
        # Rate limit errors (429)
        if "rate" in error_str and "limit" in error_str:
            return True
        if "429" in error_str:
            return True
            
        # Server errors (5xx)
        for code in ["500", "502", "503", "504"]:
            if code in error_str:
                return True
                
        # Timeout errors
        if "timeout" in error_str:
            return True
            
        # Connection errors
        if "connection" in error_str:
            return True
            
        # Check for Anthropic-specific error types
        try:
            import anthropic
            if isinstance(error, anthropic.RateLimitError):
                return True
            if isinstance(error, anthropic.APIStatusError):
                return error.status_code in TRANSIENT_STATUS_CODES
        except ImportError:
            pass
            
        return False

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
