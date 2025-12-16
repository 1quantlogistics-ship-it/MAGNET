"""
Unit tests for MAGNET Intent→Action Protocol.

Tests the foundational types that form the firewall between
LLM proposals and kernel mutations.
"""

import pytest
from datetime import datetime
from magnet.kernel.intent_protocol import (
    IntentType,
    ActionType,
    Intent,
    Action,
    ActionPlan,
    ActionResult,
)


# =============================================================================
# INTENT TESTS
# =============================================================================

class TestIntent:
    """Tests for Intent dataclass."""

    def test_intent_creation(self):
        """Intent can be created with required fields."""
        intent = Intent(
            intent_id="int_123",
            design_id="design_001",
            raw_text="Increase power by 1 MW",
            intent_type=IntentType.REFINE,
            confidence=0.95,
            parsed_at=datetime(2024, 1, 15, 10, 30, 0),
        )
        assert intent.intent_id == "int_123"
        assert intent.design_id == "design_001"
        assert intent.raw_text == "Increase power by 1 MW"
        assert intent.intent_type == IntentType.REFINE
        assert intent.confidence == 0.95

    def test_intent_is_immutable(self):
        """Intent is frozen (immutable)."""
        intent = Intent(
            intent_id="int_123",
            design_id="design_001",
            raw_text="test",
            intent_type=IntentType.QUERY,
            confidence=0.9,
            parsed_at=datetime.utcnow(),
        )
        with pytest.raises(AttributeError):
            intent.confidence = 0.5

    def test_intent_roundtrip(self):
        """Intent can be serialized and deserialized."""
        original = Intent(
            intent_id="int_abc",
            design_id="design_xyz",
            raw_text="Lock hull.loa",
            intent_type=IntentType.LOCK,
            confidence=0.88,
            parsed_at=datetime(2024, 6, 1, 12, 0, 0),
        )
        data = original.to_dict()
        restored = Intent.from_dict(data)
        assert restored == original

    def test_intent_type_values(self):
        """All intent types have expected string values."""
        assert IntentType.REFINE.value == "refine"
        assert IntentType.CREATE.value == "create"
        assert IntentType.QUERY.value == "query"
        assert IntentType.LOCK.value == "lock"
        assert IntentType.RUN_PIPELINE.value == "run_pipeline"
        assert IntentType.EXPORT.value == "export"
        assert IntentType.CLARIFY.value == "clarify"
        assert IntentType.UNKNOWN.value == "unknown"


# =============================================================================
# ACTION TESTS
# =============================================================================

class TestAction:
    """Tests for Action dataclass."""

    def test_action_set(self):
        """SET action has path and value."""
        action = Action(
            action_type=ActionType.SET,
            path="hull.loa",
            value=100.0,
            unit="m",
        )
        assert action.action_type == ActionType.SET
        assert action.path == "hull.loa"
        assert action.value == 100.0
        assert action.unit == "m"

    def test_action_increase(self):
        """INCREASE action has path and amount."""
        action = Action(
            action_type=ActionType.INCREASE,
            path="propulsion.total_installed_power_kw",
            amount=1000,
            unit="kW",
        )
        assert action.action_type == ActionType.INCREASE
        assert action.amount == 1000

    def test_action_run_phases(self):
        """RUN_PHASES action has phases list."""
        action = Action(
            action_type=ActionType.RUN_PHASES,
            phases=["hull", "weight", "stability"],
        )
        assert action.action_type == ActionType.RUN_PHASES
        assert action.phases == ["hull", "weight", "stability"]

    def test_action_is_immutable(self):
        """Action is frozen (immutable)."""
        action = Action(action_type=ActionType.SET, path="hull.loa", value=50)
        with pytest.raises(AttributeError):
            action.value = 100

    def test_action_with_value_immutable(self):
        """with_value() returns new Action, original unchanged."""
        original = Action(action_type=ActionType.SET, path="hull.loa", value=50)
        clamped = original.with_value(45)

        assert original.value == 50  # Original unchanged
        assert clamped.value == 45   # New value
        assert clamped.path == original.path
        assert clamped.action_type == original.action_type

    def test_action_with_amount(self):
        """with_amount() returns new Action for clamping amounts."""
        original = Action(action_type=ActionType.INCREASE, path="power", amount=1000)
        clamped = original.with_amount(500)

        assert original.amount == 1000
        assert clamped.amount == 500

    def test_action_roundtrip(self):
        """Action can be serialized and deserialized."""
        original = Action(
            action_type=ActionType.SET,
            path="propulsion.total_installed_power_kw",
            value=5000,
            unit="kW",
        )
        data = original.to_dict()
        restored = Action.from_dict(data)
        assert restored == original

    def test_action_roundtrip_minimal(self):
        """Action with only required fields can roundtrip."""
        original = Action(action_type=ActionType.NOOP)
        data = original.to_dict()
        restored = Action.from_dict(data)
        assert restored == original

    def test_action_type_values(self):
        """All action types have expected string values."""
        assert ActionType.SET.value == "set"
        assert ActionType.INCREASE.value == "increase"
        assert ActionType.DECREASE.value == "decrease"
        assert ActionType.LOCK.value == "lock"
        assert ActionType.UNLOCK.value == "unlock"
        assert ActionType.RUN_PHASES.value == "run_phases"
        assert ActionType.EXPORT.value == "export"
        assert ActionType.REQUEST_CLARIFICATION.value == "request_clarification"
        assert ActionType.NOOP.value == "noop"


