"""
Metric polarity configuration for delta direction computation.

Defines whether higher or lower values are "better" for each tracked metric.
Used by EnrichedDelta to compute direction: "improved" | "degraded" | "neutral"

This enables the design spiral to provide meaningful feedback:
- "GM increased from 0.4m to 0.6m — IMPROVED"
- "Resistance increased from 50kN to 60kN — DEGRADED"

Reference: MAGNET_Merge_Implementation_Plan.md Phase 4
"""

from typing import Dict


# =============================================================================
# DIRECTION POLARITY — Complete list of all tracked metrics
# =============================================================================

DIRECTION_POLARITY: Dict[str, str] = {
    # ═══════════════════════════════════════════════════════════════════════════
    # STABILITY — Higher is better (more stable)
    # ═══════════════════════════════════════════════════════════════════════════
    "stability.gm_m": "higher_is_better",
    "stability.gm_transverse_m": "higher_is_better",
    "stability.bm_m": "higher_is_better",
    "stability.bm_transverse_m": "higher_is_better",
    "stability.kb_m": "higher_is_better",
    "stability.gz_max": "higher_is_better",
    "stability.range_positive_gz_deg": "higher_is_better",
    "stability.angle_max_gz_deg": "neutral",  # Design-dependent
    "stability.downflooding_angle_deg": "higher_is_better",
    "stability.vanishing_angle_deg": "higher_is_better",
    "gm_m": "higher_is_better",  # Alias without prefix
    "bm_m": "higher_is_better",  # Alias without prefix
    "kb_m": "higher_is_better",  # Alias without prefix

    # ═══════════════════════════════════════════════════════════════════════════
    # RESISTANCE — Lower is better (less drag)
    # ═══════════════════════════════════════════════════════════════════════════
    "resistance.total_kn": "lower_is_better",
    "resistance.total_resistance_kn": "lower_is_better",
    "resistance.frictional_kn": "lower_is_better",
    "resistance.wave_kn": "lower_is_better",
    "resistance.appendage_kn": "lower_is_better",
    "resistance.air_kn": "lower_is_better",
    "resistance.residuary_kn": "lower_is_better",
    "resistance_kn": "lower_is_better",  # Alias without prefix

    # ═══════════════════════════════════════════════════════════════════════════
    # PERFORMANCE — Higher is better
    # ═══════════════════════════════════════════════════════════════════════════
    "performance.max_speed_kts": "higher_is_better",
    "performance.cruise_speed_kts": "higher_is_better",
    "performance.range_nm": "higher_is_better",
    "performance.endurance_hours": "higher_is_better",
    "performance.propulsive_efficiency": "higher_is_better",
    "max_speed_kts": "higher_is_better",
    "range_nm": "higher_is_better",

    # ═══════════════════════════════════════════════════════════════════════════
    # WEIGHT — Lower is better (lighter is generally better)
    # ═══════════════════════════════════════════════════════════════════════════
    "weight.lightship_kg": "lower_is_better",
    "weight.lightship_mt": "lower_is_better",
    "weight.structural_kg": "lower_is_better",
    "weight.outfit_kg": "lower_is_better",
    "weight.machinery_kg": "lower_is_better",
    "weight.deadweight_mt": "neutral",  # Design-dependent (cargo capacity)
    "weight.displacement_mt": "neutral",  # Design-dependent
    "lightship_kg": "lower_is_better",

    # ═══════════════════════════════════════════════════════════════════════════
    # COST — Lower is better
    # ═══════════════════════════════════════════════════════════════════════════
    "cost.build_usd": "lower_is_better",
    "cost.annual_operating_usd": "lower_is_better",
    "cost.fuel_per_nm_usd": "lower_is_better",
    "cost.crew_cost_annual_usd": "lower_is_better",
    "cost.maintenance_annual_usd": "lower_is_better",
    "cost.total_lifecycle_usd": "lower_is_better",
    "build_cost_usd": "lower_is_better",

    # ═══════════════════════════════════════════════════════════════════════════
    # HULL GEOMETRY — Mostly neutral (design-dependent)
    # ═══════════════════════════════════════════════════════════════════════════
    "hull.displacement_m3": "neutral",  # Design-dependent
    "hull.wetted_surface_m2": "lower_is_better",  # Less drag
    "hull.waterplane_area_m2": "neutral",  # Design-dependent
    "hull.loa": "neutral",  # Design-dependent
    "hull.beam": "neutral",  # Design-dependent
    "hull.draft": "neutral",  # Design-dependent
    "hull.depth": "neutral",  # Design-dependent
    "hull.cb": "neutral",  # Block coefficient
    "hull.cp": "neutral",  # Prismatic coefficient
    "hull.cm": "neutral",  # Midship coefficient
    "hull.cwp": "neutral",  # Waterplane coefficient

    # ═══════════════════════════════════════════════════════════════════════════
    # CAPACITY — Higher is better (more capacity)
    # ═══════════════════════════════════════════════════════════════════════════
    "capacity.cargo_m3": "higher_is_better",
    "capacity.passengers": "higher_is_better",
    "capacity.fuel_l": "higher_is_better",
    "capacity.freshwater_l": "higher_is_better",
    "capacity.crew_berthed": "neutral",  # Design-dependent
    "cargo_m3": "higher_is_better",
    "passengers": "higher_is_better",

    # ═══════════════════════════════════════════════════════════════════════════
    # COMPLIANCE — Higher/True is better
    # ═══════════════════════════════════════════════════════════════════════════
    "compliance.marpol_compliant": "higher_is_better",  # True = 1, False = 0
    "compliance.solas_compliant": "higher_is_better",
    "compliance.class_notation_met": "higher_is_better",
    "compliance.freeboard_margin_m": "higher_is_better",

    # ═══════════════════════════════════════════════════════════════════════════
    # PROPULSION — Efficiency higher is better
    # ═══════════════════════════════════════════════════════════════════════════
    "propulsion.propulsive_efficiency": "higher_is_better",
    "propulsion.total_installed_power_kw": "neutral",  # Design-dependent
    "propulsion.sfc_g_kwh": "lower_is_better",  # Specific fuel consumption
    "propulsion.fuel_consumption_lph": "lower_is_better",

    # ═══════════════════════════════════════════════════════════════════════════
    # STRUCTURAL — Higher strength/margin is better
    # ═══════════════════════════════════════════════════════════════════════════
    "structural.safety_factor": "higher_is_better",
    "structural.yield_margin": "higher_is_better",
    "structural.fatigue_life_years": "higher_is_better",
    "structural.corrosion_allowance_mm": "higher_is_better",

    # ═══════════════════════════════════════════════════════════════════════════
    # SEAKEEPING — Better motion characteristics
    # ═══════════════════════════════════════════════════════════════════════════
    "seakeeping.roll_period_s": "neutral",  # Design-dependent
    "seakeeping.pitch_period_s": "neutral",  # Design-dependent
    "seakeeping.roll_damping_ratio": "higher_is_better",
    "seakeeping.msi_percent": "lower_is_better",  # Motion Sickness Index
    "seakeeping.operability_percent": "higher_is_better",
}


