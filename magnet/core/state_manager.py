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
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

from magnet.core.design_state import DesignState
from magnet.core.field_aliases import normalize_path, get_canonical

logger = logging.getLogger(__name__)


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
    "hull.hull_type",

    # Hull - Form coefficients
    "hull.cb", "hull.cp", "hull.cm", "hull.cwp", "hull.cvp",

    # Hull - Angles
    "hull.deadrise_deg", "hull.deadrise_midship_deg", "hull.entrance_angle_deg",

    # Hull - Derived/Computed
    "hull.displacement_m3", "hull.displacement_mt", "hull.displacement_kg",
    "hull.wetted_surface_m2", "hull.waterplane_area_m2",

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
    "stability.gm_longitudinal_m", "stability.km_m", "stability.fsc_m",
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
    "resistance.air_resistance_kn", "resistance.froude_number", "resistance.reynolds_number",

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

    def set(self, path: str, value: Any, source: str) -> bool:
        """
        Set a value in the state using dot-notation path.

        ENFORCEMENT: Refinable paths require an active transaction.
        Use ActionPlan → ActionPlanValidator → ActionExecutor pipeline.

        Args:
            path: Dot-notation path to set.
            value: New value to assign.
            source: Identifier of who is making the change.

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
            setattr(obj, final_attr, value)

            # Record in history if in transaction
            if self._current_txn:
                if canonical_path not in self._transactions[self._current_txn]["changes"]:
                    self._transactions[self._current_txn]["changes"][canonical_path] = old_value

            # Update timestamp
            self._state.updated_at = datetime.utcnow().isoformat()

            # Add to history
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
                if canonical_path not in self._transactions[self._current_txn]["changes"]:
                    self._transactions[self._current_txn]["changes"][canonical_path] = old_value

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

    # ==================== Serialization ====================

    def to_dict(self) -> Dict[str, Any]:
        """Export the entire state as a dictionary."""
        return self._state.to_dict()

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load state from a dictionary, replacing current state."""
        self._state = DesignState.from_dict(data)

    def load_from_dict(self, data: Dict[str, Any]) -> None:
        """Alias for from_dict for API compatibility."""
        self.from_dict(data)

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

        # Increment design_version (ONLY place this happens)
        self._state.design_version += 1

        # Clear transaction data
        del self._transactions[txn_id]
        self._current_txn = None

        # Add commit to history
        self._state.history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": "transaction_commit",
            "txn_id": txn_id,
            "design_version": self._state.design_version,
        })

        return True

    def commit(self) -> int:
        """
        Canonical commit path. Commits active transaction and increments design_version.

        This is the ONLY place design_version should increment.

        Returns:
            New design_version after commit.

        Raises:
            RuntimeError: If no active transaction.
        """
        if self._current_txn is None:
            raise RuntimeError("No active transaction to commit")

        txn_id = self._current_txn
        success = self.commit_transaction(txn_id)
        if not success:
            raise RuntimeError(f"Failed to commit transaction {txn_id}")

        return self._state.design_version

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
