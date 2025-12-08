"""
kernel/registry.py - Phase and validator registry.

BRAVO OWNS THIS FILE.

Module 15 v1.1 - Phase registry and definitions.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .enums import GateCondition, PhaseType

if TYPE_CHECKING:
    from ..validators.taxonomy import ValidatorDefinition


@dataclass
class PhaseDefinition:
    """Definition of a design phase."""
    name: str
    description: str
    phase_type: PhaseType

    order: int = 0
    depends_on: List[str] = field(default_factory=list)
    validators: List[str] = field(default_factory=list)

    is_gate: bool = False
    gate_condition: GateCondition = GateCondition.ALL_PASS
    gate_threshold: float = 1.0

    state_namespace: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "phase_type": self.phase_type.value,
            "order": self.order,
            "depends_on": self.depends_on,
            "validators": self.validators,
            "is_gate": self.is_gate,
            "gate_condition": self.gate_condition.value if self.is_gate else None,
            "gate_threshold": self.gate_threshold if self.is_gate else None,
            "state_namespace": self.state_namespace,
        }


# Standard phase definitions
PHASE_DEFINITIONS = {
    "mission": PhaseDefinition(
        name="mission",
        description="Mission requirements and configuration",
        phase_type=PhaseType.DEFINITION,
        order=1,
        validators=["mission/requirements"],
        state_namespace="mission",
    ),
    "hull": PhaseDefinition(
        name="hull",
        description="Hull form definition and hydrostatics",
        phase_type=PhaseType.ANALYSIS,
        order=2,
        depends_on=["mission"],
        validators=["hull/form", "physics/hydrostatics"],
        state_namespace="hull",
    ),
    "structure": PhaseDefinition(
        name="structure",
        description="Structural design and analysis",
        phase_type=PhaseType.ANALYSIS,
        order=3,
        depends_on=["hull"],
        validators=["structure/scantlings"],
        state_namespace="structure",
    ),
    "propulsion": PhaseDefinition(
        name="propulsion",
        description="Propulsion system sizing",
        phase_type=PhaseType.ANALYSIS,
        order=4,
        depends_on=["hull"],
        validators=["propulsion/sizing"],
        state_namespace="propulsion",
    ),
    "weight": PhaseDefinition(
        name="weight",
        description="Weight estimation",
        phase_type=PhaseType.ANALYSIS,
        order=5,
        depends_on=["hull", "structure", "propulsion"],
        validators=["weight/estimation"],
        state_namespace="weight",
    ),
    "stability": PhaseDefinition(
        name="stability",
        description="Stability analysis",
        phase_type=PhaseType.ANALYSIS,
        order=6,
        depends_on=["weight"],
        validators=["stability/intact_gm", "stability/gz_curve"],
        state_namespace="stability",
    ),
    "loading": PhaseDefinition(
        name="loading",
        description="Loading conditions",
        phase_type=PhaseType.INTEGRATION,
        order=7,
        depends_on=["weight", "stability"],
        validators=["loading/computer"],
        state_namespace="loading",
    ),
    "arrangement": PhaseDefinition(
        name="arrangement",
        description="General arrangement",
        phase_type=PhaseType.INTEGRATION,
        order=8,
        depends_on=["hull"],
        validators=["arrangement/generator"],
        state_namespace="arrangement",
    ),
    "compliance": PhaseDefinition(
        name="compliance",
        description="Regulatory compliance verification",
        phase_type=PhaseType.VERIFICATION,
        order=9,
        depends_on=["stability", "loading"],
        validators=["compliance/regulatory"],
        is_gate=True,
        gate_condition=GateCondition.CRITICAL_PASS,
        state_namespace="compliance",
    ),
    "production": PhaseDefinition(
        name="production",
        description="Production planning",
        phase_type=PhaseType.VERIFICATION,
        order=10,
        depends_on=["structure", "weight"],
        validators=["production/planning"],
        state_namespace="production",
    ),
    "cost": PhaseDefinition(
        name="cost",
        description="Cost estimation",
        phase_type=PhaseType.VERIFICATION,
        order=11,
        depends_on=["production"],
        validators=["cost/estimation"],
        state_namespace="cost",
    ),
    "optimization": PhaseDefinition(
        name="optimization",
        description="Design optimization",
        phase_type=PhaseType.OUTPUT,
        order=12,
        depends_on=["cost", "compliance"],
        validators=["optimization/design"],
        state_namespace="optimization",
    ),
    "reporting": PhaseDefinition(
        name="reporting",
        description="Report generation",
        phase_type=PhaseType.OUTPUT,
        order=13,
        depends_on=["compliance", "cost"],
        validators=["reporting/generator"],
        state_namespace="reports",
    ),
}


class PhaseRegistry:
    """Registry for phases and validators."""

    def __init__(self, load_defaults: bool = True):
        """
        Initialize registry.

        Args:
            load_defaults: If True, load standard PHASE_DEFINITIONS
        """
        self._phases: Dict[str, PhaseDefinition] = {}
        self._validators: Dict[str, tuple] = {}

        # Load standard phases if requested
        if load_defaults:
            for name, phase in PHASE_DEFINITIONS.items():
                self.register_phase(phase)

    def register_phase(self, phase: PhaseDefinition) -> None:
        """Register a phase definition."""
        self._phases[phase.name] = phase

    def register_validator(
        self,
        definition: 'ValidatorDefinition',
        validator_class: type,
    ) -> None:
        """Register a validator."""
        self._validators[definition.validator_id] = (definition, validator_class)

    def get_phase(self, name: str) -> Optional[PhaseDefinition]:
        """Get phase by name."""
        return self._phases.get(name)

    def get_phases_in_order(self) -> List[PhaseDefinition]:
        """Get phases in execution order."""
        return sorted(self._phases.values(), key=lambda p: p.order)

    def get_validator(self, validator_id: str) -> Optional[tuple]:
        """Get validator definition and class."""
        return self._validators.get(validator_id)

    def get_phases_for_namespace(self, namespace: str) -> List[PhaseDefinition]:
        """Get phases that write to a namespace."""
        return [p for p in self._phases.values() if p.state_namespace == namespace]

    def get_dependencies(self, phase_name: str) -> List[str]:
        """Get phase dependencies (transitive)."""
        phase = self._phases.get(phase_name)
        if not phase:
            return []

        deps = set()
        queue = list(phase.depends_on)

        while queue:
            dep = queue.pop(0)
            if dep not in deps:
                deps.add(dep)
                dep_phase = self._phases.get(dep)
                if dep_phase:
                    queue.extend(dep_phase.depends_on)

        return list(deps)

    def get_dependents(self, phase_name: str) -> List[str]:
        """Get phases that depend on this phase."""
        dependents = []
        for name, phase in self._phases.items():
            if phase_name in phase.depends_on:
                dependents.append(name)
        return dependents

    def get_gate_phases(self) -> List[PhaseDefinition]:
        """Get all gate phases."""
        return [p for p in self._phases.values() if p.is_gate]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize registry to dictionary."""
        return {
            "phases": {k: v.to_dict() for k, v in self._phases.items()},
            "validators": list(self._validators.keys()),
        }
