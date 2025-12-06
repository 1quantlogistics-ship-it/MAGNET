"""
MAGNET Supervisor Agent
========================

The Supervisor agent has final decision authority on design proposals.

Responsibilities:
- Veto proposals that violate hard constraints
- Override consensus when safety is at stake
- Log all decisions for audit trail
- Enforce design intent preservation

Communication Flow (from Operations Guide):
1. Consensus engine evaluates votes from all agents
2. Supervisor reviews proposals flagged for attention
3. Supervisor can approve, reject, or revise with conditions
4. All decisions logged to supervisor_decisions.jsonl
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from .base import BaseAgent, AgentResponse
from memory.file_io import MemoryFileIO
from memory.schemas import DesignPhase, VoteType


class SupervisorDecision(Enum):
    """Supervisor decision types."""
    APPROVE = "approve"
    REJECT = "reject"
    REVISE = "revise"
    DEFER = "defer"
    ESCALATE = "escalate"


class ConstraintType(Enum):
    """Types of hard constraints."""
    SAFETY = "safety"
    CLASSIFICATION = "classification"
    PHYSICS = "physics"
    MISSION = "mission"
    REGULATORY = "regulatory"


class HardConstraint:
    """Definition of a hard constraint that cannot be violated."""

    def __init__(
        self,
        name: str,
        constraint_type: ConstraintType,
        description: str,
        check_fn: callable,
    ):
        self.name = name
        self.constraint_type = constraint_type
        self.description = description
        self.check_fn = check_fn

    def evaluate(self, design_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Evaluate constraint against design data.

        Returns:
            Tuple of (passed, message)
        """
        try:
            return self.check_fn(design_data)
        except Exception as e:
            return False, f"Constraint evaluation error: {str(e)}"