def get_direction(parameter: str, delta: float) -> str:
    """
    Compute direction string for a metric change.

    Args:
        parameter: The parameter path (e.g., "stability.gm_m")
        delta: The change in value (new - old)

    Returns:
        "improved" — Change is in the desirable direction
        "degraded" — Change is in the undesirable direction
        "neutral" — No preference or design-dependent
    """
    # Normalize path (remove common prefixes)
    normalized = parameter
    for prefix in ["validation.", "computed.", "hull.", "stability.", "resistance."]:
        if normalized.startswith(prefix):
            # Try both with and without prefix
            break

    # Look up polarity
    polarity = DIRECTION_POLARITY.get(parameter)
    if polarity is None:
        polarity = DIRECTION_POLARITY.get(normalized, "neutral")

    # Handle zero/near-zero deltas
    if abs(delta) < 1e-9:
        return "neutral"

    # Compute direction based on polarity
    if polarity == "higher_is_better":
        return "improved" if delta > 0 else "degraded"
    elif polarity == "lower_is_better":
        return "improved" if delta < 0 else "degraded"
    else:
        return "neutral"


def get_polarity(parameter: str) -> str:
    """
    Get the polarity configuration for a parameter.
    
    Returns:
        "higher_is_better", "lower_is_better", or "neutral"
    """
    return DIRECTION_POLARITY.get(parameter, "neutral")


def format_direction(direction: str) -> str:
    """
    Format direction for display.
    
    Returns emoji + text representation.
    """
    if direction == "improved":
        return "✅ improved"
    elif direction == "degraded":
        return "⚠️ degraded"
    else:
        return "➡️ changed"

