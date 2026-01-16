"""
MAGNET Control Plane v1.1 — HypotheticalStateView

A truth-preserving counterfactual simulator that projects proposed actions
onto the current state WITHOUT mutation or physics execution.

Core Contract:
- get(path) returns ProjectedValue with provenance
- Zero mutation: no set(), begin_transaction(), commit()
- Zero physics: no geometry generation or hydrostatics computation
- Derived fields are marked STALE when geometry-affecting paths change

This is the foundation that prevents the system from "lying forward."
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager
    from magnet.kernel.intent_protocol import Action, ActionPlan


class ValueSource(str, Enum):
    """
    Provenance tag for every value returned by HSV.
    
    This is the core mechanism for transparency:
    - ACTION: Value explicitly provided in proposed ActionPlan
    - EXISTING: Current value in StateManager (user/synthesized/kernel)
    - VIRTUAL_DEFAULT: Kernel baseline (never invisible to user)
    - STALE: Derived field invalidated by geometry-affecting change
    - PLACEHOLDER: Ship-scale baseline that MUST be replaced by synthesis
                   (Constraint-Aware Completion v1.0)
    """
    ACTION = "action"
    EXISTING = "existing"
    VIRTUAL_DEFAULT = "virtual_default"
    STALE = "stale"
    PLACEHOLDER = "placeholder"  # Needs completion before hull generation


@dataclass(frozen=True)
class ProjectedValue:
    """
    A value with its provenance attached.
    
    This is what HSV returns for every get() call.
    The source tag is mandatory—no value can exist without attribution.
    """
    path: str
    value: Any
    source: ValueSource
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "value": self.value,
            "source": self.source.value,
        }


# =============================================================================
# GEOMETRY-AFFECTING PATHS (Trigger Staleness)
# =============================================================================

# Primary dimensions that affect hull geometry
GEOMETRY_AFFECTING_PATHS: frozenset = frozenset([
    # Principal dimensions
    "hull.loa",
    "hull.lwl",
    "hull.beam",
    "hull.draft",
    "hull.depth",
    "hull.draft_fwd_m",
    "hull.draft_aft_m",
    
    # Form coefficients
    "hull.cb",
    "hull.cp",
    "hull.cm",
    "hull.cwp",
    
    # Hull form features
    "hull.deadrise_deg",
    "hull.deadrise_transom_deg",
    "hull.lcb_fraction",
    "hull.transom_beam_ratio",
    "hull.bow_entrance_deg",
    "hull.bow_flare_deg",
    "hull.stem_rake_deg",
    
    # Chine and bow configuration
    "hull.chine_type",
    "hull.chine_count",
    "hull.bow_style",
    "hull.bow_facet_count",
    "hull.stem_profile",
    
    # Transom and deck
    "hull.transom_style",
    "hull.transom_rake_deg",
    "hull.tumblehome_enabled",
    "hull.tumblehome_angle_deg",
    "hull.panel_style",
    "hull.deck_enabled",
    
    # Multi-hull
    "hull.hull_type",
    "hull.hull_spacing_m",
])

# Derived fields that become STALE when geometry changes
DERIVED_HYDROSTATIC_PATHS: frozenset = frozenset([
    # Volume and displacement
    "hull.displacement_m3",
    "hull.displacement_mt",
    "hull.displacement_kg",
    
    # Surface areas
    "hull.wetted_surface_m2",
    "hull.waterplane_area_m2",
    
    # Centroids
    "hull.vcb_m",
    "hull.lcb_from_ap_m",
    "hull.lcf_from_ap_m",
    "hull.kb_m",
    
    # Hydrostatic coefficients
    "hull.bm_m",
    "hull.bmt",
    "hull.bml",
    "hull.kmt",
    "hull.kml",
    "hull.tpc",
    "hull.mct",
    
    # Geometry-derived coefficients
    "hull.cb_geometry",
    "hull.cp_geometry",
    "hull.cm_geometry",
    "hull.cwp_geometry",
    
    # Sectional data
    "hull.sectional_areas",
    "hull.bonjean_stations",
    "hull.it_m4",
    "hull.il_m4",
    
    # Stability (depends on geometry)
    "stability.gm_m",
    "stability.gm_transverse_m",
    "stability.gm_solid_m",
    "stability.km_m",
    "stability.kb_m",
    "stability.bm_m",
    "stability.gz_curve",
    "stability.gz_max_m",
    "stability.gz_30_m",
    
    # Resistance (depends on geometry)
    "resistance.total_resistance_kn",
    "resistance.frictional_resistance_kn",
    "resistance.residuary_resistance_kn",
    "resistance.effective_power_kw",
    "resistance.froude_number",
])


# =============================================================================
# KERNEL BASELINES (Virtual Defaults)
# =============================================================================

# These match the baselines in action_validator.py
KERNEL_BASELINES: Dict[str, Any] = {
    # Hull
    "hull.loa": 30.0,
    "hull.beam": 8.0,
    "hull.draft": 2.0,
    "hull.depth": 4.0,
    "hull.hull_spacing_m": 6.0,
    "hull.cb": 0.45,
    "hull.cp": 0.65,
    "hull.cm": 0.70,
    "hull.cwp": 0.75,
    "hull.deadrise_deg": 15.0,
    "hull.deadrise_transom_deg": 10.0,
    "hull.lcb_fraction": 0.52,
    "hull.transom_beam_ratio": 0.7,
    "hull.bow_entrance_deg": 25.0,
    "hull.bow_flare_deg": 15.0,
    "hull.stem_rake_deg": 10.0,
    "hull.freeboard_m": 1.5,
    "hull.draft_fwd_m": 2.0,
    "hull.draft_aft_m": 2.0,
    # Mission
    "mission.max_speed_kts": 25.0,
    "mission.cruise_speed_kts": 18.0,
    "mission.range_nm": 500.0,
    "mission.crew_berthed": 6,
    "mission.passengers": 50,
    # Propulsion
    "propulsion.total_installed_power_kw": 2000.0,
}


# =============================================================================
# HYPOTHETICAL STATE VIEW
# =============================================================================

class HypotheticalStateView:
    """
    Read-only counterfactual simulator.
    
    Overlays proposed actions onto current state and returns values
    with provenance tags. Never mutates state or triggers physics.
    
    Usage:
        hsv = HypotheticalStateView(state_manager, proposed_actions)
        result = hsv.get("hull.beam")
        # result.value = 7.5, result.source = ValueSource.ACTION
    
    Core Invariants:
        - get() always returns ProjectedValue with source
        - Derived fields return STALE when geometry affected
        - contains_virtual_defaults flag is always accurate
        - No side effects whatsoever
    """
    
    def __init__(
        self,
        state_manager: "StateManager",
        proposed_actions: List["Action"],
    ):
        """
        Initialize the hypothetical view.
        
        Args:
            state_manager: The authoritative StateManager (read-only access)
            proposed_actions: List of Action objects to overlay
        """
        self._state = state_manager
        self._proposed_actions = proposed_actions
        
        # Build the overlay from proposed actions
        self._overlay: Dict[str, Any] = {}
        self._build_overlay()
        
        # Compute which paths are stale
        self._stale_paths: Set[str] = set()
        self._compute_stale_paths()
        
        # Track if any virtual defaults were used
        self._virtual_defaults_used: Set[str] = set()
        
        # Track placeholder dimensions found (Constraint-Aware Completion v1.0)
        # These need synthesis before hull generation can proceed
        self._placeholders_found: Set[str] = set()
        self._scan_for_placeholders()
    
    def _build_overlay(self) -> None:
        """
        Build the overlay dictionary from proposed actions.
        
        Only SET actions contribute to the overlay.
        INCREASE/DECREASE should be resolved to SET by the validator.
        """
        from magnet.kernel.intent_protocol import ActionType
        
        for action in self._proposed_actions:
            if action.action_type == ActionType.SET and action.path:
                self._overlay[action.path] = action.value
    
    def _scan_for_placeholders(self) -> None:
        """
        Scan principal hull dimensions for placeholder provenance.
        
        Constraint-Aware Completion v1.0: Called during initialization
        to eagerly detect which hull dimensions are ship-scale baselines
        that need synthesis to produce proportional values.
        """
        placeholder_paths = ["hull.beam", "hull.draft", "hull.depth"]
        
        for path in placeholder_paths:
            # Skip if path is being set by an action (will become USER)
            if path in self._overlay:
                continue
            
            # Check if state manager tracks this as placeholder
            if hasattr(self._state, 'is_placeholder'):
                if self._state.is_placeholder(path):
                    self._placeholders_found.add(path)
    
    def _compute_stale_paths(self) -> None:
        """
        Compute which derived paths are stale.
        
        If any proposed action touches a geometry-affecting path,
        ALL derived hydrostatic fields become stale.
        
        This prevents the system from returning outdated physics
        that would mislead the user about the design's properties.
        """
        geometry_touched = False
        
        for path in self._overlay.keys():
            if path in GEOMETRY_AFFECTING_PATHS:
                geometry_touched = True
                break
        
        if geometry_touched:
            self._stale_paths = set(DERIVED_HYDROSTATIC_PATHS)
    
    def get(self, path: str, default: Any = None) -> ProjectedValue:
        """
        Get a value with its provenance.
        
        Resolution order:
        1. STALE — if path is in stale set (geometry affected)
        2. ACTION — if path is in overlay (explicitly proposed)
        3. EXISTING — if path has value in real state (check placeholder status)
        4. VIRTUAL_DEFAULT — if path has kernel baseline
        5. Return default with EXISTING source
        
        Constraint-Aware Completion v1.0: Checks StateManager provenance
        to detect placeholder values that need completion.
        
        Args:
            path: State path to retrieve
            default: Value to return if not found anywhere
        
        Returns:
            ProjectedValue with value and source tag
        """
        # 1. Check if path is stale (geometry-affected derived field)
        if path in self._stale_paths:
            return ProjectedValue(
                path=path,
                value=None,
                source=ValueSource.STALE,
            )
        
        # 2. Check overlay (proposed actions)
        if path in self._overlay:
            return ProjectedValue(
                path=path,
                value=self._overlay[path],
                source=ValueSource.ACTION,
            )
        
        # 3. Check existing state
        # Always pass default through to underlying StateManager.get() for compatibility
        # with mock StateManagers that assert the default argument.
        existing_value = self._state.get(path, None)
        if existing_value is not None:
            # Constraint-Aware Completion v1.0: Check if value is a placeholder
            # Placeholders are ship-scale baselines that need synthesis
            source = ValueSource.EXISTING
            if hasattr(self._state, 'is_placeholder'):
                # IMPORTANT: use `is True` so MagicMock / truthy sentinels don't
                # accidentally mark real values as placeholders in tests.
                if self._state.is_placeholder(path) is True:
                    source = ValueSource.PLACEHOLDER
                    # Track placeholders for missing_required feedback
                    self._placeholders_found.add(path)
            return ProjectedValue(
                path=path,
                value=existing_value,
                source=source,
            )
        
        # 4. Check kernel baselines
        if path in KERNEL_BASELINES:
            self._virtual_defaults_used.add(path)
            return ProjectedValue(
                path=path,
                value=KERNEL_BASELINES[path],
                source=ValueSource.VIRTUAL_DEFAULT,
            )
        
        # 5. Return default
        return ProjectedValue(
            path=path,
            value=default,
            source=ValueSource.EXISTING,
        )
    
    def get_raw(self, path: str, default: Any = None) -> Any:
        """
        Get just the value (for gate compatibility).
        
        This method exists for compatibility with GateCondition.evaluate()
        which expects a simple get(path) interface.
        """
        projected = self.get(path, default)
        # Gate compatibility: treat virtual defaults / placeholders as "missing" so required
        # inputs still surface as missing until the user (or a proposal) sets them explicitly.
        if projected.source in (ValueSource.VIRTUAL_DEFAULT, ValueSource.PLACEHOLDER):
            return default
        return projected.value
    
    @property
    def contains_virtual_defaults(self) -> bool:
        """
        True if any value was sourced from kernel baselines.
        
        This flag MUST be included in the response so the user
        knows assumptions were made.
        """
        return len(self._virtual_defaults_used) > 0
    
    @property
    def virtual_defaults_used(self) -> Set[str]:
        """
        Set of paths that used kernel baselines.
        
        These should be presented to the user as "Suggested Values"
        that they can confirm or override.
        """
        return self._virtual_defaults_used.copy()
    
    @property
    def stale_paths(self) -> Set[str]:
        """
        Set of derived paths that are stale.
        
        These should be presented as "Requires Geometry Regeneration."
        """
        return self._stale_paths.copy()
    
    @property
    def placeholders_found(self) -> Set[str]:
        """
        Set of hull dimension paths that have placeholder provenance.
        
        Constraint-Aware Completion v1.0: These values are ship-scale
        baselines that MUST be replaced by synthesis or user input
        before hull generation can proceed.
        
        These should be presented as "Needs Proportional Sizing."
        """
        return self._placeholders_found.copy()
    
    @property
    def contains_placeholders(self) -> bool:
        """
        True if any hull dimensions are still placeholders.
        
        If True, the UI should prompt for synthesis or user input
        to complete the hull specification.
        """
        return len(self._placeholders_found) > 0
    
    @property
    def overlay(self) -> Dict[str, Any]:
        """
        The overlay dictionary (proposed values).
        
        Read-only access for debugging/logging.
        """
        return self._overlay.copy()
    
    def project_all(self, paths: List[str]) -> List[ProjectedValue]:
        """
        Project multiple paths at once.
        
        Args:
            paths: List of state paths to project
        
        Returns:
            List of ProjectedValue objects
        """
        return [self.get(path) for path in paths]
    
    def to_digest(self) -> Dict[str, Any]:
        """
        Generate a summary digest for the preview response.
        
        This is the data structure returned to the UI/LLM.
        """
        projections = []
        
        # Include all overlayed paths
        for path, value in self._overlay.items():
            projections.append({
                "path": path,
                "value": value,
                "source": ValueSource.ACTION.value,
            })
        
        # Include stale paths (explicitly mark them)
        for path in self._stale_paths:
            # Only include if not already in projections
            if path not in self._overlay:
                projections.append({
                    "path": path,
                    "value": None,
                    "source": ValueSource.STALE.value,
                })
        
        # Include virtual defaults used
        for path in self._virtual_defaults_used:
            if path not in self._overlay:
                projections.append({
                    "path": path,
                    "value": KERNEL_BASELINES.get(path),
                    "source": ValueSource.VIRTUAL_DEFAULT.value,
                })
        
        # Include placeholder paths (Constraint-Aware Completion v1.0)
        for path in self._placeholders_found:
            if path not in self._overlay:
                existing_value = self._state.get(path)
                projections.append({
                    "path": path,
                    "value": existing_value,
                    "source": ValueSource.PLACEHOLDER.value,
                })
        
        return {
            "contains_virtual_defaults": self.contains_virtual_defaults,
            "virtual_defaults_used": list(self._virtual_defaults_used),
            "stale_paths": list(self._stale_paths),
            "projections": projections,
            # Constraint-Aware Completion v1.0
            "contains_placeholders": self.contains_placeholders,
            "placeholders_found": list(self._placeholders_found),
        }

