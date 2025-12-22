"""
MAGNET ActionPlanValidator v1.0

The firewall between LLM proposals and kernel mutations.

Validates ActionPlans against:
- REFINABLE_SCHEMA (path whitelist)
- Unit conversion and normalization
- Bounds clamping
- Parameter locks
- Stale plan detection

INVARIANT: LLM never directly drives state. Validator enforces all constraints.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from magnet.kernel.intent_protocol import Action, ActionPlan, ActionType
from magnet.core.refinable_schema import REFINABLE_SCHEMA, RefinableField, is_refinable
from magnet.core.unit_converter import UnitConverter, UnitConversionError, clamp_to_bounds

# =============================================================================
# KERNEL-OWNED BASELINES AND BUCKET DELTA POLICY (v67.x)
# =============================================================================

# Deterministic baselines used when applying deltas to unset values
_BASELINE_VALUES: Dict[str, float] = {
    # Hull
    "hull.loa": 30.0,
    "hull.beam": 8.0,
    "hull.draft": 2.0,
    "hull.depth": 4.0,
    # Mission
    "mission.max_speed_kts": 25.0,
    "mission.cruise_speed_kts": 18.0,
    "mission.range_nm": 500.0,
    "mission.crew_berthed": 6,
    "mission.passengers": 50,
    # Propulsion
    "propulsion.total_installed_power_kw": 2000.0,
}

# Path-aware bucket delta policy (absolute steps or bounded percentages)
_DELTA_POLICY: Dict[str, Dict[str, float]] = {
    # Hull (absolute meters)
    "hull.loa": {"type": "absolute", "a_bit": 1.0, "normal": 2.0, "way": 5.0},
    "hull.beam": {"type": "absolute", "a_bit": 0.2, "normal": 0.5, "way": 1.0},
    "hull.draft": {"type": "absolute", "a_bit": 0.10, "normal": 0.25, "way": 0.50},
    "hull.depth": {"type": "absolute", "a_bit": 0.20, "normal": 0.50, "way": 1.00},
    # Mission (absolute kts / nm / counts)
    "mission.max_speed_kts": {"type": "absolute", "a_bit": 1.0, "normal": 3.0, "way": 7.0},
    "mission.cruise_speed_kts": {"type": "absolute", "a_bit": 1.0, "normal": 2.0, "way": 5.0},
    "mission.range_nm": {"type": "absolute", "a_bit": 50.0, "normal": 200.0, "way": 500.0},
    "mission.crew_berthed": {"type": "absolute", "a_bit": 1.0, "normal": 3.0, "way": 8.0},
    "mission.passengers": {"type": "absolute", "a_bit": 10.0, "normal": 50.0, "way": 200.0},
    # Propulsion (bounded percent with floor, kW)
    "propulsion.total_installed_power_kw": {
        "type": "percent",
        "a_bit": 0.05,
        "normal": 0.15,
        "way": 0.35,
        "min_abs": 100.0,
    },
}

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


# =============================================================================
# VALIDATION RESULT TYPES
# =============================================================================

@dataclass
class ActionValidation:
    """
    Result of validating a single Action.
    """
    approved: bool
    action: Optional[Action] = None  # May be modified (e.g., clamped value)
    reason: Optional[str] = None     # Why rejected (if not approved)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """
    Result of validating an ActionPlan.
    """
    approved: List[Action]                    # Actions that passed validation (may be clamped)
    rejected: List[Tuple[Action, str]]        # (Action, reason) pairs
    warnings: List[str]                       # Warnings (e.g., clamping)

    @property
    def has_rejections(self) -> bool:
        """True if any actions were rejected."""
        return len(self.rejected) > 0

    @property
    def all_approved(self) -> bool:
        """True if all actions were approved."""
        return len(self.rejected) == 0


class StalePlanError(Exception):
    """
    Raised when an ActionPlan's design_version_before doesn't match current state.

    This indicates a race condition where the state changed between when
    the plan was created and when it was submitted.
    """
    pass


# =============================================================================
# ACTION PLAN VALIDATOR
# =============================================================================

class ActionPlanValidator:
    """
    Deterministic validation of proposed ActionPlans.

    This is the firewall between LLM proposals and kernel mutations.
    All actions must pass validation before execution.
    """

    def __init__(self, refinable_schema: Dict[str, RefinableField] = None):
        """
        Initialize validator.

        Args:
            refinable_schema: Schema defining refinable paths.
                              Defaults to REFINABLE_SCHEMA.
        """
        self._schema = refinable_schema or REFINABLE_SCHEMA

    def validate(
        self,
        plan: ActionPlan,
        state_manager: "StateManager",
        check_stale: bool = True
    ) -> ValidationResult:
        """
        Validate an ActionPlan against the current state.

        Args:
            plan: The ActionPlan to validate
            state_manager: Current state manager (for lock checking, version)
            check_stale: Whether to check for stale plan (default True)

        Returns:
            ValidationResult with approved/rejected actions

        Raises:
            StalePlanError: If plan.design_version_before doesn't match current
        """
        # Check for stale plan FIRST
        if check_stale:
            current_version = state_manager.design_version
            if plan.design_version_before != current_version:
                raise StalePlanError(
                    f"Plan is stale: expected design_version={plan.design_version_before}, "
                    f"current={current_version}. Re-fetch state and resubmit."
                )

        approved = []
        rejected = []
        warnings = []

        # Track locks applied within this plan (for lock-then-modify detection)
        pending_locks = set()

        for action in plan.actions:
            result = self._validate_action(action, state_manager, pending_locks)

            if result.approved:
                approved.append(result.action)
                warnings.extend(result.warnings)

                # Track LOCK actions for subsequent validation
                if action.action_type == ActionType.LOCK and action.path:
                    pending_locks.add(action.path)

            else:
                rejected.append((action, result.reason))

        return ValidationResult(
            approved=approved,
            rejected=rejected,
            warnings=warnings
        )

    def _validate_action(
        self,
        action: Action,
        state_manager: "StateManager",
        pending_locks: set
    ) -> ActionValidation:
        """
        Validate a single action.

        Args:
            action: The Action to validate
            state_manager: Current state manager
            pending_locks: Set of paths locked by earlier actions in same plan

        Returns:
            ActionValidation result
        """
        if action.action_type == ActionType.SET:
            return self._validate_set(action, state_manager, pending_locks)
        elif action.action_type in (ActionType.INCREASE, ActionType.DECREASE):
            return self._validate_delta(action, state_manager, pending_locks)
        elif action.action_type == ActionType.LOCK:
            return self._validate_lock(action, state_manager)
        elif action.action_type == ActionType.UNLOCK:
            return self._validate_unlock(action, state_manager)
        elif action.action_type == ActionType.RUN_PHASES:
            return self._validate_run_phases(action)
        elif action.action_type == ActionType.EXPORT:
            return ActionValidation(approved=True, action=action)
        elif action.action_type == ActionType.REQUEST_CLARIFICATION:
            return ActionValidation(approved=True, action=action)
        elif action.action_type == ActionType.NOOP:
            return ActionValidation(approved=True, action=action)
        else:
            return ActionValidation(
                approved=False,
                reason=f"Unknown action type: {action.action_type}"
            )

    def _validate_set(
        self,
        action: Action,
        state_manager: "StateManager",
        pending_locks: set
    ) -> ActionValidation:
        """Validate a SET action."""
        warnings = []

        # 1. Check path is refinable
        if not is_refinable(action.path):
            return ActionValidation(
                approved=False,
                reason=f"Path not refinable: {action.path}"
            )

        field = self._schema[action.path]

        # 2. Check for lock (existing or pending in this plan)
        if state_manager.is_locked(action.path):
            return ActionValidation(
                approved=False,
                reason=f"Parameter locked: {action.path}"
            )

        if action.path in pending_locks:
            return ActionValidation(
                approved=False,
                reason=f"Parameter locked by earlier action in same plan: {action.path}"
            )

        # 3. Normalize unit
        value = action.value
        if action.unit and action.unit != field.kernel_unit:
            if action.unit not in field.allowed_units:
                return ActionValidation(
                    approved=False,
                    reason=f"Unit not allowed for {action.path}: {action.unit}. "
                           f"Allowed: {field.allowed_units}"
                )
            try:
                value = UnitConverter.normalize(value, action.unit, field.kernel_unit)
            except UnitConversionError as e:
                return ActionValidation(
                    approved=False,
                    reason=f"Unit conversion failed: {e}"
                )

        # 4. Type coercion
        if field.type == "int":
            value = int(round(value))
        elif field.type == "float":
            value = float(value)
        elif field.type == "bool":
            value = bool(value)
        elif field.type == "enum":
            # Validate enum value is in allowed_values
            value = str(value).lower().strip()
            if field.allowed_values and value not in field.allowed_values:
                return ActionValidation(
                    approved=False,
                    reason=f"Invalid enum value for {action.path}: {value}. "
                           f"Allowed: {field.allowed_values}"
                )

        # 5. Clamp to bounds
        if field.type in ("int", "float"):
            clamped, was_clamped = clamp_to_bounds(value, field.min_value, field.max_value)
            if was_clamped:
                warnings.append(
                    f"Value for {action.path} clamped from {value} to {clamped} "
                    f"(bounds: {field.min_value}-{field.max_value})"
                )
                value = clamped

        # Return approved action with normalized/clamped value
        return ActionValidation(
            approved=True,
            action=action.with_value(value),
            warnings=warnings
        )

    def _validate_delta(
        self,
        action: Action,
        state_manager: "StateManager",
        pending_locks: set
    ) -> ActionValidation:
        """Validate an INCREASE or DECREASE action."""
        warnings = []

        # 1. Check path is refinable
        if not is_refinable(action.path):
            return ActionValidation(
                approved=False,
                reason=f"Path not refinable: {action.path}"
            )

        field = self._schema[action.path]

        # 2. Check for lock
        if state_manager.is_locked(action.path):
            return ActionValidation(
                approved=False,
                reason=f"Parameter locked: {action.path}"
            )

        if action.path in pending_locks:
            return ActionValidation(
                approved=False,
                reason=f"Parameter locked by earlier action in same plan: {action.path}"
            )

        # 3. Get current value (prefer get_strict to detect unset)
        current = None
        try:
            if hasattr(state_manager, "get_strict"):
                current = state_manager.get_strict(action.path)
                # Handle sentinel if available
                try:
                    from magnet.core.state_manager import MISSING

                    if current is MISSING:
                        current = None
                except Exception:
                    pass
        except Exception:
            current = None

        if current is None:
            try:
                current = state_manager.get(action.path)
            except Exception:
                current = None

        if current is None:
            if action.path in _BASELINE_VALUES:
                current = _BASELINE_VALUES[action.path]
                warnings.append(f"baseline_used:{action.path}={_BASELINE_VALUES[action.path]}")
            else:
                return ActionValidation(
                    approved=False,
                    reason=f"Cannot apply delta to unset value: {action.path}"
                )

        # 4. Determine amount (bucket-aware or unit-normalized)
        is_bucket = bool(action.unit) and str(action.unit).startswith("bucket:")
        amount = action.amount

        if (amount is None) and (is_bucket or (action.unit is None and action.path in _DELTA_POLICY)):
            bucket = "normal"
            if is_bucket:
                _, _, bucket_token = str(action.unit).partition(":")
                bucket = bucket_token or "normal"
            policy = _DELTA_POLICY.get(action.path)
            if not policy:
                return ActionValidation(
                    approved=False,
                    reason=f"Bucket delta not allowed for path: {action.path}"
                )
            if bucket not in policy:
                return ActionValidation(
                    approved=False,
                    reason=f"Bucket '{bucket}' not allowed for path: {action.path}"
                )

            if policy.get("type") == "absolute":
                amount = policy[bucket]
            elif policy.get("type") == "percent":
                pct = policy[bucket]
                min_abs = policy.get("min_abs", 0.0)
                amount = max(current * pct, min_abs)
            else:
                return ActionValidation(
                    approved=False,
                    reason=f"Unknown bucket policy type for path: {action.path}"
                )
        else:
            # Non-bucket path: normalize units if provided
            if amount is None:
                return ActionValidation(
                    approved=False,
                    reason=f"Delta amount is required for {action.path}"
                )
            if action.unit and action.unit != field.kernel_unit:
                if action.unit not in field.allowed_units:
                    return ActionValidation(
                        approved=False,
                        reason=f"Unit not allowed for {action.path}: {action.unit}"
                    )
                try:
                    amount = UnitConverter.normalize(amount, action.unit, field.kernel_unit)
                except UnitConversionError as e:
                    return ActionValidation(
                        approved=False,
                        reason=f"Unit conversion failed: {e}"
                    )

        # 5. Calculate new value
        if action.action_type == ActionType.INCREASE:
            new_value = current + amount
        else:  # DECREASE
            new_value = current - amount

        # 6. Clamp to bounds
        clamped, was_clamped = clamp_to_bounds(new_value, field.min_value, field.max_value)
        if was_clamped:
            warnings.append(
                f"Resulting value for {action.path} clamped from {new_value} to {clamped} "
                f"(bounds: {field.min_value}-{field.max_value})"
            )
            new_value = clamped

        # 7. Type coercion for numeric/int fields
        if field.type == "int":
            new_value = int(round(new_value))
        elif field.type == "float":
            new_value = float(new_value)

        # Convert delta action to SET action with computed value
        return ActionValidation(
            approved=True,
            action=Action(
                action_type=ActionType.SET,
                path=action.path,
                value=new_value,
                unit=field.kernel_unit
            ),
            warnings=warnings
        )

    def _validate_lock(
        self,
        action: Action,
        state_manager: "StateManager"
    ) -> ActionValidation:
        """Validate a LOCK action."""
        if not action.path:
            return ActionValidation(
                approved=False,
                reason="LOCK action requires a path"
            )

        if not is_refinable(action.path):
            return ActionValidation(
                approved=False,
                reason=f"Cannot lock non-refinable path: {action.path}"
            )

        if state_manager.is_locked(action.path):
            return ActionValidation(
                approved=True,
                action=action,
                warnings=[f"Path already locked: {action.path}"]
            )

        return ActionValidation(approved=True, action=action)

    def _validate_unlock(
        self,
        action: Action,
        state_manager: "StateManager"
    ) -> ActionValidation:
        """Validate an UNLOCK action."""
        if not action.path:
            return ActionValidation(
                approved=False,
                reason="UNLOCK action requires a path"
            )

        if not is_refinable(action.path):
            return ActionValidation(
                approved=False,
                reason=f"Cannot unlock non-refinable path: {action.path}"
            )

        if not state_manager.is_locked(action.path):
            return ActionValidation(
                approved=True,
                action=action,
                warnings=[f"Path was not locked: {action.path}"]
            )

        return ActionValidation(approved=True, action=action)

    def _validate_run_phases(self, action: Action) -> ActionValidation:
        """Validate a RUN_PHASES action."""
        if not action.phases:
            return ActionValidation(
                approved=False,
                reason="RUN_PHASES action requires phases list"
            )

        # Valid phase names
        valid_phases = {
            "mission", "hull", "structure", "propulsion",
            "weight", "stability", "compliance", "loading",
            "production", "optimization"
        }

        invalid = [p for p in action.phases if p not in valid_phases]
        if invalid:
            return ActionValidation(
                approved=False,
                reason=f"Invalid phase names: {invalid}. Valid: {valid_phases}"
            )

        return ActionValidation(approved=True, action=action)