class SupervisorAgent(BaseAgent):
    """
    Supervisor Agent - Final Decision Authority.

    Has veto power over design proposals and enforces hard constraints:
    - Safety constraints (stability, structural)
    - Classification constraints (ABS HSNC, IMO)
    - Physics constraints (bounds, feasibility)
    - Mission constraints (design intent)
    """

    SUPERVISOR_PROMPT = """You are the Supervisor Agent for MAGNET (Multi-Agent Guided Naval Engineering Testbed).

Your role is to make final decisions on design proposals with veto authority.

## Your Responsibilities:
1. Review proposals flagged by other agents
2. Enforce hard constraints (safety, classification, physics)
3. Veto proposals that violate safety requirements
4. Override consensus when design integrity is at stake
5. Log all decisions for audit trail
6. Preserve design intent across iterations

## Decision Authority:
- APPROVE: Proposal meets all constraints
- REJECT: Proposal violates hard constraints
- REVISE: Proposal needs modifications
- DEFER: Insufficient information to decide
- ESCALATE: Requires external review

## Hard Constraints (NEVER Compromise):
1. Stability: GM > 0.15m, IMO A.749 compliance
2. Structural: ABS HSNC minimum scantlings
3. Materials: No prohibited alloys (6xxx series)
4. Physics: Parameters within feasible bounds

## Output Format:
Respond with decision and reasoning followed by JSON with DECISION_JSON: marker.

Example output:
```
DECISION: REJECT

Proposal violates hard safety constraints:
- GM = 0.10m is below minimum 0.15m (IMO A.749)
- Insufficient stability margin for operational sea states

DECISION_JSON:
{
  "decision": "REJECT",
  "constraints_violated": ["stability/gm_minimum"],
  "reasoning": "GM below IMO A.749 minimum",
  "conditions": [],
  "escalate": false
}
```
"""

    def __init__(
        self,
        agent_id: str = "supervisor_001",
        memory_path: str = "memory",
        **kwargs
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="supervisor",
            memory_path=memory_path,
            **kwargs
        )
        self._hard_constraints = self._define_hard_constraints()

    @property
    def system_prompt(self) -> str:
        return self.SUPERVISOR_PROMPT

    def _define_hard_constraints(self) -> List[HardConstraint]:
        """Define hard constraints that cannot be violated."""
        constraints = []

        # Stability constraint: GM > 0.15m
        constraints.append(HardConstraint(
            name="stability/gm_minimum",
            constraint_type=ConstraintType.SAFETY,
            description="Metacentric height must exceed 0.15m (IMO A.749)",
            check_fn=self._check_gm_minimum,
        ))

        # Stability constraint: IMO criteria
        constraints.append(HardConstraint(
            name="stability/imo_criteria",
            constraint_type=ConstraintType.CLASSIFICATION,
            description="Must pass all IMO A.749 intact stability criteria",
            check_fn=self._check_imo_criteria,
        ))

        # Material constraint: No 6xxx series
        constraints.append(HardConstraint(
            name="material/no_prohibited_alloys",
            constraint_type=ConstraintType.CLASSIFICATION,
            description="6xxx series alloys prohibited in primary structure",
            check_fn=self._check_no_prohibited_alloys,
        ))

        # Structural constraint: Plating compliance
        constraints.append(HardConstraint(
            name="structural/plating_compliant",
            constraint_type=ConstraintType.CLASSIFICATION,
            description="All plating must meet ABS HSNC minimum thickness",
            check_fn=self._check_plating_compliance,
        ))

        # Physics constraint: Positive displacement
        constraints.append(HardConstraint(
            name="physics/positive_displacement",
            constraint_type=ConstraintType.PHYSICS,
            description="Displacement must be positive",
            check_fn=self._check_positive_displacement,
        ))

        return constraints

    def _check_gm_minimum(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """Check GM is above minimum."""
        stability = data.get("stability_results", {})
        gm = stability.get("GM", None)

        if gm is None:
            return True, "GM not yet calculated"

        if gm >= 0.15:
            return True, f"GM = {gm:.3f}m meets minimum 0.15m"
        else:
            return False, f"GM = {gm:.3f}m is below minimum 0.15m"

    def _check_imo_criteria(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """Check IMO A.749 criteria."""
        stability = data.get("stability_results", {})
        passed = stability.get("imo_criteria_passed", None)

        if passed is None:
            return True, "IMO criteria not yet evaluated"

        if passed:
            return True, "IMO A.749 criteria satisfied"
        else:
            return False, "One or more IMO A.749 criteria not met"

    def _check_no_prohibited_alloys(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """Check for prohibited 6xxx alloys."""
        structural = data.get("structural_design", {})
        material = structural.get("material", {})
        alloy = material.get("alloy", "")

        if not alloy:
            return True, "Material not yet specified"

        prohibited = ["6061", "6063", "6082"]
        for p in prohibited:
            if p in alloy:
                return False, f"Alloy {alloy} is PROHIBITED for primary structure"

        return True, f"Alloy {alloy} is acceptable"

    def _check_plating_compliance(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """Check plating compliance."""
        structural = data.get("structural_design", {})
        summary = structural.get("summary", {})
        compliant = summary.get("all_plating_compliant", None)

        if compliant is None:
            return True, "Plating not yet designed"

        if compliant:
            return True, "All plating meets requirements"
        else:
            return False, "Some plating does not meet minimum thickness"

    def _check_positive_displacement(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """Check displacement is positive."""
        hull = data.get("hull_params", {})
        displacement = hull.get("displacement_tonnes", None)

        if displacement is None:
            return True, "Displacement not yet calculated"

        if displacement > 0:
            return True, f"Displacement = {displacement:.0f}t is positive"
        else:
            return False, f"Displacement = {displacement:.0f}t must be positive"

    def _read_design_data(self) -> Dict[str, Optional[Dict]]:
        """Read all relevant design data from memory."""
        return {
            "mission": self.memory.read("mission"),
            "hull_params": self.memory.read("hull_params"),
            "stability_results": self.memory.read("stability_results"),
            "structural_design": self.memory.read("structural_design"),
            "propulsion_config": self.memory.read("propulsion_config"),
            "reviews": self.memory.read("reviews"),
        }

    def _evaluate_constraints(
        self,
        design_data: Dict[str, Any],
    ) -> tuple[bool, List[Dict[str, Any]]]:
        """
        Evaluate all hard constraints.

        Returns:
            Tuple of (all_passed, results)
        """
        results = []
        all_passed = True

        for constraint in self._hard_constraints:
            passed, message = constraint.evaluate(design_data)
            results.append({
                "name": constraint.name,
                "type": constraint.constraint_type.value,
                "passed": passed,
                "message": message,
            })
            if not passed:
                all_passed = False

        return all_passed, results

    def _check_consensus_override_needed(
        self,
        design_data: Dict[str, Any],
    ) -> tuple[bool, str]:
        """Check if supervisor should override consensus."""
        reviews = design_data.get("reviews", {})

        if not reviews:
            return False, "No reviews to override"

        # Check if class reviewer flagged critical issues
        vote = reviews.get("vote", "")
        failed = reviews.get("summary", {}).get("failed", 0)

        if vote == "reject" and failed > 0:
            return True, f"Class reviewer rejected with {failed} failed checks"

        return False, "No override needed"

    def supervise_design(
        self,
        design_data: Optional[Dict[str, Dict]] = None,
        force_review: bool = False,
    ) -> AgentResponse:
        """
        Review and supervise current design.

        Args:
            design_data: Optional design data (reads from memory if not provided)
            force_review: Force full review even if constraints pass

        Returns:
            AgentResponse with supervision decision
        """
        # Read from memory if not provided
        if design_data is None:
            design_data = self._read_design_data()

        # Evaluate hard constraints
        all_passed, constraint_results = self._evaluate_constraints(design_data)

        # Check if override needed
        override_needed, override_reason = self._check_consensus_override_needed(design_data)

        # Determine decision
        violations = [r for r in constraint_results if not r["passed"]]
        warnings = []
        conditions = []

        if len(violations) > 0:
            decision = SupervisorDecision.REJECT
            decision_reason = f"Violates {len(violations)} hard constraint(s)"
            confidence = 0.95
        elif override_needed:
            decision = SupervisorDecision.REVISE
            decision_reason = override_reason
            conditions.append("Address class reviewer concerns")
            confidence = 0.80
        elif force_review:
            decision = SupervisorDecision.APPROVE
            decision_reason = "Manual review requested, all constraints satisfied"
            confidence = 0.85
        else:
            decision = SupervisorDecision.APPROVE
            decision_reason = "All hard constraints satisfied"
            confidence = 0.90

        # Build decision output
        decision_output = {
            "decision": decision.value,
            "confidence": confidence,
            "reasoning": decision_reason,
            "constraint_results": constraint_results,
            "violations": [v["name"] for v in violations],
            "override_consensus": override_needed,
            "override_reason": override_reason if override_needed else None,
            "conditions": conditions,
            "supervised_by": self.agent_id,
            "timestamp": datetime.now().isoformat(),
        }

        # Log decision
        self.memory.append_log("supervisor_decisions", decision_output)

        # Log to agent decision history
        self.log_decision({
            "action": "supervision",
            "decision": decision.value,
            "violations": len(violations),
            "override": override_needed,
        })

        # Build response content
        decision_emoji = {
            "approve": "✓",
            "reject": "✗",
            "revise": "↻",
            "defer": "○",
            "escalate": "⚠",
        }.get(decision.value, "?")

        content = (
            f"Supervisor [{decision_emoji} {decision.value.upper()}]: "
            f"{decision_reason} | "
            f"Constraints: {len(constraint_results) - len(violations)}/{len(constraint_results)} passed"
        )

        concerns = [v["message"] for v in violations[:5]]

        return AgentResponse(
            agent_id=self.agent_id,
            content=content,
            confidence=confidence,
            reasoning=decision_reason,
            proposals=[decision_output],
            concerns=concerns,
            metadata={
                "decision": decision.value,
                "violations": len(violations),
                "constraints_checked": len(constraint_results),
                "override_consensus": override_needed,
            },
        )

    def veto_proposal(
        self,
        proposal_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Exercise veto authority on a proposal.

        Args:
            proposal_id: Proposal to veto
            reason: Reason for veto

        Returns:
            Veto record
        """
        veto_record = {
            "action": "veto",
            "proposal_id": proposal_id,
            "reason": reason,
            "vetoed_by": self.agent_id,
            "timestamp": datetime.now().isoformat(),
        }

        self.memory.append_log("supervisor_decisions", veto_record)

        self.log_decision({
            "action": "veto",
            "proposal_id": proposal_id,
            "reason": reason,
        })

        return veto_record

    def override_consensus(
        self,
        decision: SupervisorDecision,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Override consensus decision.

        Args:
            decision: Supervisor's override decision
            reason: Reason for override

        Returns:
            Override record
        """
        override_record = {
            "action": "override",
            "decision": decision.value,
            "reason": reason,
            "overridden_by": self.agent_id,
            "timestamp": datetime.now().isoformat(),
        }

        self.memory.append_log("supervisor_decisions", override_record)

        self.log_decision({
            "action": "override",
            "decision": decision.value,
            "reason": reason,
        })

        return override_record

    def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Process input - main entry point.

        Args:
            input_data: Optional design data or empty to read from memory

        Returns:
            AgentResponse with supervision decision
        """
        design_data = input_data if input_data else None
        force_review = input_data.get("force_review", False) if input_data else False
        return self.supervise_design(design_data, force_review)


# Convenience function
def create_supervisor(
    memory_path: str = "memory",
    **kwargs
) -> SupervisorAgent:
    """Create a Supervisor agent instance."""
    return SupervisorAgent(memory_path=memory_path, **kwargs)
