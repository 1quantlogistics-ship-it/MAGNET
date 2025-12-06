"""
MAGNET Phase Gates
==================

Phase gate logic for design spiral progression.
Gates ensure required outputs exist before advancing phases.

Per Operations Guide:
- Each phase has required inputs and outputs
- Gates are hard requirements - cannot advance without passing
- Phase iteration allowed when gate fails with partial outputs
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from pathlib import Path

from memory.schemas import DesignPhase


@dataclass
class PhaseGate:
    """
    Definition of a phase gate.

    Attributes:
        phase: The phase this gate guards entry to
        required_inputs: Files that must exist to start phase
        required_outputs: Files that must exist to complete phase
        soft_requirements: Files that should exist but won't block
        description: Human-readable gate description
    """
    phase: DesignPhase
    required_inputs: List[str]
    required_outputs: List[str]
    soft_requirements: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class PhaseGateResult:
    """
    Result of checking a phase gate.

    Attributes:
        passed: Whether gate passed
        missing_inputs: Required inputs that are missing
        missing_outputs: Required outputs that are missing
        missing_soft: Soft requirements that are missing
        message: Human-readable result message
    """
    passed: bool
    missing_inputs: List[str] = field(default_factory=list)
    missing_outputs: List[str] = field(default_factory=list)
    missing_soft: List[str] = field(default_factory=list)
    message: str = ""


# Phase gate definitions per Operations Guide
PHASE_GATES: Dict[DesignPhase, PhaseGate] = {
    DesignPhase.MISSION: PhaseGate(
        phase=DesignPhase.MISSION,
        required_inputs=[],  # First phase - no inputs required
        required_outputs=["mission"],
        soft_requirements=[],
        description="Mission requirements must be captured",
    ),

    DesignPhase.HULL_FORM: PhaseGate(
        phase=DesignPhase.HULL_FORM,
        required_inputs=["mission"],
        required_outputs=["hull_params", "stability_results"],
        soft_requirements=["resistance_results"],
        description="Hull form defined with stability calculated",
    ),

    DesignPhase.PROPULSION: PhaseGate(
        phase=DesignPhase.PROPULSION,
        required_inputs=["mission", "hull_params"],
        required_outputs=["propulsion_config"],
        soft_requirements=["resistance_results"],
        description="Propulsion system selected and sized",
    ),

    DesignPhase.STRUCTURE: PhaseGate(
        phase=DesignPhase.STRUCTURE,
        required_inputs=["mission", "hull_params"],
        required_outputs=["structural_design"],
        soft_requirements=[],
        description="Structural scantlings designed per ABS HSNC",
    ),

    DesignPhase.ARRANGEMENT: PhaseGate(
        phase=DesignPhase.ARRANGEMENT,
        required_inputs=["mission", "hull_params", "propulsion_config"],
        required_outputs=["general_arrangement"],
        soft_requirements=["structural_design"],
        description="General arrangement completed",
    ),

    DesignPhase.WEIGHT_STABILITY: PhaseGate(
        phase=DesignPhase.WEIGHT_STABILITY,
        required_inputs=["hull_params", "structural_design", "propulsion_config"],
        required_outputs=["weight_estimate", "stability_results"],
        soft_requirements=["general_arrangement"],
        description="Weight estimated and stability verified",
    ),

    DesignPhase.COMPLIANCE: PhaseGate(
        phase=DesignPhase.COMPLIANCE,
        required_inputs=["hull_params", "structural_design", "stability_results"],
        required_outputs=["reviews"],
        soft_requirements=["supervisor_decisions"],
        description="Classification compliance verified",
    ),

    DesignPhase.PRODUCTION: PhaseGate(
        phase=DesignPhase.PRODUCTION,
        required_inputs=["reviews"],
        required_outputs=["production_package"],
        soft_requirements=[],
        description="Production documentation ready",
    ),
}


def get_required_outputs(phase: DesignPhase) -> List[str]:
    """
    Get required outputs for a phase.

    Args:
        phase: Design phase

    Returns:
        List of required output file names
    """
    gate = PHASE_GATES.get(phase)
    if gate:
        return gate.required_outputs.copy()
    return []


def get_phase_requirements(phase: DesignPhase) -> Dict[str, List[str]]:
    """
    Get all requirements for a phase.

    Args:
        phase: Design phase

    Returns:
        Dict with 'inputs', 'outputs', and 'soft' lists
    """
    gate = PHASE_GATES.get(phase)
    if gate:
        return {
            "inputs": gate.required_inputs.copy(),
            "outputs": gate.required_outputs.copy(),
            "soft": gate.soft_requirements.copy(),
        }
    return {"inputs": [], "outputs": [], "soft": []}


def check_phase_gate(
    phase: DesignPhase,
    memory_path: str,
    check_completion: bool = False,
) -> PhaseGateResult:
    """
    Check if a phase gate is satisfied.

    Args:
        phase: Phase to check gate for
        memory_path: Path to memory directory
        check_completion: If True, check outputs; if False, check inputs only

    Returns:
        PhaseGateResult with pass/fail and missing items
    """
    gate = PHASE_GATES.get(phase)
    if not gate:
        return PhaseGateResult(
            passed=False,
            message=f"Unknown phase: {phase}",
        )

    memory_dir = Path(memory_path)

    # Check required inputs
    missing_inputs = []
    for input_file in gate.required_inputs:
        file_path = memory_dir / f"{input_file}.json"
        if not file_path.exists():
            missing_inputs.append(input_file)

    # Check outputs if requested (for completion check)
    missing_outputs = []
    if check_completion:
        for output_file in gate.required_outputs:
            file_path = memory_dir / f"{output_file}.json"
            if not file_path.exists():
                missing_outputs.append(output_file)

    # Check soft requirements
    missing_soft = []
    for soft_file in gate.soft_requirements:
        file_path = memory_dir / f"{soft_file}.json"
        if not file_path.exists():
            missing_soft.append(soft_file)

    # Determine if gate passed
    if check_completion:
        passed = len(missing_inputs) == 0 and len(missing_outputs) == 0
    else:
        passed = len(missing_inputs) == 0

    # Generate message
    if passed:
        message = f"Phase gate for {phase.value} passed"
        if missing_soft:
            message += f" (soft requirements missing: {missing_soft})"
    else:
        parts = []
        if missing_inputs:
            parts.append(f"missing inputs: {missing_inputs}")
        if missing_outputs:
            parts.append(f"missing outputs: {missing_outputs}")
        message = f"Phase gate for {phase.value} failed - {', '.join(parts)}"

    return PhaseGateResult(
        passed=passed,
        missing_inputs=missing_inputs,
        missing_outputs=missing_outputs,
        missing_soft=missing_soft,
        message=message,
    )


def can_advance_to_phase(
    target_phase: DesignPhase,
    memory_path: str,
) -> Tuple[bool, str]:
    """
    Check if design can advance to a target phase.

    Args:
        target_phase: Phase to advance to
        memory_path: Path to memory directory

    Returns:
        Tuple of (can_advance, reason)
    """
    # Get phases in order
    phases = list(DesignPhase)
    target_idx = phases.index(target_phase)

    # Check all preceding phases are complete
    for i in range(target_idx):
        prev_phase = phases[i]
        result = check_phase_gate(prev_phase, memory_path, check_completion=True)
        if not result.passed:
            return False, f"Cannot advance: {prev_phase.value} not complete - {result.message}"

    # Check target phase inputs are available
    result = check_phase_gate(target_phase, memory_path, check_completion=False)
    if not result.passed:
        return False, f"Cannot start {target_phase.value}: {result.message}"

    return True, f"Ready to advance to {target_phase.value}"


def get_next_phase(current_phase: DesignPhase) -> Optional[DesignPhase]:
    """
    Get the next phase in the design spiral.

    Args:
        current_phase: Current design phase

    Returns:
        Next phase, or None if at final phase
    """
    phases = list(DesignPhase)
    try:
        idx = phases.index(current_phase)
        if idx < len(phases) - 1:
            return phases[idx + 1]
        return None
    except ValueError:
        return None


def get_phase_order() -> List[DesignPhase]:
    """
    Get phases in design spiral order.

    Returns:
        Ordered list of design phases
    """
    return list(DesignPhase)
