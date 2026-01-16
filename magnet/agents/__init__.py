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
from magnet.agents.llm_client import LLMClient
from magnet.agents.factory import AgentFactory
from magnet.agents.geometry_proposer import (
    GeometryProposer,
    ProposerResult,
    DesignProgram,
    GeometryOperation,
    Constraint,
    create_geometry_proposer,
    propose_geometry,
    GEOMETRY_PROPOSER_SYSTEM_PROMPT,
)

__all__ = [
    'AckType',
    'ClarificationRequest',
    'ClarificationAck',
    'ClarificationManager',
    'create_agents_router',
    'LLMClient',
    'AgentFactory',
    # Geometry Proposer (Phase 6)
    'GeometryProposer',
    'ProposerResult',
    'DesignProgram',
    'GeometryOperation',
    'Constraint',
    'create_geometry_proposer',
    'propose_geometry',
    'GEOMETRY_PROPOSER_SYSTEM_PROMPT',
]
