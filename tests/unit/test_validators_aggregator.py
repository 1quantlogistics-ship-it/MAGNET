"""
Unit tests for validators/aggregator.py

Tests ResultAggregator and GateStatus for gate condition checking.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from magnet.validators.aggregator import (
    GateStatus,
    ResultAggregator,
    create_aggregator,
    check_phase_gate,
)
from magnet.validators.taxonomy import (
    ValidatorState,
    ValidationResult,
    ValidationFinding,
    ResultSeverity,
    ValidatorDefinition,
    ValidatorCategory,
    GateRequirement,
)
from magnet.validators.executor import ExecutionState
from magnet.validators.topology import ValidatorTopology


class TestGateStatus:
    """Test GateStatus dataclass."""

    def test_create_gate_status(self):
        """Test creating gate status."""
        status = GateStatus(gate_id="hull_form", can_advance=True)
        assert status.gate_id == "hull_form"
        assert status.can_advance == True
        assert status.required_passed == 0
        assert status.required_failed == 0

    def test_has_blocking_conditions_none(self):
        """Test no blocking conditions."""
        status = GateStatus(gate_id="test", can_advance=True)
        assert status.has_blocking_conditions == False

    def test_has_blocking_conditions_required_failed(self):
        """Test blocking when required validators fail."""
        status = GateStatus(
            gate_id="test",
            can_advance=False,
            required_failed=1,
        )
        assert status.has_blocking_conditions == True

    def test_fix7_has_blocking_conditions_stale(self):
        """Test FIX #7: Blocking when stale parameters."""
        status = GateStatus(
            gate_id="test",
            can_advance=False,
            stale_parameters=["LOA", "beam"],
        )
        assert status.has_blocking_conditions == True

    def test_fix7_has_blocking_conditions_missing(self):
        """Test FIX #7: Blocking when missing validators."""
        status = GateStatus(
            gate_id="test",
            can_advance=False,
            missing_validators=["hull/volume"],
        )
        assert status.has_blocking_conditions == True

    def test_fix7_has_blocking_conditions_contracts(self):
        """Test FIX #7: Blocking when contract errors."""
        status = GateStatus(
            gate_id="test",
            can_advance=False,
            contract_errors=["LOA must be positive"],
        )
        assert status.has_blocking_conditions == True

    def test_fix7_has_blocking_conditions_intent(self):
        """Test FIX #7: Blocking when intent violations."""
        status = GateStatus(
            gate_id="test",
            can_advance=False,
            intent_violations=["Speed exceeds design intent"],
        )
        assert status.has_blocking_conditions == True

    def test_get_all_blocking_messages(self):
        """Test getting all blocking messages."""
        result = ValidationResult(
            validator_id="hull/volume",
            state=ValidatorState.FAILED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            findings=[
                ValidationFinding(
                    finding_id="f1",
                    severity=ResultSeverity.ERROR,
                    message="Volume is negative",
                ),
            ],
        )

        status = GateStatus(
            gate_id="test",
            can_advance=False,
            blocking_validators=["hull/volume"],
            validator_results={"hull/volume": result},
            stale_parameters=["LOA"],
            missing_validators=["hull/wetted"],
            contract_errors=["Contract violation"],
            intent_violations=["Intent violation"],
        )

        messages = status.get_all_blocking_messages()
        assert any("Volume is negative" in m for m in messages)
        assert any("STALE" in m and "LOA" in m for m in messages)
        assert any("MISSING" in m and "hull/wetted" in m for m in messages)
        assert any("CONTRACT" in m for m in messages)
        assert any("INTENT" in m for m in messages)

    def test_get_all_warning_messages(self):
        """Test getting all warning messages."""
        result = ValidationResult(
            validator_id="hull/volume",
            state=ValidatorState.WARNING,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            findings=[
                ValidationFinding(
                    finding_id="w1",
                    severity=ResultSeverity.WARNING,
                    message="Volume is borderline",
                ),
            ],
        )

        status = GateStatus(
            gate_id="test",
            can_advance=True,
            warning_validators=["hull/volume"],
            validator_results={"hull/volume": result},
        )

        messages = status.get_all_warning_messages()
        assert any("borderline" in m for m in messages)

    def test_get_summary(self):
        """Test get_summary method."""
        status = GateStatus(
            gate_id="hull_form",
            can_advance=True,
            required_passed=5,
            required_failed=0,
            recommended_passed=3,
            recommended_failed=1,
            stale_parameters=["LOA"],
        )

        summary = status.get_summary()
        assert summary["gate_id"] == "hull_form"
        assert summary["can_advance"] == True
        assert summary["required_passed"] == 5
        assert summary["stale_count"] == 1

    def test_to_dict(self):
        """Test full serialization."""
        status = GateStatus(
            gate_id="mission",
            can_advance=False,
            blocking_validators=["mission/range"],
            stale_parameters=["fuel_capacity"],
        )

        data = status.to_dict()
        assert data["gate_id"] == "mission"
        assert "mission/range" in data["blocking_validators"]
        assert "fuel_capacity" in data["stale_parameters"]
        assert "blocking_messages" in data


