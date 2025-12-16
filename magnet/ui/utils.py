"""
ui/utils.py - Unified state access for UI layer v1.1

Provides consistent state access across all UI modules, handling:
- Field aliases for schema compatibility
- Phase state enum translation
- Snapshot registry for reports
- Phase completion hooks for vision integration

This module is the SINGLE SOURCE OF TRUTH for UI state access.
All UI modules (CLI, Vision, Reporting, Dashboard, Chat) use these functions.
"""

from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from enum import Enum
from dataclasses import dataclass, field
import logging

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger("ui.utils")


# =============================================================================
# FIELD ALIAS SYSTEM
# =============================================================================

UI_FIELD_ALIASES: Dict[str, List[str]] = {
    # Hull Parameters
    "hull.loa": ["hull.length_overall", "principal_dimensions.loa", "hull_form.loa"],
    "hull.lwl": ["hull.waterline_length", "principal_dimensions.lwl", "hull_form.lwl"],
    "hull.beam": ["hull.breadth", "principal_dimensions.beam", "hull_form.beam"],
    "hull.draft": ["hull.design_draft", "principal_dimensions.draft", "hull_form.draft"],
    "hull.depth": ["hull.moulded_depth", "principal_dimensions.depth", "hull_form.depth"],
    "hull.displacement_mt": [
        "weight.full_load_displacement_mt",
        "displacement_tonnes",
        "hull.displacement_tonnes",
        "weight.displacement_mt",
        "hydrostatics.displacement_mt",
    ],
    "hull.cb": ["hull.block_coefficient", "coefficients.cb", "hull_form.cb"],
    "hull.cp": ["hull.prismatic_coefficient", "coefficients.cp", "hull_form.cp"],
    "hull.cwp": ["hull.waterplane_coefficient", "coefficients.cwp", "hull_form.cwp"],
    "hull.deadrise_deg": ["hull.deadrise", "hull.deadrise_angle_deg", "hull_form.deadrise_deg"],
    "hull.transom_width_ratio": ["hull.transom_ratio", "hull_form.transom_width_ratio"],

    # Mission Parameters
    "mission.max_speed_kts": ["mission.max_speed_knots", "performance.max_speed_kts"],
    "mission.cruise_speed_kts": ["mission.cruise_speed_knots", "performance.cruise_speed_kts"],
    "mission.range_nm": ["mission.endurance_nm", "performance.range_nm"],

    # Propulsion
    "propulsion.installed_power_kw": [
        "propulsion.total_installed_power_kw",
        "power.installed_kw",
        "systems.propulsion.installed_power_kw",
    ],
    "propulsion.num_engines": ["propulsion.engine_count", "systems.propulsion.num_engines"],
    "propulsion.propulsion_type": ["propulsion.type", "systems.propulsion.type"],

    # Structure
    "structure.plating.bottom_thickness_mm": [
        "structure.bottom_plating_mm",
        "scantlings.bottom_thickness_mm",
    ],
    "structure.plating.side_thickness_mm": [
        "structure.side_plating_mm",
        "scantlings.side_thickness_mm",
    ],
    "structure.frame_spacing_mm": ["structure.framing.frame_spacing_mm", "scantlings.frame_spacing_mm"],

    # Stability
    "stability.gm_transverse_m": [
        "stability.gm_m",
        "stability.transverse_gm_m",
        "hydrostatics.gm_transverse_m",
    ],
    "stability.gz_max": ["stability.max_gz_m", "stability.gz_max_m"],
    "stability.gz_curve": ["stability.gz_data", "stability.righting_arm_curve"],
    "stability.gz_curve.points": ["stability.gz_curve.data", "stability.gz_data.points"],

    # Weight
    "weight.groups": ["weight.weight_groups", "weight.swbs_groups"],
    "weight.loading_conditions": ["weight.load_cases", "stability.loading_conditions", "loading.conditions"],

    # Compliance
    "compliance.overall_passed": ["compliance.passed", "compliance.all_passed", "validation.overall_passed"],
    "compliance.errors": ["compliance.failures", "validation.errors"],
    "compliance.warnings": ["compliance.cautions", "validation.warnings"],
    "compliance.checks": ["compliance.results", "validation.checks"],

    # Phase States
    "phase_states": ["phases", "phase_machine.states", "orchestration.phases"],
}


