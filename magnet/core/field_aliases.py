"""
MAGNET Field Aliases

Maps alternative field names to their canonical paths.
Provides normalization for consistent state access.
"""

from typing import Dict, Optional

# ==================== Field Alias Mapping ====================
# Format: "alias_path" -> "canonical_path"

FIELD_ALIASES: Dict[str, str] = {
    # Mission aliases
    "mission.max_speed_knots": "mission.max_speed_kts",
    "mission.cruise_speed_knots": "mission.cruise_speed_kts",
    "mission.economical_speed_knots": "mission.economical_speed_kts",
    "mission.range_nautical_miles": "mission.range_nm",
    "mission.crew": "mission.crew_berthed",
    "mission.pax": "mission.passengers",
    "mission.class_society": "mission.classification_society",

    # Hull aliases
    "hull.length": "hull.loa",
    "hull.length_overall": "hull.loa",
    "hull.length_waterline": "hull.lwl",
    "hull.breadth": "hull.beam",
    "hull.moulded_beam": "hull.beam",
    "hull.moulded_depth": "hull.depth",
    "hull.design_draft": "hull.draft",
    "hull.block_coefficient": "hull.cb",
    "hull.prismatic_coefficient": "hull.cp",
    "hull.midship_coefficient": "hull.cm",
    "hull.waterplane_coefficient": "hull.cwp",
    "hull.deadrise": "hull.deadrise_deg",
    "hull.deadrise_angle": "hull.deadrise_deg",
    "hull.displacement": "hull.displacement_m3",
    "hull.displacement_volume": "hull.displacement_m3",
    "hull.wetted_area": "hull.wetted_surface_m2",
    "hull.lcb": "hull.lcb_from_ap_m",
    "hull.kb": "hull.vcb_m",

    # Weight aliases
    "weight.lightship": "weight.lightship_weight_mt",
    "weight.displacement": "weight.full_load_displacement_mt",
    "weight.full_load": "weight.full_load_displacement_mt",
    "weight.dwt": "weight.deadweight_mt",
    "weight.deadweight": "weight.deadweight_mt",
    "weight.hull_weight": "weight.hull_structure_mt",
    "weight.machinery_weight": "weight.machinery_mt",
    "weight.lcg": "weight.lightship_lcg_m",
    "weight.vcg": "weight.lightship_vcg_m",
    "weight.kg": "weight.lightship_vcg_m",

    # Stability aliases
    "stability.gm": "stability.gm_transverse_m",
    "stability.gmt": "stability.gm_transverse_m",
    "stability.gml": "stability.gm_longitudinal_m",
    "stability.gz_max": "stability.gz_max_m",
    "stability.max_gz": "stability.gz_max_m",
    "stability.angle_gz_max": "stability.angle_of_max_gz_deg",
    "stability.vanishing_angle": "stability.angle_of_vanishing_stability_deg",
    "stability.kg": "stability.kg_m",
    "stability.kb": "stability.kb_m",
    "stability.bm": "stability.bm_m",

    # Propulsion aliases
    "propulsion.power": "propulsion.total_installed_power_kw",
    "propulsion.installed_power": "propulsion.total_installed_power_kw",
    "propulsion.engines": "propulsion.num_engines",
    "propulsion.propellers": "propulsion.num_propellers",
    "propulsion.prop_diameter": "propulsion.propeller_diameter_m",
    "propulsion.pitch": "propulsion.propeller_pitch_m",
    "propulsion.fuel_consumption": "propulsion.sfc_g_kwh",
    "propulsion.sfc": "propulsion.sfc_g_kwh",
    "propulsion.efficiency": "propulsion.propulsive_efficiency",

    # Structure aliases
    "structure": "structural_design",
    "structure.material": "structural_design.hull_material",
    "structure.hull_material": "structural_design.hull_material",
    "structure.bottom_plate": "structural_design.bottom_plating_mm",
    "structure.side_plate": "structural_design.side_plating_mm",
    "structure.deck_plate": "structural_design.deck_plating_mm",
    "structure.frame_spacing": "structural_design.frame_spacing_mm",
    "structural_design.material": "structural_design.hull_material",

    # Loads aliases
    "loads": "structural_loads",
    "loads.slamming": "structural_loads.slamming_pressure_kpa",
    "loads.design_acceleration": "structural_loads.design_vertical_acceleration_g",

    # Resistance aliases
    "resistance.total": "resistance.total_resistance_kn",
    "resistance.friction": "resistance.frictional_resistance_kn",
    "resistance.residual": "resistance.residuary_resistance_kn",
    "resistance.wave": "resistance.wave_resistance_kn",
    "resistance.air": "resistance.air_resistance_kn",
    "resistance.froude": "resistance.froude_number",
    "resistance.reynolds": "resistance.reynolds_number",

    # Performance aliases
    "performance.speed": "performance.design_speed_kts",
    "performance.power": "performance.design_power_kw",
    "performance.range": "performance.range_at_cruise_nm",
    "performance.endurance": "performance.endurance_at_cruise_hr",
    "performance.bollard": "performance.bollard_pull_kn",

    # Systems aliases
    "systems.electrical": "systems.electrical_load_kw",
    "systems.generator": "systems.generator_capacity_kw",
    "systems.fuel_capacity": "systems.fuel_tank_capacity_l",
    "systems.fw_capacity": "systems.fw_tank_capacity_l",
    "systems.freshwater": "systems.fw_tank_capacity_l",

    # Arrangement aliases
    "arrangement.fuel": "arrangement.total_fuel_capacity_l",
    "arrangement.freshwater": "arrangement.total_fw_capacity_l",
    "arrangement.ballast": "arrangement.total_ballast_capacity_l",
    "arrangement.decks": "arrangement.num_decks",

    # Environmental aliases
    "environment": "environmental",
    "environment.sea_state": "environmental.design_sea_state",
    "environment.wave_height": "environmental.design_wave_height_m",
    "environment.water_density": "environmental.water_density_kg_m3",
    "environmental.rho": "environmental.water_density_kg_m3",
    "environmental.density": "environmental.water_density_kg_m3",

    # Seakeeping aliases
    "seakeeping.roll": "seakeeping.roll_period_s",
    "seakeeping.pitch": "seakeeping.pitch_period_s",
    "seakeeping.roll_period": "seakeeping.roll_period_s",
    "seakeeping.pitch_period": "seakeeping.pitch_period_s",

    # Analysis aliases
    "analysis.operability": "analysis.operability_index",
    "analysis.roll": "analysis.roll_amplitude_deg",
    "analysis.pitch": "analysis.pitch_amplitude_deg",
    "analysis.msi": "analysis.msi_percent",
    "analysis.noise": "analysis.noise_level_db",

    # Safety aliases
    "safety.lifejackets": "safety.lifejackets",
    "safety.liferafts": "safety.num_liferafts",

    # Cost aliases
    "cost.total": "cost.total_cost",
    "cost.materials": "cost.material_cost",
    "cost.labor": "cost.labor_cost",

    # Production aliases
    "production.hours": "production.build_hours",
    "production.duration": "production.build_duration_days",

    # Deck equipment aliases
    "deck.anchor": "deck_equipment.anchor_weight_kg",
    "deck.windlass": "deck_equipment.windlass_type",
    "deck.cleats": "deck_equipment.cleats_count",

    # Outfitting aliases
    "outfitting.berths": "outfitting.berth_count",
    "outfitting.cabins": "outfitting.cabin_count",
    "outfitting.heads": "outfitting.head_count",

    # Vision aliases
    "geometry": "vision",
    "geometry.generated": "vision.geometry_generated",
    "geometry.mesh": "vision.mesh_valid",
    "geometry.vertices": "vision.vertex_count",

    # Compliance aliases
    "compliance.passed": "compliance.overall_passed",
    "compliance.status": "compliance.overall_passed",
}


