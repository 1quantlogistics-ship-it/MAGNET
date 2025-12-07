"""
MAGNET Phase Ownership

Maps design phases to the state paths they own.
Used for determining what data is affected by phase changes.
"""

from typing import Dict, List, Set

# ==================== Phase to State Path Mapping ====================
# Each phase owns specific sections/paths of the DesignState

PHASE_OWNERSHIP: Dict[str, List[str]] = {
    "mission": [
        "mission",
        "mission.vessel_type",
        "mission.vessel_name",
        "mission.max_speed_kts",
        "mission.cruise_speed_kts",
        "mission.range_nm",
        "mission.endurance_hours",
        "mission.crew_berthed",
        "mission.passengers",
        "mission.cargo_capacity_mt",
        "mission.operating_area",
        "mission.design_sea_state",
        "mission.classification_society",
        "mission.class_notation",
        "environmental",
        "environmental.design_sea_state",
        "environmental.design_wave_height_m",
        "environmental.water_density_kg_m3",
    ],

    "hull_form": [
        "hull",
        "hull.loa",
        "hull.lwl",
        "hull.beam",
        "hull.draft",
        "hull.depth",
        "hull.hull_type",
        "hull.cb",
        "hull.cp",
        "hull.cm",
        "hull.cwp",
        "hull.deadrise_deg",
        "hull.displacement_m3",
        "hull.wetted_surface_m2",
        "hull.waterplane_area_m2",
        "hull.lcb_from_ap_m",
        "hull.lcf_from_ap_m",
        "hull.vcb_m",
        "hull.bmt",
        "hull.bml",
        "hull.kmt",
        "hull.tpc",
        "hull.mct",
        "vision",
        "vision.geometry_generated",
        "vision.mesh_valid",
        "vision.vertex_count",
        "vision.face_count",
        "resistance",
        "resistance.total_resistance_kn",
        "resistance.froude_number",
        "resistance.reynolds_number",
    ],

    "structure": [
        "structural_design",
        "structural_design.hull_material",
        "structural_design.plating_zones",
        "structural_design.bottom_plating_mm",
        "structural_design.side_plating_mm",
        "structural_design.deck_plating_mm",
        "structural_design.frame_spacing_mm",
        "structural_design.longitudinals",
        "structural_design.transverse_frames",
        "structural_design.watertight_bulkheads",
        "structural_design.bulkhead_positions_m",
        "structural_loads",
        "structural_loads.slamming_pressure_kpa",
        "structural_loads.hydrostatic_pressure_kpa",
        "structural_loads.design_vertical_acceleration_g",
        "structural_loads.design_bending_moment_knm",
    ],

    "arrangement": [
        "arrangement",
        "arrangement.deck_layouts",
        "arrangement.num_decks",
        "arrangement.compartments",
        "arrangement.fuel_tanks",
        "arrangement.fresh_water_tanks",
        "arrangement.ballast_tanks",
        "arrangement.total_fuel_capacity_l",
        "arrangement.total_fw_capacity_l",
        "arrangement.engine_room_volume_m3",
        "arrangement.accommodation_area_m2",
        "outfitting",
        "outfitting.berth_count",
        "outfitting.cabin_count",
        "outfitting.helm_seats",
        "deck_equipment",
        "deck_equipment.anchor_weight_kg",
        "deck_equipment.windlass_type",
        "deck_equipment.cleats_count",
    ],

    "propulsion": [
        "propulsion",
        "propulsion.propulsion_type",
        "propulsion.total_installed_power_kw",
        "propulsion.num_engines",
        "propulsion.engine_make",
        "propulsion.engine_model",
        "propulsion.engine_power_kw",
        "propulsion.num_propellers",
        "propulsion.propeller_diameter_m",
        "propulsion.propeller_pitch_m",
        "propulsion.propulsive_efficiency",
        "propulsion.fuel_type",
        "propulsion.sfc_g_kwh",
        "performance",
        "performance.speed_power_curve",
        "performance.design_speed_kts",
        "performance.design_power_kw",
        "performance.range_at_cruise_nm",
        "performance.fuel_consumption_cruise_lph",
    ],

    "weight": [
        "weight",
        "weight.lightship_weight_mt",
        "weight.full_load_displacement_mt",
        "weight.deadweight_mt",
        "weight.hull_structure_mt",
        "weight.machinery_mt",
        "weight.outfit_mt",
        "weight.fuel_mt",
        "weight.fresh_water_mt",
        "weight.cargo_mt",
        "weight.lightship_lcg_m",
        "weight.lightship_vcg_m",
        "weight.full_load_lcg_m",
        "weight.full_load_vcg_m",
        "weight.weight_items",
        "weight.free_surface_moment_mt_m",
    ],

    "stability": [
        "stability",
        "stability.gm_transverse_m",
        "stability.gm_longitudinal_m",
        "stability.gz_max_m",
        "stability.angle_of_max_gz_deg",
        "stability.angle_of_vanishing_stability_deg",
        "stability.area_0_30_m_rad",
        "stability.area_0_40_m_rad",
        "stability.area_30_40_m_rad",
        "stability.kg_m",
        "stability.kb_m",
        "stability.bm_m",
        "stability.gz_curve",
        "stability.damage_cases",
        "stability.imo_intact_passed",
        "stability.imo_damage_passed",
        "loading",
        "loading.loading_conditions",
        "loading.current_condition",
        "loading.tank_states",
        "seakeeping",
        "seakeeping.roll_period_s",
        "seakeeping.pitch_period_s",
        "seakeeping.roll_rao",
        "seakeeping.pitch_rao",
        "maneuvering",
        "maneuvering.tactical_diameter_m",
        "maneuvering.turning_radius_m",
    ],

    "compliance": [
        "compliance",
        "compliance.overall_passed",
        "compliance.checks",
        "compliance.errors",
        "compliance.warnings",
        "compliance.stability_checks_passed",
        "compliance.structural_checks_passed",
        "compliance.safety_checks_passed",
        "compliance.class_rules",
        "compliance.certifications_required",
        "safety",
        "safety.liferaft_capacity",
        "safety.num_liferafts",
        "safety.lifejackets",
        "safety.fire_detection_zones",
        "safety.escape_routes",
    ],

    "production": [
        "production",
        "production.build_hours",
        "production.hull_hours",
        "production.material_cost",
        "production.labor_cost",
        "production.build_duration_days",
        "production.milestones",
        "production.yard_name",
        "cost",
        "cost.total_cost",
        "cost.material_cost",
        "cost.labor_cost",
        "cost.engineering_cost",
        "cost.contingency_amount",
        "reports",
        "reports.generated",
        "reports.design_summary",
        "reports.compliance_report",
    ],
}

