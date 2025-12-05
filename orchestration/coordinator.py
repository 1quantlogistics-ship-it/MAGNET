"""
MAGNET Coordinator
==================

Routes messages to appropriate agents and manages the design workflow.

From Operations Guide:
- Director handles mission phase
- NavalArchitect handles hull_form phase
- Routes based on current design phase
"""

from typing import Dict, Any, Optional, List, Type
from dataclasses import dataclass, field
from datetime import datetime

from agents.base import BaseAgent, AgentResponse
from agents.director import DirectorAgent
from agents.naval_architect import NavalArchitectAgent
from memory.file_io import MemoryFileIO
from memory.schemas import DesignPhase, SystemStateSchema
from .consensus import ConsensusEngine, ConsensusResult


@dataclass
class WorkflowStep:
    """A step in the design workflow."""

    phase: DesignPhase
    agent_type: str
    description: str
    required_inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)


# Design spiral workflow definition
DESIGN_WORKFLOW = [
    WorkflowStep(
        phase=DesignPhase.MISSION,
        agent_type="director",
        description="Interpret user requirements and create mission specification",
        required_inputs=[],
        outputs=["mission"],
    ),
    WorkflowStep(
        phase=DesignPhase.HULL_FORM,
        agent_type="naval_architect",
        description="Design hull form parameters based on mission",
        required_inputs=["mission"],
        outputs=["hull_params"],
    ),
    WorkflowStep(
        phase=DesignPhase.PROPULSION,
        agent_type="propulsion_engineer",  # Not yet implemented
        description="Design propulsion system",
        required_inputs=["mission", "hull_params"],
        outputs=["propulsion_params"],
    ),
    WorkflowStep(
        phase=DesignPhase.STRUCTURE,
        agent_type="structural_engineer",  # Not yet implemented
        description="Design structural elements and scantlings",
        required_inputs=["mission", "hull_params"],
        outputs=["structural_params"],
    ),
    # Additional phases to be implemented...
]


