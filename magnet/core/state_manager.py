"""
MAGNET StateManager

Path-based state access with alias resolution, transactions, and persistence.
Implements the StateManagerContract interface.

v1.1: Added path-strict checking with MISSING sentinel, get_strict(), exists(),
      and InvalidPathError for invalid schema paths.
"""

import json
import copy
import uuid
import logging
import hashlib
import base64
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union
from pathlib import Path

from magnet.core.design_state import DesignState
from magnet.core.field_aliases import normalize_path, get_canonical

logger = logging.getLogger(__name__)


# =============================================================================
# DIMENSION PROVENANCE (Constraint-Aware Completion v1.0)
# =============================================================================

class DimensionProvenance(str, Enum):
    """
    Tracks where a hull dimension value came from.
    
    Critical for constraint-aware completion: placeholders must be replaced
    with synthesized values before hull generation can run.
    
    PLACEHOLDER: Ship-scale baseline injected at design creation (8m beam, etc.)
                 These values are NOT authoritative and must be replaced.
    USER: Explicitly set by user (via chat or direct action)
    LLM_PROPOSED: Proposed by LLM as part of hull feature/style selection
                  (LLM-Generated Hull Refinement v1.0)
    SYNTHESIZED: Derived by hull synthesis from mission constraints
    KERNEL: Set by kernel validators (clamping, defaults with reasoning)
    """
    PLACEHOLDER = "placeholder"
    USER = "user"
    LLM_PROPOSED = "llm_proposed"
    SYNTHESIZED = "synthesized"
    KERNEL = "kernel"


# =============================================================================
# API VALUE PROVENANCE (Walking Trail Ledge 3)
# =============================================================================

class ValueProvenance(str, Enum):
    """
    Canonical provenance source strings for API responses.

    NOTE: These are intentionally UPPERCASE to be stable in external contracts.
    """
    USER = "USER"            # Explicitly provided by user input
    LLM = "LLM"              # Proposed by agent, not yet confirmed
    KERNEL = "KERNEL"        # Computed by physics/synthesis kernel
    FALLBACK = "FALLBACK"    # Estimated when required input missing
    INHERITED = "INHERITED"  # Carried forward from previous version / loaded legacy state
    DEFAULT = "DEFAULT"      # Placeholder / baseline / unknown origin (explicitly marked)


def _validate_confidence(
    provenance: ValueProvenance,
    confidence: float,
    original_confidence: Optional[float] = None,
) -> float:
    """
    Enforce confidence semantics (Walking Trail Contract 2).

    Confidence expresses certainty about origin/existence, not correctness.
    """
    try:
        c = float(confidence)
    except Exception:
        c = 0.0

    # Clamp first to avoid NaNs/inf propagating.
    if c != c or c == float("inf") or c == float("-inf"):
        c = 0.0
    c = max(0.0, min(1.0, c))

    if provenance == ValueProvenance.USER:
        return 1.0
    if provenance == ValueProvenance.FALLBACK:
        return min(c, 0.5)
    if provenance == ValueProvenance.DEFAULT:
        # Defaults are placeholders; keep the canonical 0.3 unless caller is explicitly marking "unknown" (0.0)
        return 0.0 if c == 0.0 else 0.3
    if provenance == ValueProvenance.INHERITED:
        return float(original_confidence) if original_confidence is not None else c
    return c


def _map_dimension_provenance_to_api(p: DimensionProvenance) -> ValueProvenance:
    if p == DimensionProvenance.PLACEHOLDER:
        return ValueProvenance.DEFAULT
    if p == DimensionProvenance.USER:
        return ValueProvenance.USER
    if p == DimensionProvenance.LLM_PROPOSED:
        return ValueProvenance.LLM
    if p == DimensionProvenance.SYNTHESIZED:
        return ValueProvenance.KERNEL
    if p == DimensionProvenance.KERNEL:
        return ValueProvenance.KERNEL
    return ValueProvenance.DEFAULT


def _infer_api_provenance(source: str, dim_prov: Optional[DimensionProvenance]) -> ValueProvenance:
    if dim_prov is not None:
        return _map_dimension_provenance_to_api(dim_prov)

    s = (source or "").lower()
    if s in ("ui", "user", "human", "human_decision"):
        return ValueProvenance.USER
    if "llm" in s or "agent" in s or "proposer" in s:
        return ValueProvenance.LLM
    if "fallback" in s:
        return ValueProvenance.FALLBACK
    if "default" in s or "placeholder" in s:
        return ValueProvenance.DEFAULT
    return ValueProvenance.KERNEL


# Paths that support provenance tracking (principal hull dimensions)
PROVENANCE_TRACKED_PATHS = frozenset([
    # Principal dimensions
    "hull.loa",
    "hull.lwl",
    "hull.beam",
    "hull.draft",
    "hull.depth",
    # Form coefficients
    "hull.cb",
    "hull.cp",
    "hull.cm",
    "hull.cwp",
    "hull.deadrise_deg",
    "hull.deadrise_transom_deg",
    # Hull features (LLM-Generated Hull Refinement v1.0)
    "hull.bow_style",
    "hull.chine_type",
    "hull.chine_count",
    "hull.spray_rail_count",
    "hull.has_spray_rails",
    "hull.tumblehome_enabled",
    "hull.tumblehome_angle_deg",
    "hull.tumblehome_start_ratio",
    "hull.transom_style",
    "hull.transom_rake_deg",
    "hull.stem_profile",
    "hull.panel_style",
    "hull.deck_enabled",
    "hull.deck_camber_m",
    "hull.has_knuckle_lines",
    "hull.bow_half_angle_deg",
])


# =============================================================================
# PATH-STRICT FOUNDATION (v1.1)
# =============================================================================

