"""
MAGNET Agents Module
====================

Multi-agent system for naval design.
All agents inherit from BaseAgent and communicate via file-based protocol.

Agent Types:
- Director: Interprets user requirements, manages design flow
- NavalArchitect: Hull form design, hydrostatics
- PropulsionEngineer: Propulsion system sizing and selection
- StructuralEngineer: Scantlings, structural design
- ProductionEngineer: Manufacturability review
- ClassReviewer: Classification society compliance
- MilSpecReviewer: Military specification compliance
- Supervisor: Final decision authority
- Historian: Design history tracking
- Executor: Output formatting
"""

from .base import BaseAgent, AgentMessage, AgentResponse, MockLLMAgent
from .director import DirectorAgent, create_director
from .naval_architect import NavalArchitectAgent, create_naval_architect
from .propulsion_engineer import PropulsionEngineerAgent, create_propulsion_engineer
from .structural_engineer import StructuralEngineerAgent, create_structural_engineer
from .class_reviewer import ClassReviewerAgent, create_class_reviewer, ComplianceStandard
from .supervisor import SupervisorAgent, create_supervisor, SupervisorDecision

__all__ = [
    "BaseAgent",
    "AgentMessage",
    "AgentResponse",
    "MockLLMAgent",
    "DirectorAgent",
    "create_director",
    "NavalArchitectAgent",
    "create_naval_architect",
    "PropulsionEngineerAgent",
    "create_propulsion_engineer",
    "StructuralEngineerAgent",
    "create_structural_engineer",
    "ClassReviewerAgent",
    "create_class_reviewer",
    "ComplianceStandard",
    "SupervisorAgent",
    "create_supervisor",
    "SupervisorDecision",
]
