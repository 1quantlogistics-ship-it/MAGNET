"""
Unit tests for validators/topology.py

Tests validator dependency graph construction and traversal.
"""

import pytest

from magnet.validators.topology import (
    ValidatorTopology,
    TopologyNode,
    ExecutionGroup,
    TopologyError,
    CyclicDependencyError,
)
from magnet.validators.taxonomy import (
    ValidatorDefinition,
    ValidatorCategory,
    ValidatorPriority,
)


class TestTopologyNode:
    """Test TopologyNode dataclass."""

    def test_create_node(self):
        """Test creating a topology node."""
        defn = ValidatorDefinition(
            validator_id="test/node",
            name="Test Node",
            description="A test node",
            category=ValidatorCategory.PHYSICS,
        )
        node = TopologyNode(validator=defn)
        assert node.depth == 0
        assert len(node.depends_on) == 0

    def test_all_dependencies(self):
        """Test all_dependencies property combines explicit and implicit."""
        defn = ValidatorDefinition(
            validator_id="test/deps",
            name="Test Deps",
            description="Test dependencies",
            category=ValidatorCategory.PHYSICS,
        )
        node = TopologyNode(
            validator=defn,
            depends_on={"explicit/dep"},
            implicit_depends_on={"implicit/dep"},
        )
        all_deps = node.all_dependencies
        assert "explicit/dep" in all_deps
        assert "implicit/dep" in all_deps
        assert len(all_deps) == 2

    def test_can_run(self):
        """Test can_run method."""
        defn = ValidatorDefinition(
            validator_id="test/can_run",
            name="Test Can Run",
            description="Test can run",
            category=ValidatorCategory.PHYSICS,
        )
        node = TopologyNode(
            validator=defn,
            depends_on={"dep/a", "dep/b"},
        )

        # Cannot run without dependencies
        assert node.can_run(set()) == False
        assert node.can_run({"dep/a"}) == False

        # Can run with all dependencies completed
        assert node.can_run({"dep/a", "dep/b"}) == True
        assert node.can_run({"dep/a", "dep/b", "dep/c"}) == True


