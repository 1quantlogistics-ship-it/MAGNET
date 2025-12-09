"""
bootstrap/state_compat.py - State manager compatibility layer v1.1

Module 55: Bootstrap Layer

Provides compatibility wrappers ensuring StateManager works with all modules.
Addresses blocker #2: StateManager missing to_dict()/from_dict()
"""

from __future__ import annotations
from typing import Any, Dict, Optional, TYPE_CHECKING
from enum import Enum
import logging
import types

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger("bootstrap.state_compat")


def ensure_state_methods(state_manager: "StateManager") -> "StateManager":
    """
    Ensure StateManager has required methods.

    Adds missing methods if not present:
    - to_dict()
    - from_dict() / load_from_dict()
    - export_snapshot()
    - get() with path support

    This is a compatibility layer for Module 01 versions prior to v1.19.
    """

    # Check if to_dict exists
    if not hasattr(state_manager, 'to_dict') or not callable(getattr(state_manager, 'to_dict', None)):
        logger.info("Adding to_dict() compatibility method to StateManager")

        def to_dict(self) -> Dict[str, Any]:
            """Serialize state to dictionary."""
            try:
                from magnet.ui.utils import serialize_state
                return serialize_state(self)
            except ImportError:
                # Fallback if ui.utils not available
                if hasattr(self, '_state') and hasattr(self._state, '__dict__'):
                    return _recursive_dict(self._state.__dict__)
                return {}

        state_manager.to_dict = types.MethodType(to_dict, state_manager)

    # Check if load_from_dict exists
    if not hasattr(state_manager, 'load_from_dict') or not callable(getattr(state_manager, 'load_from_dict', None)):
        logger.info("Adding load_from_dict() compatibility method to StateManager")

        def load_from_dict(self, data: Dict[str, Any]) -> None:
            """Load state from dictionary."""
            try:
                from magnet.ui.utils import load_state_from_dict
                load_state_from_dict(self, data)
            except ImportError:
                # Fallback: set values directly
                if hasattr(self, 'set'):
                    for key, value in data.items():
                        try:
                            self.set(key, value)
                        except Exception:
                            pass

        state_manager.load_from_dict = types.MethodType(load_from_dict, state_manager)

    # Alias from_dict to load_from_dict
    if not hasattr(state_manager, 'from_dict'):
        state_manager.from_dict = state_manager.load_from_dict

    # Check if export_snapshot exists
    if not hasattr(state_manager, 'export_snapshot'):
        logger.info("Adding export_snapshot() compatibility method to StateManager")

        def export_snapshot(self, include_metadata: bool = True) -> Dict[str, Any]:
            """Export state snapshot for persistence."""
            from datetime import datetime, timezone

            data = self.to_dict()

            if include_metadata:
                data["_snapshot"] = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "1.1.0",
                }

            return data

        state_manager.export_snapshot = types.MethodType(export_snapshot, state_manager)

    # Ensure get() supports path notation
    if not _supports_path_notation(state_manager):
        logger.info("Enhancing get() with path notation support")

        # Store original get if exists
        original_get = getattr(state_manager, 'get', None)

        def enhanced_get(self, path: str, default: Any = None) -> Any:
            """Get value at path with default support."""
            try:
                from magnet.ui.utils import get_state_value
                return get_state_value(self, path, default)
            except ImportError:
                # Fallback to original get or direct access
                if original_get:
                    try:
                        return original_get(path, default)
                    except Exception:
                        pass
                return default

        state_manager.get = types.MethodType(enhanced_get, state_manager)

    return state_manager


def _supports_path_notation(state_manager: "StateManager") -> bool:
    """Check if get() supports dot-notation paths."""
    if not hasattr(state_manager, 'get'):
        return False

    try:
        # Try with a complex path
        state_manager.get("test.path.notation", None)
        return True
    except (TypeError, AttributeError, KeyError):
        return False


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
        # Skip private attributes
        return {
            k: _recursive_dict(v)
            for k, v in obj.__dict__.items()
            if not k.startswith('_')
        }
    else:
        # Try to return primitive types
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        try:
            return str(obj)
        except Exception:
            return None


def create_compatible_state_manager() -> "StateManager":
    """
    Create a StateManager with all compatibility methods.

    Returns:
        Fully compatible StateManager instance
    """
    try:
        from magnet.core.state_manager import StateManager
        from magnet.core.design_state import DesignState

        sm = StateManager(DesignState())
        return ensure_state_methods(sm)
    except ImportError as e:
        logger.error(f"Failed to create StateManager: {e}")
        raise


class StateManagerProxy:
    """
    Proxy wrapper for StateManager providing guaranteed API compatibility.

    Use this when you need to ensure all methods exist regardless of
    the underlying StateManager implementation version.
    """

    def __init__(self, state_manager: "StateManager"):
        self._sm = ensure_state_methods(state_manager)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._sm, name)

    def to_dict(self) -> Dict[str, Any]:
        return self._sm.to_dict()

    def load_from_dict(self, data: Dict[str, Any]) -> None:
        self._sm.load_from_dict(data)

    def from_dict(self, data: Dict[str, Any]) -> None:
        self.load_from_dict(data)

    def export_snapshot(self, include_metadata: bool = True) -> Dict[str, Any]:
        return self._sm.export_snapshot(include_metadata)

    def get(self, path: str, default: Any = None) -> Any:
        try:
            from magnet.ui.utils import get_state_value
            return get_state_value(self._sm, path, default)
        except ImportError:
            return self._sm.get(path, default)

    def set(self, path: str, value: Any, source: str = "proxy") -> bool:
        try:
            from magnet.ui.utils import set_state_value
            return set_state_value(self._sm, path, value, source)
        except ImportError:
            if hasattr(self._sm, 'set'):
                self._sm.set(path, value, source=source)
                return True
            return False

    @property
    def wrapped(self) -> "StateManager":
        """Get the wrapped StateManager instance."""
        return self._sm