def normalize_path(path: str) -> str:
    """
    Normalize a path by resolving aliases to canonical form.

    Args:
        path: Input path (may be alias or canonical)

    Returns:
        Canonical path
    """
    if path in FIELD_ALIASES:
        return FIELD_ALIASES[path]

    # Check for partial matches (prefix aliases)
    for alias, canonical in FIELD_ALIASES.items():
        if path.startswith(alias + "."):
            suffix = path[len(alias) + 1:]
            return f"{canonical}.{suffix}"

    return path


def is_alias(path: str) -> bool:
    """
    Check if a path is an alias (not canonical).

    Args:
        path: Path to check

    Returns:
        True if path is an alias
    """
    return path in FIELD_ALIASES


def get_canonical(path: str) -> str:
    """
    Get the canonical path for an alias.

    Args:
        path: Input path (may be alias or canonical)

    Returns:
        Canonical path
    """
    return normalize_path(path)


def get_alias(canonical_path: str) -> Optional[str]:
    """
    Get an alias for a canonical path (if one exists).

    Note: Returns first matching alias if multiple exist.

    Args:
        canonical_path: Canonical path

    Returns:
        Alias path if found, None otherwise
    """
    for alias, canonical in FIELD_ALIASES.items():
        if canonical == canonical_path:
            return alias
    return None


def list_aliases(prefix: Optional[str] = None) -> Dict[str, str]:
    """
    List all aliases, optionally filtered by prefix.

    Args:
        prefix: Optional prefix to filter by (e.g., 'mission')

    Returns:
        Dictionary of alias -> canonical mappings
    """
    if prefix is None:
        return dict(FIELD_ALIASES)

    return {
        alias: canonical
        for alias, canonical in FIELD_ALIASES.items()
        if alias.startswith(prefix + ".") or alias == prefix
    }


def get_all_paths_for_section(section: str) -> Dict[str, str]:
    """
    Get all valid paths (aliases and canonical) for a section.

    Args:
        section: Section name (e.g., 'mission', 'hull')

    Returns:
        Dictionary mapping all valid paths to their canonical form
    """
    result = {}

    # Add all aliases for this section
    for alias, canonical in FIELD_ALIASES.items():
        if alias.startswith(section + ".") or canonical.startswith(section + "."):
            result[alias] = canonical
            result[canonical] = canonical

    return result
