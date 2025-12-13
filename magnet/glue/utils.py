"""
glue/utils.py - Shared utilities for System Glue Layer
BRAVO OWNS THIS FILE.

Provides safe accessor functions that work with both StateManager
and dict-like objects, handling missing get() default parameter
in older StateManager versions.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


def safe_get(state, path: str, default=None) -> Any:
    """
    Safely get value from state with default.

    Works with both StateManager and dict-like objects.
    Handles missing get() default parameter in older StateManager versions.

    Args:
        state: StateManager or dict-like object
        path: Dot-notation path (e.g., "hull.loa")
        default: Value to return if path not found

    Returns:
        Value at path, or default if not found
    """
    if state is None:
        return default

    # Try StateManager.get() with default
    if hasattr(state, 'get'):
        try:
            # Try two-arg version first
            result = state.get(path, default)
            return result if result is not None else default
        except TypeError:
            # Fallback: single-arg version
            try:
                result = state.get(path)
                return result if result is not None else default
            except (KeyError, AttributeError):
                return default

    # Dict-like access
    if isinstance(state, dict):
        parts = path.split('.')
        current = state
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    return default


def safe_write(state, path: str, value: Any, source: str = "glue") -> bool:
    """
    Safely write value to state.

    Returns True if successful, False otherwise.

    Args:
        state: StateManager or dict-like object
        path: Dot-notation path
        value: Value to write
        source: Source identifier for tracking

    Returns:
        True if write succeeded, False otherwise
    """
    try:
        # Hole #7 Fix: Standardize on .set() with proper source
        if hasattr(state, 'set'):
            state.set(path, value, source)
            return True
        elif isinstance(state, dict):
            parts = path.split('.')
            current = state
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
            return True
    except Exception:
        pass
    return False


def serialize_state(state) -> Dict[str, Any]:
    """
    Serialize state to JSON-compatible dict.

    Handles StateManager, DesignState, and dict.

    Args:
        state: State object to serialize

    Returns:
        JSON-compatible dictionary
    """
    if state is None:
        return {}

    # Try to_dict() method
    if hasattr(state, 'to_dict'):
        return state.to_dict()

    # Try dataclass asdict
    if hasattr(state, '__dataclass_fields__'):
        from dataclasses import asdict
        return asdict(state)

    # Dict passthrough
    if isinstance(state, dict):
        return dict(state)

    # Last resort: vars()
    try:
        return vars(state)
    except TypeError:
        return {}


# Speed field mapping (consistency fix A)
SPEED_FIELD_ALIASES = {
    "max_speed_kts": ["max_speed_knots", "speed_max_kts", "speed_max"],
    "cruise_speed_kts": ["cruise_speed_knots", "speed_cruise_kts"],
    "min_speed_kts": ["min_speed_knots", "speed_min_kts"],
}


def get_speed_field(state, base_path: str, field: str, default=None) -> Any:
    """
    Get speed field with alias fallback.

    Handles inconsistent naming between modules.

    Args:
        state: StateManager or dict-like object
        base_path: Base path (e.g., "mission" or "performance")
        field: Field name (e.g., "max_speed_kts")
        default: Default value if not found

    Returns:
        Speed value or default
    """
    # Try primary field name
    primary_path = f"{base_path}.{field}"
    value = safe_get(state, primary_path)
    if value is not None:
        return value

    # Try aliases
    if field in SPEED_FIELD_ALIASES:
        for alias in SPEED_FIELD_ALIASES[field]:
            alias_path = f"{base_path}.{alias}"
            value = safe_get(state, alias_path)
            if value is not None:
                return value

    return default


def compute_state_hash(state_dict: Dict[str, Any], exclude_fields: Optional[List[str]] = None) -> str:
    """
    Compute deterministic hash of state dict.

    Excludes timestamp fields by default for reproducibility.

    Args:
        state_dict: State dictionary to hash
        exclude_fields: Additional fields to exclude

    Returns:
        Hexadecimal hash string
    """
    import hashlib
    import json

    # Default exclusions (timestamps cause non-determinism)
    default_excludes = {'created_at', 'updated_at', 'timestamp', 'modified_at'}
    excludes = default_excludes | set(exclude_fields or [])

    def filter_dict(d: Dict) -> Dict:
        """Recursively filter out excluded fields."""
        result = {}
        for k, v in d.items():
            if k in excludes:
                continue
            if isinstance(v, dict):
                result[k] = filter_dict(v)
            else:
                result[k] = v
        return result

    filtered = filter_dict(state_dict)
    # Sort keys for determinism
    json_str = json.dumps(filtered, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode()).hexdigest()[:16]