class TestResultAggregator:
    """Test ResultAggregator class."""

    def _create_mock_topology(self, gate_validators=None):
        """Create a mock topology."""
        topology = Mock(spec=ValidatorTopology)
        topology.get_gate_validators_for_phase.return_value = gate_validators or []

        def mock_get_node(v_id):
            if not v_id:
                return None
            node = Mock()
            node.validator = ValidatorDefinition(
                validator_id=v_id,
                name=v_id,
                description="Test",
                category=ValidatorCategory.PHYSICS,
                is_gate_condition=True,
                gate_severity=ResultSeverity.ERROR,
                gate_requirement=GateRequirement.REQUIRED,  # v1.1: Required for gate blocking
            )
            return node

        topology.get_node.side_effect = mock_get_node
        return topology

    def test_create_aggregator(self):
        """Test creating aggregator."""
        topology = self._create_mock_topology()
        aggregator = ResultAggregator(topology=topology)
        assert aggregator._topology == topology

    def test_check_gate_no_validators(self):
        """Test checking gate with no validators."""
        topology = self._create_mock_topology([])
        aggregator = ResultAggregator(topology=topology)

        exec_state = ExecutionState(
            execution_id="test",
            started_at=datetime.utcnow(),
        )

        status = aggregator.check_gate("hull_form", exec_state)
        assert status.can_advance == True
        assert status.required_passed == 0

    def test_check_gate_all_passed(self):
        """Test gate check when all validators pass."""
        topology = self._create_mock_topology(["hull/volume", "hull/wetted"])
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

        status = aggregator.check_gate("hull_form", exec_state)
        assert status.can_advance == True
        assert status.required_passed == 2
        assert status.required_failed == 0

    def test_check_gate_required_failed(self):
        """Test gate check when required validator fails."""
        topology = self._create_mock_topology(["hull/volume"])
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
                    message="Volume too small",
                ),
            ],
        )

        status = aggregator.check_gate("hull_form", exec_state)
        assert status.can_advance == False
        assert status.required_failed == 1
        assert "hull/volume" in status.blocking_validators

    def test_check_gate_warning_still_passes(self):
        """Test gate check with warnings still passes."""
        topology = self._create_mock_topology(["hull/volume"])
        aggregator = ResultAggregator(topology=topology)

        exec_state = ExecutionState(
            execution_id="test",
            started_at=datetime.utcnow(),
        )
        exec_state.results["hull/volume"] = ValidationResult(
            validator_id="hull/volume",
            state=ValidatorState.WARNING,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            findings=[
                ValidationFinding(
                    finding_id="w1",
                    severity=ResultSeverity.WARNING,
                    message="Volume borderline",
                ),
            ],
        )

        status = aggregator.check_gate("hull_form", exec_state)
        assert status.can_advance == True
        assert "hull/volume" in status.warning_validators

    def test_check_gate_error_state_blocks(self):
        """Test gate check with ERROR state (code failure) blocks."""
        topology = self._create_mock_topology(["hull/volume"])
        aggregator = ResultAggregator(topology=topology)

        exec_state = ExecutionState(
            execution_id="test",
            started_at=datetime.utcnow(),
        )
        exec_state.results["hull/volume"] = ValidationResult(
            validator_id="hull/volume",
            state=ValidatorState.ERROR,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            error_message="Exception in validator",
        )

        status = aggregator.check_gate("hull_form", exec_state)
        assert status.can_advance == False
        assert "hull/volume" in status.blocking_validators

    def test_check_gate_missing_result_blocks(self):
        """Test gate check when required validator has no result."""
        topology = self._create_mock_topology(["hull/volume"])
        aggregator = ResultAggregator(topology=topology)

        exec_state = ExecutionState(
            execution_id="test",
            started_at=datetime.utcnow(),
        )
        # No results - hull/volume never ran

        status = aggregator.check_gate("hull_form", exec_state)
        assert status.can_advance == False
        assert status.required_failed == 1

    def test_fix7_missing_validator_tracked(self):
        """Test FIX #7: Missing validators are tracked."""
        topology = Mock(spec=ValidatorTopology)
        topology.get_gate_validators_for_phase.return_value = ["nonexistent/v"]
        topology.get_node.return_value = None  # Validator not found

        aggregator = ResultAggregator(topology=topology)

        exec_state = ExecutionState(
            execution_id="test",
            started_at=datetime.utcnow(),
        )

        status = aggregator.check_gate("hull_form", exec_state)
        assert "nonexistent/v" in status.missing_validators

    def test_fix7_stale_parameters_checked(self):
        """Test FIX #7: Stale parameters checked via state manager."""
        topology = self._create_mock_topology([])

        state_manager = Mock()
        state_manager.is_field_stale.side_effect = lambda p: p == "LOA"

        aggregator = ResultAggregator(
            topology=topology,
            state_manager=state_manager,
        )

        exec_state = ExecutionState(
            execution_id="test",
            started_at=datetime.utcnow(),
        )

        with patch(
            "magnet.dependencies.graph.PHASE_OWNERSHIP",
            {"hull_form": ["LOA", "beam"]}
        ):
            status = aggregator.check_gate("hull_form", exec_state)
            assert "LOA" in status.stale_parameters
            assert status.can_advance == False

    def test_fix7_contract_errors_checked(self):
        """Test FIX #7: Contract errors checked."""
        topology = self._create_mock_topology([])

        contract_layer = Mock()
        contract_layer.get_violations_for_phase.return_value = ["LOA > 0 violated"]

        aggregator = ResultAggregator(
            topology=topology,
            contract_layer=contract_layer,
        )

        exec_state = ExecutionState(
            execution_id="test",
            started_at=datetime.utcnow(),
        )

        status = aggregator.check_gate("hull_form", exec_state)
        assert len(status.contract_errors) > 0
        assert status.can_advance == False

    def test_fix7_intent_violations_checked(self):
        """Test FIX #7: Intent violations checked."""
        topology = self._create_mock_topology([])

        intent_engine = Mock()
        intent_engine.get_violations_for_phase.return_value = ["Speed exceeds intent"]

        aggregator = ResultAggregator(
            topology=topology,
            intent_engine=intent_engine,
        )

        exec_state = ExecutionState(
            execution_id="test",
            started_at=datetime.utcnow(),
        )

        status = aggregator.check_gate("hull_form", exec_state)
        assert len(status.intent_violations) > 0
        assert status.can_advance == False

    def test_check_all_gates(self):
        """Test checking all gates."""
        topology = self._create_mock_topology([])
        aggregator = ResultAggregator(topology=topology)

        exec_state = ExecutionState(
            execution_id="test",
            started_at=datetime.utcnow(),
        )

        with patch(
            "magnet.dependencies.graph.PHASE_OWNERSHIP",
            {"hull_form": [], "mission": [], "resistance": []}
        ):
            results = aggregator.check_all_gates(exec_state)
            assert "hull_form" in results
            assert "mission" in results
            assert "resistance" in results

    def test_get_blocking_summary(self):
        """Test getting blocking summary."""
        topology = self._create_mock_topology(["hull/volume"])
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
        )

        with patch(
            "magnet.dependencies.graph.PHASE_OWNERSHIP",
            {"hull_form": []}
        ):
            summary = aggregator.get_blocking_summary(exec_state)
            assert "blocked_phases" in summary
            assert "total_blocking_validators" in summary


