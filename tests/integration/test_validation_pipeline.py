"""
Integration tests for the Validation Pipeline (Module 04)

Tests the complete validation pipeline from topology building through
execution and gate aggregation.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from magnet.validators.taxonomy import (
    ValidatorDefinition,
    ValidatorCategory,
    ValidatorPriority,
    ValidatorState,
    ValidationResult,
    ValidationFinding,
    ResultSeverity,
    GateRequirement,
    ValidatorInterface,
    ResourcePool,
    ResourceRequirements,
)
from magnet.validators.topology import (
    ValidatorTopology,
    TopologyNode,
    ExecutionGroup,
    CyclicDependencyError,
)
from magnet.validators.executor import (
    ExecutionState,
    ValidationCache,
    PipelineExecutor,
)
from magnet.validators.aggregator import (
    GateStatus,
    ResultAggregator,
)
from magnet.dependencies.graph import (
    DependencyGraph,
    get_phase_for_parameter,
)
from magnet.dependencies.invalidation import (
    InvalidationEngine,
    InvalidationReason,
)
from magnet.dependencies.revalidation import (
    RevalidationScheduler,
    RevalidationTask,
)


class MockValidator(ValidatorInterface):
    """Mock validator for testing."""

    def __init__(self, validator_id: str, result_state: ValidatorState = ValidatorState.PASSED):
        self.validator_id = validator_id
        self.result_state = result_state
        self.call_count = 0

    def validate(self, state_manager, context) -> ValidationResult:
        self.call_count += 1
        return ValidationResult(
            validator_id=self.validator_id,
            state=self.result_state,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

    def get_input_hash(self, state_manager) -> str:
        return f"hash_{self.validator_id}"

    def should_skip_unchanged(self, state_manager, last_run_time) -> bool:
        return False


class TestTopologyBuilding:
    """Test building validator topologies."""

    def test_build_linear_topology(self):
        """Test building a linear A -> B -> C topology."""
        topology = ValidatorTopology()

        topology.add_validator(ValidatorDefinition(
            validator_id="phase1/validate",
            name="Phase 1",
            description="First phase",
            category=ValidatorCategory.PHYSICS,
        ))
        topology.add_validator(ValidatorDefinition(
            validator_id="phase2/validate",
            name="Phase 2",
            description="Second phase",
            category=ValidatorCategory.PHYSICS,
            depends_on_validators=["phase1/validate"],
        ))
        topology.add_validator(ValidatorDefinition(
            validator_id="phase3/validate",
            name="Phase 3",
            description="Third phase",
            category=ValidatorCategory.PHYSICS,
            depends_on_validators=["phase2/validate"],
        ))

        topology.build()

        assert topology.is_built
        assert topology.validator_count == 3

        # Check depths
        assert topology.get_node("phase1/validate").depth == 0
        assert topology.get_node("phase2/validate").depth == 1
        assert topology.get_node("phase3/validate").depth == 2

    def test_build_parallel_topology(self):
        """Test topology with parallel validators."""
        topology = ValidatorTopology()

        # Two independent validators
        topology.add_validator(ValidatorDefinition(
            validator_id="parallel/a",
            name="Parallel A",
            description="Independent A",
            category=ValidatorCategory.PHYSICS,
        ))
        topology.add_validator(ValidatorDefinition(
            validator_id="parallel/b",
            name="Parallel B",
            description="Independent B",
            category=ValidatorCategory.PHYSICS,
        ))

        # Depends on both
        topology.add_validator(ValidatorDefinition(
            validator_id="merge/c",
            name="Merge C",
            description="Depends on A and B",
            category=ValidatorCategory.PHYSICS,
            depends_on_validators=["parallel/a", "parallel/b"],
        ))

        topology.build()

        # A and B at same depth
        assert topology.get_node("parallel/a").depth == 0
        assert topology.get_node("parallel/b").depth == 0
        assert topology.get_node("merge/c").depth == 1

    def test_cycle_detection(self):
        """Test that cyclic dependencies are detected."""
        topology = ValidatorTopology()

        topology.add_validator(ValidatorDefinition(
            validator_id="cycle/a",
            name="A",
            description="A",
            category=ValidatorCategory.PHYSICS,
            depends_on_validators=["cycle/c"],  # Depends on C
        ))
        topology.add_validator(ValidatorDefinition(
            validator_id="cycle/b",
            name="B",
            description="B",
            category=ValidatorCategory.PHYSICS,
            depends_on_validators=["cycle/a"],  # Depends on A
        ))
        topology.add_validator(ValidatorDefinition(
            validator_id="cycle/c",
            name="C",
            description="C",
            category=ValidatorCategory.PHYSICS,
            depends_on_validators=["cycle/b"],  # Depends on B -> Cycle!
        ))

        with pytest.raises(CyclicDependencyError):
            topology.build()


class TestPipelineExecution:
    """Test pipeline execution."""

    def _create_simple_pipeline(self):
        """Create a simple test pipeline."""
        topology = ValidatorTopology()

        topology.add_validator(ValidatorDefinition(
            validator_id="test/first",
            name="First",
            description="First validator",
            category=ValidatorCategory.PHYSICS,
        ))
        topology.add_validator(ValidatorDefinition(
            validator_id="test/second",
            name="Second",
            description="Second validator",
            category=ValidatorCategory.PHYSICS,
            depends_on_validators=["test/first"],
        ))

        topology.build()
        return topology

    def test_execute_simple_pipeline(self):
        """Test executing a simple pipeline."""
        topology = self._create_simple_pipeline()
        state_manager = Mock()

        registry = {
            "test/first": MockValidator("test/first"),
            "test/second": MockValidator("test/second"),
        }

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry=registry,
            max_workers=1,
        )

        result = executor.execute_all()

        assert result.is_complete
        assert "test/first" in result.completed
        assert "test/second" in result.completed
        assert len(result.failed) == 0

    def test_execute_with_failure(self):
        """Test execution when validator fails."""
        topology = self._create_simple_pipeline()
        state_manager = Mock()

        registry = {
            "test/first": MockValidator("test/first", ValidatorState.FAILED),
            "test/second": MockValidator("test/second"),
        }

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry=registry,
            max_workers=1,
        )

        result = executor.execute_all(stop_on_failure=True)

        assert "test/first" in result.failed
        # Second should be skipped due to dependency failure
        assert "test/second" in result.skipped

    def test_fix4_fatal_error_handling(self):
        """Test FIX #4: Stop on fatal error (ERROR state)."""
        topology = self._create_simple_pipeline()
        state_manager = Mock()

        # First validator returns ERROR (code failure)
        registry = {
            "test/first": MockValidator("test/first", ValidatorState.ERROR),
            "test/second": MockValidator("test/second"),
        }

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry=registry,
            max_workers=1,
        )

        result = executor.execute_all(stop_on_fatal_error=True)

        assert result.had_fatal_error
        assert result.fatal_error_validator == "test/first"