class _MISSING:
    """
    Sentinel for truly missing paths (path exists in schema but never written).

    Used to distinguish:
    - MISSING: path is valid but no value has been written yet
    - None: path exists and was explicitly set to None
    - InvalidPathError: path is not in schema (a bug)
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "<MISSING>"

    def __bool__(self):
        return False


MISSING = _MISSING()


class InvalidPathError(Exception):
    """
    Raised when accessing a path not in the schema.

    This indicates a bug in the calling code (typo in path) rather than
    missing data. Helps catch contract definition errors early.
    """
    pass


class MutationEnforcementError(Exception):
    """
    Raised when a mutation is attempted outside the allowed context.

    Refinable paths (hull.loa, mission.max_speed_kts, etc.) require an active
    transaction via the ActionPlan → ActionExecutor pipeline. Direct calls
    to StateManager.set() on refinable paths will raise this exception.
    """
    pass




# Valid paths in the MAGNET state schema
# This is the authoritative list - anything not here raises InvalidPathError
VALID_PATHS = frozenset([
    # Identity
    "design_id", "design_name", "version",

    # Mission
    "mission.vessel_type", "mission.vessel_name", "mission.hull_number",
    "mission.max_speed_kts", "mission.cruise_speed_kts", "mission.economical_speed_kts",
    "mission.range_nm", "mission.endurance_hours", "mission.endurance_days",
    "mission.crew_berthed", "mission.crew_day", "mission.crew_size", "mission.crew_count",
    "mission.passengers", "mission.passengers_seated",
    "mission.cargo_capacity_mt", "mission.cargo_volume_m3", "mission.deck_cargo_area_m2",
    "mission.operating_area", "mission.design_sea_state", "mission.service_notation",
    "mission.classification_society", "mission.class_notation", "mission.flag_state",
    "mission.special_features", "mission.operational_profile",
    "mission.hull_type", "mission.loa", "mission.gm_required_m",

    # Hull - Principal dimensions
    "hull.loa", "hull.lwl", "hull.lbp", "hull.beam", "hull.beam_wl",
    "hull.draft", "hull.draft_max", "hull.depth", "hull.freeboard",
    "hull.draft_fwd_m", "hull.draft_aft_m", "hull.freeboard_m",
    "hull.hull_type",

    # Hull - Form coefficients
    "hull.cb", "hull.cp", "hull.cm", "hull.cwp", "hull.cvp",

    # Hull - Angles
    "hull.deadrise_deg", "hull.deadrise_transom_deg", "hull.deadrise_midship_deg", "hull.entrance_angle_deg",
    "hull.bow_flare_deg", "hull.stem_rake_deg", "hull.bow_entrance_deg",

    # Hull - Form/feature inputs
    "hull.lcb_fraction", "hull.transom_beam_ratio",

    # ==========================================================================
    # Hull - Phase 2: Chine Variations
    # ==========================================================================
    "hull.chine_type",                    # "soft" | "hard" | "double" | "triple" | "reverse" | "variable"
    "hull.chine_count",                   # int: 1, 2, or 3
    "hull.chine_style",                   # "standard" | "reverse" | "variable"
    "hull.chine_transition_start",        # float: 0.0-1.0 station
    "hull.chine_transition_end",          # float: 0.0-1.0 station
    "hull.reverse_chine_height_ratio",    # float: 0.0-1.0
    "hull.reverse_chine_extension_m",     # float: meters
    "hull.chine_flat_width_m",            # float: meters

    # ==========================================================================
    # Hull - Phase 3: Bow Forms
    # ==========================================================================
    "hull.bow_style",                     # "traditional" | "wedge" | "axe" | "faceted" | "wave_piercing"
    "hull.bow_facet_count",               # int: panels per side
    "hull.bow_planarity",                 # float: 0.0-1.0
    "hull.bow_half_angle_deg",            # float: degrees
    "hull.bow_region_length",             # float: fraction of LWL
    "hull.bow_freeboard_ratio",           # float: ratio
    "hull.stem_profile",                  # "vertical" | "raked" | "wave_piercing" | "axe" | "clipper"
    "hull.stem_radius_m",                 # float: meters

    # ==========================================================================
    # Hull - Phase 4: Spray Rails + Knuckle Lines
    # ==========================================================================
    "hull.spray_rail_count",              # int: 0-5
    "hull.spray_rail_spacing",            # float: vertical spacing ratio
    "hull.has_spray_rails",               # bool
    "hull.has_knuckle_lines",             # bool

    # ==========================================================================
    # Hull - Phase 5: Transom Variations
    # ==========================================================================
    "hull.transom_style",                 # "vertical" | "raked" | "stepped" | "tunneled" | "sugar_scoop"
    "hull.transom_rake_deg",              # float: degrees

    # ==========================================================================
    # Hull - Phase 6: Tumblehome, Panels, Deck
    # ==========================================================================
    "hull.tumblehome_enabled",            # bool
    "hull.tumblehome_angle_deg",          # float: degrees (positive = inward)
    "hull.tumblehome_start_ratio",        # float: 0.0-1.0 height above WL
    "hull.panel_style",                   # "smooth" | "faceted" | "developable"
    "hull.deck_enabled",                  # bool
    "hull.deck_camber_m",                 # float: meters

    # Hull - Derived/Computed
    "hull.displacement_m3", "hull.displacement_mt", "hull.displacement_kg",
    "hull.wetted_surface_m2", "hull.waterplane_area_m2",
    # Hull - Geometry-derived hydrostatics (P2)
    "hull.hydrostatics_method",
    "hull.cb_geometry", "hull.cp_geometry", "hull.cm_geometry", "hull.cwp_geometry",
    "hull.sectional_areas", "hull.bonjean_stations",
    "hull.it_m4", "hull.il_m4",

    # Hull - Centroids
    "hull.lcb_from_ap_m", "hull.lcf_from_ap_m", "hull.vcb_m",

    # Hull - Hydrostatics
    "hull.kb_m", "hull.bm_m", "hull.bmt", "hull.bml", "hull.kmt", "hull.kml",
    "hull.tpc", "hull.mct", "hull.gm_transverse_m",

    # Hull - Multi-hull
    "hull.hull_spacing_m", "hull.demi_hull_beam_m",

    # Hull - Weather criterion
    "hull.projected_lateral_area_m2", "hull.height_of_wind_pressure_m",

    # Structural design
    "structural_design.hull_material", "structural_design.superstructure_material",
    "structural_design.bottom_plating_mm", "structural_design.side_plating_mm",
    "structural_design.deck_plating_mm", "structural_design.keel_plating_mm",
    "structural_design.transom_plating_mm", "structural_design.frame_spacing_mm",
    "structural_design.plating_zones", "structural_design.stiffeners",

    # Structure aliases
    "structure.material", "structure.frame_spacing_mm",

    # Structural loads
    "structural_loads.slamming_pressure_kpa", "structural_loads.design_bending_moment_knm",
    "structural_loads.design_vertical_acceleration_g",

    # Propulsion
    "propulsion.propulsion_type", "propulsion.num_engines", "propulsion.num_propellers",
    "propulsion.total_installed_power_kw", "propulsion.installed_power_kw",
    "propulsion.engine_model", "propulsion.engine_power_kw",
    "propulsion.propeller_diameter_m", "propulsion.propeller_pitch_m",
    "propulsion.propeller_type", "propulsion.propulsive_efficiency",
    "propulsion.sfc_g_kwh", "propulsion.number_of_engines",

    # Weight
    "weight.lightship_weight_mt", "weight.lightship_mt", "weight.full_load_displacement_mt",
    "weight.deadweight_mt", "weight.hull_structure_mt", "weight.machinery_mt",
    "weight.lightship_lcg_m", "weight.lightship_vcg_m", "weight.lightship_tcg_m",
    "weight.group_100_mt", "weight.group_200_mt", "weight.group_300_mt",
    "weight.group_400_mt", "weight.group_500_mt", "weight.group_600_mt",
    "weight.margin_mt", "weight.average_confidence", "weight.summary_data",
    "weight.estimated_gm_m", "weight.stability_ready",

    # Stability
    "stability.gm_transverse_m", "stability.gm_m", "stability.gm_solid_m",
    "stability.gm_longitudinal_m", "stability.gm_corrected_m",
    "stability.km_m", "stability.fsc_m", "stability.has_fsc",
    "stability.kg_m", "stability.kb_m", "stability.bm_m",
    "stability.passes_gm_criterion", "stability.gz_curve",
    "stability.gz_max_m", "stability.gz_30_m",
    "stability.angle_gz_max_deg", "stability.angle_of_max_gz_deg",
    "stability.angle_vanishing_deg", "stability.angle_of_vanishing_stability_deg",
    "stability.range_deg",
    "stability.area_0_30_m_rad", "stability.area_0_40_m_rad", "stability.area_30_40_m_rad",
    "stability.passes_gz_criteria",
    "stability.damage_cases_evaluated", "stability.damage_all_pass",
    "stability.damage_worst_case", "stability.damage_results",
    "stability.weather_area_a_m_rad", "stability.weather_area_b_m_rad",
    "stability.weather_ratio", "stability.weather_passes",
    # Legacy stability outputs still referenced by phase gates / older UI
    "stability.imo_intact_passed", "stability.imo_damage_passed",
    "stability.damage_cases", "stability.damage_gm_min_m", "stability.damage_range_deg",

    # Loading
    "loading.full_load_departure", "loading.full_load_arrival",
    "loading.minimum_operating", "loading.lightship",
    "loading.all_conditions_pass", "loading.worst_case_gm_m", "loading.worst_case_condition",

    # Arrangement
    "arrangement.data", "arrangement.compartment_count", "arrangement.collision_bulkhead_m",
    "arrangement.tanks", "arrangement.compartments", "arrangement.tank_summary",
    "arrangement.total_fuel_capacity_l", "arrangement.total_fw_capacity_l",
    "arrangement.total_ballast_capacity_l", "arrangement.num_decks",

    # Compliance
    "compliance.status", "compliance.overall_passed", "compliance.pass_count",
    "compliance.fail_count", "compliance.incomplete_count",
    "compliance.findings", "compliance.report", "compliance.frameworks_checked",
    "compliance.pass_rate", "compliance.stability_status",
    "compliance.stability_pass_count", "compliance.stability_fail_count",

    # Resistance
    "resistance.total_resistance_kn", "resistance.frictional_resistance_kn",
    "resistance.residuary_resistance_kn", "resistance.wave_resistance_kn",
    "resistance.air_resistance_kn", "resistance.appendage_resistance_kn",
    "resistance.effective_power_kw", "resistance.effective_power_hp",
    "resistance.ct", "resistance.cf", "resistance.cr", "resistance.method",
    "resistance.froude_number", "resistance.reynolds_number",
    "resistance.regime", "resistance.method_valid", "resistance.validity_note",
    # Resistance - planing + multihull details (P2)
    "resistance.running_trim_deg", "resistance.wetted_length_m", "resistance.wetted_surface_m2",
    "resistance.froude_beam",
    "resistance.lift_coefficient", "resistance.drag_coefficient", "resistance.friction_coefficient",
    "resistance.pressure_resistance_kn",
    "resistance.interference_factor", "resistance.interference_note",

    # Performance
    "performance.design_speed_kts", "performance.design_power_kw",
    "performance.range_at_cruise_nm", "performance.endurance_at_cruise_hr",
    "performance.bollard_pull_kn",

    # Production
    "production.material_takeoff", "production.assembly_sequence",
    "production.build_schedule", "production.summary",
    "production.build_hours", "production.build_duration_days",

    # Cost
    "cost.estimate", "cost.total_price", "cost.total_cost",
    "cost.acquisition_cost", "cost.lifecycle_npv",
    "cost.subtotal_material", "cost.subtotal_labor", "cost.subtotal_equipment",
    "cost.material_cost", "cost.labor_cost",
    "cost.summary", "cost.confidence",

    # Optimization
    "optimization.problem", "optimization.result", "optimization.pareto_front",
    "optimization.selected_solution", "optimization.status",
    "optimization.iterations", "optimization.evaluations", "optimization.metrics",

    # Reports
    "reports.available_types", "reports.generated_reports",
    "reports.last_report_type", "reports.design_summary",
    "reporting.available_types", "reporting.generated_reports",
    "reporting.last_report_type", "reporting.design_summary",

    # Kernel
    "kernel.session", "kernel.status", "kernel.current_phase",
    "kernel.phase_history", "kernel.gate_status",

    # Analysis
    "analysis.operability_index", "analysis.roll_amplitude_deg",
    "analysis.pitch_amplitude_deg", "analysis.msi_percent", "analysis.noise_level_db",

    # Systems
    "systems.electrical_load_kw", "systems.generator_capacity_kw",
    "systems.fuel_tank_capacity_l", "systems.fw_tank_capacity_l",

    # Environmental
    "environmental.design_sea_state", "environmental.design_wave_height_m",
    "environmental.water_density_kg_m3",

    # Seakeeping
    "seakeeping.roll_period_s", "seakeeping.pitch_period_s",

    # Maneuvering
    "maneuvering.turning_circle_m", "maneuvering.advance_m", "maneuvering.transfer_m",

    # Electrical
    "electrical.total_connected_load_kw", "electrical.generator_sets",

    # Safety
    "safety.lifejackets", "safety.num_liferafts", "safety.epirb", "safety.fire_pumps",

    # Vision/Geometry
    "vision.geometry_generated", "vision.mesh_valid", "vision.vertex_count",

    # Outfitting
    "outfitting.berth_count", "outfitting.cabin_count", "outfitting.head_count",

    # Deck equipment
    "deck_equipment.anchor_weight_kg", "deck_equipment.windlass_type", "deck_equipment.cleats_count",
])


class StateManager:
    """
    State manager providing path-based access to DesignState.

    Features:
    - Dot-notation path access (e.g., 'mission.max_speed_kts')
    - Alias resolution (e.g., 'mission.max_speed_knots' -> 'mission.max_speed_kts')
    - Transaction support for atomic updates
    - File I/O for persistence
    """

    def __init__(self, state: Optional[DesignState] = None):
        """
        Initialize the state manager.

        Args:
            state: Optional DesignState to manage. Creates new if not provided.
        """
        self._state = state if state is not None else DesignState()
        self._transactions: Dict[str, Dict[str, Any]] = {}
        self._current_txn: Optional[str] = None
        # Versioned snapshots for revert operations
        self._version_snapshots: Dict[int, Dict[str, Any]] = {}
        self._version_snapshots[self._state.design_version] = copy.deepcopy(self._state.to_dict())
        # Dimension provenance tracking (Constraint-Aware Completion v1.0)
        # Maps path → DimensionProvenance for tracked hull dimensions
        self._value_provenance: Dict[str, DimensionProvenance] = {}
        # Hydrate stored provenance if present (persisted in DesignState.metadata)
        try:
            self._hydrate_dimension_provenance_from_metadata()
        except Exception:
            pass
        
        # TASK-024: Undo/Redo stack
        self._undo_stack: List[Dict[str, Any]] = []  # Stack of previous states
        self._redo_stack: List[Dict[str, Any]] = []  # Stack of undone states
        self._max_undo_depth: int = 20  # Maximum undo history
        # Contract 3: tracks paths written in the last committed transaction (best-effort).
        self._last_commit_written_paths: List[str] = []

    @property
    def state(self) -> DesignState:
        """Access the underlying DesignState."""
        return self._state

    # ==================== Path-Based Access ====================

    def get(self, path: str, default: Any = None) -> Any:
        """
        Get a value from the state using dot-notation path.

        Supports alias resolution - alternative names are mapped to canonical paths.

        Args:
            path: Dot-notation path (e.g., 'mission.max_speed_kts')
            default: Value to return if path not found.

        Returns:
            The value at the path, or default if not found.
        """
        # Resolve aliases
        canonical_path = normalize_path(path)
        parts = canonical_path.split(".")

        obj: Any = self._state
        for part in parts:
            if obj is None:
                return default
            if hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict):
                obj = obj.get(part, default)
                if obj is default:
                    return default
            else:
                return default

        return obj if obj is not None else default

    # ==================== Path-Strict Access (v1.1) ====================

    def _is_valid_path(self, path: str) -> bool:
        """
        Check if a path is valid in the schema.

        Args:
            path: Canonical path to check (after alias resolution)

        Returns:
            True if path is in VALID_PATHS or is a known alias
        """
        # Check direct match
        if path in VALID_PATHS:
            return True

        # Check if it's a valid prefix path (for nested access)
        # e.g., "hull" is valid because "hull.lwl" exists
        for valid_path in VALID_PATHS:
            if valid_path.startswith(path + "."):
                return True

        return False

    def get_strict(self, path: str) -> Union[Any, _MISSING]:
        """
        Get value, distinguishing missing from None (path-strict mode).

        Returns:
            - The value if set (including None if explicitly set to None)
            - MISSING sentinel if path never written

        Raises:
            InvalidPathError: if path not in schema
        """
        # Resolve aliases first
        canonical_path = normalize_path(path)

        # Validate path exists in schema
        if not self._is_valid_path(canonical_path):
            raise InvalidPathError(
                f"Unknown path: '{canonical_path}'. "
                f"Check schema or add to VALID_PATHS."
            )

        # Get raw value without default substitution
        parts = canonical_path.split(".")
        obj: Any = self._state

        for part in parts:
            if obj is None:
                return MISSING
            if hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict):
                if part not in obj:
                    return MISSING
                obj = obj[part]
            else:
                return MISSING

        # Note: obj could be None here (explicitly set to None)
        # We only return MISSING if the path didn't exist
        return obj

    def exists(self, path: str) -> bool:
        """
        Check if path has been set (not just in schema).

        Different from get() != None:
        - exists("hull.lwl") = True if LWL has been written
        - exists("hull.lwl") = False if LWL never written (even if in schema)

        Args:
            path: Path to check

        Returns:
            True if value exists at path (even if None)

        Raises:
            InvalidPathError: if path not in schema
        """
        value = self.get_strict(path)
        return value is not MISSING

    def set(
        self,
        path: str,
        value: Any,
        source: str,
        provenance: Optional[DimensionProvenance] = None,
    ) -> bool:
        """
        Set a value in the state using dot-notation path.

        ENFORCEMENT: Refinable paths require an active transaction.
        Use ActionPlan → ActionPlanValidator → ActionExecutor pipeline.

        Args:
            path: Dot-notation path to set.
            value: New value to assign.
            source: Identifier of who is making the change.
            provenance: Optional DimensionProvenance for tracked hull dimensions.
                        If not provided, defaults to USER for tracked paths.

        Returns:
            True if successful, False otherwise.

        Raises:
            MutationEnforcementError: If refinable path written outside transaction.
        """
        # Resolve aliases
        canonical_path = normalize_path(path)

        # === MUTATION ENFORCEMENT (Module 62 P0.3) ===
        # Refinable-first enforcement: only refinable paths need transactions.
        # Non-refinable paths (kernel, metadata, phase_states, etc.) are always allowed.
        from magnet.core.refinable_schema import is_refinable
        if is_refinable(canonical_path):
            if self._current_txn is None:
                raise MutationEnforcementError(
                    f"Refinable path '{canonical_path}' requires active transaction. "
                    f"Use ActionPlan → ActionExecutor pipeline. "
                    f"Source '{source}' attempted direct write."
                )
        # === END ENFORCEMENT ===

        # === PROVENANCE TRACKING (Constraint-Aware Completion v1.0) ===
        if canonical_path in PROVENANCE_TRACKED_PATHS:
            if provenance is not None:
                self._value_provenance[canonical_path] = provenance
            elif canonical_path not in self._value_provenance:
                # Default to USER if no provenance specified and not already tracked
                self._value_provenance[canonical_path] = DimensionProvenance.USER
            # Persist dimension provenance for crash recovery + API provenance generation.
            self._persist_dimension_provenance_to_metadata(canonical_path)
        # === END PROVENANCE ===

        # Record API-grade provenance for every write (Ledge 3 hinge).
        # This is intentionally outside the "tracked paths" list: API provenance is not optional.
        try:
            self._record_api_provenance(canonical_path, value, source, provenance)
        except Exception:
            # Never fail the mutation due to provenance bookkeeping.
            pass

        parts = canonical_path.split(".")

        if len(parts) == 0:
            return False

        # Navigate to parent
        obj: Any = self._state
        for part in parts[:-1]:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict):
                if part not in obj:
                    obj[part] = {}
                obj = obj[part]
            else:
                return False

        # Set the final attribute
        final_attr = parts[-1]
        if hasattr(obj, final_attr):
            old_value = getattr(obj, final_attr)
            # DesignState write guard: allow top-level attribute writes only inside mutator_context.
            if obj is self._state and hasattr(self._state, "mutator_context"):
                try:
                    with self._state.mutator_context():
                        setattr(obj, final_attr, value)
                except Exception:
                    setattr(obj, final_attr, value)
            else:
                setattr(obj, final_attr, value)

            # Record in history if in transaction
            if self._current_txn:
                # Contract 3: track written paths for the current transaction.
                try:
                    tx = self._transactions.get(self._current_txn) or {}
                    wp = tx.setdefault("written_paths", [])
                    if isinstance(wp, list):
                        wp.append(canonical_path)
                except Exception:
                    pass
                if canonical_path not in self._transactions[self._current_txn]["changes"]:
                    self._transactions[self._current_txn]["changes"][canonical_path] = old_value

            # Update timestamp (DesignState write guard)
            try:
                with self._state.mutator_context():
                    self._state.updated_at = datetime.utcnow().isoformat()
            except Exception:
                # Fallback for legacy states that may not have mutator_context yet
                self._state.updated_at = datetime.utcnow().isoformat()

            # Add to history
            try:
                with self._state.mutator_context():
                    self._state.history.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "source": source,
                        "action": "set",
                        "path": canonical_path,
                        "old_value": self._serialize_value(old_value),
                        "new_value": self._serialize_value(value),
                    })
            except Exception:
                self._state.history.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": source,
                    "action": "set",
                    "path": canonical_path,
                    "old_value": self._serialize_value(old_value),
                    "new_value": self._serialize_value(value),
                })

            return True
        elif isinstance(obj, dict):
            old_value = obj.get(final_attr)
            obj[final_attr] = value

            if self._current_txn:
                try:
                    tx = self._transactions.get(self._current_txn) or {}
                    wp = tx.setdefault("written_paths", [])
                    if isinstance(wp, list):
                        wp.append(canonical_path)
                except Exception:
                    pass
                if canonical_path not in self._transactions[self._current_txn]["changes"]:
                    self._transactions[self._current_txn]["changes"][canonical_path] = old_value

            try:
                with self._state.mutator_context():
                    self._state.updated_at = datetime.utcnow().isoformat()
            except Exception:
                self._state.updated_at = datetime.utcnow().isoformat()
            return True

        return False

    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value for storage in history."""
        if hasattr(value, "to_dict"):
            return value.to_dict()
        elif isinstance(value, (list, dict)):
            return copy.deepcopy(value)
        else:
            return value

    # ==================== Dimension Provenance (Constraint-Aware Completion v1.0) ====================

    def get_provenance(self, path: str) -> Optional[DimensionProvenance]:
        """
        Get the provenance of a tracked hull dimension.
        
        Args:
            path: Path to check (e.g., 'hull.beam')
            
        Returns:
            DimensionProvenance if tracked, None otherwise
        """
        canonical_path = normalize_path(path)
        return self._value_provenance.get(canonical_path)

    def is_placeholder(self, path: str) -> bool:
        """
        Check if a path has placeholder provenance.
        
        Placeholder values are ship-scale baselines that must be replaced
        before hull generation can proceed.
        
        Args:
            path: Path to check (e.g., 'hull.beam')
            
        Returns:
            True if the value is a placeholder, False otherwise
        """
        prov = self.get_provenance(path)
        return prov == DimensionProvenance.PLACEHOLDER

    def is_real_dimension(self, path: str) -> bool:
        """
        Check if a hull dimension has real (non-placeholder) provenance.
        
        A "real" dimension is one set by the user, synthesized from constraints,
        or set by the kernel with reasoning. Placeholder values are NOT real.
        
        Args:
            path: Path to check (e.g., 'hull.beam')
            
        Returns:
            True if the dimension is user/synthesized/kernel, False if placeholder or unset
        """
        prov = self.get_provenance(path)
        if prov is None:
            return False  # Not tracked or never set
        return prov in (
            DimensionProvenance.USER,
            DimensionProvenance.SYNTHESIZED,
            DimensionProvenance.KERNEL,
        )

    def get_placeholder_dimensions(self) -> List[str]:
        """
        Get list of hull dimensions that are still placeholders.
        
        These must be completed (via synthesis or user input) before
        hull generation can proceed.
        
        Returns:
            List of paths with placeholder provenance
        """
        return [
            path for path, prov in self._value_provenance.items()
            if prov == DimensionProvenance.PLACEHOLDER
        ]

    def hull_dimensions_complete(self) -> bool:
        """
        Check if all principal hull dimensions have real (non-placeholder) provenance.
        
        Required for hull generation to proceed.
        
        Returns:
            True if loa, beam, draft, depth all have real provenance
        """
        required = ["hull.loa", "hull.beam", "hull.draft", "hull.depth"]
        for path in required:
            if not self.is_real_dimension(path):
                return False
        return True

    # ==================== Serialization ====================

    def to_dict(self) -> Dict[str, Any]:
        """Export the entire state as a dictionary (including persisted provenance metadata)."""
        # Ensure persisted provenance snapshots are up to date.
        try:
            # Keep dimension provenance persisted for the tracked subset.
            self._persist_all_dimension_provenance_to_metadata()
        except Exception:
            pass
        return self._state.to_dict()

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load state from a dictionary, replacing current state."""
        self._state = DesignState.from_dict(data)
        # Rehydrate internal provenance caches from metadata.
        self._hydrate_dimension_provenance_from_metadata()

    def load_from_dict(self, data: Dict[str, Any]) -> None:
        """Alias for from_dict for API compatibility."""
        self.from_dict(data)

    # ==================== API Provenance (Walking Trail Ledge 3) ====================

    def compute_explain_ref(self, path: str, design_version: Optional[int] = None) -> str:
        """
        Deterministic, cacheable explain reference.

        Includes the design_version in the prefix to make refs resolvable without hidden indexes:
        exp_v{version}_{token}
        """
        dv = int(design_version if design_version is not None else (self.get("design_version", 0) or 0))
        design_id = str(self.get("design_id", "") or "")
        canonical_path = normalize_path(path)
        content = f"{design_id}:{dv}:{canonical_path}"
        digest = hashlib.sha256(content.encode("utf-8")).digest()[:6]
        token = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
        return f"exp_v{dv}_{token}"

    def _api_provenance_store(self) -> Dict[str, Any]:
        meta = self._state.metadata if isinstance(self._state.metadata, dict) else {}
        try:
            with self._state.mutator_context():
                self._state.metadata = meta
        except Exception:
            self._state.metadata = meta
        store = meta.get("_api_provenance")
        if not isinstance(store, dict):
            store = {}
            meta["_api_provenance"] = store
        return store

    def _record_api_provenance(
        self,
        canonical_path: str,
        value: Any,
        source: str,
        dim_prov: Optional[DimensionProvenance],
    ) -> None:
        store = self._api_provenance_store()

        # Nulls are explicit "unknown/unset" placeholders in the contract.
        if value is None:
            api_source = ValueProvenance.DEFAULT
            conf = 0.0
        else:
            api_source = _infer_api_provenance(source, dim_prov)
            # Default confidence by provenance category; can be refined upstream later.
            default_conf = {
                ValueProvenance.USER: 1.0,
                ValueProvenance.KERNEL: 0.95,
                ValueProvenance.LLM: 0.6,
                ValueProvenance.FALLBACK: 0.3,
                ValueProvenance.DEFAULT: 0.3,
                ValueProvenance.INHERITED: 0.3,
            }.get(api_source, 0.3)
            prev = store.get(canonical_path) if isinstance(store.get(canonical_path), dict) else {}
            prev_conf = prev.get("confidence") if isinstance(prev, dict) else None
            conf = _validate_confidence(api_source, default_conf, original_confidence=prev_conf)

        dv = int(self.get("design_version", 0) or 0)
        store[canonical_path] = {
            "source": api_source.value,
            "confidence": conf,
            "explain_ref": self.compute_explain_ref(canonical_path, design_version=dv),
            "validator_id": source,
            "design_version": dv,
            "updated_at": datetime.utcnow().isoformat(),
        }

    def export_api_provenance(
        self,
        serialized_state: Dict[str, Any],
        include: str = "full",
    ) -> Dict[str, Any]:
        """
        Build the API provenance map for a given serialized state dict.

        include:
          - "none": {}
          - "summary": {path: {"source": "...", "confidence": 0.x, "explain_ref": "..."}}
          - "full": includes validator_id + design_version + updated_at
        """
        include = (include or "full").lower()
        if include == "none":
            return {}

        store = self._api_provenance_store()
        out: Dict[str, Any] = {}
        for path, value in self._iter_state_leaves(serialized_state):
            if path.startswith("metadata.") or path.startswith("_internal."):
                continue

            entry = store.get(path)
            if not isinstance(entry, dict):
                # Contract 1: do not silently omit provenance; mark explicitly.
                dv = int(self.get("design_version", 0) or 0)
                entry = {
                    "source": ValueProvenance.DEFAULT.value,
                    "confidence": 0.0 if value is None else 0.3,
                    "explain_ref": self.compute_explain_ref(path, design_version=dv),
                    "validator_id": "missing_provenance",
                    "design_version": dv,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                # Persist the backfill so future responses are stable (still explicit).
                store[path] = entry

            if include == "summary":
                out[path] = {
                    "source": entry.get("source"),
                    "confidence": entry.get("confidence"),
                    "explain_ref": entry.get("explain_ref"),
                }
            else:
                out[path] = entry

        return out

    def _iter_state_leaves(self, obj: Any, prefix: str = "") -> Iterator[Tuple[str, Any]]:
        """
        Iterate "leaf" values to apply provenance to.

        - dict: recurse
        - list: treated as a single value at the list path
        - scalar: yielded
        """
        if isinstance(obj, dict):
            for k, v in obj.items():
                if not isinstance(k, str):
                    continue
                p = f"{prefix}.{k}" if prefix else k
                # Nested dicts don't get provenance at the container level; only their leaves do.
                yield from self._iter_state_leaves(v, p)
            return

        if isinstance(obj, list):
            # Lists/arrays are treated as a computed unit.
            if prefix:
                yield (prefix, obj)
            return

        if prefix:
            yield (prefix, obj)

    # ==================== Contract 1: canonical flat state map ====================

    def export_state_flat(self, include_metadata: bool = False) -> Dict[str, Any]:
        """
        Return flat state map: dot-path -> value.

        This matches Walking Trail Contract 1 (the `state` object).
        """
        raw = self.to_dict()
        out: Dict[str, Any] = {}
        for path, value in self._iter_state_leaves(raw):
            if not include_metadata and (path.startswith("metadata.") or path.startswith("_internal.")):
                continue
            out[path] = value
        return out

    # ==================== Provenance persistence helpers ====================

    def _persist_dimension_provenance_to_metadata(self, canonical_path: str) -> None:
        if not isinstance(self._state.metadata, dict):
            self._state.metadata = {}
        m = self._state.metadata.get("_dimension_provenance")
        if not isinstance(m, dict):
            m = {}
            self._state.metadata["_dimension_provenance"] = m
        prov = self._value_provenance.get(canonical_path)
        if prov is not None:
            m[canonical_path] = prov.value

    def _persist_all_dimension_provenance_to_metadata(self) -> None:
        for p in list(self._value_provenance.keys()):
            self._persist_dimension_provenance_to_metadata(p)

    def _hydrate_dimension_provenance_from_metadata(self) -> None:
        meta = self._state.metadata if isinstance(self._state.metadata, dict) else {}
        m = meta.get("_dimension_provenance")
        if not isinstance(m, dict):
            return
        hydrated: Dict[str, DimensionProvenance] = {}
        for path, value in m.items():
            if not isinstance(path, str) or not isinstance(value, str):
                continue
            try:
                hydrated[normalize_path(path)] = DimensionProvenance(value)
            except Exception:
                continue
        self._value_provenance = hydrated

    def export_snapshot(self, include_metadata: bool = True) -> Dict[str, Any]:
        """
        Export a snapshot of the current state.

        Args:
            include_metadata: Whether to include history and metadata.

        Returns:
            Snapshot dictionary suitable for storage or comparison.
        """
        snapshot = self._state.to_dict()

        if not include_metadata:
            snapshot.pop("history", None)
            snapshot.pop("metadata", None)

        snapshot["snapshot_timestamp"] = datetime.utcnow().isoformat()
        return snapshot

    # ==================== Safe Cloning (Emergency Stabilization: E0.1) ====================

    def clone(self) -> "StateManager":
        """
        Return an isolated copy of this StateManager.

        This is used for "what-if" evaluation paths (sensitivity/optimization) and MUST
        never return the live canonical object.

        Notes:
        - Uses a deep-copied DesignState dictionary round-trip for isolation.
        - Produces a fresh StateManager with no open transactions.
        """
        snapshot = copy.deepcopy(self._state.to_dict())
        cloned_state = DesignState.from_dict(snapshot)
        return StateManager(state=cloned_state)

    # ==================== File I/O ====================

    def save_to_file(self, filepath: str) -> None:
        """
        Save the current state to a JSON file.

        Args:
            filepath: Path to the output file.
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    def load_from_file(self, filepath: str) -> None:
        """
        Load state from a JSON file.

        Args:
            filepath: Path to the input file.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.from_dict(data)

    # ==================== Validation ====================

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate the current state.

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        return self._state.validate()

    def patch(self, updates: Dict[str, Any], source: str) -> List[str]:
        """
        Apply multiple updates atomically.

        Args:
            updates: Dictionary of path -> value updates.
            source: Identifier of the update source.

        Returns:
            List of paths that were modified.
        """
        modified = []
        for path, value in updates.items():
            if self.set(path, value, source):
                modified.append(normalize_path(path))
        return modified

    def diff(self, other: "StateManager") -> Dict[str, Tuple[Any, Any]]:
        """
        Compare with another state manager.

        Args:
            other: Another StateManager to compare against.

        Returns:
            Dictionary of changed paths to (old, new) tuples.
        """
        return self._state.diff(other._state)

    # ==================== Transactions ====================

    def begin_transaction(self) -> str:
        """
        Begin a new transaction.

        All changes until commit/rollback can be reverted.

        Returns:
            Transaction ID string.
        """
        if self._current_txn is not None:
            raise RuntimeError("Transaction already in progress")

        txn_id = str(uuid.uuid4())
        self._transactions[txn_id] = {
            "started_at": datetime.utcnow().isoformat(),
            "changes": {},
            "snapshot": copy.deepcopy(self._state.to_dict()),
            # TASK-024: Save pre-transaction state for undo (only pushed on commit)
            "pre_transaction_state": copy.deepcopy(self._state.to_dict()),
            # Contract 3: paths written during transaction
            "written_paths": [],
        }
        self._current_txn = txn_id
        return txn_id

    def commit_transaction(self, txn_id: str) -> bool:
        """
        Commit a transaction, making changes permanent.

        Args:
            txn_id: Transaction ID from begin_transaction.

        Returns:
            True if commit successful.

        Note:
            Prefer using commit() which is the canonical commit path.
        """
        if txn_id not in self._transactions:
            return False

        if self._current_txn != txn_id:
            return False

        # TASK-024: Push pre-transaction state to undo stack on successful commit
        pre_state = self._transactions[txn_id].get("pre_transaction_state")
        if pre_state:
            self._push_undo_state(pre_state)

        # Contract 3: capture written paths prior to clearing transaction.
        try:
            wp = self._transactions[txn_id].get("written_paths", [])
            if isinstance(wp, list):
                seen = set()
                ordered: List[str] = []
                for p in wp:
                    if not isinstance(p, str):
                        continue
                    if p in seen:
                        continue
                    seen.add(p)
                    ordered.append(p)
                self._last_commit_written_paths = ordered
                try:
                    with self._state.mutator_context():
                        if not isinstance(self._state.metadata, dict):
                            self._state.metadata = {}
                        self._state.metadata["_last_commit_written_paths"] = ordered
                except Exception:
                    if not isinstance(self._state.metadata, dict):
                        self._state.metadata = {}
                    self._state.metadata["_last_commit_written_paths"] = ordered
        except Exception:
            self._last_commit_written_paths = []

        # Increment design_version (ONLY place this happens) (DesignState write guard)
        try:
            with self._state.mutator_context():
                self._state.design_version += 1
        except Exception:
            self._state.design_version += 1

        # -----------------------------------------------------------------
        # Turn Contract Vault: invalidate current contract pointer on commit
        # UNLESS the transaction itself wrote a new contract/pointer.
        # -----------------------------------------------------------------
        try:
            wrote_contract = False
            try:
                wp = self._transactions[txn_id].get("written_paths", []) or []
                for p in wp:
                    if not isinstance(p, str):
                        continue
                    if p == "current_turn_contract_id" or p.startswith("turn_contracts"):
                        wrote_contract = True
                        break
            except Exception:
                wrote_contract = False

            if not wrote_contract:
                try:
                    with self._state.mutator_context():
                        self._state.current_turn_contract_id = None
                except Exception:
                    self._state.current_turn_contract_id = None
        except Exception:
            pass

        # Save snapshot of committed state for potential revert
        self._version_snapshots[self._state.design_version] = copy.deepcopy(self._state.to_dict())

        # Clear transaction data
        del self._transactions[txn_id]
        self._current_txn = None

        # Add commit to history (DesignState write guard)
        try:
            with self._state.mutator_context():
                self._state.history.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "action": "transaction_commit",
                    "txn_id": txn_id,
                    "design_version": self._state.design_version,
                })
        except Exception:
            self._state.history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "action": "transaction_commit",
                "txn_id": txn_id,
                "design_version": self._state.design_version,
            })

        return True

    def get_last_commit_written_paths(self) -> List[str]:
        """Return the written paths from the most recent commit (best-effort)."""
        if self._last_commit_written_paths:
            return list(self._last_commit_written_paths)
        try:
            meta = self._state.metadata if isinstance(self._state.metadata, dict) else {}
            wp = meta.get("_last_commit_written_paths", [])
            return list(wp) if isinstance(wp, list) else []
        except Exception:
            return []

    def commit(self, explain_record_id: Optional[str] = None) -> int:
        """
        Canonical commit path. Commits active transaction and increments design_version.

        This is the ONLY place design_version should increment.

        Args:
            explain_record_id: [v1.1] Correlation token for ExplainRecord.
                               Stored in metadata for crash recovery reconciliation.

        Returns:
            New design_version after commit.

        Raises:
            RuntimeError: If no active transaction.
        """
        if self._current_txn is None:
            raise RuntimeError("No active transaction to commit")

        # v1.1: Store correlation token BEFORE commit
        if explain_record_id:
            self._state.metadata["last_explain_record_id"] = explain_record_id

        txn_id = self._current_txn
        success = self.commit_transaction(txn_id)
        if not success:
            raise RuntimeError(f"Failed to commit transaction {txn_id}")

        return self._state.design_version
    
    def get_last_explain_record_id(self) -> Optional[str]:
        """
        Get the correlation token for the last committed version.
        
        Used by ExplainRecordStore.reconcile_pending() to determine
        if a PENDING record's commit succeeded.
        """
        return self._state.metadata.get("last_explain_record_id")

    def rollback_transaction(self, txn_id: str) -> bool:
        """
        Rollback a transaction, reverting all changes.

        Args:
            txn_id: Transaction ID from begin_transaction.

        Returns:
            True if rollback successful.
        """
        if txn_id not in self._transactions:
            return False

        if self._current_txn != txn_id:
            return False

        # Restore from snapshot
        snapshot = self._transactions[txn_id]["snapshot"]
        self._state = DesignState.from_dict(snapshot)

        # Clear transaction data
        del self._transactions[txn_id]
        self._current_txn = None

        # Add rollback to history
        self._state.history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": "transaction_rollback",
            "txn_id": txn_id,
        })

        return True

    # ==================== Revert ====================

    def revert_to_version(self, target_version: int) -> bool:
        """
        Revert state to a previously committed design_version.

        Args:
            target_version: Design version to restore.

        Returns:
            True if revert succeeded, False otherwise.
        """
        if target_version not in self._version_snapshots:
            return False

        snapshot = self._version_snapshots[target_version]
        self._state = DesignState.from_dict(copy.deepcopy(snapshot))
        self._current_txn = None
        self._transactions.clear()

        # Record revert in history
        self._state.history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": "revert",
            "design_version": target_version,
        })

        return True

    def rollback(self) -> bool:
        """
        Rollback the active transaction.

        This is a convenience wrapper around rollback_transaction() that
        uses the currently active transaction.

        Returns:
            True if rollback successful.

        Raises:
            RuntimeError: If no active transaction.
        """
        if self._current_txn is None:
            raise RuntimeError("No active transaction to rollback")

        return self.rollback_transaction(self._current_txn)

    def in_transaction(self) -> bool:
        """
        Check if currently in a transaction.

        Returns:
            True if a transaction is active.
        """
        return self._current_txn is not None

    # ==================== Undo/Redo (TASK-024) ====================

    def _push_undo_state(self, snapshot: Dict[str, Any]) -> None:
        """
        Push a state snapshot to undo stack.
        
        Args:
            snapshot: State dictionary to push
        """
        self._undo_stack.append(snapshot)
        
        # Limit stack depth
        if len(self._undo_stack) > self._max_undo_depth:
            self._undo_stack.pop(0)
        
        # Clear redo stack on new mutation
        self._redo_stack.clear()

    def undo(self) -> bool:
        """
        Undo the last change.
        
        Returns:
            True if undo succeeded, False if nothing to undo.
        """
        if not self._undo_stack:
            return False
        
        # Save current state to redo stack
        current = copy.deepcopy(self._state.to_dict())
        self._redo_stack.append(current)
        
        # Restore previous state
        previous = self._undo_stack.pop()
        self._state = DesignState.from_dict(previous)
        
        # Record in history
        self._state.history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": "undo",
            "design_version": self._state.design_version,
        })
        
        return True

    def redo(self) -> bool:
        """
        Redo the last undone change.
        
        Returns:
            True if redo succeeded, False if nothing to redo.
        """
        if not self._redo_stack:
            return False
        
        # Save current state to undo stack
        current = copy.deepcopy(self._state.to_dict())
        self._undo_stack.append(current)
        
        # Restore next state
        next_state = self._redo_stack.pop()
        self._state = DesignState.from_dict(next_state)
        
        # Record in history
        self._state.history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": "redo",
            "design_version": self._state.design_version,
        })
        
        return True

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0

    def undo_stack_depth(self) -> int:
        """Get current undo stack depth."""
        return len(self._undo_stack)

    def redo_stack_depth(self) -> int:
        """Get current redo stack depth."""
        return len(self._redo_stack)

    # ==================== design_version Property ====================

    @property
    def design_version(self) -> int:
        """
        Current design_version (mutation counter).

        This is a read-only property. Increments only happen in commit().
        """
        return self._state.design_version

    # ==================== Parameter Locks ====================

    def is_locked(self, path: str) -> bool:
        """
        Check if a parameter path is locked.

        Args:
            path: State path (e.g., "hull.loa")

        Returns:
            True if the path is locked.
        """
        return path in self._state.locked_parameters

    def lock_parameter(self, path: str) -> None:
        """
        Lock a parameter, preventing modification.

        Args:
            path: State path to lock.
        """
        self._state.locked_parameters.add(path)

    def unlock_parameter(self, path: str) -> None:
        """
        Unlock a parameter, allowing modification.

        Args:
            path: State path to unlock.
        """
        self._state.locked_parameters.discard(path)

    def get_locked_parameters(self) -> set:
        """
        Get all locked parameter paths.

        Returns:
            Set of locked paths.
        """
        return self._state.locked_parameters.copy()

    # ==================== Internal API for Phase Machine ====================

    def _set_phase_state_internal(
        self,
        phase: str,
        state: str,
        entered_by: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Internal method for phase machine to update phase states.

        This bypasses normal validation to allow the phase machine
        to manage its own state transitions.

        Args:
            phase: Phase name (e.g., 'mission', 'hull_form')
            state: New state (e.g., 'draft', 'active', 'locked')
            entered_by: Who triggered the transition
            metadata: Additional metadata for the transition
        """
        try:
            with self._state.mutator_context():
                if phase not in self._state.phase_states:
                    self._state.phase_states[phase] = {}

                self._state.phase_states[phase] = {
                    "state": state,
                    "entered_at": datetime.utcnow().isoformat(),
                    "entered_by": entered_by,
                    **(metadata or {}),
                }

                # Also update phase_metadata
                if phase not in self._state.phase_metadata:
                    self._state.phase_metadata[phase] = {}

                self._state.phase_metadata[phase].update({
                    "phase": phase,
                    "state": state,
                    "entered_at": datetime.utcnow().isoformat(),
                    "entered_by": entered_by,
                })

                if metadata:
                    self._state.phase_metadata[phase].update(metadata)

                self._state.updated_at = datetime.utcnow().isoformat()
        except Exception:
            if phase not in self._state.phase_states:
                self._state.phase_states[phase] = {}

            self._state.phase_states[phase] = {
                "state": state,
                "entered_at": datetime.utcnow().isoformat(),
                "entered_by": entered_by,
                **(metadata or {}),
            }

            if phase not in self._state.phase_metadata:
                self._state.phase_metadata[phase] = {}

            self._state.phase_metadata[phase].update({
                "phase": phase,
                "state": state,
                "entered_at": datetime.utcnow().isoformat(),
                "entered_by": entered_by,
            })

            if metadata:
                self._state.phase_metadata[phase].update(metadata)

            self._state.updated_at = datetime.utcnow().isoformat()

    def _get_phase_states_internal(self) -> Dict[str, Dict[str, Any]]:
        """
        Internal method to get all phase states.

        Returns:
            Dictionary mapping phase names to their state info.
        """
        return copy.deepcopy(self._state.phase_states)

    def _set_phase_states_internal(self, phase_states: Dict[str, Dict[str, Any]]) -> None:
        """
        Internal method to set all phase states at once.

        Args:
            phase_states: Dictionary mapping phase names to their state info.
        """
        try:
            with self._state.mutator_context():
                self._state.phase_states = copy.deepcopy(phase_states)
                self._state.updated_at = datetime.utcnow().isoformat()
        except Exception:
            self._state.phase_states = copy.deepcopy(phase_states)
            self._state.updated_at = datetime.utcnow().isoformat()

    # ==================== Utility Methods ====================

    def get_design_id(self) -> Optional[str]:
        """Get the design ID."""
        return self._state.design_id

    def get_design_name(self) -> Optional[str]:
        """Get the design name."""
        return self._state.design_name

    def set_design_name(self, name: str, source: str) -> None:
        """Set the design name."""
        self.set("design_name", name, source)

    def get_version(self) -> str:
        """Get the design state version."""
        return self._state.version

    def summary(self) -> str:
        """Get a summary of the current state."""
        return self._state.summary()

    def __repr__(self) -> str:
        return f"StateManager({self._state})"
