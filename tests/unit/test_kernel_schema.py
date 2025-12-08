"""
tests/unit/test_kernel_schema.py - Tests for kernel schema.

BRAVO OWNS THIS FILE.

Tests for Module 15 v1.1 - Kernel data structures.
"""

import pytest
from datetime import datetime, timezone, timedelta
from magnet.kernel import (
    PhaseResult,
    GateResult,
    SessionState,
    PhaseStatus,
    GateCondition,
    SessionStatus,
)


class TestPhaseResult:
    """Tests for PhaseResult dataclass."""

    def test_create_phase_result(self):
        """Test basic phase result creation."""
        result = PhaseResult(
            phase_name="hull",
            status=PhaseStatus.COMPLETED,
        )
        assert result.phase_name == "hull"
        assert result.status == PhaseStatus.COMPLETED

    def test_default_values(self):
        """Test default values."""
        result = PhaseResult(
            phase_name="test",
            status=PhaseStatus.PENDING,
        )
        assert result.started_at is None
        assert result.completed_at is None
        assert result.validators_run == 0
        assert result.validators_passed == 0
        assert result.validators_failed == 0
        assert result.errors == []
        assert result.warnings == []

    def test_duration_with_times(self):
        """Test duration calculation with times."""
        now = datetime.now(timezone.utc)
        result = PhaseResult(
            phase_name="test",
            status=PhaseStatus.COMPLETED,
            started_at=now,
            completed_at=now + timedelta(seconds=5),
        )
        assert result.duration_s == 5.0

    def test_duration_without_times(self):
        """Test duration is 0 without times."""
        result = PhaseResult(
            phase_name="test",
            status=PhaseStatus.PENDING,
        )
        assert result.duration_s == 0.0

    def test_pass_rate_calculation(self):
        """Test pass rate calculation."""
        result = PhaseResult(
            phase_name="test",
            status=PhaseStatus.COMPLETED,
            validators_run=10,
            validators_passed=8,
            validators_failed=2,
        )
        assert result.pass_rate == 0.8

    def test_pass_rate_zero_validators(self):
        """Test pass rate is 0 with no validators."""
        result = PhaseResult(
            phase_name="test",
            status=PhaseStatus.COMPLETED,
        )
        assert result.pass_rate == 0.0

    def test_to_dict(self):
        """Test dictionary serialization."""
        now = datetime.now(timezone.utc)
        result = PhaseResult(
            phase_name="hull",
            status=PhaseStatus.COMPLETED,
            started_at=now,
            completed_at=now + timedelta(seconds=2),
            validators_run=5,
            validators_passed=4,
            validators_failed=1,
            errors=["error1"],
            warnings=["warn1"],
        )
        data = result.to_dict()

        assert data["phase_name"] == "hull"
        assert data["status"] == "completed"
        assert data["duration_s"] == 2.0
        assert data["validators_run"] == 5
        assert data["validators_passed"] == 4
        assert data["validators_failed"] == 1
        assert data["pass_rate"] == 0.8
        assert data["errors"] == ["error1"]
        assert data["warnings"] == ["warn1"]


class TestGateResult:
    """Tests for GateResult dataclass."""

    def test_create_gate_result(self):
        """Test basic gate result creation."""
        result = GateResult(
            gate_name="compliance_gate",
            condition=GateCondition.ALL_PASS,
            passed=True,
        )
        assert result.gate_name == "compliance_gate"
        assert result.condition == GateCondition.ALL_PASS
        assert result.passed == True

    def test_default_values(self):
        """Test default values."""
        result = GateResult(
            gate_name="test",
            condition=GateCondition.THRESHOLD,
            passed=False,
        )
        assert result.evaluated_at is None
        assert result.threshold is None
        assert result.actual_value is None
        assert result.blocking_failures == []

    def test_gate_with_threshold(self):
        """Test gate with threshold values."""
        result = GateResult(
            gate_name="quality_gate",
            condition=GateCondition.THRESHOLD,
            passed=True,
            threshold=0.8,
            actual_value=0.9,
        )
        assert result.threshold == 0.8
        assert result.actual_value == 0.9

    def test_gate_with_blocking_failures(self):
        """Test gate with blocking failures."""
        result = GateResult(
            gate_name="test",
            condition=GateCondition.ALL_PASS,
            passed=False,
            blocking_failures=["Validator A failed", "Validator B failed"],
        )
        assert len(result.blocking_failures) == 2

    def test_to_dict(self):
        """Test dictionary serialization."""
        now = datetime.now(timezone.utc)
        result = GateResult(
            gate_name="compliance_gate",
            condition=GateCondition.CRITICAL_PASS,
            passed=True,
            evaluated_at=now,
            threshold=0.0,
            actual_value=0.0,
        )
        data = result.to_dict()

        assert data["gate_name"] == "compliance_gate"
        assert data["condition"] == "critical_pass"
        assert data["passed"] == True
        assert data["threshold"] == 0.0
        assert data["actual_value"] == 0.0


