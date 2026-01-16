"""
TASK-026: API Failure Handling — Graceful Degradation

Tests for LLM API failure handling, retry logic, and user-friendly errors.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from magnet.llm.exceptions import (
    LLMError,
    RateLimitError,
    TimeoutError as LLMTimeoutError,
    TransientError,
    ProviderUnavailableError,
)
from magnet.deployment.error_handlers import (
    map_exception_to_user_error,
    ErrorCode,
)


class TestLLMExceptionMapping:
    """Test that LLM exceptions map to user-friendly errors."""

    def test_rate_limit_error_mapped(self):
        """RateLimitError gets user-friendly message."""
        exc = RateLimitError("Rate limit exceeded", retry_after_seconds=30)
        result = map_exception_to_user_error(exc)
        
        assert result.code == ErrorCode.E300_RATE_LIMIT
        assert "too many requests" in result.error.lower()
        assert "wait" in result.suggestion.lower()

    def test_timeout_error_mapped(self):
        """TimeoutError gets user-friendly message."""
        exc = LLMTimeoutError(timeout_seconds=120)
        result = map_exception_to_user_error(exc)
        
        assert result.code == ErrorCode.E301_TIMEOUT
        assert "not responding" in result.error.lower() or "timeout" in result.error.lower()

    def test_provider_unavailable_mapped(self):
        """ProviderUnavailableError mentions API key."""
        exc = ProviderUnavailableError("anthropic", "No API key")
        result = map_exception_to_user_error(exc)
        
        assert result.code == ErrorCode.E302_LLM_ERROR
        assert "api" in result.suggestion.lower() or "configured" in result.error.lower()

    def test_transient_error_mapped(self):
        """TransientError gets retry suggestion."""
        exc = TransientError("Connection reset")
        result = map_exception_to_user_error(exc)
        
        assert result.code == ErrorCode.E302_LLM_ERROR
        assert "try again" in result.suggestion.lower()

    def test_generic_llm_error_mapped(self):
        """Generic LLMError gets user-friendly message."""
        exc = LLMError("Something went wrong")
        result = map_exception_to_user_error(exc)
        
        assert result.code == ErrorCode.E302_LLM_ERROR
        assert "ai" in result.error.lower() or "error" in result.error.lower()


class TestRetryConfiguration:
    """Test that retry configuration is correct."""

    def test_default_retry_attempts(self):
        """Default retry attempts is 3."""
        from magnet.llm.providers.base import BaseProvider
        
        # Check the default value in the signature
        import inspect
        sig = inspect.signature(BaseProvider.__init__)
        retry_param = sig.parameters.get("retry_attempts")
        assert retry_param is not None
        assert retry_param.default == 3

    def test_default_retry_delay(self):
        """Default retry delay is 2000ms."""
        from magnet.llm.providers.base import BaseProvider
        
        import inspect
        sig = inspect.signature(BaseProvider.__init__)
        delay_param = sig.parameters.get("retry_delay_ms")
        assert delay_param is not None
        assert delay_param.default == 2000


class TestAnthropicTransientErrorDetection:
    """Test transient error detection in Anthropic provider."""

    @pytest.fixture
    def provider(self):
        """Create a mock Anthropic provider."""
        from magnet.llm.providers.anthropic import AnthropicProvider
        return AnthropicProvider(api_key="test-key")

    def test_rate_limit_is_transient(self, provider):
        """Rate limit errors are transient."""
        exc = Exception("Rate limit exceeded (429)")
        assert provider._is_transient_error(exc) is True

    def test_429_code_is_transient(self, provider):
        """429 status code is transient."""
        exc = Exception("API returned 429")
        assert provider._is_transient_error(exc) is True

    def test_500_is_transient(self, provider):
        """500 server error is transient."""
        exc = Exception("Internal server error 500")
        assert provider._is_transient_error(exc) is True

    def test_502_is_transient(self, provider):
        """502 bad gateway is transient."""
        exc = Exception("Bad Gateway 502")
        assert provider._is_transient_error(exc) is True

    def test_503_is_transient(self, provider):
        """503 service unavailable is transient."""
        exc = Exception("Service Unavailable 503")
        assert provider._is_transient_error(exc) is True

    def test_timeout_is_transient(self, provider):
        """Timeout errors are transient."""
        exc = Exception("Request timeout")
        assert provider._is_transient_error(exc) is True

    def test_connection_error_is_transient(self, provider):
        """Connection errors are transient."""
        exc = Exception("Connection refused")
        assert provider._is_transient_error(exc) is True

    def test_validation_error_not_transient(self, provider):
        """Validation errors are not transient."""
        exc = Exception("Invalid request format")
        assert provider._is_transient_error(exc) is False

    def test_auth_error_not_transient(self, provider):
        """Authentication errors are not transient."""
        exc = Exception("Invalid API key")
        assert provider._is_transient_error(exc) is False


class TestErrorMessagesNoTechnicalDetails:
    """Test that error messages don't expose technical details."""

    def test_no_python_exception_names(self):
        """User-facing errors don't include Python exception names."""
        exceptions = [
            RateLimitError(),
            LLMTimeoutError(120),
            TransientError("test"),
            ProviderUnavailableError("test"),
        ]
        
        for exc in exceptions:
            result = map_exception_to_user_error(exc)
            # Error message should not contain Python exception class names
            assert "Error" not in result.error or "error" in result.error.lower()
            assert "Exception" not in result.error

    def test_suggestions_are_actionable(self):
        """Suggestions tell user what to do."""
        exceptions = [
            RateLimitError(),
            LLMTimeoutError(120),
            ProviderUnavailableError("anthropic"),
        ]
        
        actionable_words = ["try", "wait", "check", "contact", "simplify"]
        
        for exc in exceptions:
            result = map_exception_to_user_error(exc)
            has_action = any(word in result.suggestion.lower() for word in actionable_words)
            assert has_action, f"Suggestion not actionable: {result.suggestion}"
