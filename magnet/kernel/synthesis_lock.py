"""
MAGNET Synthesis Lock

Exclusive write lock for hull parameters during synthesis.
Prevents race conditions with downstream phases.

v1.0: Initial implementation
"""

from contextlib import contextmanager
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class SynthesisLockError(Exception):
    """Raised when lock acquisition or release fails."""
    pass


class SynthesisLock:
    """
    Exclusive write lock for hull parameters during synthesis.

    Prevents race conditions with downstream phases by ensuring
    only the lock owner can write hull parameters during synthesis.
    """

    # Hull paths that are protected during synthesis (all 21 schema params + derived + Phase 2-6)
    HULL_PATHS = frozenset([
        # Principal dimensions
        "hull.loa", "hull.lwl", "hull.beam", "hull.draft", "hull.depth",
        "hull.draft_fwd_m", "hull.draft_aft_m", "hull.freeboard_m",
        # Form coefficients
        "hull.cb", "hull.cp", "hull.cm", "hull.cwp", "hull.lcb_fraction",
        # Hull form inputs
        "hull.transom_beam_ratio", "hull.bow_entrance_deg", "hull.bow_flare_deg",
        "hull.stem_rake_deg", "hull.deadrise_deg", "hull.deadrise_transom_deg",
        # Type and multihull
        "hull.hull_type", "hull.hull_spacing_m",
        # Derived (computed by hydrostatics)
        "hull.displacement_m3", "hull.displacement_kg", "hull.displacement_mt",
        # Phase 2: Chine Variations
        "hull.chine_type", "hull.chine_count", "hull.chine_style",
        "hull.chine_transition_start", "hull.chine_transition_end",
        "hull.reverse_chine_height_ratio", "hull.reverse_chine_extension_m",
        "hull.chine_flat_width_m",
        # Phase 3: Bow Forms
        "hull.bow_style", "hull.bow_facet_count", "hull.bow_planarity",
        "hull.bow_half_angle_deg", "hull.bow_region_length",
        "hull.bow_freeboard_ratio", "hull.stem_profile", "hull.stem_radius_m",
        # Phase 4: Spray Rails + Knuckle Lines
        "hull.spray_rail_count", "hull.spray_rail_spacing",
        "hull.has_spray_rails", "hull.has_knuckle_lines",
        # Phase 5: Transom Variations
        "hull.transom_style", "hull.transom_rake_deg",
        # Phase 6: Tumblehome, Panels, Deck
        "hull.tumblehome_enabled", "hull.tumblehome_angle_deg",
        "hull.tumblehome_start_ratio", "hull.panel_style",
        "hull.deck_enabled", "hull.deck_camber_m",
    ])

    def __init__(self, state_manager: "StateManager"):
        """
        Initialize the synthesis lock.

        Args:
            state_manager: StateManager instance for state access
        """
        self._state = state_manager
        self._locked = False
        self._owner: Optional[str] = None

    @property
    def is_locked(self) -> bool:
        """Check if lock is currently held."""
        return self._locked

    @property
    def owner(self) -> Optional[str]:
        """Get current lock owner."""
        return self._owner

    def acquire(self, owner: str) -> bool:
        """
        Acquire exclusive hull write lock.

        Args:
            owner: Identifier of lock requestor

        Returns:
            True if acquired

        Raises:
            SynthesisLockError: If lock already held by another owner
        """
        if self._locked:
            raise SynthesisLockError(
                f"Hull locked by {self._owner}, cannot acquire for {owner}"
            )
        self._locked = True
        self._owner = owner
        return True

    def release(self, owner: str) -> None:
        """
        Release hull write lock.

        Args:
            owner: Identifier of lock holder

        Raises:
            SynthesisLockError: If owner doesn't match lock holder
        """
        if self._owner != owner:
            raise SynthesisLockError(
                f"Lock owned by {self._owner}, not {owner}"
            )
        self._locked = False
        self._owner = None

    def write_hull_params(
        self,
        params: dict,
        owner: str,
    ) -> None:
        """
        Atomically write hull parameters to state within a transaction.

        Only allowed by lock owner. All-or-nothing write (never partial state).
        Module 62.4: Wraps writes in transaction to satisfy enforcement.

        Args:
            params: Dictionary of path -> value for hull parameters
            owner: Lock owner identifier

        Raises:
            SynthesisLockError: If owner doesn't match lock holder
            ValueError: If params are incomplete
        """
        if self._owner != owner:
            raise SynthesisLockError(
                f"Cannot write: lock owned by {self._owner}, not {owner}"
            )

        # Verify we have the core params
        required = {"hull.lwl", "hull.beam", "hull.draft"}
        provided = set(params.keys())
        missing = required - provided
        if missing:
            raise ValueError(f"Cannot write incomplete hull params, missing: {missing}")

        # Module 62.4: Wrap refinable writes in transaction if not already in one
        source = f"synthesis:{owner}"
        owns_transaction = not self._state.in_transaction()

        # Constraint-Aware Completion v1.0: Import provenance enum
        from magnet.core.state_manager import DimensionProvenance

        if owns_transaction:
            self._state.begin_transaction()
        try:
            for path, value in params.items():
                # Mark synthesized dimensions with SYNTHESIZED provenance
                # This distinguishes them from ship-scale placeholders
                self._state.set(
                    path, value, source,
                    provenance=DimensionProvenance.SYNTHESIZED
                )
            if owns_transaction:
                self._state.commit()
        except Exception:
            if owns_transaction:
                self._state.rollback()
            raise

    @contextmanager
    def exclusive_access(self, owner: str):
        """
        Context manager for exclusive hull access.

        Usage:
            with lock.exclusive_access("synthesizer"):
                # Write hull params safely
                lock.write_hull_params(params, "synthesizer")

        Args:
            owner: Lock owner identifier

        Yields:
            self for chaining
        """
        self.acquire(owner)
        try:
            yield self
        finally:
            self.release(owner)
