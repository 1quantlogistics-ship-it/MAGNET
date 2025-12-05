"""
MAGNET Agents Module
====================

Multi-agent system for naval design.
All agents inherit from BaseAgent and communicate via file-based protocol.

Agent Types:
- Director: Interprets user requirements, manages design flow
- NavalArchitect: Hull form design, hydrostatics
- StructuralEngineer: Scantlings, structural design
- ProductionEngineer: Manufacturability review
- ClassReviewer: Classification society compliance
- MilSpecReviewer: Military specification compliance
- Supervisor: Final decision authority
- Historian: Design history tracking
- Executor: Output formatting
"""

from .base import BaseAgent, AgentMessage, AgentResponse

__all__ = [
    "BaseAgent",
    "AgentMessage",
    "AgentResponse",
]
