"""
MAGNET Base Agent
=================

Foundation class for all MAGNET agents.
Provides common functionality for LLM interaction, memory access, and message handling.

Design Principles (from Operations Guide):
- Stateless Agents: Each invocation receives full context
- Schema Enforcement: All messages validated
- File-Based Protocol: Communication via JSON files
- Domain Expertise: Agent differentiation via system prompts
"""

import os
import json
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from pydantic import BaseModel

from memory.file_io import MemoryFileIO, get_memory
from memory.schemas import SystemStateSchema, AgentVoteSchema, VoteType


@dataclass
class AgentMessage:
    """Message to/from an agent."""
    role: str  # "system", "user", "assistant"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentResponse:
    """Response from an agent."""
    agent_id: str
    content: str
    confidence: float
    reasoning: Optional[str] = None
    proposals: List[Dict[str, Any]] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class BaseAgent(ABC):
    """
    Base class for all MAGNET agents.

    Provides:
    - LLM inference via vLLM endpoint
    - Memory file access
    - Standard message patterns
    - Voting/consensus interface
    """

    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        llm_endpoint: str = "http://localhost:8000/v1/completions",
        model_name: str = "Qwen/Qwen2.5-72B-Instruct",
        memory_path: str = "memory",
        timeout: int = 120,
        max_retries: int = 3,
    ):
        """
        Initialize base agent.

        Args:
            agent_id: Unique identifier for this agent instance
            agent_type: Type of agent (e.g., "director", "naval_architect")
            llm_endpoint: vLLM API endpoint
            model_name: Model to use for inference
            memory_path: Path to memory directory
            timeout: Request timeout in seconds
            max_retries: Max retry attempts
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.llm_endpoint = llm_endpoint
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries

        # Memory access
        self.memory = MemoryFileIO(memory_path)

        # Conversation history for this invocation
        self.messages: List[AgentMessage] = []

        # Initialize with system prompt
        self._init_system_prompt()

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """
        Return the system prompt for this agent.
        Each agent type must define its own domain expertise prompt.
        """
        pass

    def _init_system_prompt(self) -> None:
        """Initialize conversation with system prompt."""
        self.messages = [
            AgentMessage(role="system", content=self.system_prompt)
        ]

    def generate(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None,
    ) -> str:
        """
        Generate response from LLM.

        Args:
            prompt: User prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            stop_sequences: Stop generation sequences

        Returns:
            Generated text
        """
        # Build full prompt with history
        full_prompt = self._build_prompt(prompt)

        payload = {
            "prompt": full_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "model": self.model_name,
        }

        if stop_sequences:
            payload["stop"] = stop_sequences

        # Retry logic
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.llm_endpoint,
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()

                data = response.json()

                # Handle vLLM response format
                if "choices" in data:
                    text = data["choices"][0].get("text", "")
                elif "text" in data:
                    text = data["text"][0] if isinstance(data["text"], list) else data["text"]
                else:
                    text = str(data)

                # Add to conversation history
                self.messages.append(AgentMessage(role="user", content=prompt))
                self.messages.append(AgentMessage(role="assistant", content=text))

                return text

            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff

        # If we get here, all retries failed
        raise ConnectionError(f"Failed to connect to LLM after {self.max_retries} attempts: {last_error}")

    def _build_prompt(self, user_prompt: str) -> str:
        """
        Build full prompt with conversation history.

        Args:
            user_prompt: Current user prompt

        Returns:
            Full prompt string for LLM
        """
        prompt_parts = []

        for msg in self.messages:
            if msg.role == "system":
                prompt_parts.append(f"<|im_start|>system\n{msg.content}<|im_end|>")
            elif msg.role == "user":
                prompt_parts.append(f"<|im_start|>user\n{msg.content}<|im_end|>")
            elif msg.role == "assistant":
                prompt_parts.append(f"<|im_start|>assistant\n{msg.content}<|im_end|>")

        prompt_parts.append(f"<|im_start|>user\n{user_prompt}<|im_end|>")
        prompt_parts.append("<|im_start|>assistant\n")

        return "\n".join(prompt_parts)

    def read_context(self) -> Dict[str, Any]:
        """
        Read all relevant memory files for context.

        Returns:
            Dict of all available memory data
        """
        context = {}

        for key in self.memory.files.keys():
            data = self.memory.read(key)
            if data:
                context[key] = data

        return context

    def vote(
        self,
        proposal_id: str,
        vote: VoteType,
        confidence: float,
        reasoning: str,
        concerns: Optional[List[str]] = None,
    ) -> AgentVoteSchema:
        """
        Cast a vote on a proposal.

        Args:
            proposal_id: ID of the proposal
            vote: approve, reject, or revise
            confidence: Confidence in vote (0-1)
            reasoning: Explanation for vote
            concerns: List of concerns

        Returns:
            Vote schema
        """
        vote_schema = AgentVoteSchema(
            agent_id=self.agent_id,
            proposal_id=proposal_id,
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
            concerns=concerns or [],
        )

        # Record vote
        self.memory.append_vote(vote_schema)

        return vote_schema

    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Process input and generate response.

        Each agent type implements its own processing logic.

        Args:
            input_data: Input data for processing

        Returns:
            Agent response
        """
        pass

    def log_decision(self, decision: Dict[str, Any]) -> None:
        """
        Log a decision to the design iterations log.

        Args:
            decision: Decision to log
        """
        decision["agent_id"] = self.agent_id
        decision["agent_type"] = self.agent_type
        self.memory.append_log("design_iterations", decision)


class MockLLMAgent(BaseAgent):
    """
    Mock agent for testing without LLM endpoint.
    Returns predefined responses for testing.
    """

    def __init__(self, agent_id: str, agent_type: str, **kwargs):
        # Override LLM endpoint
        kwargs["llm_endpoint"] = "mock://localhost"
        super().__init__(agent_id, agent_type, **kwargs)
        self._mock_responses: List[str] = []

    @property
    def system_prompt(self) -> str:
        return "You are a mock agent for testing."

    def set_mock_response(self, response: str) -> None:
        """Set a mock response to return."""
        self._mock_responses.append(response)

    def generate(self, prompt: str, **kwargs) -> str:
        """Return mock response instead of calling LLM."""
        if self._mock_responses:
            return self._mock_responses.pop(0)
        return f"Mock response to: {prompt[:100]}..."

    def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """Return mock response."""
        return AgentResponse(
            agent_id=self.agent_id,
            content="Mock processing complete",
            confidence=0.9,
        )
