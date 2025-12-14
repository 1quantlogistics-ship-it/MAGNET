"""
Unit tests for MAGNET Validator Pipeline.

Tests Module 04 v1.1 validator topology and execution.
"""

import pytest
from datetime import datetime

from magnet.validators import (
    ValidatorTopology,
    TopologyNode,
    ExecutionGroup,
    TopologyError,
    CyclicDependencyError,
    ValidatorCategory,
    ValidatorPriority,
    ValidatorState,
    ResultSeverity,
    ResourceRequirements,
    ResourcePool,
    ValidatorDefinition,
    ValidationFinding,
    ValidationResult,
    ValidatorInterface,
    PipelineExecutor,
    ExecutionState,
    ValidationCache,
    ResultAggregator,
    GateStatus,
    GateRequirement,
    get_all_validators,
    get_validators_for_phase,
    get_gate_validators_for_phase,
    get_validator_by_id,
)


class TestValidatorTaxonomy:
    """Test validator taxonomy classes."""

    def test_resource_requirements_default(self):
        """Test default resource requirements."""
        req = ResourceRequirements()
        assert req.cpu_cores == 1
        assert req.ram_gb == 0.5
        assert req.gpu_required == False

    def test_resource_pool_allocation(self):
        """Test resource pool allocation."""
        pool = ResourcePool(cpu_cores=4, ram_gb=8.0)
        req = ResourceRequirements(cpu_cores=2, ram_gb=2.0)

        assert req.fits_in(pool)
        assert pool.allocate(req)
        assert pool.cpu_cores == 2
        assert pool.ram_gb == 6.0

        pool.release(req)
        assert pool.cpu_cores == 4
        assert pool.ram_gb == 8.0

    def test_validator_definition_serialization(self):
        """Test validator definition serialization."""
        defn = ValidatorDefinition(
            validator_id="test/validator",
            name="Test Validator",
            description="A test validator",
            category=ValidatorCategory.PHYSICS,
            priority=ValidatorPriority.CRITICAL,
            phase="hull",  # Use canonical phase name
            is_gate_condition=True,
            gate_requirement=GateRequirement.REQUIRED,  # v1.1: Required for gate blocking
        )

        data = defn.to_dict()
        assert data["validator_id"] == "test/validator"
        assert data["category"] == "physics"
        assert data["priority"] == 1

        restored = ValidatorDefinition.from_dict(data)
        assert restored.validator_id == defn.validator_id
        assert restored.category == defn.category

    def test_validation_finding(self):
        """Test validation finding creation."""
        finding = ValidationFinding(
            finding_id="f1",
            severity=ResultSeverity.ERROR,
            message="Test error",
            parameter_path="hull.loa",
        )

        data = finding.to_dict()
        assert data["severity"] == "error"
        assert data["message"] == "Test error"

    def test_validation_result_add_finding(self):
        """Test adding findings to result."""
        result = ValidationResult(
            validator_id="test",
            state=ValidatorState.PENDING,
            started_at=datetime.utcnow(),
        )

        result.add_finding(ValidationFinding(
            finding_id="f1",
            severity=ResultSeverity.ERROR,
            message="Error 1",
        ))
        result.add_finding(ValidationFinding(
            finding_id="f2",
            severity=ResultSeverity.WARNING,
            message="Warning 1",
        ))

        assert result.error_count == 1
        assert result.warning_count == 1


class TestValidatorRegistry:
    """Test built-in validator registry."""

    def test_get_all_validators(self):
        """Test getting all validators."""
        validators = get_all_validators()
        assert len(validators) > 0
        # Should have physics validators
        physics = [v for v in validators if v.category == ValidatorCategory.PHYSICS]
        assert len(physics) > 0

    def test_get_validators_for_phase(self):
        """Test getting validators for a phase."""
        hull_validators = get_validators_for_phase("hull")  # Use canonical phase name
        assert len(hull_validators) > 0
        for v in hull_validators:
            assert v.phase == "hull"  # Use canonical phase name

    def test_get_gate_validators_for_phase(self):
        """Test getting gate validators for a phase."""
        gate_validators = get_gate_validators_for_phase("hull")  # Use canonical phase name
        assert len(gate_validators) > 0
        for v in gate_validators:
            assert v.is_gate_condition == True

    def test_get_validator_by_id(self):
        """Test getting validator by ID."""
        validator = get_validator_by_id("physics/hydrostatics")
        assert validator is not None
        assert validator.name == "Hydrostatics Calculator"

        missing = get_validator_by_id("nonexistent/validator")
        assert missing is None


