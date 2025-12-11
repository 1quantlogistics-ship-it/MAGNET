"""
state_integration.py - Interior state management integration v1.0
BRAVO OWNS THIS FILE.

Module 59: Interior Layout
Integrates interior layout with core state management system.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any, TYPE_CHECKING
import logging
import uuid

from magnet.interior.schema.layout import InteriorLayout, LayoutVersion
from magnet.interior.schema.space import SpaceDefinition
from magnet.interior.schema.validation import ValidationResult, validate_space_constraints

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

__all__ = [
    'InteriorStateIntegrator',
    'InteriorStateError',
]

logger = logging.getLogger(__name__)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class InteriorStateError(Exception):
    """Error in interior state operations."""
    pass


# =============================================================================
# STATE INTEGRATOR
# =============================================================================

@dataclass
class InteriorStateIntegrator:
    """
    Integrates interior layout with core state management.

    This class provides the interface between the interior module
    and the central state manager, handling:
    - Layout persistence
    - Version tracking (update_id/prev_update_id chain)
    - Hash computation for staleness detection
    - Event emission for real-time updates
    """

    _sm: Optional[Any] = None  # StateManager reference
    _layouts: Dict[str, InteriorLayout] = field(default_factory=dict)

    def __init__(self, state_manager: Optional[Any] = None):
        """
        Initialize the integrator.

        Args:
            state_manager: Optional StateManager instance
        """
        self._sm = state_manager
        self._layouts = {}

    # -------------------------------------------------------------------------
    # Layout Management
    # -------------------------------------------------------------------------

    def get_layout(self, design_id: str) -> Optional[InteriorLayout]:
        """
        Get layout for a design.

        Args:
            design_id: Design ID

        Returns:
            InteriorLayout or None
        """
        # Check cache first
        if design_id in self._layouts:
            return self._layouts[design_id]

        # Try to load from state manager
        if self._sm:
            try:
                data = self._sm.get(f"interior.layout.{design_id}")
                if data:
                    layout = InteriorLayout.from_dict(data)
                    self._layouts[design_id] = layout
                    return layout
            except Exception as e:
                logger.warning(f"Failed to load layout from state: {e}")

        return None

    def save_layout(self, layout: InteriorLayout) -> str:
        """
        Save layout to state.

        Args:
            layout: Layout to save

        Returns:
            New update_id for the saved version
        """
        # Create new version
        layout.create_new_version(
            description="Layout saved",
            author="system",
        )

        # Cache
        self._layouts[layout.design_id] = layout

        # Persist to state manager
        if self._sm:
            try:
                self._sm.set(
                    f"interior.layout.{layout.design_id}",
                    layout.to_dict(),
                )
            except Exception as e:
                logger.error(f"Failed to save layout to state: {e}")
                raise InteriorStateError(f"Failed to save layout: {e}")

        return layout.version_info.update_id

    def delete_layout(self, design_id: str) -> bool:
        """
        Delete layout for a design.

        Args:
            design_id: Design ID

        Returns:
            True if deleted
        """
        # Remove from cache
        if design_id in self._layouts:
            del self._layouts[design_id]

        # Remove from state manager
        if self._sm:
            try:
                self._sm.delete(f"interior.layout.{design_id}")
            except Exception as e:
                logger.warning(f"Failed to delete layout from state: {e}")
                return False

        return True

    # -------------------------------------------------------------------------
    # Space Operations
    # -------------------------------------------------------------------------

    def add_space(
        self,
        design_id: str,
        space: SpaceDefinition,
    ) -> Optional[str]:
        """
        Add a space to a layout.

        Args:
            design_id: Design ID
            space: Space to add

        Returns:
            Update ID if successful
        """
        layout = self.get_layout(design_id)
        if not layout:
            raise InteriorStateError(f"Layout not found for design {design_id}")

        if not layout.add_space(space):
            raise InteriorStateError(f"Failed to add space to deck {space.deck_id}")

        return self.save_layout(layout)

    def update_space(
        self,
        design_id: str,
        space: SpaceDefinition,
    ) -> Optional[str]:
        """
        Update a space in a layout.

        Args:
            design_id: Design ID
            space: Updated space

        Returns:
            Update ID if successful
        """
        layout = self.get_layout(design_id)
        if not layout:
            raise InteriorStateError(f"Layout not found for design {design_id}")

        if not layout.update_space(space):
            raise InteriorStateError(f"Space {space.space_id} not found")

        return self.save_layout(layout)

    def delete_space(
        self,
        design_id: str,
        space_id: str,
    ) -> Optional[str]:
        """
        Delete a space from a layout.

        Args:
            design_id: Design ID
            space_id: Space ID to delete

        Returns:
            Update ID if successful
        """
        layout = self.get_layout(design_id)
        if not layout:
            raise InteriorStateError(f"Layout not found for design {design_id}")

        removed = layout.remove_space(space_id)
        if not removed:
            raise InteriorStateError(f"Space {space_id} not found")

        return self.save_layout(layout)

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def validate_layout(self, design_id: str) -> ValidationResult:
        """
        Validate a layout.

        Args:
            design_id: Design ID

        Returns:
            ValidationResult
        """
        layout = self.get_layout(design_id)
        if not layout:
            result = ValidationResult(is_valid=False)
            result.add_error(
                issue_id="layout_not_found",
                category="system",
                message=f"Layout not found for design {design_id}",
            )
            return result

        spaces = layout.get_all_spaces()
        return validate_space_constraints(spaces)

    # -------------------------------------------------------------------------
    # Hash Operations (FIX #2 - Domain Hashes)
    # -------------------------------------------------------------------------

    def get_arrangement_hash(self, design_id: str) -> Optional[str]:
        """
        Get arrangement hash for a design.

        This is the domain-specific hash for staleness detection
        as specified in V1.4 FIX #2.

        Args:
            design_id: Design ID

        Returns:
            Arrangement hash or None
        """
        layout = self.get_layout(design_id)
        if layout:
            return layout.arrangement_hash
        return None

    def get_version_info(self, design_id: str) -> Optional[Dict[str, Any]]:
        """
        Get version info for a design.

        Returns update_id, prev_update_id, and version for
        chain tracking (FIX #1).

        Args:
            design_id: Design ID

        Returns:
            Version info dict or None
        """
        layout = self.get_layout(design_id)
        if layout:
            return {
                "update_id": layout.version_info.update_id,
                "prev_update_id": layout.version_info.prev_update_id,
                "version": layout.version_info.version,
                "arrangement_hash": layout.arrangement_hash,
            }
        return None

    # -------------------------------------------------------------------------
    # Optimization
    # -------------------------------------------------------------------------

    def optimize_layout(
        self,
        design_id: str,
        objectives: Optional[Dict[str, float]] = None,
    ) -> Optional[str]:
        """
        Optimize a layout.

        Args:
            design_id: Design ID
            objectives: Optimization objectives and weights

        Returns:
            Update ID if successful
        """
        layout = self.get_layout(design_id)
        if not layout:
            raise InteriorStateError(f"Layout not found for design {design_id}")

        # TODO: Implement optimization algorithm
        # For now, just re-validate and save
        logger.info(f"Optimization requested for {design_id} (not yet implemented)")

        return self.save_layout(layout)
