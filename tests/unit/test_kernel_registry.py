"""
tests/unit/test_kernel_registry.py - Tests for kernel registry.

BRAVO OWNS THIS FILE.

Tests for Module 15 v1.1 - PhaseRegistry and PhaseDefinition.
"""

import pytest
from magnet.kernel import (
    PhaseDefinition,
    PhaseRegistry,
    PHASE_DEFINITIONS,
    PhaseType,
    GateCondition,
)


class TestPhaseDefinition:
    """Tests for PhaseDefinition dataclass."""

    def test_create_phase_definition(self):
        """Test basic phase definition creation."""
        phase = PhaseDefinition(
            name="test_phase",
            description="Test phase description",
            phase_type=PhaseType.ANALYSIS,
        )
        assert phase.name == "test_phase"
        assert phase.description == "Test phase description"
        assert phase.phase_type == PhaseType.ANALYSIS

    def test_default_values(self):
        """Test default values."""
        phase = PhaseDefinition(
            name="test",
            description="test",
            phase_type=PhaseType.DEFINITION,
        )
        assert phase.order == 0
        assert phase.depends_on == []
        assert phase.validators == []
        assert phase.is_gate == False
        assert phase.gate_condition == GateCondition.ALL_PASS
        assert phase.gate_threshold == 1.0
        assert phase.state_namespace == ""

    def test_phase_with_dependencies(self):
        """Test phase with dependencies."""
        phase = PhaseDefinition(
            name="stability",
            description="Stability analysis",
            phase_type=PhaseType.ANALYSIS,
            order=6,
            depends_on=["weight", "hull"],
            validators=["stability/intact_gm"],
        )
        assert phase.depends_on == ["weight", "hull"]
        assert len(phase.validators) == 1

    def test_gate_phase(self):
        """Test gate phase configuration."""
        phase = PhaseDefinition(
            name="compliance",
            description="Compliance check",
            phase_type=PhaseType.VERIFICATION,
            is_gate=True,
            gate_condition=GateCondition.CRITICAL_PASS,
        )
        assert phase.is_gate == True
        assert phase.gate_condition == GateCondition.CRITICAL_PASS

    def test_to_dict(self):
        """Test dictionary serialization."""
        phase = PhaseDefinition(
            name="hull",
            description="Hull analysis",
            phase_type=PhaseType.ANALYSIS,
            order=2,
            depends_on=["mission"],
            validators=["hull/form"],
            state_namespace="hull",
        )
        data = phase.to_dict()

        assert data["name"] == "hull"
        assert data["description"] == "Hull analysis"
        assert data["phase_type"] == "analysis"
        assert data["order"] == 2
        assert data["depends_on"] == ["mission"]
        assert data["validators"] == ["hull/form"]
        assert data["state_namespace"] == "hull"
        assert data["is_gate"] == False

    def test_to_dict_gate(self):
        """Test dictionary serialization for gate."""
        phase = PhaseDefinition(
            name="compliance",
            description="Compliance",
            phase_type=PhaseType.VERIFICATION,
            is_gate=True,
            gate_condition=GateCondition.THRESHOLD,
            gate_threshold=0.9,
        )
        data = phase.to_dict()

        assert data["is_gate"] == True
        assert data["gate_condition"] == "threshold"
        assert data["gate_threshold"] == 0.9


class TestPHASE_DEFINITIONS:
    """Tests for standard PHASE_DEFINITIONS."""

    def test_definitions_exist(self):
        """Test standard definitions exist."""
        assert "mission" in PHASE_DEFINITIONS
        assert "hull" in PHASE_DEFINITIONS
        assert "structure" in PHASE_DEFINITIONS
        assert "propulsion" in PHASE_DEFINITIONS
        assert "weight" in PHASE_DEFINITIONS
        assert "stability" in PHASE_DEFINITIONS
        assert "loading" in PHASE_DEFINITIONS
        assert "arrangement" in PHASE_DEFINITIONS
        assert "compliance" in PHASE_DEFINITIONS
        assert "production" in PHASE_DEFINITIONS
        assert "cost" in PHASE_DEFINITIONS
        assert "optimization" in PHASE_DEFINITIONS
        assert "reporting" in PHASE_DEFINITIONS

    def test_mission_is_first(self):
        """Test mission phase is first."""
        mission = PHASE_DEFINITIONS["mission"]
        assert mission.order == 1
        assert mission.depends_on == []

    def test_compliance_is_gate(self):
        """Test compliance phase is a gate."""
        compliance = PHASE_DEFINITIONS["compliance"]
        assert compliance.is_gate == True
        assert compliance.gate_condition == GateCondition.CRITICAL_PASS

    def test_phase_ordering(self):
        """Test phases have increasing order."""
        orders = [p.order for p in PHASE_DEFINITIONS.values()]
        assert orders == sorted(orders)

    def test_dependencies_reference_existing_phases(self):
        """Test all dependencies reference existing phases."""
        for name, phase in PHASE_DEFINITIONS.items():
            for dep in phase.depends_on:
                assert dep in PHASE_DEFINITIONS, f"{name} depends on non-existent {dep}"


