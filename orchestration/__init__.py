"""
MAGNET Orchestration Module
============================

Coordinates multi-agent design workflow.

Components:
- Coordinator: Routes messages to appropriate agents
- Consensus: Voting and agreement engine
"""

from .coordinator import Coordinator, create_coordinator
from .consensus import ConsensusEngine, ConsensusResult

__all__ = [
    "Coordinator",
    "create_coordinator",
    "ConsensusEngine",
    "ConsensusResult",
]