class TestValidatorTopology:
    """Test ValidatorTopology class."""

    def test_create_empty_topology(self):
        """Test creating empty topology."""
        topology = ValidatorTopology()
        assert topology.validator_count == 0
        assert topology.is_built == False

    def test_add_validator(self):
        """Test adding a validator."""
        topology = ValidatorTopology()
        defn = ValidatorDefinition(
            validator_id="test/add",
            name="Test Add",
            description="Test add",
            category=ValidatorCategory.PHYSICS,
        )
        topology.add_validator(defn)
        assert topology.validator_count == 1

    def test_add_all_validators(self):
        """Test adding all built-in validators."""
        topology = ValidatorTopology()
        topology.add_all_validators()
        assert topology.validator_count > 0

    def test_build_simple_topology(self):
        """Test building a simple linear topology: A -> B -> C."""
        topology = ValidatorTopology()

        # A has no dependencies
        topology.add_validator(ValidatorDefinition(
            validator_id="test/a",
            name="A",
            description="First",
            category=ValidatorCategory.PHYSICS,
        ))

        # B depends on A
        topology.add_validator(ValidatorDefinition(
            validator_id="test/b",
            name="B",
            description="Second",
            category=ValidatorCategory.PHYSICS,
            depends_on_validators=["test/a"],
        ))

        # C depends on B
        topology.add_validator(ValidatorDefinition(
            validator_id="test/c",
            name="C",
            description="Third",
            category=ValidatorCategory.PHYSICS,
            depends_on_validators=["test/b"],
        ))

        topology.build()

        assert topology.is_built == True

        # Check depths
        assert topology.get_node("test/a").depth == 0
        assert topology.get_node("test/b").depth == 1
        assert topology.get_node("test/c").depth == 2

    def test_build_parallel_topology(self):
        """Test topology with parallel validators."""
        topology = ValidatorTopology()

        # A and B have no dependencies (can run in parallel)
        topology.add_validator(ValidatorDefinition(
            validator_id="test/a",
            name="A",
            description="First",
            category=ValidatorCategory.PHYSICS,
        ))
        topology.add_validator(ValidatorDefinition(
            validator_id="test/b",
            name="B",
            description="Second",
            category=ValidatorCategory.PHYSICS,
        ))

        # C depends on both A and B
        topology.add_validator(ValidatorDefinition(
            validator_id="test/c",
            name="C",
            description="Third",
            category=ValidatorCategory.PHYSICS,
            depends_on_validators=["test/a", "test/b"],
        ))

        topology.build()

        # A and B at depth 0
        assert topology.get_node("test/a").depth == 0
        assert topology.get_node("test/b").depth == 0

        # C at depth 1
        assert topology.get_node("test/c").depth == 1

    def test_cycle_detection(self):
        """Test cycle detection raises error."""
        topology = ValidatorTopology()

        # A depends on C
        topology.add_validator(ValidatorDefinition(
            validator_id="test/a",
            name="A",
            description="First",
            category=ValidatorCategory.PHYSICS,
            depends_on_validators=["test/c"],
        ))

        # B depends on A
        topology.add_validator(ValidatorDefinition(
            validator_id="test/b",
            name="B",
            description="Second",
            category=ValidatorCategory.PHYSICS,
            depends_on_validators=["test/a"],
        ))

        # C depends on B (creates cycle: A -> B -> C -> A)
        topology.add_validator(ValidatorDefinition(
            validator_id="test/c",
            name="C",
            description="Third",
            category=ValidatorCategory.PHYSICS,
            depends_on_validators=["test/b"],
        ))

        with pytest.raises(CyclicDependencyError):
            topology.build()

    def test_get_ready_validators(self):
        """Test getting validators ready to run."""
        topology = ValidatorTopology()

        topology.add_validator(ValidatorDefinition(
            validator_id="test/a",
            name="A",
            description="First",
            category=ValidatorCategory.PHYSICS,
        ))
        topology.add_validator(ValidatorDefinition(
            validator_id="test/b",
            name="B",
            description="Second",
            category=ValidatorCategory.PHYSICS,
            depends_on_validators=["test/a"],
        ))

        topology.build()

        # Initially only A is ready
        ready = topology.get_ready_validators(completed=set(), running=set())
        assert "test/a" in ready
        assert "test/b" not in ready

        # After A completes, B is ready
        ready = topology.get_ready_validators(completed={"test/a"}, running=set())
        assert "test/b" in ready

    def test_get_validators_for_phase(self):
        """Test getting validators for a specific phase."""
        topology = ValidatorTopology()

        topology.add_validator(ValidatorDefinition(
            validator_id="test/hull",
            name="Hull Validator",
            description="Hull",
            category=ValidatorCategory.PHYSICS,
            phase="hull",  # Use canonical phase name
        ))
        topology.add_validator(ValidatorDefinition(
            validator_id="test/mission",
            name="Mission Validator",
            description="Mission",
            category=ValidatorCategory.BOUNDS,
            phase="mission",
        ))

        topology.build()

        hull_validators = topology.get_validators_for_phase("hull")  # Use canonical phase name
        assert "test/hull" in hull_validators
        assert "test/mission" not in hull_validators

    def test_get_gate_validators_for_phase(self):
        """Test getting gate validators for a phase."""
        topology = ValidatorTopology()

        topology.add_validator(ValidatorDefinition(
            validator_id="test/gate",
            name="Gate Validator",
            description="Gate",
            category=ValidatorCategory.PHYSICS,
            phase="hull",  # Use canonical phase name
            is_gate_condition=True,
        ))
        topology.add_validator(ValidatorDefinition(
            validator_id="test/nongate",
            name="Non-Gate",
            description="Non-gate",
            category=ValidatorCategory.PHYSICS,
            phase="hull",  # Use canonical phase name
            is_gate_condition=False,
        ))

        topology.build()

        gates = topology.get_gate_validators_for_phase("hull")  # Use canonical phase name
        assert "test/gate" in gates
        assert "test/nongate" not in gates

    def test_get_transitive_dependents(self):
        """Test getting all transitive dependents."""
        topology = ValidatorTopology()

        # A -> B -> C
        topology.add_validator(ValidatorDefinition(
            validator_id="test/a",
            name="A",
            description="First",
            category=ValidatorCategory.PHYSICS,
        ))
        topology.add_validator(ValidatorDefinition(
            validator_id="test/b",
            name="B",
            description="Second",
            category=ValidatorCategory.PHYSICS,
            depends_on_validators=["test/a"],
        ))
        topology.add_validator(ValidatorDefinition(
            validator_id="test/c",
            name="C",
            description="Third",
            category=ValidatorCategory.PHYSICS,
            depends_on_validators=["test/b"],
        ))

        topology.build()

        # A's transitive dependents are B and C
        dependents = topology.get_transitive_dependents("test/a")
        assert "test/b" in dependents
        assert "test/c" in dependents

    def test_get_execution_order(self):
        """Test getting execution order."""
        topology = ValidatorTopology()

        topology.add_validator(ValidatorDefinition(
            validator_id="test/a",
            name="A",
            description="First",
            category=ValidatorCategory.PHYSICS,
        ))
        topology.add_validator(ValidatorDefinition(
            validator_id="test/b",
            name="B",
            description="Second",
            category=ValidatorCategory.PHYSICS,
            depends_on_validators=["test/a"],
        ))

        topology.build()

        order = topology.get_execution_order()
        assert order.index("test/a") < order.index("test/b")

    def test_to_dict(self):
        """Test serialization."""
        topology = ValidatorTopology()
        topology.add_validator(ValidatorDefinition(
            validator_id="test/serialize",
            name="Serialize Test",
            description="Test",
            category=ValidatorCategory.PHYSICS,
        ))
        topology.build()

        data = topology.to_dict()
        assert "nodes" in data
        assert "execution_groups" in data
        assert "test/serialize" in data["nodes"]


class TestExecutionGroup:
    """Test ExecutionGroup dataclass."""

    def test_create_group(self):
        """Test creating execution group."""
        group = ExecutionGroup(
            group_id=0,
            validators=["test/a", "test/b"],
            priority=ValidatorPriority.NORMAL,
        )
        assert group.group_id == 0
        assert len(group.validators) == 2

    def test_to_dict(self):
        """Test serialization."""
        group = ExecutionGroup(
            group_id=1,
            validators=["test/x"],
            priority=ValidatorPriority.HIGH,
            estimated_duration_ms=5000,
        )
        data = group.to_dict()
        assert data["group_id"] == 1
        assert data["priority"] == 2  # HIGH = 2