class TestPhaseRegistry:
    """Tests for PhaseRegistry."""

    def test_create_registry(self):
        """Test registry creation loads standard phases."""
        registry = PhaseRegistry()
        assert len(registry._phases) > 0

    def test_get_phase(self):
        """Test getting a phase by name."""
        registry = PhaseRegistry()
        hull = registry.get_phase("hull")

        assert hull is not None
        assert hull.name == "hull"

    def test_get_phase_not_found(self):
        """Test getting non-existent phase returns None."""
        registry = PhaseRegistry()
        result = registry.get_phase("nonexistent")

        assert result is None

    def test_register_phase(self):
        """Test registering a new phase."""
        registry = PhaseRegistry()
        custom_phase = PhaseDefinition(
            name="custom",
            description="Custom phase",
            phase_type=PhaseType.CUSTOM,
            order=100,
        )

        registry.register_phase(custom_phase)

        assert registry.get_phase("custom") is not None

    def test_get_phases_in_order(self):
        """Test getting phases in order."""
        registry = PhaseRegistry()
        phases = registry.get_phases_in_order()

        assert len(phases) > 0
        # Verify ordering
        for i in range(1, len(phases)):
            assert phases[i].order >= phases[i-1].order

    def test_get_phases_for_namespace(self):
        """Test getting phases by namespace."""
        registry = PhaseRegistry()
        hull_phases = registry.get_phases_for_namespace("hull")

        assert len(hull_phases) >= 1
        assert all(p.state_namespace == "hull" for p in hull_phases)

    def test_get_dependencies_direct(self):
        """Test getting direct dependencies."""
        registry = PhaseRegistry()
        deps = registry.get_dependencies("stability")

        # Stability depends on weight (and weight has dependencies)
        assert "weight" in deps

    def test_get_dependencies_transitive(self):
        """Test getting transitive dependencies."""
        registry = PhaseRegistry()
        deps = registry.get_dependencies("compliance")

        # Compliance -> stability -> weight -> hull/structure/propulsion -> mission
        assert "mission" in deps or "hull" in deps

    def test_get_dependencies_no_deps(self):
        """Test getting dependencies for phase with none."""
        registry = PhaseRegistry()
        deps = registry.get_dependencies("mission")

        assert deps == []

    def test_get_dependencies_unknown_phase(self):
        """Test getting dependencies for unknown phase."""
        registry = PhaseRegistry()
        deps = registry.get_dependencies("nonexistent")

        assert deps == []

    def test_get_dependents(self):
        """Test getting phases that depend on a phase."""
        registry = PhaseRegistry()
        dependents = registry.get_dependents("mission")

        # Hull depends on mission
        assert "hull" in dependents

    def test_get_gate_phases(self):
        """Test getting gate phases."""
        registry = PhaseRegistry()
        gates = registry.get_gate_phases()

        assert len(gates) >= 1
        assert all(p.is_gate for p in gates)
        # Compliance should be a gate
        gate_names = [p.name for p in gates]
        assert "compliance" in gate_names

    def test_to_dict(self):
        """Test registry serialization."""
        registry = PhaseRegistry()
        data = registry.to_dict()

        assert "phases" in data
        assert "validators" in data
        assert len(data["phases"]) > 0


class TestPhaseType:
    """Tests for PhaseType enum."""

    def test_all_types_exist(self):
        """Test all expected types exist."""
        assert PhaseType.DEFINITION.value == "definition"
        assert PhaseType.ANALYSIS.value == "analysis"
        assert PhaseType.INTEGRATION.value == "integration"
        assert PhaseType.VERIFICATION.value == "verification"
        assert PhaseType.OUTPUT.value == "output"
