"""
Unit tests for validators/executor.py

Tests the PipelineExecutor, ExecutionState, and ValidationCache.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import tempfile
import json

from magnet.validators.executor import (
    ExecutionState,
    CacheEntry,
    ValidationCache,
    PipelineExecutor,
)
from magnet.validators.taxonomy import (
    ValidatorState,
    ValidationResult,
    ValidationFinding,
    ResultSeverity,
    ValidatorDefinition,
    ValidatorCategory,
    ResourcePool,
    ResourceRequirements,
)
from magnet.validators.topology import ValidatorTopology


class TestExecutionState:
    """Test ExecutionState dataclass."""

    def test_create_state(self):
        """Test creating execution state."""
        state = ExecutionState(
            execution_id="test-123",
            started_at=datetime.utcnow(),
        )
        assert state.execution_id == "test-123"
        assert len(state.pending) == 0
        assert len(state.completed) == 0
        assert state.had_fatal_error == False

    def test_is_complete(self):
        """Test is_complete property."""
        state = ExecutionState(
            execution_id="test",
            started_at=datetime.utcnow(),
        )
        # Empty state is complete
        assert state.is_complete == True

        # With pending, not complete
        state.pending.add("test/validator")
        assert state.is_complete == False

        # With running, not complete
        state.pending.clear()
        state.running.add("test/validator")
        assert state.is_complete == False

        # All cleared is complete
        state.running.clear()
        assert state.is_complete == True

    def test_has_failures(self):
        """Test has_failures property."""
        state = ExecutionState(
            execution_id="test",
            started_at=datetime.utcnow(),
        )
        assert state.has_failures == False

        state.failed.add("test/validator")
        assert state.has_failures == True

    def test_get_summary(self):
        """Test get_summary method."""
        state = ExecutionState(
            execution_id="test-456",
            started_at=datetime.utcnow(),
        )
        state.pending = {"a", "b"}
        state.completed = {"c"}
        state.failed = {"d"}
        state.skipped = {"e"}
        state.had_fatal_error = True

        summary = state.get_summary()
        assert summary["execution_id"] == "test-456"
        assert summary["pending"] == 2
        assert summary["completed"] == 1
        assert summary["failed"] == 1
        assert summary["skipped"] == 1
        assert summary["had_fatal_error"] == True

    def test_to_dict_serialization(self):
        """Test FIX #11: ExecutionState serialization."""
        state = ExecutionState(
            execution_id="serial-test",
            started_at=datetime.utcnow(),
        )
        state.pending = {"pending/v"}
        state.completed = {"done/v"}
        state.results["done/v"] = ValidationResult(
            validator_id="done/v",
            state=ValidatorState.PASSED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        data = state.to_dict()
        assert data["execution_id"] == "serial-test"
        assert "pending/v" in data["pending"]
        assert "done/v" in data["completed"]
        assert "done/v" in data["results"]

    def test_save_and_load(self):
        """Test FIX #11: Save and load execution state."""
        state = ExecutionState(
            execution_id="save-load",
            started_at=datetime.utcnow(),
        )
        state.completed = {"test/v"}
        state.failed = {"test/fail"}
        state.had_fatal_error = True
        state.fatal_error_validator = "test/fail"
        state.results["test/v"] = ValidationResult(
            validator_id="test/v",
            state=ValidatorState.PASSED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)

        try:
            state.save(path)

            loaded = ExecutionState.load(path)
            assert loaded.execution_id == "save-load"
            assert "test/v" in loaded.completed
            assert "test/fail" in loaded.failed
            assert loaded.had_fatal_error == True
            assert loaded.fatal_error_validator == "test/fail"
        finally:
            path.unlink()


class TestCacheEntry:
    """Test CacheEntry dataclass."""

    def test_is_valid_fresh(self):
        """Test cache entry is valid when fresh."""
        entry = CacheEntry(
            result=Mock(),
            input_hash="abc123",
            cached_at=datetime.utcnow(),
            ttl_seconds=3600,
        )
        assert entry.is_valid() == True

    def test_is_valid_expired(self):
        """Test cache entry is invalid when expired."""
        entry = CacheEntry(
            result=Mock(),
            input_hash="abc123",
            cached_at=datetime.utcnow() - timedelta(hours=2),
            ttl_seconds=3600,
        )
        assert entry.is_valid() == False


class TestValidationCache:
    """Test ValidationCache class."""

    def test_put_and_get(self):
        """Test caching and retrieving results."""
        cache = ValidationCache()
        result = ValidationResult(
            validator_id="test/v",
            state=ValidatorState.PASSED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        cache.put("test/v", "hash123", result, 3600)

        cached = cache.get("test/v", "hash123")
        assert cached is not None
        assert cached.validator_id == "test/v"
        assert cached.was_cached == True

    def test_get_wrong_hash(self):
        """Test cache miss with wrong hash."""
        cache = ValidationCache()
        result = ValidationResult(
            validator_id="test/v",
            state=ValidatorState.PASSED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        cache.put("test/v", "hash123", result, 3600)

        # Wrong hash returns None
        cached = cache.get("test/v", "different_hash")
        assert cached is None

    def test_get_nonexistent(self):
        """Test cache miss for nonexistent validator."""
        cache = ValidationCache()
        cached = cache.get("nonexistent", "hash")
        assert cached is None

    def test_invalidate_single(self):
        """Test invalidating single cache entry."""
        cache = ValidationCache()
        result = ValidationResult(
            validator_id="test/v",
            state=ValidatorState.PASSED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        cache.put("test/v", "hash", result, 3600)
        assert cache.get("test/v", "hash") is not None

        cache.invalidate("test/v")
        assert cache.get("test/v", "hash") is None

    def test_invalidate_all(self):
        """Test invalidating all cache entries."""
        cache = ValidationCache()
        result = ValidationResult(
            validator_id="test/v",
            state=ValidatorState.PASSED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        cache.put("test/a", "hash", result, 3600)
        cache.put("test/b", "hash", result, 3600)

        cache.invalidate_all()
        assert cache.get("test/a", "hash") is None
        assert cache.get("test/b", "hash") is None

    def test_get_stats(self):
        """Test cache statistics."""
        cache = ValidationCache()
        result = ValidationResult(
            validator_id="test/v",
            state=ValidatorState.PASSED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        cache.put("test/a", "hash", result, 3600)
        cache.put("test/b", "hash", result, 3600)

        stats = cache.get_stats()
        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 2
        assert "test/a" in stats["validator_ids"]


class TestPipelineExecutor:
    """Test PipelineExecutor class."""

    def _create_mock_topology(self, validators=None):
        """Create a mock topology."""
        if validators is None:
            validators = ["test/a", "test/b"]

        topology = Mock(spec=ValidatorTopology)
        topology.get_execution_order.return_value = validators
        topology.get_ready_validators.return_value = validators
        topology.get_validators_for_phase.return_value = validators

        def mock_get_node(v_id):
            node = Mock()
            node.validator = ValidatorDefinition(
                validator_id=v_id,
                name=v_id,
                description="Test",
                category=ValidatorCategory.PHYSICS,
            )
            return node

        topology.get_node.side_effect = mock_get_node
        topology.get_transitive_dependents.return_value = set()

        return topology

    def _create_mock_impl(self, state=ValidatorState.PASSED):
        """Create a mock validator implementation."""
        impl = Mock()
        impl.validate.return_value = ValidationResult(
            validator_id="test",
            state=state,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        impl.get_input_hash.return_value = "hash123"
        impl.should_skip_unchanged.return_value = False
        return impl

    def test_create_executor(self):
        """Test creating pipeline executor."""
        topology = self._create_mock_topology()
        state_manager = Mock()
        registry = {}

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry=registry,
        )
        assert executor._max_workers == 4

    def test_execute_all_empty(self):
        """Test executing with no validators."""
        topology = self._create_mock_topology([])
        state_manager = Mock()
        registry = {}

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry=registry,
        )

        result = executor.execute_all()
        assert result.is_complete == True
        assert len(result.completed) == 0

    def test_execute_single_missing_impl(self):
        """Test executing validator with no implementation."""
        topology = self._create_mock_topology(["test/v"])
        state_manager = Mock()
        registry = {}  # Empty registry

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry=registry,
        )

        result = executor.execute_single("test/v")
        # NOT_IMPLEMENTED is the correct state for validators without implementations
        # (distinct from ERROR which indicates code failure)
        assert result.state == ValidatorState.NOT_IMPLEMENTED
        assert "No implementation" in result.error_message

    def test_execute_single_validator_not_found(self):
        """Test executing nonexistent validator."""
        topology = Mock(spec=ValidatorTopology)
        topology.get_node.return_value = None
        state_manager = Mock()
        registry = {}

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry=registry,
        )

        result = executor.execute_single("nonexistent")
        assert result.state == ValidatorState.ERROR
        assert "not found" in result.error_message

    def test_execute_single_success(self):
        """Test successfully executing single validator."""
        topology = self._create_mock_topology(["test/v"])
        state_manager = Mock()
        impl = self._create_mock_impl(ValidatorState.PASSED)
        registry = {"test/v": impl}

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry=registry,
        )

        result = executor.execute_single("test/v")
        assert result.state == ValidatorState.PASSED

    def test_fix4_stop_on_fatal_error(self):
        """Test FIX #4: Stops on fatal error (ERROR state)."""
        topology = Mock(spec=ValidatorTopology)
        topology.get_execution_order.return_value = ["test/a", "test/b"]

        # First call returns test/a, second returns empty (after fatal)
        topology.get_ready_validators.side_effect = [
            ["test/a"],
            [],
        ]

        def mock_get_node(v_id):
            node = Mock()
            node.validator = ValidatorDefinition(
                validator_id=v_id,
                name=v_id,
                description="Test",
                category=ValidatorCategory.PHYSICS,
            )
            return node

        topology.get_node.side_effect = mock_get_node

        state_manager = Mock()

        # Create impl that returns ERROR
        error_impl = Mock()
        error_impl.validate.return_value = ValidationResult(
            validator_id="test/a",
            state=ValidatorState.ERROR,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            error_message="Code failure",
        )
        error_impl.get_input_hash.return_value = "hash"
        error_impl.should_skip_unchanged.return_value = False

        registry = {"test/a": error_impl, "test/b": Mock()}

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry=registry,
        )

        result = executor.execute_all(stop_on_fatal_error=True)
        assert result.had_fatal_error == True
        assert result.fatal_error_validator == "test/a"

    def test_fix5_no_retry_on_failed(self):
        """Test FIX #5: No retry on FAILED state (validation failure)."""
        topology = self._create_mock_topology(["test/v"])
        state_manager = Mock()

        impl = Mock()
        # Return FAILED - should NOT retry
        impl.validate.return_value = ValidationResult(
            validator_id="test/v",
            state=ValidatorState.FAILED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        impl.get_input_hash.return_value = "hash"
        impl.should_skip_unchanged.return_value = False

        # Set max retries
        node = topology.get_node("test/v")
        node.validator.max_retries = 3

        registry = {"test/v": impl}

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry=registry,
        )

        result = executor.execute_single("test/v")
        # Should only be called once - no retries for FAILED
        assert impl.validate.call_count == 1
        assert result.state == ValidatorState.FAILED

    def test_fix5_retry_on_exception(self):
        """Test FIX #5: Retry on exceptions."""
        topology = self._create_mock_topology(["test/v"])
        state_manager = Mock()

        impl = Mock()
        # First call raises exception, second succeeds
        impl.validate.side_effect = [
            Exception("Transient error"),
            ValidationResult(
                validator_id="test/v",
                state=ValidatorState.PASSED,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
            ),
        ]
        impl.get_input_hash.return_value = "hash"
        impl.should_skip_unchanged.return_value = False

        # Set max retries
        node = topology.get_node("test/v")
        node.validator.max_retries = 3
        node.validator.retry_delay_seconds = 0

        registry = {"test/v": impl}

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry=registry,
        )

        result = executor.execute_single("test/v")
        # Should be called twice - first fails, second succeeds
        assert impl.validate.call_count == 2
        assert result.state == ValidatorState.PASSED

    def test_fix10_skip_unchanged(self):
        """Test FIX #10: Skip unchanged validators."""
        topology = self._create_mock_topology(["test/v"])
        state_manager = Mock()

        impl = Mock()
        impl.should_skip_unchanged.return_value = True  # Inputs unchanged
        impl.get_input_hash.return_value = "hash"

        registry = {"test/v": impl}

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry=registry,
        )

        result = executor._execute_validator("test/v", skip_cached=True, skip_unchanged=True)
        assert result.state == ValidatorState.SKIPPED
        assert result.was_skipped_unchanged == True
        # validate should NOT be called
        assert impl.validate.call_count == 0

    def test_fix9_resource_filtering(self):
        """Test FIX #9: Resource-aware scheduling."""
        topology = Mock(spec=ValidatorTopology)

        # Create two nodes with different resource requirements
        node_a = Mock()
        node_a.validator = ValidatorDefinition(
            validator_id="test/a",
            name="A",
            description="Test",
            category=ValidatorCategory.PHYSICS,
            resource_requirements=ResourceRequirements(cpu_cores=2, ram_gb=1.0),
        )

        node_b = Mock()
        node_b.validator = ValidatorDefinition(
            validator_id="test/b",
            name="B",
            description="Test",
            category=ValidatorCategory.PHYSICS,
            resource_requirements=ResourceRequirements(cpu_cores=8, ram_gb=10.0),
        )

        def get_node_side_effect(v_id):
            return {"test/a": node_a, "test/b": node_b}.get(v_id)

        topology.get_node.side_effect = get_node_side_effect

        state_manager = Mock()

        # Small resource pool - only test/a should fit
        resource_pool = ResourcePool(cpu_cores=4, ram_gb=2.0)

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry={},
            resource_pool=resource_pool,
        )

        filtered = executor._filter_by_resources(["test/a", "test/b"])
        assert "test/a" in filtered
        assert "test/b" not in filtered

    def test_progress_callback(self):
        """Test progress callbacks."""
        topology = self._create_mock_topology(["test/v"])
        state_manager = Mock()
        impl = self._create_mock_impl(ValidatorState.PASSED)
        registry = {"test/v": impl}

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry=registry,
        )

        callback_results = []

        def on_progress(v_id, result):
            callback_results.append((v_id, result.state))

        executor.on_progress(on_progress)
        executor.execute_single("test/v")

        # Direct execute_single doesn't trigger callback, but _notify_progress does
        executor._notify_progress("test/v", impl.validate.return_value)
        assert len(callback_results) == 1
        assert callback_results[0][0] == "test/v"

    def test_execute_phase(self):
        """Test executing validators for a phase."""
        topology = Mock(spec=ValidatorTopology)
        topology.get_validators_for_phase.return_value = ["hull/volume", "hull/wetted"]
        topology.get_execution_order.return_value = ["hull/volume", "hull/wetted"]
        topology.get_ready_validators.return_value = []

        state_manager = Mock()

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry={},
        )

        result = executor.execute_phase("hull")  # Use canonical phase name
        topology.get_validators_for_phase.assert_called_with("hull")  # Use canonical phase name

    def test_invalidate_cache(self):
        """Test cache invalidation."""
        topology = self._create_mock_topology()
        state_manager = Mock()

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry={},
        )

        # Add to cache
        result = ValidationResult(
            validator_id="test/v",
            state=ValidatorState.PASSED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        executor._cache.put("test/v", "hash", result, 3600)

        # Invalidate
        executor.invalidate_cache("test/v")
        assert executor._cache.get("test/v", "hash") is None

    def test_get_cache_stats(self):
        """Test getting cache stats."""
        topology = self._create_mock_topology()
        state_manager = Mock()

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry={},
        )

        stats = executor.get_cache_stats()
        assert "total_entries" in stats
        assert "valid_entries" in stats


class TestPipelineExecutorIntegration:
    """Integration tests for PipelineExecutor."""

    def test_full_execution_flow(self):
        """Test complete execution flow with multiple validators."""
        # Build a real topology
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

        state_manager = Mock()

        # Create implementations
        def create_impl(v_id):
            impl = Mock()
            impl.validate.return_value = ValidationResult(
                validator_id=v_id,
                state=ValidatorState.PASSED,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
            )
            impl.get_input_hash.return_value = f"hash_{v_id}"
            impl.should_skip_unchanged.return_value = False
            return impl

        registry = {
            "test/a": create_impl("test/a"),
            "test/b": create_impl("test/b"),
        }

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry=registry,
            max_workers=1,  # Sequential for predictable testing
        )

        result = executor.execute_all()

        assert result.is_complete == True
        assert "test/a" in result.completed
        assert "test/b" in result.completed
        assert len(result.failed) == 0
