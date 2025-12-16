"""
Unit tests for ActionPlanValidator.

Tests the firewall between LLM proposals and kernel mutations.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from magnet.kernel.action_validator import (
    ActionPlanValidator,
    ValidationResult,
    ActionValidation,
    StalePlanError,
)
from magnet.kernel.intent_protocol import Action, ActionPlan, ActionType


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_state_manager():
    """Create a mock StateManager."""
    mock = Mock()
    mock.design_version = 5
    mock.is_locked = Mock(return_value=False)
    mock.get = Mock(return_value=100.0)  # Default current value for deltas
    return mock


@pytest.fixture
def validator():
    """Create an ActionPlanValidator."""
    return ActionPlanValidator()


@pytest.fixture
def sample_plan():
    """Create a sample ActionPlan."""
    return ActionPlan(
        plan_id="test_plan",
        intent_id="test_intent",
        design_id="test_design",
        actions=[
            Action(action_type=ActionType.SET, path="hull.loa", value=50, unit="m"),
        ],
        design_version_before=5,
        proposed_at=datetime.utcnow(),
    )


# =============================================================================
# STALE PLAN DETECTION
# =============================================================================

class TestStalePlanDetection:
    """Tests for stale plan detection."""

    def test_stale_plan_raises_error(self, validator, mock_state_manager):
        """Stale plan (version mismatch) raises StalePlanError."""
        mock_state_manager.design_version = 10  # Current is 10

        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[],
            design_version_before=5,  # Plan was created at version 5
            proposed_at=datetime.utcnow(),
        )

        with pytest.raises(StalePlanError, match="Plan is stale"):
            validator.validate(plan, mock_state_manager)

    def test_fresh_plan_accepted(self, validator, mock_state_manager):
        """Fresh plan (version matches) is accepted."""
        mock_state_manager.design_version = 5

        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        assert isinstance(result, ValidationResult)

    def test_skip_stale_check(self, validator, mock_state_manager):
        """Can skip stale check if needed."""
        mock_state_manager.design_version = 10

        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        # Should not raise when check_stale=False
        result = validator.validate(plan, mock_state_manager, check_stale=False)
        assert isinstance(result, ValidationResult)


# =============================================================================
# SET ACTION VALIDATION
# =============================================================================

class TestSetActionValidation:
    """Tests for SET action validation."""

    def test_valid_set_action(self, validator, mock_state_manager, sample_plan):
        """Valid SET action is approved."""
        result = validator.validate(sample_plan, mock_state_manager)
        assert len(result.approved) == 1
        assert len(result.rejected) == 0

    def test_rejects_non_refinable_path(self, validator, mock_state_manager):
        """Rejects SET on non-refinable path."""
        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[
                Action(action_type=ActionType.SET, path="nonexistent.path", value=100),
            ],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        assert len(result.approved) == 0
        assert len(result.rejected) == 1
        assert "not refinable" in result.rejected[0][1]

    def test_rejects_locked_parameter(self, validator, mock_state_manager):
        """Rejects SET on locked parameter."""
        mock_state_manager.is_locked = Mock(return_value=True)

        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[
                Action(action_type=ActionType.SET, path="hull.loa", value=100),
            ],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        assert len(result.approved) == 0
        assert len(result.rejected) == 1
        assert "locked" in result.rejected[0][1].lower()

    def test_clamps_to_bounds(self, validator, mock_state_manager):
        """Values exceeding bounds are clamped."""
        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[
                # hull.loa has max_value=500
                Action(action_type=ActionType.SET, path="hull.loa", value=999, unit="m"),
            ],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        assert len(result.approved) == 1
        assert result.approved[0].value == 500  # Clamped to max
        assert len(result.warnings) > 0
        assert "clamped" in result.warnings[0].lower()

    def test_converts_units(self, validator, mock_state_manager):
        """Units are converted to kernel_unit."""
        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[
                # 100 ft in meters
                Action(action_type=ActionType.SET, path="hull.loa", value=100, unit="ft"),
            ],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        assert len(result.approved) == 1
        # 100 ft = 30.48 m
        assert abs(result.approved[0].value - 30.48) < 0.01

    def test_rejects_invalid_unit(self, validator, mock_state_manager):
        """Rejects invalid unit for path."""
        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[
                # hull.loa doesn't accept "kW" as unit
                Action(action_type=ActionType.SET, path="hull.loa", value=100, unit="kW"),
            ],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        assert len(result.rejected) == 1
        assert "not allowed" in result.rejected[0][1].lower()


# =============================================================================
# INCREASE/DECREASE ACTION VALIDATION
# =============================================================================

class TestDeltaActionValidation:
    """Tests for INCREASE/DECREASE action validation."""

    def test_valid_increase(self, validator, mock_state_manager):
        """Valid INCREASE action is approved."""
        mock_state_manager.get = Mock(return_value=1000.0)

        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[
                Action(
                    action_type=ActionType.INCREASE,
                    path="propulsion.total_installed_power_kw",
                    amount=500,
                    unit="kW"
                ),
            ],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        assert len(result.approved) == 1
        # Should be converted to SET with computed value
        assert result.approved[0].action_type == ActionType.SET
        assert result.approved[0].value == 1500.0  # 1000 + 500

    def test_valid_decrease(self, validator, mock_state_manager):
        """Valid DECREASE action is approved."""
        mock_state_manager.get = Mock(return_value=1000.0)

        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[
                Action(
                    action_type=ActionType.DECREASE,
                    path="propulsion.total_installed_power_kw",
                    amount=200,
                    unit="kW"
                ),
            ],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        assert len(result.approved) == 1
        assert result.approved[0].value == 800.0  # 1000 - 200

    def test_increase_with_unit_conversion(self, validator, mock_state_manager):
        """INCREASE with different unit is converted."""
        mock_state_manager.get = Mock(return_value=1000.0)  # 1000 kW

        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[
                # +1 MW = +1000 kW
                Action(
                    action_type=ActionType.INCREASE,
                    path="propulsion.total_installed_power_kw",
                    amount=1,
                    unit="MW"
                ),
            ],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        assert len(result.approved) == 1
        assert result.approved[0].value == 2000.0  # 1000 + 1000

    def test_rejects_delta_on_unset_value(self, validator, mock_state_manager):
        """Rejects delta on unset value."""
        mock_state_manager.get = Mock(return_value=None)

        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[
                Action(
                    action_type=ActionType.INCREASE,
                    path="propulsion.total_installed_power_kw",
                    amount=500
                ),
            ],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        assert len(result.rejected) == 1
        assert "unset" in result.rejected[0][1].lower()


# =============================================================================
# LOCK/UNLOCK ACTION VALIDATION
# =============================================================================

class TestLockActionValidation:
    """Tests for LOCK/UNLOCK action validation."""

    def test_valid_lock(self, validator, mock_state_manager):
        """Valid LOCK action is approved."""
        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[
                Action(action_type=ActionType.LOCK, path="hull.loa"),
            ],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        assert len(result.approved) == 1

    def test_lock_then_set_same_path_rejected(self, validator, mock_state_manager):
        """LOCK followed by SET on same path is rejected."""
        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[
                Action(action_type=ActionType.LOCK, path="hull.loa"),
                Action(action_type=ActionType.SET, path="hull.loa", value=100),
            ],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        # LOCK is approved
        assert any(a.action_type == ActionType.LOCK for a in result.approved)
        # SET is rejected
        assert len(result.rejected) == 1
        assert "locked by earlier action" in result.rejected[0][1].lower()

    def test_lock_nonexistent_path_rejected(self, validator, mock_state_manager):
        """LOCK on non-refinable path is rejected."""
        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[
                Action(action_type=ActionType.LOCK, path="nonexistent.path"),
            ],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        assert len(result.rejected) == 1
        assert "non-refinable" in result.rejected[0][1].lower()

    def test_unlock_nonlocked_path_warns(self, validator, mock_state_manager):
        """UNLOCK on non-locked path gives warning."""
        mock_state_manager.is_locked = Mock(return_value=False)

        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[
                Action(action_type=ActionType.UNLOCK, path="hull.loa"),
            ],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        assert len(result.approved) == 1
        assert len(result.warnings) > 0
        assert "was not locked" in result.warnings[0].lower()


# =============================================================================
# RUN_PHASES ACTION VALIDATION
# =============================================================================

class TestRunPhasesValidation:
    """Tests for RUN_PHASES action validation."""

    def test_valid_phases(self, validator, mock_state_manager):
        """Valid phase names are approved."""
        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[
                Action(
                    action_type=ActionType.RUN_PHASES,
                    phases=["hull", "weight", "stability"]
                ),
            ],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        assert len(result.approved) == 1

    def test_invalid_phase_rejected(self, validator, mock_state_manager):
        """Invalid phase names are rejected."""
        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[
                Action(
                    action_type=ActionType.RUN_PHASES,
                    phases=["hull", "nonexistent_phase"]
                ),
            ],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        assert len(result.rejected) == 1
        assert "invalid phase" in result.rejected[0][1].lower()

    def test_empty_phases_rejected(self, validator, mock_state_manager):
        """Empty phases list is rejected."""
        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[
                Action(action_type=ActionType.RUN_PHASES, phases=[]),
            ],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        assert len(result.rejected) == 1


# =============================================================================
# OTHER ACTION TYPES
# =============================================================================

class TestOtherActionTypes:
    """Tests for NOOP, EXPORT, REQUEST_CLARIFICATION."""

    def test_noop_approved(self, validator, mock_state_manager):
        """NOOP action is approved (query-only)."""
        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[
                Action(action_type=ActionType.NOOP),
            ],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        assert len(result.approved) == 1

    def test_export_approved(self, validator, mock_state_manager):
        """EXPORT action is approved."""
        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[
                Action(action_type=ActionType.EXPORT, format="pdf"),
            ],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        assert len(result.approved) == 1

    def test_clarification_approved(self, validator, mock_state_manager):
        """REQUEST_CLARIFICATION action is approved."""
        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[
                Action(
                    action_type=ActionType.REQUEST_CLARIFICATION,
                    message="What speed do you want?"
                ),
            ],
            design_version_before=5,
            proposed_at=datetime.utcnow(),
        )

        result = validator.validate(plan, mock_state_manager)
        assert len(result.approved) == 1


# =============================================================================
# VALIDATION RESULT PROPERTIES
# =============================================================================

class TestValidationResultProperties:
    """Tests for ValidationResult properties."""

    def test_all_approved(self):
        """all_approved is True when no rejections."""
        result = ValidationResult(
            approved=[Action(action_type=ActionType.NOOP)],
            rejected=[],
            warnings=[]
        )
        assert result.all_approved is True
        assert result.has_rejections is False

    def test_has_rejections(self):
        """has_rejections is True when rejections exist."""
        result = ValidationResult(
            approved=[],
            rejected=[(Action(action_type=ActionType.SET, path="x", value=1), "reason")],
            warnings=[]
        )
        assert result.all_approved is False
        assert result.has_rejections is True