class TestSessionState:
    """Tests for SessionState dataclass."""

    def test_create_session_state(self):
        """Test basic session state creation."""
        session = SessionState(
            session_id="sess-123",
            design_id="design-456",
            status=SessionStatus.ACTIVE,
        )
        assert session.session_id == "sess-123"
        assert session.design_id == "design-456"
        assert session.status == SessionStatus.ACTIVE

    def test_default_values(self):
        """Test default values."""
        session = SessionState(
            session_id="test",
            design_id="test",
            status=SessionStatus.INITIALIZING,
        )
        assert session.current_phase is None
        assert session.completed_phases == []
        assert session.phase_results == {}
        assert session.gate_results == {}
        assert session.total_validators_run == 0
        assert session.total_validators_passed == 0

    def test_add_phase_result(self):
        """Test adding phase result."""
        session = SessionState(
            session_id="test",
            design_id="test",
            status=SessionStatus.ACTIVE,
        )

        result = PhaseResult(
            phase_name="hull",
            status=PhaseStatus.COMPLETED,
            validators_run=5,
            validators_passed=4,
        )

        session.add_phase_result(result)

        assert "hull" in session.phase_results
        assert "hull" in session.completed_phases
        assert session.total_validators_run == 5
        assert session.total_validators_passed == 4

    def test_add_phase_result_failed(self):
        """Test adding failed phase result."""
        session = SessionState(
            session_id="test",
            design_id="test",
            status=SessionStatus.ACTIVE,
        )

        result = PhaseResult(
            phase_name="stability",
            status=PhaseStatus.FAILED,
            validators_run=3,
            validators_passed=1,
        )

        session.add_phase_result(result)

        assert "stability" in session.phase_results
        # Failed phases not added to completed
        assert "stability" not in session.completed_phases

    def test_add_gate_result(self):
        """Test adding gate result."""
        session = SessionState(
            session_id="test",
            design_id="test",
            status=SessionStatus.ACTIVE,
        )

        gate = GateResult(
            gate_name="compliance_gate",
            condition=GateCondition.ALL_PASS,
            passed=True,
        )

        session.add_gate_result(gate)

        assert "compliance_gate" in session.gate_results
        assert session.gate_results["compliance_gate"].passed == True

    def test_overall_pass_rate(self):
        """Test overall pass rate calculation."""
        session = SessionState(
            session_id="test",
            design_id="test",
            status=SessionStatus.ACTIVE,
        )

        result1 = PhaseResult(
            phase_name="phase1",
            status=PhaseStatus.COMPLETED,
            validators_run=10,
            validators_passed=8,
        )
        result2 = PhaseResult(
            phase_name="phase2",
            status=PhaseStatus.COMPLETED,
            validators_run=10,
            validators_passed=9,
        )

        session.add_phase_result(result1)
        session.add_phase_result(result2)

        # 17/20 = 0.85
        assert session.overall_pass_rate == 0.85

    def test_overall_pass_rate_zero(self):
        """Test overall pass rate with no validators."""
        session = SessionState(
            session_id="test",
            design_id="test",
            status=SessionStatus.ACTIVE,
        )
        assert session.overall_pass_rate == 0.0

    def test_to_dict(self):
        """Test dictionary serialization."""
        session = SessionState(
            session_id="sess-123",
            design_id="design-456",
            status=SessionStatus.ACTIVE,
            current_phase="hull",
            completed_phases=["mission"],
        )

        data = session.to_dict()

        assert data["session_id"] == "sess-123"
        assert data["design_id"] == "design-456"
        assert data["status"] == "active"
        assert data["current_phase"] == "hull"
        assert data["completed_phases"] == ["mission"]
        assert "created_at" in data
        assert "updated_at" in data


class TestPhaseStatus:
    """Tests for PhaseStatus enum."""

    def test_all_statuses_exist(self):
        """Test all expected statuses exist."""
        assert PhaseStatus.PENDING.value == "pending"
        assert PhaseStatus.RUNNING.value == "running"
        assert PhaseStatus.COMPLETED.value == "completed"
        assert PhaseStatus.FAILED.value == "failed"
        assert PhaseStatus.SKIPPED.value == "skipped"
        assert PhaseStatus.BLOCKED.value == "blocked"


class TestGateCondition:
    """Tests for GateCondition enum."""

    def test_all_conditions_exist(self):
        """Test all expected conditions exist."""
        assert GateCondition.ALL_PASS.value == "all_pass"
        assert GateCondition.CRITICAL_PASS.value == "critical_pass"
        assert GateCondition.THRESHOLD.value == "threshold"
        assert GateCondition.MANUAL.value == "manual"


class TestSessionStatus:
    """Tests for SessionStatus enum."""

    def test_all_statuses_exist(self):
        """Test all expected statuses exist."""
        assert SessionStatus.INITIALIZING.value == "initializing"
        assert SessionStatus.ACTIVE.value == "active"
        assert SessionStatus.PAUSED.value == "paused"
        assert SessionStatus.COMPLETED.value == "completed"
        assert SessionStatus.FAILED.value == "failed"
        assert SessionStatus.CANCELLED.value == "cancelled"