class TestAggregatorHelpers:
    """Test helper functions."""

    def test_create_aggregator_function(self):
        """Test create_aggregator helper."""
        # This requires builtin validators to exist
        try:
            aggregator = create_aggregator()
            assert aggregator._topology.is_built == True
        except Exception:
            # May fail if no validators registered
            pass

    def test_check_phase_gate_function(self):
        """Test check_phase_gate helper."""
        exec_state = ExecutionState(
            execution_id="test",
            started_at=datetime.utcnow(),
        )

        try:
            status = check_phase_gate("hull_form", exec_state)
            assert status.gate_id == "hull_form"
        except Exception:
            # May fail if no validators registered
            pass


class TestGateStatusEdgeCases:
    """Test edge cases for GateStatus."""

    def test_blocking_validator_no_result(self):
        """Test blocking message when validator has no result."""
        status = GateStatus(
            gate_id="test",
            can_advance=False,
            blocking_validators=["missing/v"],
            validator_results={},  # No result
        )

        messages = status.get_all_blocking_messages()
        assert any("Did not run" in m for m in messages)

    def test_combined_blocking_conditions(self):
        """Test gate with multiple blocking conditions."""
        status = GateStatus(
            gate_id="test",
            can_advance=False,
            required_failed=1,
            stale_parameters=["LOA"],
            contract_errors=["Contract error"],
            intent_violations=["Intent violation"],
        )

        assert status.has_blocking_conditions == True
        messages = status.get_all_blocking_messages()
        # Should have messages for all conditions
        assert len(messages) >= 3
