"""
magnet/agents/llm_client.py - LLM Client Facade

Thin adapter that delegates to magnet.llm infrastructure.
"""

from typing import Any, Optional, Type

from pydantic import BaseModel

from magnet.llm import create_llm_provider, LLMResponse


class LLMClient:
    """
    Facade for LLM operations used by the agent system.

    Delegates to the existing magnet.llm provider infrastructure.
    """

    def __init__(
        self,
        provider: str = "anthropic",
        model: str = "claude-sonnet-4-20250514",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        timeout: int = 120,
        **kwargs: Any,
    ):
        """
        Initialize the LLM client.

        Args:
            provider: Provider type ("anthropic" or "local")
            model: Model identifier
            api_key: API key (for Anthropic)
            base_url: Base URL (for local/Ollama)
            max_tokens: Max completion tokens
            temperature: Sampling temperature
            timeout: Request timeout in seconds
        """
        self._provider = create_llm_provider(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout,  # Note: factory uses timeout_seconds
            **kwargs,
        )

    async def complete(self, prompt: str, **kwargs: Any) -> str:
        """
        Complete a prompt and return the response text.

        Args:
            prompt: The prompt to complete
            **kwargs: Additional options (system_prompt, options)

        Returns:
            Response text from the LLM
        """
        response: LLMResponse = await self._provider.complete(prompt, **kwargs)
        return response.content

    async def complete_json(
        self,
        prompt: str,
        response_model: Type[BaseModel],
        **kwargs: Any,
    ) -> BaseModel:
        """
        Complete a prompt expecting structured JSON response.

        Args:
            prompt: The prompt (should request JSON output)
            response_model: Pydantic model class for validation
            **kwargs: Additional options

        Returns:
            Validated Pydantic model instance

        Note:
            The underlying provider handles markdown code block stripping
            and Pydantic validation (see base.py:349-369).
        """
        return await self._provider.complete_json(prompt, response_model, **kwargs)

    @property
    def provider(self):
        """Access the underlying provider for advanced usage."""
        return self._provider

    def is_available(self) -> bool:
        """Check if the LLM provider is available."""
        try:
            return self._provider.is_available()
        except Exception:
            return False