class TestGateAggregation:
    """Test gate condition aggregation."""

    def _create_gate_topology(self):
        """Create topology with gate validators."""
        topology = ValidatorTopology()

        # Required gate validator - v1.1: Use gate_requirement for blocking behavior
        topology.add_validator(ValidatorDefinition(
            validator_id="hull/volume",
            name="Hull Volume",
            description="Required hull volume check",
            category=ValidatorCategory.PHYSICS,
            phase="hull",  # Use canonical phase name
            is_gate_condition=True,
            gate_severity=ResultSeverity.ERROR,
            gate_requirement=GateRequirement.REQUIRED,  # v1.1: Blocks gate on failure
        ))

        # Recommended gate validator - v1.1: OPTIONAL means warning only
        topology.add_validator(ValidatorDefinition(
            validator_id="hull/wetted",
            name="Hull Wetted",
            description="Recommended wetted surface check",
            category=ValidatorCategory.PHYSICS,
            phase="hull",  # Use canonical phase name
            is_gate_condition=True,
            gate_severity=ResultSeverity.WARNING,
            gate_requirement=GateRequirement.OPTIONAL,  # v1.1: Doesn't block gate
        ))

        topology.build()
        return topology

    def test_gate_passed_all_validators(self):
        """Test gate passes when all validators pass."""
        topology = self._create_gate_topology()
        aggregator = ResultAggregator(topology=topology)

        exec_state = ExecutionState(
            execution_id="test",
            started_at=datetime.utcnow(),
        )
        exec_state.results["hull/volume"] = ValidationResult(
            validator_id="hull/volume",
            state=ValidatorState.PASSED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        exec_state.results["hull/wetted"] = ValidationResult(
            validator_id="hull/wetted",
            state=ValidatorState.PASSED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        status = aggregator.check_gate("hull", exec_state)  # Use canonical phase name

        assert status.can_advance
        assert status.required_passed == 1
        assert status.recommended_passed == 1

    def test_gate_blocked_required_failed(self):
        """Test gate blocks when required validator fails."""
        topology = self._create_gate_topology()
        aggregator = ResultAggregator(topology=topology)

        exec_state = ExecutionState(
            execution_id="test",
            started_at=datetime.utcnow(),
        )
        exec_state.results["hull/volume"] = ValidationResult(
            validator_id="hull/volume",
            state=ValidatorState.FAILED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            findings=[
                ValidationFinding(
                    finding_id="f1",
                    severity=ResultSeverity.ERROR,
                    message="Volume below minimum",
                )
            ]
        )
        exec_state.results["hull/wetted"] = ValidationResult(
            validator_id="hull/wetted",
            state=ValidatorState.PASSED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        status = aggregator.check_gate("hull", exec_state)  # Use canonical phase name

        assert not status.can_advance
        assert status.required_failed == 1
        assert "hull/volume" in status.blocking_validators


class TestDependencyInvalidation:
    """Test dependency invalidation integration."""

    def test_parameter_change_invalidates_downstream(self):
        """Test changing parameter invalidates downstream validators."""
        graph = DependencyGraph()
        graph.add_dependency("hull.displacement_m3", "hull.loa")
        graph.add_dependency("resistance.total", "hull.displacement_m3")
        graph._compute_order()

        engine = InvalidationEngine(dependency_graph=graph)

        # Change LOA
        event = engine.invalidate_parameter("hull.loa")

        # Downstream should be stale
        assert engine.is_stale("hull.loa")
        assert engine.is_stale("hull.displacement_m3")
        assert engine.is_stale("resistance.total")

    def test_phase_invalidation(self):
        """Test invalidating entire phase."""
        graph = DependencyGraph()
        graph.build_from_definitions()

        engine = InvalidationEngine(dependency_graph=graph)

        event = engine.invalidate_phase("hull_form")

        assert engine.is_phase_stale("hull_form")
        assert len(event.invalidated_parameters) > 0


class TestRevalidationScheduler:
    """Test revalidation scheduler integration."""

    def test_queue_and_process_validators(self):
        """Test queuing and processing validators."""
        scheduler = RevalidationScheduler()

        # Queue validators triggered by parameter change
        scheduler.queue_validators(
            ["hull/volume", "hull/wetted", "stability/gm"],
            triggered_by="hull.loa",
            priority=1,
        )

        assert scheduler.get_pending_count() == 3

        # Process with priority order
        task1 = scheduler.pop_next()
        assert task1.triggered_by == "hull.loa"

    def test_priority_ordering(self):
        """Test validators processed in priority order."""
        scheduler = RevalidationScheduler()

        scheduler.queue_validator("low_priority", priority=3)
        scheduler.queue_validator("high_priority", priority=1)
        scheduler.queue_validator("medium_priority", priority=2)

        assert scheduler.pop_next().validator_id == "high_priority"
        assert scheduler.pop_next().validator_id == "medium_priority"
        assert scheduler.pop_next().validator_id == "low_priority"


class TestEndToEndPipeline:
    """End-to-end integration tests."""

    def test_full_validation_cycle(self):
        """Test complete validation cycle from change to gate check."""
        # 1. Build topology
        topology = ValidatorTopology()
        topology.add_validator(ValidatorDefinition(
            validator_id="hull/dimensions",
            name="Dimensions",
            description="Dimension check",
            category=ValidatorCategory.BOUNDS,
            phase="hull",  # Use canonical phase name
            is_gate_condition=True,
            gate_severity=ResultSeverity.ERROR,
            gate_requirement=GateRequirement.REQUIRED,  # v1.1: Blocks gate on failure
        ))
        topology.add_validator(ValidatorDefinition(
            validator_id="hull/volume",
            name="Volume",
            description="Volume check",
            category=ValidatorCategory.PHYSICS,
            phase="hull",  # Use canonical phase name
            is_gate_condition=True,
            gate_severity=ResultSeverity.ERROR,
            gate_requirement=GateRequirement.REQUIRED,  # v1.1: Blocks gate on failure
            depends_on_validators=["hull/dimensions"],
        ))
        topology.build()

        # 2. Create executor
        state_manager = Mock()
        registry = {
            "hull/dimensions": MockValidator("hull/dimensions"),
            "hull/volume": MockValidator("hull/volume"),
        }

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry=registry,
            max_workers=1,
        )

        # 3. Execute validators
        exec_state = executor.execute_all()

        assert exec_state.is_complete
        assert not exec_state.has_failures

        # 4. Check gate
        aggregator = ResultAggregator(topology=topology)
        gate_status = aggregator.check_gate("hull", exec_state)  # Use canonical phase name

        assert gate_status.can_advance
        assert gate_status.required_passed == 2

    def test_invalidation_triggers_revalidation(self):
        """Test parameter change triggers revalidation scheduling."""
        # 1. Build dependency graph
        graph = DependencyGraph()
        graph.add_dependency("computed_param", "input_param")
        graph._compute_order()

        # 2. Setup invalidation engine
        engine = InvalidationEngine(dependency_graph=graph)

        # 3. Setup revalidation scheduler
        scheduler = RevalidationScheduler()

        # 4. Register callback to schedule revalidation
        def on_invalidate(event):
            # Queue validators for affected parameters
            for param in event.invalidated_parameters:
                validator_id = f"validator/{param.replace('.', '_')}"
                scheduler.queue_validator(
                    validator_id,
                    triggered_by=event.trigger_parameter,
                )

        engine.on_invalidate(on_invalidate)

        # 5. Trigger parameter change
        engine.invalidate_parameter("input_param")

        # 6. Verify validators queued
        assert scheduler.get_pending_count() >= 1

    def test_execution_state_persistence(self):
        """Test FIX #11: ExecutionState save/load cycle."""
        import tempfile
        from pathlib import Path

        # Create execution state with results
        state = ExecutionState(
            execution_id="persist-test",
            started_at=datetime.utcnow(),
        )
        state.completed = {"hull/volume", "hull/wetted"}
        state.failed = {"hull/stability"}
        state.had_fatal_error = False
        state.results["hull/volume"] = ValidationResult(
            validator_id="hull/volume",
            state=ValidatorState.PASSED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)

        try:
            state.save(path)

            # Load back
            loaded = ExecutionState.load(path)

            assert loaded.execution_id == "persist-test"
            assert "hull/volume" in loaded.completed
            assert "hull/stability" in loaded.failed
            assert "hull/volume" in loaded.results
            assert loaded.results["hull/volume"].state == ValidatorState.PASSED
        finally:
            path.unlink()
