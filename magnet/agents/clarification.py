"""
clarification.py - Agent Clarification System v1.0
BRAVO OWNS THIS FILE.

V1.4 UI Integration: Agent Clarification ACK Protocol

Provides:
- Clarification request lifecycle tracking
- ACK types: queued, presented, responded, skipped, cancelled
- Request token correlation
- Agent priority arbitration
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List
from enum import Enum
from datetime import datetime, timezone
import uuid
import logging

__all__ = [
    'AckType',
    'AgentPriority',
    'ClarificationRequest',
    'ClarificationAck',
    'ClarificationManager',
]

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class AckType(str, Enum):
    """ACK type for clarification lifecycle tracking."""
    QUEUED = "queued"           # Request added to queue
    PRESENTED = "presented"     # Request shown to user
    RESPONDED = "responded"     # User provided response
    SKIPPED = "skipped"         # User skipped the request
    CANCELLED = "cancelled"     # Request cancelled (timeout, superseded)


class AgentPriority(int, Enum):
    """Agent priority levels for arbitration."""
    COMPLIANCE = 4      # Highest - regulatory/safety
    ROUTING = 3         # Systems routing decisions
    INTERIOR = 2        # Layout/arrangement decisions
    PRODUCTION = 1      # Manufacturing decisions
    DEFAULT = 0         # Lowest priority


# =============================================================================
# CLARIFICATION REQUEST
# =============================================================================

@dataclass
class ClarificationRequest:
    """
    A clarification request from an agent.

    Tracks the full lifecycle of an agent's request for
    user input/clarification.
    """

    request_id: str = ""
    agent_id: str = ""
    request_token: str = ""

    # Request content
    message: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    options: List[str] = field(default_factory=list)
    default_option: Optional[str] = None

    # Priority
    priority: AgentPriority = AgentPriority.DEFAULT

    # Timing
    created_at: str = ""
    timeout_seconds: int = 300  # 5 minutes default

    # State
    current_ack: AckType = AckType.QUEUED
    ack_history: List[Dict[str, Any]] = field(default_factory=list)

    # Response
    response: Optional[str] = None
    response_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.request_id:
            self.request_id = str(uuid.uuid4())
        if not self.request_token:
            self.request_token = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def acknowledge(
        self,
        ack_type: AckType,
        reason: Optional[str] = None,
    ) -> 'ClarificationAck':
        """
        Record an ACK for this request.

        Args:
            ack_type: Type of acknowledgment
            reason: Optional reason for the ACK

        Returns:
            ClarificationAck record
        """
        ack = ClarificationAck(
            request_id=self.request_id,
            agent_id=self.agent_id,
            request_token=self.request_token,
            ack_type=ack_type,
            reason=reason,
        )

        # Update state
        self.current_ack = ack_type
        self.ack_history.append(ack.to_dict())

        logger.info(
            f"Clarification {self.request_id} ACK: {ack_type.value}"
            f"{f' ({reason})' if reason else ''}"
        )

        return ack

    def set_response(
        self,
        response: str,
        response_data: Optional[Dict[str, Any]] = None,
    ) -> 'ClarificationAck':
        """
        Set the user response for this request.

        Args:
            response: User's response string
            response_data: Additional response data

        Returns:
            ClarificationAck for the response
        """
        self.response = response
        if response_data:
            self.response_data = response_data

        return self.acknowledge(AckType.RESPONDED)

    def is_terminal(self) -> bool:
        """Check if the request is in a terminal state."""
        return self.current_ack in [
            AckType.RESPONDED,
            AckType.SKIPPED,
            AckType.CANCELLED,
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'request_id': self.request_id,
            'agent_id': self.agent_id,
            'request_token': self.request_token,
            'message': self.message,
            'context': self.context,
            'options': self.options,
            'default_option': self.default_option,
            'priority': self.priority.value,
            'created_at': self.created_at,
            'timeout_seconds': self.timeout_seconds,
            'current_ack': self.current_ack.value,
            'ack_history': self.ack_history,
            'response': self.response,
            'response_data': self.response_data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClarificationRequest':
        """Create from dictionary."""
        return cls(
            request_id=data.get('request_id', ''),
            agent_id=data.get('agent_id', ''),
            request_token=data.get('request_token', ''),
            message=data.get('message', ''),
            context=data.get('context', {}),
            options=data.get('options', []),
            default_option=data.get('default_option'),
            priority=AgentPriority(data.get('priority', 0)),
            created_at=data.get('created_at', ''),
            timeout_seconds=data.get('timeout_seconds', 300),
            current_ack=AckType(data.get('current_ack', 'queued')),
            ack_history=data.get('ack_history', []),
            response=data.get('response'),
            response_data=data.get('response_data', {}),
        )


# =============================================================================
# CLARIFICATION ACK
# =============================================================================

@dataclass
class ClarificationAck:
    """
    Acknowledgment record for a clarification request.

    V1.4 spec requires:
    - ack_type: queued | presented | responded | skipped | cancelled
    - request_token: For response correlation
    - reason: Optional explanation
    """

    request_id: str = ""
    agent_id: str = ""
    request_token: str = ""
    ack_type: AckType = AckType.QUEUED
    reason: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'request_id': self.request_id,
            'agent_id': self.agent_id,
            'request_token': self.request_token,
            'ack_type': self.ack_type.value,
            'reason': self.reason,
            'timestamp': self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClarificationAck':
        """Create from dictionary."""
        return cls(
            request_id=data.get('request_id', ''),
            agent_id=data.get('agent_id', ''),
            request_token=data.get('request_token', ''),
            ack_type=AckType(data.get('ack_type', 'queued')),
            reason=data.get('reason'),
            timestamp=data.get('timestamp', ''),
        )


# =============================================================================
# CLARIFICATION MANAGER
# =============================================================================

@dataclass
class ClarificationManager:
    """
    Manages clarification requests and ACK lifecycle.

    Provides:
    - Request queuing by agent priority
    - ACK tracking with retry support (V1.4 FIX #5)
    - Request timeout handling
    """

    _requests: Dict[str, ClarificationRequest] = field(default_factory=dict)
    _by_agent: Dict[str, List[str]] = field(default_factory=dict)

    def __init__(self):
        self._requests = {}
        self._by_agent = {}

    def create_request(
        self,
        agent_id: str,
        message: str,
        options: Optional[List[str]] = None,
        priority: AgentPriority = AgentPriority.DEFAULT,
        context: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 300,
    ) -> ClarificationRequest:
        """
        Create a new clarification request.

        Args:
            agent_id: Agent identifier
            message: Request message
            options: Response options
            priority: Agent priority
            context: Additional context
            timeout_seconds: Timeout duration

        Returns:
            New ClarificationRequest
        """
        request = ClarificationRequest(
            agent_id=agent_id,
            message=message,
            options=options or [],
            priority=priority,
            context=context or {},
            timeout_seconds=timeout_seconds,
        )

        # Store request
        self._requests[request.request_id] = request

        # Track by agent
        if agent_id not in self._by_agent:
            self._by_agent[agent_id] = []
        self._by_agent[agent_id].append(request.request_id)

        logger.info(f"Created clarification request {request.request_id} for agent {agent_id}")

        return request

    def get_request(self, request_id: str) -> Optional[ClarificationRequest]:
        """Get a clarification request by ID."""
        return self._requests.get(request_id)

    def get_request_by_token(self, request_token: str) -> Optional[ClarificationRequest]:
        """Get a clarification request by token."""
        for request in self._requests.values():
            if request.request_token == request_token:
                return request
        return None

    def get_agent_requests(self, agent_id: str) -> List[ClarificationRequest]:
        """Get all requests for an agent."""
        request_ids = self._by_agent.get(agent_id, [])
        return [
            self._requests[rid]
            for rid in request_ids
            if rid in self._requests
        ]

    def get_pending_requests(self) -> List[ClarificationRequest]:
        """
        Get all pending requests sorted by priority.

        Returns highest priority requests first.
        """
        pending = [
            r for r in self._requests.values()
            if not r.is_terminal()
        ]
        return sorted(pending, key=lambda r: -r.priority.value)

    def acknowledge(
        self,
        agent_id: str,
        request_id: str,
        ack_type: AckType,
        request_token: str,
        reason: Optional[str] = None,
    ) -> Optional[ClarificationAck]:
        """
        Record an ACK for a clarification request.

        V1.4 spec endpoint:
        POST /api/v1/agents/{agent_id}/clarification/{request_id}/ack

        Args:
            agent_id: Agent identifier
            request_id: Request identifier
            ack_type: Type of acknowledgment
            request_token: Token for correlation
            reason: Optional reason

        Returns:
            ClarificationAck if successful
        """
        request = self.get_request(request_id)
        if not request:
            logger.warning(f"Clarification request {request_id} not found")
            return None

        # Validate agent
        if request.agent_id != agent_id:
            logger.warning(
                f"Agent {agent_id} cannot ACK request {request_id} "
                f"owned by {request.agent_id}"
            )
            return None

        # Validate token
        if request.request_token != request_token:
            logger.warning(
                f"Invalid request token for {request_id}"
            )
            return None

        return request.acknowledge(ack_type, reason)

    def respond(
        self,
        request_id: str,
        response: str,
        response_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[ClarificationAck]:
        """
        Record a user response to a clarification.

        Args:
            request_id: Request identifier
            response: User's response
            response_data: Additional response data

        Returns:
            ClarificationAck if successful
        """
        request = self.get_request(request_id)
        if not request:
            logger.warning(f"Clarification request {request_id} not found")
            return None

        return request.set_response(response, response_data)

    def cancel(
        self,
        request_id: str,
        reason: str = "cancelled",
    ) -> Optional[ClarificationAck]:
        """
        Cancel a clarification request.

        Args:
            request_id: Request identifier
            reason: Cancellation reason

        Returns:
            ClarificationAck if successful
        """
        request = self.get_request(request_id)
        if not request:
            return None

        return request.acknowledge(AckType.CANCELLED, reason)

    def cleanup_expired(self) -> int:
        """
        Clean up expired requests.

        Returns:
            Number of requests cleaned up
        """
        from datetime import datetime

        count = 0
        now = datetime.now(timezone.utc)

        for request in list(self._requests.values()):
            if request.is_terminal():
                continue

            created = datetime.fromisoformat(request.created_at.replace('Z', '+00:00'))
            elapsed = (now - created).total_seconds()

            if elapsed > request.timeout_seconds:
                request.acknowledge(AckType.CANCELLED, "timeout")
                count += 1

        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        by_ack = {}
        for request in self._requests.values():
            ack = request.current_ack.value
            by_ack[ack] = by_ack.get(ack, 0) + 1

        return {
            'total_requests': len(self._requests),
            'pending_requests': len(self.get_pending_requests()),
            'agents': len(self._by_agent),
            'by_ack_type': by_ack,
        }