class Coordinator:
    """
    Multi-agent workflow coordinator.

    Routes messages to appropriate agents based on the current
    design phase and manages the design spiral workflow.
    """

    def __init__(
        self,
        memory_path: str = "memory",
        consensus_threshold: float = 0.66,
    ):
        """
        Initialize coordinator.

        Args:
            memory_path: Path to memory directory
            consensus_threshold: Threshold for consensus approval
        """
        self.memory_path = memory_path
        self.memory = MemoryFileIO(memory_path)
        self.consensus = ConsensusEngine(threshold=consensus_threshold)

        # Initialize agents (lazy loading)
        self._agents: Dict[str, BaseAgent] = {}

        # Track workflow
        self._workflow = {step.phase: step for step in DESIGN_WORKFLOW}

    def _get_agent(self, agent_type: str) -> Optional[BaseAgent]:
        """Get or create an agent by type."""
        if agent_type not in self._agents:
            if agent_type == "director":
                self._agents[agent_type] = DirectorAgent(
                    agent_id="director_001",
                    memory_path=self.memory_path,
                )
            elif agent_type == "naval_architect":
                self._agents[agent_type] = NavalArchitectAgent(
                    agent_id="naval_architect_001",
                    memory_path=self.memory_path,
                )
            else:
                # Agent type not yet implemented
                return None

        return self._agents.get(agent_type)

    def get_current_phase(self) -> DesignPhase:
        """Get current design phase from system state."""
        state = self.memory.get_system_state()
        return state.current_phase

    def get_workflow_step(self, phase: DesignPhase) -> Optional[WorkflowStep]:
        """Get workflow step for a phase."""
        return self._workflow.get(phase)

    def check_inputs_available(self, step: WorkflowStep) -> bool:
        """Check if required inputs are available for a workflow step."""
        for input_key in step.required_inputs:
            if not self.memory.exists(input_key):
                return False
        return True

    def process_message(
        self,
        message: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a user message through the appropriate agent.

        Args:
            message: User message
            session_id: Optional session identifier

        Returns:
            Response dictionary with agent output
        """
        # Get current phase
        current_phase = self.get_current_phase()
        step = self.get_workflow_step(current_phase)

        if step is None:
            return {
                "success": False,
                "error": f"No workflow step defined for phase: {current_phase}",
                "phase": current_phase.value,
            }

        # Get appropriate agent
        agent = self._get_agent(step.agent_type)

        if agent is None:
            return {
                "success": False,
                "error": f"Agent '{step.agent_type}' not yet implemented",
                "phase": current_phase.value,
                "suggestion": f"Phase {current_phase.value} requires {step.agent_type}",
            }

        # Check inputs
        if not self.check_inputs_available(step):
            missing = [k for k in step.required_inputs if not self.memory.exists(k)]
            return {
                "success": False,
                "error": f"Missing required inputs: {missing}",
                "phase": current_phase.value,
            }

        # Process through agent
        try:
            if current_phase == DesignPhase.MISSION:
                response = agent.process({"user_input": message})
            else:
                response = agent.process({})

            return {
                "success": True,
                "phase": current_phase.value,
                "agent": step.agent_type,
                "response": response.content,
                "confidence": response.confidence,
                "concerns": response.concerns,
                "proposals": response.proposals,
                "metadata": response.metadata,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "phase": current_phase.value,
                "agent": step.agent_type,
            }

    def advance_phase(self) -> Dict[str, Any]:
        """
        Advance to the next design phase.

        Returns:
            Result of phase advancement
        """
        current_phase = self.get_current_phase()
        current_step = self.get_workflow_step(current_phase)

        if current_step is None:
            return {
                "success": False,
                "error": f"Unknown current phase: {current_phase}",
            }

        # Check outputs are available
        for output_key in current_step.outputs:
            if not self.memory.exists(output_key):
                return {
                    "success": False,
                    "error": f"Cannot advance: missing output '{output_key}'",
                    "current_phase": current_phase.value,
                }

        # Find next phase
        phases = list(DesignPhase)
        current_idx = phases.index(current_phase)

        if current_idx >= len(phases) - 1:
            return {
                "success": False,
                "error": "Already at final phase",
                "current_phase": current_phase.value,
            }

        next_phase = phases[current_idx + 1]

        # Update system state
        self.memory.update_system_state(
            current_phase=next_phase,
            status=f"entering_{next_phase.value}",
        )

        return {
            "success": True,
            "previous_phase": current_phase.value,
            "current_phase": next_phase.value,
        }

    def get_design_status(self) -> Dict[str, Any]:
        """Get current design status."""
        state = self.memory.get_system_state()
        current_step = self.get_workflow_step(state.current_phase)

        # Check what's completed
        completed_outputs = []
        pending_outputs = []

        for step in DESIGN_WORKFLOW:
            for output_key in step.outputs:
                if self.memory.exists(output_key):
                    completed_outputs.append(output_key)
                else:
                    pending_outputs.append(output_key)

        return {
            "current_phase": state.current_phase.value,
            "phase_iteration": state.phase_iteration,
            "design_iteration": state.design_iteration,
            "status": state.status,
            "current_step": current_step.description if current_step else None,
            "completed_outputs": completed_outputs,
            "pending_outputs": pending_outputs,
            "active_agents": state.active_agents,
        }

    def run_consensus(
        self,
        proposal_id: str,
        agents: Optional[List[str]] = None,
    ) -> ConsensusResult:
        """
        Run consensus voting for a proposal.

        Args:
            proposal_id: Proposal to vote on
            agents: Optional list of agent types to include

        Returns:
            ConsensusResult with voting outcome
        """
        # Get votes from history
        votes = self.consensus.get_votes_for_proposal(proposal_id)

        if not votes:
            # Trigger voting from agents
            # For now, return insufficient votes
            return self.consensus.evaluate([], proposal_id)

        return self.consensus.evaluate(votes, proposal_id)


# Convenience function
def create_coordinator(
    memory_path: str = "memory",
    **kwargs,
) -> Coordinator:
    """Create a Coordinator instance."""
    return Coordinator(memory_path=memory_path, **kwargs)
