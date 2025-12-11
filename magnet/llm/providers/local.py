"""
magnet/llm/providers/local.py - Local LLM Provider (Ollama)

Implementation of LLMProviderProtocol for local LLMs via Ollama.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Dict, Optional

from ..protocol import LLMResponse, LLMOptions
from ..exceptions import (
    ProviderUnavailableError,
    TransientError,
)
from .base import BaseProvider

logger = logging.getLogger("llm.local")

# Default Ollama configuration
DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3"


class LocalProvider(BaseProvider):
    """
    Local LLM provider using Ollama.

    Requires Ollama to be running locally:
        - Install: https://ollama.ai
        - Start: ollama serve
        - Pull model: ollama pull llama3

    Configuration:
        - base_url: Ollama server URL (default: http://localhost:11434)
        - model: Model name (e.g., llama3, mistral, codellama)
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        timeout_seconds: int = 120,
        **kwargs: Any,
    ):
        """
        Initialize the local provider.

        Args:
            model: Ollama model name
            base_url: Ollama server URL
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

        self.base_url = base_url.rstrip("/")
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        """
        Get or create the HTTP client.

        Uses httpx for async HTTP requests.
        """
        if self._client is not None:
            return self._client

        try:
            import httpx
        except ImportError as e:
            self._available = False
            raise ProviderUnavailableError(
                "local",
                "httpx package not installed. Run: pip install httpx",
            ) from e

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
        )
        return self._client

    async def _check_server(self) -> bool:
        """
        Check if Ollama server is running.

        Returns:
            True if server is reachable
        """
        try:
            client = self._get_client()
            response = await client.get("/api/tags")
            self._available = response.status_code == 200
            return self._available
        except Exception as e:
            logger.warning(f"Ollama server not available: {e}")
            self._available = False
            return False

    async def _raw_complete(
        self,
        prompt: str,
        system_prompt: Optional[str],
        options: LLMOptions,
    ) -> LLMResponse:
        """
        Make the actual Ollama API call.

        Args:
            prompt: User message
            system_prompt: System instructions
            options: Completion options

        Returns:
            LLMResponse from Ollama
        """
        client = self._get_client()

        try:
            # Build request payload
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": options.max_tokens or self.default_max_tokens,
                    "temperature": options.temperature or self.default_temperature,
                },
            }

            if system_prompt:
                payload["system"] = system_prompt

            if options.stop_sequences:
                payload["options"]["stop"] = options.stop_sequences

            # Make the API call
            response = await client.post(
                "/api/generate",
                json=payload,
                timeout=options.timeout_seconds,
            )

            if response.status_code != 200:
                raise TransientError(
                    f"Ollama returned status {response.status_code}: {response.text}"
                )

            data = response.json()

            # Ollama doesn't provide token counts directly, estimate from content
            prompt_tokens = len(prompt.split()) * 1.3  # rough estimate
            completion_tokens = len(data.get("response", "").split()) * 1.3

            usage = {
                "prompt_tokens": int(prompt_tokens),
                "completion_tokens": int(completion_tokens),
                "total_tokens": int(prompt_tokens + completion_tokens),
            }

            return LLMResponse(
                content=data.get("response", ""),
                model=data.get("model", self.model),
                usage=usage,
                finish_reason=data.get("done_reason", "stop"),
            )

        except Exception as e:
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
        Stream tokens from Ollama.

        Args:
            prompt: User message
            system_prompt: System instructions
            options: Completion options

        Yields:
            Token strings as they arrive
        """
        client = self._get_client()

        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "num_predict": options.max_tokens or self.default_max_tokens,
                    "temperature": options.temperature or self.default_temperature,
                },
            }

            if system_prompt:
                payload["system"] = system_prompt

            async with client.stream(
                "POST",
                "/api/generate",
                json=payload,
                timeout=options.timeout_seconds,
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue

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

        transient_patterns = [
            "connection",
            "timeout",
            "temporarily unavailable",
            "503",
            "502",
            "reset by peer",
        ]

        for pattern in transient_patterns:
            if pattern in error_str:
                return True

        return False

    def is_available(self) -> bool:
        """
        Check if the local provider is available.

        Note: This is a synchronous check of cached state.
        Use _check_server() for actual connectivity test.
        """
        return self._available

    async def check_availability(self) -> bool:
        """
        Async check if Ollama server is available.

        Returns:
            True if server is reachable and model is available
        """
        if not await self._check_server():
            return False

        # Check if model is available
        try:
            client = self._get_client()
            response = await client.get("/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
                if self.model not in models and f"{self.model}:latest" not in [m.get("name", "") for m in data.get("models", [])]:
                    logger.warning(f"Model {self.model} not found. Available: {models}")
                    # Still available, just needs to pull the model
                    return True
                return True
        except Exception as e:
            logger.warning(f"Failed to check model availability: {e}")

        return self._available

    async def list_models(self) -> list[str]:
        """
        List available models on the Ollama server.

        Returns:
            List of model names
        """
        try:
            client = self._get_client()
            response = await client.get("/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [m.get("name", "") for m in data.get("models", [])]
        except Exception as e:
            logger.warning(f"Failed to list models: {e}")

        return []

    async def pull_model(self, model_name: Optional[str] = None) -> bool:
        """
        Pull a model from Ollama library.

        Args:
            model_name: Model to pull (default: current model)

        Returns:
            True if successful
        """
        model = model_name or self.model

        try:
            client = self._get_client()
            response = await client.post(
                "/api/pull",
                json={"name": model},
                timeout=600,  # Model downloads can take a while
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dict with model metadata
        """
        # Common Ollama models and their approximate capabilities
        model_info = {
            "llama3": {
                "context_window": 8192,
                "max_output": 4096,
                "supports_vision": False,
                "supports_tools": False,
            },
            "llama3:70b": {
                "context_window": 8192,
                "max_output": 4096,
                "supports_vision": False,
                "supports_tools": False,
            },
            "mistral": {
                "context_window": 32768,
                "max_output": 4096,
                "supports_vision": False,
                "supports_tools": False,
            },
            "codellama": {
                "context_window": 16384,
                "max_output": 4096,
                "supports_vision": False,
                "supports_tools": False,
            },
            "llava": {
                "context_window": 4096,
                "max_output": 2048,
                "supports_vision": True,
                "supports_tools": False,
            },
        }

        # Strip version tag for lookup
        base_model = self.model.split(":")[0]

        return model_info.get(
            base_model,
            {
                "context_window": 4096,
                "max_output": 2048,
                "supports_vision": False,
                "supports_tools": False,
            },
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