# =============================================================================
# ACTION PLAN TESTS
# =============================================================================

class TestActionPlan:
    """Tests for ActionPlan dataclass."""

    def test_action_plan_creation(self):
        """ActionPlan can be created with actions list."""
        actions = [
            Action(action_type=ActionType.LOCK, path="hull.loa"),
            Action(action_type=ActionType.SET, path="hull.beam", value=20),
            Action(action_type=ActionType.RUN_PHASES, phases=["hull", "weight"]),
        ]
        plan = ActionPlan(
            plan_id="plan_001",
            intent_id="int_abc",
            design_id="design_xyz",
            actions=actions,
            design_version_before=5,
            proposed_at=datetime(2024, 1, 15, 10, 0, 0),
        )
        assert plan.plan_id == "plan_001"
        assert plan.design_version_before == 5
        assert len(plan) == 3

    def test_action_plan_converts_list_to_tuple(self):
        """ActionPlan converts actions list to tuple for immutability."""
        actions = [Action(action_type=ActionType.SET, path="hull.loa", value=100)]
        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=actions,
            design_version_before=0,
            proposed_at=datetime.utcnow(),
        )
        assert isinstance(plan.actions, tuple)

    def test_action_plan_is_immutable(self):
        """ActionPlan is frozen (immutable)."""
        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[],
            design_version_before=0,
            proposed_at=datetime.utcnow(),
        )
        with pytest.raises(AttributeError):
            plan.design_version_before = 10

    def test_action_plan_roundtrip(self):
        """ActionPlan can be serialized and deserialized."""
        original = ActionPlan(
            plan_id="plan_xyz",
            intent_id="int_abc",
            design_id="design_001",
            actions=[
                Action(action_type=ActionType.SET, path="hull.loa", value=100),
                Action(action_type=ActionType.INCREASE, path="power", amount=500, unit="kW"),
            ],
            design_version_before=7,
            proposed_at=datetime(2024, 3, 20, 14, 30, 0),
        )
        data = original.to_dict()
        restored = ActionPlan.from_dict(data)

        assert restored.plan_id == original.plan_id
        assert restored.intent_id == original.intent_id
        assert restored.design_version_before == original.design_version_before
        assert len(restored.actions) == len(original.actions)
        assert restored.actions[0].path == original.actions[0].path

    def test_action_plan_iterable(self):
        """ActionPlan can be iterated over actions."""
        actions = [
            Action(action_type=ActionType.SET, path="a", value=1),
            Action(action_type=ActionType.SET, path="b", value=2),
        ]
        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=actions,
            design_version_before=0,
            proposed_at=datetime.utcnow(),
        )
        paths = [a.path for a in plan]
        assert paths == ["a", "b"]


# =============================================================================
# ACTION RESULT TESTS
# =============================================================================