def get_nested(data: Any, path: str, default: Any = None) -> Any:
    """
    Get nested value from dict/object using dot notation.

    Args:
        data: Dict, object, or StateManager
        path: Dot-notation path (e.g., "hull.loa")
        default: Value to return if path not found

    Returns:
        Value at path or default
    """
    if data is None:
        return default

    parts = path.split(".")
    current = data

    for part in parts:
        if current is None:
            return default

        if isinstance(current, dict):
            current = current.get(part)
        elif hasattr(current, part):
            current = getattr(current, part)
        elif hasattr(current, '__getitem__'):
            try:
                current = current[part]
            except (KeyError, TypeError, IndexError):
                return default
        else:
            return default

    return current if current is not None else default


def get_state_value(
    state: Any,
    path: str,
    default: Any = None,
    use_aliases: bool = True,
) -> Any:
    """
    Get value from state with alias fallback.

    This is the PRIMARY state accessor for ALL UI modules.

    Args:
        state: StateManager, DesignState, or dict
        path: Dot-notation path (e.g., "hull.loa")
        default: Default value if not found
        use_aliases: Whether to try alias paths (default True)

    Returns:
        Value at path or default
    """
    # Try direct path
    value = get_nested(state, path)
    if value is not None:
        return value

    # Try aliases
    if use_aliases and path in UI_FIELD_ALIASES:
        for alias in UI_FIELD_ALIASES[path]:
            value = get_nested(state, alias)
            if value is not None:
                return value

    # Try StateManager.get() if available
    if hasattr(state, 'get'):
        try:
            value = state.get(path, None)
            if value is not None:
                return value
        except Exception:
            pass

    return default


def set_state_value(
    state: Any,
    path: str,
    value: Any,
    source: str = "ui",
) -> bool:
    """
    Set value in state.

    Args:
        state: StateManager or dict
        path: Dot-notation path
        value: Value to set
        source: Source identifier for audit trail

    Returns:
        True if successful
    """
    # Try glue/utils.py safe_write first
    try:
        from magnet.glue.utils import safe_write
        if safe_write(state, path, value, source):
            return True
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"safe_write failed: {e}")

    # Try StateManager.set()
    if hasattr(state, 'set'):
        try:
            return state.set(path, value, source)
        except Exception as e:
            logger.warning(f"StateManager.set() failed: {e}")

    # Fallback to dict manipulation
    if isinstance(state, dict):
        parts = path.split(".")
        current = state

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
            if not isinstance(current, dict):
                return False

        current[parts[-1]] = value
        return True

    return False


# =============================================================================
# PHASE STATE TRANSLATION
# =============================================================================

PHASE_STATE_ENUM_MAP: Dict[str, str] = {
    "DRAFT": "pending",
    "PENDING": "pending",
    "ACTIVE": "active",
    "IN_PROGRESS": "active",
    "LOCKED": "completed",
    "COMPLETED": "completed",
    "APPROVED": "approved",
    "INVALIDATED": "error",
    "ERROR": "error",
    "SKIPPED": "skipped",
}

UI_STATUS_TO_ENUM: Dict[str, str] = {
    "pending": "PENDING",
    "active": "ACTIVE",
    "completed": "COMPLETED",
    "approved": "APPROVED",
    "error": "ERROR",
    "skipped": "SKIPPED",
}


