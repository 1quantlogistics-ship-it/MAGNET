from __future__ import annotations

from typing import Optional

from magnet.core.state_manager import StateManager
from magnet.ui.utils import get_state_value


class DesignNotFound(Exception):
    """Raised when a requested design is not available in the store."""


class DesignStore:
    """
    Minimal design store responsible for resolving StateManager by design_id.

    Note: This implementation prefers correctness over availability. If a design
    is not the currently loaded state, it is treated as missing (404) rather
    than risking serving the wrong design.
    """

    def __init__(self, container: Optional[object] = None):
        self._container = container

    def load(self, design_id: str) -> StateManager:
        """
        Resolve a StateManager for the given design_id.

        Returns:
            StateManager bound to the requested design_id.

        Raises:
            DesignNotFound: if the design is not available.
        """
        if not self._container:
            raise DesignNotFound(f"Design {design_id} not available (no container).")

        try:
            sm: StateManager = self._container.resolve(StateManager)
        except Exception as exc:  # pragma: no cover - container failure path
            raise DesignNotFound(f"Design {design_id} not available: {exc}") from exc

        current_id = get_state_value(sm, "metadata.design_id")
        if current_id and current_id == design_id:
            return sm

        raise DesignNotFound(f"Design {design_id} not loaded.")

