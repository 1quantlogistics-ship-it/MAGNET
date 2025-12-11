"""
MAGNET Agents Module v1.0
BRAVO OWNS THIS FILE.

V1.4 UI Integration: Agent Clarification System

This module provides:
- Agent arbitration protocol
- Clarification ACK lifecycle tracking
- Agent priority queuing
"""

from magnet.agents.clarification import (
    AckType,
    ClarificationRequest,
    ClarificationAck,
    ClarificationManager,
)
from magnet.agents.api_endpoints import create_agents_router

__all__ = [
    'AckType',
    'ClarificationRequest',
    'ClarificationAck',
    'ClarificationManager',
    'create_agents_router',
]