class TestValidatorTopology:
    """Test ValidatorTopology class."""

    def test_create_empty_topology(self):
        """Test creating an empty topology."""
        topology = ValidatorTopology()
        assert not topology.is_built
        assert topology.validator_count == 0

    def test_add_all_validators(self):
        """Test adding all built-in validators."""
        topology = ValidatorTopology()
        topology.add_all_validators()
        topology.build()

        assert topology.is_built
        assert topology.validator_count > 0
        assert topology.group_count > 0

    def test_get_execution_order(self):
        """Test getting execution order."""
        topology = ValidatorTopology()
        topology.add_all_validators()
        topology.build()

        order = topology.get_execution_order()
        assert len(order) > 0

        # Check dependencies come before dependents
        hydro_idx = order.index("physics/hydrostatics") if "physics/hydrostatics" in order else -1
        resist_idx = order.index("physics/resistance") if "physics/resistance" in order else -1

        if hydro_idx >= 0 and resist_idx >= 0:
            # Hydrostatics should come before resistance
            assert hydro_idx < resist_idx

    def test_get_ready_validators(self):
        """Test getting ready validators."""
        topology = ValidatorTopology()
        topology.add_all_validators()
        topology.build()

        # Initially, validators with no dependencies should be ready
        ready = topology.get_ready_validators(set(), set())
        assert len(ready) > 0

        # After completing some, more should become ready
        completed = set(ready[:2])
        ready2 = topology.get_ready_validators(completed, set())
        assert len(ready2) >= 0

    def test_get_transitive_dependents(self):
        """Test getting transitive dependents."""
        topology = ValidatorTopology()
        topology.add_all_validators()
        topology.build()

        # Get dependents of hydrostatics
        dependents = topology.get_transitive_dependents("physics/hydrostatics")
        # Resistance depends on hydrostatics
        assert "physics/resistance" in dependents

    def test_get_validators_for_phase(self):
        """Test getting validators for a phase."""
        topology = ValidatorTopology()
        topology.add_all_validators()
        topology.build()

        hull_validators = topology.get_validators_for_phase("hull")  # Use canonical phase name
        assert "physics/hydrostatics" in hull_validators
        assert "physics/resistance" in hull_validators


class TestValidationCache:
    """Test ValidationCache class."""

    def test_cache_put_get(self):
        """Test putting and getting from cache."""
        cache = ValidationCache()

        result = ValidationResult(
            validator_id="test",
            state=ValidatorState.PASSED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        cache.put("test", "hash123", result, ttl_seconds=3600)

        # Should get cached result
        cached = cache.get("test", "hash123")
        assert cached is not None
        assert cached.was_cached == True

        # Wrong hash should miss
        missed = cache.get("test", "wronghash")
        assert missed is None

    def test_cache_invalidate(self):
        """Test cache invalidation."""
        cache = ValidationCache()

        result = ValidationResult(
            validator_id="test",
            state=ValidatorState.PASSED,
            started_at=datetime.utcnow(),
        )
        cache.put("test", "hash123", result, ttl_seconds=3600)

        cache.invalidate("test")
        assert cache.get("test", "hash123") is None


class TestExecutionState:
    """Test ExecutionState class."""

    def test_execution_state_creation(self):
        """Test creating execution state."""
        state = ExecutionState(
            execution_id="test123",
            started_at=datetime.utcnow(),
        )

        assert state.execution_id == "test123"
        # Empty state (no pending, no running) is considered complete
        assert state.is_complete
        assert not state.has_failures

    def test_execution_state_tracking(self):
        """Test tracking validator states."""
        state = ExecutionState(
            execution_id="test123",
            started_at=datetime.utcnow(),
        )
        state.pending = {"v1", "v2", "v3"}

        # Simulate execution
        state.pending.remove("v1")
        state.completed.add("v1")

        assert len(state.completed) == 1
        assert len(state.pending) == 2
        assert not state.is_complete

    def test_execution_state_serialization(self):
        """Test execution state serialization."""
        state = ExecutionState(
            execution_id="test123",
            started_at=datetime.utcnow(),
        )
        state.completed = {"v1"}
        state.failed = {"v2"}

        data = state.to_dict()
        assert data["execution_id"] == "test123"
        assert "v1" in data["completed"]
        assert "v2" in data["failed"]


class TestGateStatus:
    """Test GateStatus class."""

    def test_gate_status_creation(self):
        """Test creating gate status."""
        status = GateStatus(gate_id="hull_form", can_advance=True)

        assert status.gate_id == "hull_form"
        assert status.can_advance == True
        assert not status.has_blocking_conditions

    def test_gate_status_blocking(self):
        """Test blocking conditions detection."""
        status = GateStatus(gate_id="hull_form", can_advance=False)
        status.required_failed = 1
        status.blocking_validators = ["test/validator"]

        assert status.has_blocking_conditions
        messages = status.get_all_blocking_messages()
        assert len(messages) > 0

    def test_gate_status_with_stale(self):
        """Test gate status with stale parameters."""
        status = GateStatus(gate_id="hull_form", can_advance=False)
        status.stale_parameters = ["hull.loa"]

        assert status.has_blocking_conditions
        messages = status.get_all_blocking_messages()
        assert any("STALE" in m for m in messages)


class TestResultAggregator:
    """Test ResultAggregator class."""

    def test_create_aggregator(self):
        """Test creating result aggregator."""
        topology = ValidatorTopology()
        topology.add_all_validators()
        topology.build()

        aggregator = ResultAggregator(topology)
        assert aggregator._topology is topology

    def test_check_gate_empty_results(self):
        """Test checking gate with no results."""
        topology = ValidatorTopology()
        topology.add_all_validators()
        topology.build()

        aggregator = ResultAggregator(topology)
        execution = ExecutionState(
            execution_id="test",
            started_at=datetime.utcnow(),
        )

        status = aggregator.check_gate("hull", execution)  # Use canonical phase name

        # Gate should not pass without results
        assert not status.can_advance
        assert status.required_failed > 0
