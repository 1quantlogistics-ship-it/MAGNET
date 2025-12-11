"""
magnet/llm/providers/base.py - Base Provider with Safety Features

Abstract base class for LLM providers with built-in:
- Response caching
- Rate limiting
- Cost tracking
- Retry with exponential backoff
- Fallback to deterministic behavior
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Optional,
    Type,
    TypeVar,
    Union,
)

from pydantic import BaseModel, ValidationError as PydanticValidationError

from ..protocol import LLMProviderProtocol, LLMResponse, LLMOptions
from ..exceptions import (
    LLMError,
    RateLimitError,
    CostLimitError,
    ProviderUnavailableError,
    ValidationError,
    TimeoutError as LLMTimeoutError,
    TransientError,
)
from ..safety import (
    ResponseCache,
    RateLimiter,
    CostTracker,
    LLMMetrics,
)

logger = logging.getLogger("llm.provider")

T = TypeVar("T")


class BaseProvider(ABC):
    """
    Abstract base class for LLM providers.

    Implements safety features (caching, rate limiting, cost tracking)
    and delegates actual API calls to subclasses.
    """

    def __init__(
        self,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        timeout_seconds: int = 120,
        # Safety configuration
        fallback_to_deterministic: bool = True,
        retry_attempts: int = 2,
        retry_delay_ms: int = 1000,
        max_requests_per_minute: int = 60,
        max_cost_per_session_usd: float = 5.0,
        cache_ttl_seconds: int = 3600,
        enable_caching: bool = True,
    ):
        """
        Initialize the base provider.

        Args:
            model: Model identifier
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
        """
        self.model = model
        self.default_max_tokens = max_tokens
        self.default_temperature = temperature
        self.timeout_seconds = timeout_seconds

        # Safety configuration
        self.fallback_to_deterministic = fallback_to_deterministic
        self.retry_attempts = retry_attempts
        self.retry_delay_ms = retry_delay_ms
        self.enable_caching = enable_caching

        # Safety components
        self.cache = ResponseCache(default_ttl_seconds=cache_ttl_seconds)
        self.rate_limiter = RateLimiter(requests_per_minute=max_requests_per_minute)
        self.cost_tracker = CostTracker(max_cost_usd=max_cost_per_session_usd)
        self.metrics = LLMMetrics()

        self._available = True

    @abstractmethod
    async def _raw_complete(
        self,
        prompt: str,
        system_prompt: Optional[str],
        options: LLMOptions,
    ) -> LLMResponse:
        """
        Make the actual API call. Implemented by subclasses.

        Args:
            prompt: User prompt
            system_prompt: System instructions
            options: Completion options

        Returns:
            LLMResponse from the API
        """
        ...

    @abstractmethod
    async def _raw_stream(
        self,
        prompt: str,
        system_prompt: Optional[str],
        options: LLMOptions,
    ) -> AsyncIterator[str]:
        """
        Make streaming API call. Implemented by subclasses.
        """
        ...

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        options: Optional[LLMOptions] = None,
    ) -> LLMResponse:
        """
        Generate a completion with safety checks.

        Args:
            prompt: User prompt
            system_prompt: System instructions
            options: Completion options

        Returns:
            LLMResponse

        Raises:
            RateLimitError: If rate limit exceeded
            CostLimitError: If cost limit exceeded
            LLMError: On other failures
        """
        opts = (options or LLMOptions()).merge_with_defaults(
            self.default_max_tokens,
            self.default_temperature,
        )
        request_id = str(uuid.uuid4())[:8]

        # Check cache first
        if self.enable_caching:
            cached = self.cache.get(prompt, system_prompt, self.model)
            if cached:
                self.metrics.record_from_response(
                    request_id=request_id,
                    model=self.model,
                    latency_ms=0,
                    usage=cached.usage,
                    cost_usd=0.0,
                    cached=True,
                )
                return cached

        # Check rate limit
        if not self.rate_limiter.allow():
            raise RateLimitError(
                retry_after_seconds=self.rate_limiter.wait_time(),
                request_id=request_id,
            )

        # Check cost budget
        estimated_cost = self.cost_tracker.estimate_prompt_cost(
            self.model, prompt, opts.max_tokens or self.default_max_tokens
        )
        if self.cost_tracker.would_exceed(estimated_cost):
            raise CostLimitError(
                current_cost=self.cost_tracker._session_cost,
                limit=self.cost_tracker.max_cost_usd,
                request_id=request_id,
            )

        # Make request with retry
        last_error: Optional[Exception] = None
        start_time = time.monotonic()

        for attempt in range(self.retry_attempts + 1):
            try:
                response = await asyncio.wait_for(
                    self._raw_complete(prompt, system_prompt, opts),
                    timeout=opts.timeout_seconds,
                )

                latency_ms = int((time.monotonic() - start_time) * 1000)
                response.latency_ms = latency_ms
                response.request_id = request_id

                # Calculate actual cost
                actual_cost = self.cost_tracker.estimate(
                    self.model,
                    response.usage.get("prompt_tokens", 0),
                    response.usage.get("completion_tokens", 0),
                )
                response.estimated_cost_usd = actual_cost

                # Record metrics and cost
                self.metrics.record_from_response(
                    request_id=request_id,
                    model=self.model,
                    latency_ms=latency_ms,
                    usage=response.usage,
                    cost_usd=actual_cost,
                    cached=False,
                )
                self.cost_tracker.add(
                    actual_cost,
                    response.usage.get("prompt_tokens", 0),
                    response.usage.get("completion_tokens", 0),
                )

                # Cache successful response
                if self.enable_caching:
                    self.cache.set(
                        prompt, response, system_prompt, self.model, opts.cache_ttl_seconds
                    )

                return response

            except asyncio.TimeoutError:
                last_error = LLMTimeoutError(opts.timeout_seconds, request_id)
                logger.warning(f"Request timeout (attempt {attempt + 1})")

            except TransientError as e:
                last_error = e
                logger.warning(f"Transient error (attempt {attempt + 1}): {e}")

            except Exception as e:
                last_error = TransientError(str(e), e, request_id)
                logger.warning(f"Request error (attempt {attempt + 1}): {e}")

            # Retry delay
            if attempt < self.retry_attempts:
                delay = self.retry_delay_ms * (2 ** attempt) / 1000
                await asyncio.sleep(delay)

        # All retries exhausted
        latency_ms = int((time.monotonic() - start_time) * 1000)
        self.metrics.record_error(
            request_id=request_id,
            model=self.model,
            latency_ms=latency_ms,
            error=str(last_error),
        )

        raise LLMError(f"Request failed after {self.retry_attempts + 1} attempts: {last_error}")

    async def complete_with_fallback(
        self,
        prompt: str,
        fallback_fn: Callable[[], T],
        system_prompt: Optional[str] = None,
        options: Optional[LLMOptions] = None,
    ) -> Union[LLMResponse, T]:
        """
        Generate completion with automatic fallback on failure.

        Args:
            prompt: User prompt
            fallback_fn: Function to call if LLM fails
            system_prompt: System instructions
            options: Completion options

        Returns:
            LLMResponse on success, or fallback result on failure
        """
        try:
            return await self.complete(prompt, system_prompt, options)

        except (RateLimitError, CostLimitError) as e:
            logger.warning(f"Using fallback due to limit: {e}")
            if self.fallback_to_deterministic:
                return fallback_fn()
            raise

        except LLMError as e:
            logger.warning(f"Using fallback due to error: {e}")
            if self.fallback_to_deterministic:
                return fallback_fn()
            raise

    async def complete_json(
        self,
        prompt: str,
        response_model: Type[BaseModel],
        system_prompt: Optional[str] = None,
        options: Optional[LLMOptions] = None,
    ) -> BaseModel:
        """
        Generate JSON completion and validate against Pydantic model.

        Args:
            prompt: User prompt (should request JSON output)
            response_model: Pydantic model for validation
            system_prompt: System instructions
            options: Completion options

        Returns:
            Validated Pydantic model instance

        Raises:
            ValidationError: If response doesn't match schema
        """
        # Add JSON instruction to system prompt
        json_instruction = (
            f"You must respond with valid JSON matching this schema:\n"
            f"{response_model.model_json_schema()}\n"
            f"Only output the JSON object, no other text."
        )
        full_system = f"{system_prompt}\n\n{json_instruction}" if system_prompt else json_instruction

        response = await self.complete(prompt, full_system, options)

        try:
            # Try to parse JSON from response
            content = response.content.strip()
            # Handle markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            data = json.loads(content)
            return response_model.model_validate(data)

        except json.JSONDecodeError as e:
            raise ValidationError(
                f"Response is not valid JSON: {e}",
                raw_response=response.content,
                request_id=response.request_id,
            )
        except PydanticValidationError as e:
            raise ValidationError(
                f"Response doesn't match schema: {e}",
                raw_response=response.content,
                request_id=response.request_id,
            )

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        options: Optional[LLMOptions] = None,
    ) -> AsyncIterator[str]:
        """
        Stream completion tokens with safety checks.

        Note: Streaming bypasses caching.
        """
        opts = (options or LLMOptions()).merge_with_defaults(
            self.default_max_tokens,
            self.default_temperature,
        )

        # Check rate limit
        if not self.rate_limiter.allow():
            raise RateLimitError(retry_after_seconds=self.rate_limiter.wait_time())

        # Estimate cost (can't know exact until done)
        estimated_cost = self.cost_tracker.estimate_prompt_cost(
            self.model, prompt, opts.max_tokens or self.default_max_tokens
        )
        if self.cost_tracker.would_exceed(estimated_cost):
            raise CostLimitError(
                current_cost=self.cost_tracker._session_cost,
                limit=self.cost_tracker.max_cost_usd,
            )

        async for chunk in self._raw_stream(prompt, system_prompt, opts):
            yield chunk

    def is_available(self) -> bool:
        """Check if provider is available."""
        return self._available

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get combined usage statistics."""
        return {
            "metrics": self.metrics.get_stats(),
            "cache": self.cache.get_stats(),
            "rate_limiter": self.rate_limiter.get_stats(),
            "cost": self.cost_tracker.get_stats(),
        }

    def estimate_cost(self, prompt: str, max_completion_tokens: int = 1000) -> float:
        """Estimate cost for a prompt."""
        return self.cost_tracker.estimate_prompt_cost(
            self.model, prompt, max_completion_tokens
        )