def get_phase_status(state: Any, phase: str, default: str = "pending") -> str:
    """
    Get phase status, translating from PhaseState enum if needed.

    Returns UI-friendly status: pending, active, completed, approved, error, skipped

    Args:
        state: StateManager or dict
        phase: Phase name (e.g., "hull_form")
        default: Default status if not found

    Returns:
        UI-friendly status string
    """
    # Try phase_states.<phase>.status (dict format)
    status = get_state_value(state, f"phase_states.{phase}.status", use_aliases=False)

    if status is None:
        status = get_state_value(state, f"phase_states.{phase}", use_aliases=False)

    if status is None:
        for path in [f"phases.{phase}.status", f"phases.{phase}"]:
            status = get_nested(state, path)
            if status is not None:
                break

    if status is None:
        return default

    # Handle Enum type
    if isinstance(status, Enum):
        status = status.name
    elif isinstance(status, dict):
        status = status.get("status", status.get("state", default))

    # Translate to UI-friendly status
    status_str = str(status).upper()
    return PHASE_STATE_ENUM_MAP.get(status_str, default)


def set_phase_status(state: Any, phase: str, status: str, source: str = "ui") -> bool:
    """
    Set phase status.

    DEPRECATED: Use PhaseMachine.transition() directly for proper state machine transitions.
    This function is retained for backwards compatibility and will be removed in v2.0.

    Args:
        state: StateManager or dict
        phase: Phase name
        status: UI status (pending/active/completed/approved/error/skipped)
        source: Source identifier

    Returns:
        True if successful
    """
    import warnings
    warnings.warn(
        "set_phase_status() is deprecated. Use PhaseMachine.transition() instead. "
        "This function will be removed in v2.0.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Try to use PhaseMachine.transition() if StateManager is available
    if hasattr(state, '_state') or hasattr(state, 'get'):
        try:
            from magnet.core.phase_states import PhaseMachine
            from magnet.core.enums import PhaseState

            # Map UI status to PhaseState enum
            status_map = {
                "pending": PhaseState.PENDING,
                "active": PhaseState.ACTIVE,
                "completed": PhaseState.COMPLETED,
                "approved": PhaseState.APPROVED,
                "error": PhaseState.ERROR,
                "skipped": PhaseState.SKIPPED,
                "locked": PhaseState.LOCKED,
                "draft": PhaseState.DRAFT,
                "invalidated": PhaseState.INVALIDATED,
            }

            target_state = status_map.get(status.lower())
            if target_state is not None:
                machine = PhaseMachine(state)
                result = machine.transition(phase, target_state, source, reason="via deprecated set_phase_status()")
                if result:
                    return True
                # Fall through to legacy behavior if transition fails
                logger.debug(f"PhaseMachine.transition() returned False for {phase}->{status}, using fallback")

        except Exception as e:
            logger.debug(f"PhaseMachine.transition() failed: {e}, using fallback")

    # Legacy fallback for dict-based state or when transition fails
    if isinstance(state, dict) and "phase_states" not in state:
        state["phase_states"] = {}

    phase_data = get_state_value(state, f"phase_states.{phase}", {})
    if not isinstance(phase_data, dict):
        phase_data = {}

    phase_data["status"] = status

    return set_state_value(state, f"phase_states.{phase}", phase_data, source)


# =============================================================================
# STATE SERIALIZATION
# =============================================================================

def serialize_state(state: Any) -> Dict[str, Any]:
    """
    Serialize state to dictionary.

    Used by CLI save, ReportGenerator, DataPackageExporter.

    Returns:
        Dictionary representation of state
    """
    if hasattr(state, 'to_dict'):
        try:
            return state.to_dict()
        except Exception as e:
            logger.warning(f"to_dict() failed: {e}")

    try:
        from magnet.glue.utils import serialize_state as glue_serialize
        return glue_serialize(state)
    except ImportError:
        pass

    if hasattr(state, '__dict__'):
        return _recursive_dict(state.__dict__)

    if isinstance(state, dict):
        return _recursive_dict(state)

    logger.warning(f"Unable to serialize state of type {type(state)}")
    return {}


def _recursive_dict(obj: Any) -> Any:
    """Recursively convert objects to serializable dicts."""
    if isinstance(obj, dict):
        return {k: _recursive_dict(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_recursive_dict(item) for item in obj]
    elif isinstance(obj, Enum):
        return obj.value
    elif hasattr(obj, 'to_dict'):
        return obj.to_dict()
    elif hasattr(obj, '__dict__') and not isinstance(obj, type):
        return _recursive_dict(obj.__dict__)
    else:
        return obj


def load_state_from_dict(state: Any, data: Dict[str, Any]) -> bool:
    """
    Load state from dictionary.

    Args:
        state: StateManager or dict to load into
        data: Dictionary of state data

    Returns:
        True if successful
    """
    if hasattr(state, 'load_from_dict'):
        try:
            state.load_from_dict(data)
            return True
        except Exception as e:
            logger.warning(f"load_from_dict() failed: {e}")

    if hasattr(state, 'from_dict'):
        try:
            state.from_dict(data)
            return True
        except Exception as e:
            logger.warning(f"from_dict() failed: {e}")

    if isinstance(state, dict):
        state.update(data)
        return True

    return False


# =============================================================================
# SNAPSHOT REGISTRY
# =============================================================================

class SnapshotRegistry:
    """
    Registry for managing vision snapshots by section_id.

    Reports need snapshots keyed by section_id (e.g., "hull_render").
    """

    def __init__(self):
        self._snapshots: Dict[str, str] = {}
        self._by_phase: Dict[str, List[str]] = {}

    def register(
        self,
        section_id: str,
        path: str,
        phase: Optional[str] = None,
    ) -> None:
        """
        Register snapshot path for section.

        Args:
            section_id: Unique identifier (e.g., "hull_render", "gz_chart")
            path: File path to snapshot image
            phase: Optional phase name for grouping
        """
        self._snapshots[section_id] = path

        if phase:
            if phase not in self._by_phase:
                self._by_phase[phase] = []
            if section_id not in self._by_phase[phase]:
                self._by_phase[phase].append(section_id)

    def get(self, section_id: str) -> Optional[str]:
        """Get snapshot path by section_id."""
        return self._snapshots.get(section_id)

    def get_for_phase(self, phase: str) -> Dict[str, str]:
        """Get all snapshots for a phase."""
        return {
            sid: self._snapshots[sid]
            for sid in self._by_phase.get(phase, [])
            if sid in self._snapshots
        }

    def get_all(self) -> Dict[str, str]:
        """Get all registered snapshots."""
        return dict(self._snapshots)

    def clear(self) -> None:
        """Clear all snapshots."""
        self._snapshots.clear()
        self._by_phase.clear()


# Global singleton
snapshot_registry = SnapshotRegistry()


# =============================================================================
# PHASE COMPLETION HOOKS
# =============================================================================

class PhaseCompletionHooks:
    """
    Manages phase completion hooks for triggering vision snapshots.
    """

    _instance = None
    _hooks: Dict[str, List[Callable]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._hooks = {}
        return cls._instance

    @classmethod
    def register(cls, phase: str, callback: Callable) -> None:
        """
        Register callback for phase completion.

        Args:
            phase: Phase name (e.g., "hull_form")
            callback: Function(state, phase=phase, **kwargs) -> Any
        """
        if phase not in cls._hooks:
            cls._hooks[phase] = []
        cls._hooks[phase].append(callback)

    @classmethod
    def trigger(cls, phase: str, state: Any, **kwargs) -> List[Any]:
        """
        Trigger all callbacks for phase completion.

        Args:
            phase: Phase name
            state: Current design state
            **kwargs: Additional arguments passed to callbacks

        Returns:
            List of callback return values
        """
        results = []
        for callback in cls._hooks.get(phase, []):
            try:
                result = callback(state, phase=phase, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Hook failed for phase {phase}: {e}")
        return results

    @classmethod
    def clear(cls, phase: str = None) -> None:
        """Clear hooks for a phase or all hooks."""
        if phase:
            cls._hooks.pop(phase, None)
        else:
            cls._hooks.clear()


# Global singleton
phase_hooks = PhaseCompletionHooks()