# ==================== Phase Dependencies ====================
# Which phases must be locked before this phase can progress

PHASE_DEPENDENCIES: Dict[str, List[str]] = {
    "mission": [],
    "hull_form": ["mission"],
    "structure": ["hull_form"],
    "arrangement": ["hull_form", "structure"],
    "propulsion": ["hull_form", "mission"],
    "weight": ["structure", "propulsion", "arrangement"],
    "stability": ["hull_form", "weight"],
    "compliance": ["structure", "stability", "weight"],
    "production": ["compliance"],
}

# ==================== Downstream Phase Mapping ====================
# Which phases are downstream of (depend on) each phase

DOWNSTREAM_PHASES: Dict[str, List[str]] = {
    "mission": ["hull_form", "propulsion", "weight", "stability", "compliance", "production"],
    "hull_form": ["structure", "arrangement", "propulsion", "weight", "stability", "compliance", "production"],
    "structure": ["arrangement", "weight", "compliance", "production"],
    "arrangement": ["weight", "production"],
    "propulsion": ["weight", "stability", "compliance", "production"],
    "weight": ["stability", "compliance", "production"],
    "stability": ["compliance", "production"],
    "compliance": ["production"],
    "production": [],
}

# ==================== Ordered Phase List ====================

PHASE_ORDER: List[str] = [
    "mission",
    "hull_form",
    "structure",
    "arrangement",
    "propulsion",
    "weight",
    "stability",
    "compliance",
    "production",
]


def get_phase_for_path(path: str) -> str | None:
    """
    Determine which phase owns a given state path.

    Args:
        path: State path (e.g., 'hull.loa', 'mission.max_speed_kts')

    Returns:
        Phase name that owns this path, or None if not found
    """
    # First check for exact match
    for phase, paths in PHASE_OWNERSHIP.items():
        if path in paths:
            return phase

    # Check for prefix match (e.g., 'hull.some_new_field' -> 'hull_form')
    section = path.split(".")[0] if "." in path else path

    section_to_phase = {
        "mission": "mission",
        "environmental": "mission",
        "hull": "hull_form",
        "vision": "hull_form",
        "resistance": "hull_form",
        "structural_design": "structure",
        "structural_loads": "structure",
        "arrangement": "arrangement",
        "outfitting": "arrangement",
        "deck_equipment": "arrangement",
        "propulsion": "propulsion",
        "performance": "propulsion",
        "weight": "weight",
        "stability": "stability",
        "loading": "stability",
        "seakeeping": "stability",
        "maneuvering": "stability",
        "compliance": "compliance",
        "safety": "compliance",
        "production": "production",
        "cost": "production",
        "reports": "production",
    }

    return section_to_phase.get(section)


def get_paths_for_phase(phase: str) -> List[str]:
    """
    Get all state paths owned by a phase.

    Args:
        phase: Phase name

    Returns:
        List of state paths
    """
    return PHASE_OWNERSHIP.get(phase, [])


def get_dependencies(phase: str) -> List[str]:
    """
    Get the phases that must be complete before this phase can start.

    Args:
        phase: Phase name

    Returns:
        List of dependency phase names
    """
    return PHASE_DEPENDENCIES.get(phase, [])


def get_downstream(phase: str) -> List[str]:
    """
    Get phases that depend on (are downstream of) this phase.

    Args:
        phase: Phase name

    Returns:
        List of downstream phase names
    """
    return DOWNSTREAM_PHASES.get(phase, [])


def get_all_downstream(phase: str) -> Set[str]:
    """
    Get all phases downstream of this phase (transitive closure).

    Args:
        phase: Phase name

    Returns:
        Set of all downstream phase names
    """
    result = set()
    to_process = [phase]

    while to_process:
        current = to_process.pop()
        for downstream in DOWNSTREAM_PHASES.get(current, []):
            if downstream not in result:
                result.add(downstream)
                to_process.append(downstream)

    return result


def get_phase_index(phase: str) -> int:
    """
    Get the index of a phase in the ordered phase list.

    Args:
        phase: Phase name

    Returns:
        Index (0-based), or -1 if not found
    """
    try:
        return PHASE_ORDER.index(phase)
    except ValueError:
        return -1


def is_upstream_of(phase_a: str, phase_b: str) -> bool:
    """
    Check if phase_a is upstream of (comes before and affects) phase_b.

    Args:
        phase_a: First phase
        phase_b: Second phase

    Returns:
        True if phase_a is upstream of phase_b
    """
    return phase_b in get_all_downstream(phase_a)
