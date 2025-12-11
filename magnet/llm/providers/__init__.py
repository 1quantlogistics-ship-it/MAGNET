"""
magnet/llm/providers - LLM Provider Implementations

Available providers:
- AnthropicProvider: Claude API (default)
- LocalProvider: Ollama/llama.cpp for local LLMs
"""

from .base import BaseProvider
from .anthropic import AnthropicProvider
from .local import LocalProvider

__all__ = [
    "BaseProvider",
    "AnthropicProvider",
    "LocalProvider",
]
