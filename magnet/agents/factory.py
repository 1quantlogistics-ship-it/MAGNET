"""
magnet/agents/factory.py - Agent Factory

Simple DI-friendly constructor for agent components.
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .llm_client import LLMClient
    from magnet.core.state_manager import StateManager


class AgentFactory:
    """
    Factory for creating agent components.

    Provides DI-friendly access to LLM and state management.
    """

    def __init__(
        self,
        llm_client: Optional["LLMClient"] = None,
        state_manager: Optional["StateManager"] = None,
    ):
        """
        Initialize the agent factory.

        Args:
            llm_client: LLM client for AI operations
            state_manager: State manager for design state
        """
        self._llm_client = llm_client
        self._state_manager = state_manager

    def get_llm(self) -> Optional["LLMClient"]:
        """Get the LLM client."""
        return self._llm_client

    def get_state_manager(self) -> Optional["StateManager"]:
        """Get the state manager."""
        return self._state_manager

    @property
    def llm_client(self) -> Optional["LLMClient"]:
        """LLM client property."""
        return self._llm_client

    @property
    def state_manager(self) -> Optional["StateManager"]:
        """State manager property."""
        return self._state_manager