class TestActionResult:
    """Tests for ActionResult dataclass."""

    def test_action_result_success(self):
        """ActionResult.success is True when actions were executed."""
        result = ActionResult(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            design_version_before=5,
            design_version_after=6,
            actions_executed=[
                Action(action_type=ActionType.SET, path="hull.loa", value=100),
            ],
            actions_rejected=[],
            warnings=[],
            executed_at=datetime.utcnow(),
        )
        assert result.success is True
        assert result.version_changed is True

    def test_action_result_failure(self):
        """ActionResult.success is False when no actions were executed."""
        result = ActionResult(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            design_version_before=5,
            design_version_after=5,  # No change
            actions_executed=[],
            actions_rejected=[
                (Action(action_type=ActionType.SET, path="bad.path", value=1), "Path not refinable"),
            ],
            warnings=[],
            executed_at=datetime.utcnow(),
        )
        assert result.success is False
        assert result.version_changed is False

    def test_action_result_with_warnings(self):
        """ActionResult can include warnings (e.g., clamping)."""
        result = ActionResult(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            design_version_before=0,
            design_version_after=1,
            actions_executed=[
                Action(action_type=ActionType.SET, path="hull.loa", value=50),  # Clamped
            ],
            actions_rejected=[],
            warnings=["Value clamped from 100 to 50"],
            executed_at=datetime.utcnow(),
        )
        assert result.success is True
        assert len(result.warnings) == 1
        assert "clamped" in result.warnings[0]

    def test_action_result_roundtrip(self):
        """ActionResult can be serialized and deserialized."""
        original = ActionResult(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            design_version_before=5,
            design_version_after=6,
            actions_executed=[
                Action(action_type=ActionType.SET, path="hull.loa", value=100),
            ],
            actions_rejected=[
                (Action(action_type=ActionType.SET, path="locked.param", value=50), "Parameter locked"),
            ],
            warnings=["Some warning"],
            executed_at=datetime(2024, 6, 15, 12, 0, 0),
        )
        data = original.to_dict()
        restored = ActionResult.from_dict(data)

        assert restored.plan_id == original.plan_id
        assert restored.design_version_before == original.design_version_before
        assert restored.design_version_after == original.design_version_after
        assert len(restored.actions_executed) == 1
        assert len(restored.actions_rejected) == 1
        assert restored.warnings == original.warnings


# =============================================================================
# INTEGRATION / WORKFLOW TESTS
# =============================================================================

class TestIntentToActionWorkflow:
    """Tests for the full Intent → ActionPlan → ActionResult workflow."""

    def test_full_workflow_types(self):
        """Complete workflow maintains type integrity."""
        # 1. User input parsed to Intent
        intent = Intent(
            intent_id="int_workflow_001",
            design_id="design_test",
            raw_text="I need 1 more megawatt, keep the hull size fixed",
            intent_type=IntentType.REFINE,
            confidence=0.92,
            parsed_at=datetime.utcnow(),
        )

        # 2. Intent translated to ActionPlan
        plan = ActionPlan(
            plan_id="plan_workflow_001",
            intent_id=intent.intent_id,
            design_id=intent.design_id,
            actions=[
                Action(action_type=ActionType.LOCK, path="hull.loa"),
                Action(action_type=ActionType.LOCK, path="hull.beam"),
                Action(action_type=ActionType.INCREASE, path="propulsion.total_installed_power_kw", amount=1000, unit="kW"),
                Action(action_type=ActionType.RUN_PHASES, phases=["propulsion", "weight", "stability"]),
            ],
            design_version_before=7,
            proposed_at=datetime.utcnow(),
        )

        # 3. Execution produces ActionResult
        result = ActionResult(
            plan_id=plan.plan_id,
            intent_id=plan.intent_id,
            design_id=plan.design_id,
            design_version_before=plan.design_version_before,
            design_version_after=8,
            actions_executed=plan.actions,  # All approved
            actions_rejected=[],
            warnings=[],
            executed_at=datetime.utcnow(),
        )

        # Assertions
        assert result.intent_id == intent.intent_id
        assert result.plan_id == plan.plan_id
        assert result.success is True
        assert result.version_changed is True
        assert len(result.actions_executed) == 4

    def test_stale_plan_detection_data(self):
        """ActionPlan carries version info for stale detection."""
        plan = ActionPlan(
            plan_id="p1",
            intent_id="i1",
            design_id="d1",
            actions=[Action(action_type=ActionType.SET, path="hull.loa", value=100)],
            design_version_before=5,  # Plan created when version was 5
            proposed_at=datetime.utcnow(),
        )

        # If current version is 7, plan is stale
        current_version = 7
        is_stale = plan.design_version_before != current_version
        assert is_stale is True

        # If current version is 5, plan is fresh
        current_version = 5
        is_stale = plan.design_version_before != current_version
        assert is_stale is False
