"""
MAGNET Built-in Validators

Module 04 v1.1 - Production-Ready

Registry of built-in validator definitions.

v1.1: FIX #2 - All parameter names normalized to Section 1 conventions.
"""

from typing import Dict, List, Optional

from .taxonomy import (
    ValidatorDefinition,
    ValidatorCategory,
    ValidatorPriority,
    ResultSeverity,
    ResourceRequirements,
)


# =============================================================================
# PHYSICS VALIDATORS (FIX #2: Normalized parameter names)
# =============================================================================

PHYSICS_VALIDATORS = [
    ValidatorDefinition(
        validator_id="physics/hydrostatics",
        name="Hydrostatics Calculator",
        description="Computes displacement, LCB, VCB, waterplane area, coefficients",
        category=ValidatorCategory.PHYSICS,
        priority=ValidatorPriority.CRITICAL,
        phase="hull_form",
        is_gate_condition=True,
        # FIX #2: Use Section 1 field names
        depends_on_parameters=[
            "hull.loa", "hull.beam", "hull.depth", "hull.draft",
            "hull.cb", "hull.cp", "hull.cwp"
        ],
        # FIX #3: Outputs for implicit dependency edges
        produces_parameters=[
            "hull.displacement_m3", "hull.lcb_from_ap_m", "hull.vcb_m",
            "hull.waterplane_area_m2", "hull.wetted_surface_m2"
        ],
        timeout_seconds=120,
        resource_requirements=ResourceRequirements(cpu_cores=2, ram_gb=1.0),
        tags=["core", "hull", "buoyancy"],
    ),

    ValidatorDefinition(
        validator_id="physics/resistance",
        name="Resistance Prediction",
        description="Calculates hull resistance using Holtrop-Mennen or similar",
        category=ValidatorCategory.PHYSICS,
        priority=ValidatorPriority.CRITICAL,
        phase="hull_form",
        is_gate_condition=True,
        depends_on_validators=["physics/hydrostatics"],
        depends_on_parameters=[
            "hull.loa", "hull.beam", "hull.draft",
            "hull.displacement_m3", "mission.max_speed_kts"
        ],
        produces_parameters=[
            "resistance.total_resistance_kn", "resistance.froude_number",
            "resistance.reynolds_number"
        ],
        timeout_seconds=180,
        resource_requirements=ResourceRequirements(cpu_cores=2, ram_gb=2.0),
        tags=["core", "hull", "propulsion"],
    ),

    ValidatorDefinition(
        validator_id="physics/powering",
        name="Power Requirements",
        description="Calculates required shaft power from resistance",
        category=ValidatorCategory.PHYSICS,
        priority=ValidatorPriority.HIGH,
        phase="propulsion",
        is_gate_condition=True,
        depends_on_validators=["physics/resistance"],
        depends_on_parameters=[
            "resistance.total_resistance_kn",
            "propulsion.propulsive_efficiency",
            "mission.max_speed_kts"
        ],
        produces_parameters=[
            "performance.design_power_kw"
        ],
        timeout_seconds=60,
        tags=["propulsion", "power"],
    ),

    ValidatorDefinition(
        validator_id="physics/structural_loads",
        name="Structural Load Calculator",
        description="Computes bending moments, shear forces, slamming pressures",
        category=ValidatorCategory.PHYSICS,
        priority=ValidatorPriority.HIGH,
        phase="structure",
        is_gate_condition=True,
        depends_on_validators=["physics/hydrostatics"],
        depends_on_parameters=[
            "hull.loa", "hull.displacement_m3",
            "structural_design.frame_spacing_mm"
        ],
        produces_parameters=[
            "structural_loads.slamming_pressure_kpa",
            "structural_loads.design_bending_moment_knm"
        ],
        timeout_seconds=300,
        resource_requirements=ResourceRequirements(cpu_cores=2, ram_gb=2.0),
        tags=["structure", "loads"],
    ),

    ValidatorDefinition(
        validator_id="physics/scantlings",
        name="Scantlings Calculator",
        description="Determines plate thickness, stiffener sizes per loads",
        category=ValidatorCategory.PHYSICS,
        priority=ValidatorPriority.HIGH,
        phase="structure",
        is_gate_condition=True,
        depends_on_validators=["physics/structural_loads"],
        depends_on_parameters=[
            "structural_design.hull_material",
            "structural_loads.slamming_pressure_kpa"
        ],
        produces_parameters=[
            "structural_design.bottom_plating_mm",
            "structural_design.side_plating_mm"
        ],
        timeout_seconds=300,
        resource_requirements=ResourceRequirements(cpu_cores=2, ram_gb=2.0),
        tags=["structure", "aluminum"],
    ),
]


# =============================================================================
# BOUNDS VALIDATORS (FIX #2: Normalized parameter names)
# =============================================================================

BOUNDS_VALIDATORS = [
    ValidatorDefinition(
        validator_id="bounds/hull_parameters",
        name="Hull Parameter Bounds",
        description="Checks hull dimensions against design intent constraints",
        category=ValidatorCategory.BOUNDS,
        priority=ValidatorPriority.CRITICAL,
        phase="hull_form",
        is_gate_condition=True,
        depends_on_parameters=[
            "hull.loa", "hull.beam", "hull.depth", "hull.draft"
        ],
        timeout_seconds=10,
        tags=["bounds", "hull"],
    ),

    ValidatorDefinition(
        validator_id="bounds/mission_parameters",
        name="Mission Parameter Bounds",
        description="Validates mission requirements are within feasible ranges",
        category=ValidatorCategory.BOUNDS,
        priority=ValidatorPriority.CRITICAL,
        phase="mission",
        is_gate_condition=True,
        depends_on_parameters=[
            "mission.max_speed_kts", "mission.range_nm",
            "mission.crew_berthed", "mission.endurance_hours"
        ],
        timeout_seconds=10,
        tags=["bounds", "mission"],
    ),

    ValidatorDefinition(
        validator_id="bounds/weight_margins",
        name="Weight Margin Validator",
        description="Ensures weight estimates include required margins",
        category=ValidatorCategory.BOUNDS,
        priority=ValidatorPriority.NORMAL,
        phase="weight",
        is_gate_condition=True,
        depends_on_parameters=[
            "weight.lightship_weight_mt", "weight.deadweight_mt"
        ],
        timeout_seconds=10,
        tags=["bounds", "weight"],
    ),

    ValidatorDefinition(
        validator_id="bounds/design_intent",
        name="Design Intent Validator",
        description="Checks all parameters against DesignIntent constraints",
        category=ValidatorCategory.BOUNDS,
        priority=ValidatorPriority.CRITICAL,
        phase="mission",
        is_gate_condition=True,
        depends_on_parameters=[],  # Reads all from DesignIntent
        timeout_seconds=30,
        tags=["bounds", "constraints", "design_intent"],
    ),
]


# =============================================================================
# STABILITY VALIDATORS (FIX #2: Normalized parameter names)
# =============================================================================

STABILITY_VALIDATORS = [
    ValidatorDefinition(
        validator_id="stability/intact_gm",
        name="Intact GM Calculator",
        description="Calculates metacentric height for intact stability",
        category=ValidatorCategory.STABILITY,
        priority=ValidatorPriority.CRITICAL,
        phase="stability",
        is_gate_condition=True,
        depends_on_validators=["physics/hydrostatics"],
        depends_on_parameters=[
            "weight.lightship_weight_mt", "weight.lightship_vcg_m",
            "hull.bmt", "hull.vcb_m"
        ],
        produces_parameters=["stability.gm_transverse_m"],
        timeout_seconds=60,
        tags=["stability", "intact"],
    ),

    ValidatorDefinition(
        validator_id="stability/gz_curve",
        name="GZ Curve Generator",
        description="Generates righting arm curve across heel angles",
        category=ValidatorCategory.STABILITY,
        priority=ValidatorPriority.HIGH,
        phase="stability",
        is_gate_condition=True,
        depends_on_validators=["stability/intact_gm", "physics/hydrostatics"],
        depends_on_parameters=[
            "stability.gm_transverse_m", "hull.displacement_m3"
        ],
        produces_parameters=[
            "stability.gz_curve", "stability.gz_max_m",
            "stability.angle_of_max_gz_deg"
        ],
        timeout_seconds=120,
        resource_requirements=ResourceRequirements(cpu_cores=2, ram_gb=1.5),
        tags=["stability", "gz"],
    ),

    ValidatorDefinition(
        validator_id="stability/damage",
        name="Damage Stability Analysis",
        description="Evaluates stability under damaged conditions",
        category=ValidatorCategory.STABILITY,
        priority=ValidatorPriority.HIGH,
        phase="stability",
        is_gate_condition=True,
        depends_on_validators=["stability/gz_curve"],
        depends_on_parameters=[
            "stability.gz_curve", "arrangement.compartments"
        ],
        produces_parameters=["stability.damage_cases"],
        timeout_seconds=300,
        resource_requirements=ResourceRequirements(cpu_cores=4, ram_gb=4.0),
        tags=["stability", "damage", "compliance"],
    ),

    ValidatorDefinition(
        validator_id="stability/weather_criterion",
        name="Weather Criterion Check",
        description="IMO weather criterion (wind heeling vs GZ)",
        category=ValidatorCategory.STABILITY,
        priority=ValidatorPriority.NORMAL,
        phase="stability",
        is_gate_condition=True,
        gate_severity=ResultSeverity.WARNING,  # Advisory
        depends_on_validators=["stability/gz_curve"],
        depends_on_parameters=[
            "hull.loa", "environmental.design_wave_height_m"
        ],
        timeout_seconds=60,
        tags=["stability", "imo", "weather"],
    ),
]


# =============================================================================
# CLASS RULES VALIDATORS
# =============================================================================

CLASS_VALIDATORS = [
    ValidatorDefinition(
        validator_id="class/abs_hsv",
        name="ABS HSV Rules",
        description="American Bureau of Shipping High Speed Vessel rules",
        category=ValidatorCategory.CLASS_RULES,
        priority=ValidatorPriority.NORMAL,
        phase="compliance",
        is_gate_condition=True,
        depends_on_validators=[
            "physics/structural_loads", "physics/scantlings",
            "stability/intact_gm", "stability/damage"
        ],
        depends_on_parameters=[
            "structural_design.bottom_plating_mm",
            "structural_design.frame_spacing_mm"
        ],
        timeout_seconds=300,
        resource_requirements=ResourceRequirements(cpu_cores=2, ram_gb=2.0),
        tags=["class", "abs", "hsv"],
    ),

    ValidatorDefinition(
        validator_id="class/dnv_hslc",
        name="DNV HSLC Rules",
        description="DNV High Speed Light Craft classification rules",
        category=ValidatorCategory.CLASS_RULES,
        priority=ValidatorPriority.NORMAL,
        phase="compliance",
        is_gate_condition=True,
        depends_on_validators=[
            "physics/structural_loads", "physics/scantlings"
        ],
        timeout_seconds=300,
        tags=["class", "dnv", "hslc"],
    ),

    ValidatorDefinition(
        validator_id="class/uscg_subchapter_t",
        name="USCG Subchapter T",
        description="US Coast Guard small passenger vessel regulations",
        category=ValidatorCategory.REGULATORY,
        priority=ValidatorPriority.NORMAL,
        phase="compliance",
        is_gate_condition=True,
        depends_on_validators=["stability/damage"],
        depends_on_parameters=[
            "mission.passengers", "hull.loa"
        ],
        timeout_seconds=180,
        tags=["regulatory", "uscg", "passenger"],
    ),
]


# =============================================================================
# PRODUCTION VALIDATORS
# =============================================================================

PRODUCTION_VALIDATORS = [
    ValidatorDefinition(
        validator_id="production/plate_nesting",
        name="Plate Nesting Feasibility",
        description="Checks if plates can be nested on standard sheets",
        category=ValidatorCategory.PRODUCTION,
        priority=ValidatorPriority.LOW,
        phase="production",
        is_gate_condition=False,
        depends_on_validators=["physics/scantlings"],
        depends_on_parameters=[],
        timeout_seconds=120,
        tags=["production", "nesting"],
    ),

    ValidatorDefinition(
        validator_id="production/weld_accessibility",
        name="Weld Accessibility Check",
        description="Verifies welds are accessible for fabrication",
        category=ValidatorCategory.PRODUCTION,
        priority=ValidatorPriority.LOW,
        phase="production",
        is_gate_condition=False,
        depends_on_parameters=[
            "structural_design.frame_spacing_mm"
        ],
        timeout_seconds=60,
        tags=["production", "welding"],
    ),
]


# =============================================================================
# VALIDATOR REGISTRY
# =============================================================================

ALL_VALIDATORS = (
    PHYSICS_VALIDATORS +
    BOUNDS_VALIDATORS +
    STABILITY_VALIDATORS +
    CLASS_VALIDATORS +
    PRODUCTION_VALIDATORS
)


def get_all_validators() -> List[ValidatorDefinition]:
    """Get all built-in validator definitions."""
    return list(ALL_VALIDATORS)


def get_validators_for_phase(phase: str) -> List[ValidatorDefinition]:
    """Get validators for a specific phase."""
    return [v for v in ALL_VALIDATORS if v.phase == phase]


def get_gate_validators_for_phase(phase: str) -> List[ValidatorDefinition]:
    """Get gate condition validators for a phase."""
    return [v for v in ALL_VALIDATORS if v.phase == phase and v.is_gate_condition]


def get_validator_by_id(validator_id: str) -> Optional[ValidatorDefinition]:
    """Get a validator by its ID."""
    for v in ALL_VALIDATORS:
        if v.validator_id == validator_id:
            return v
    return None


# =============================================================================
# PARAMETER -> VALIDATOR MAPPING (FIX #3)
# =============================================================================

def build_parameter_to_producer_map() -> Dict[str, str]:
    """
    Build mapping from produced parameters to their producing validators.

    FIX #3: Used to create implicit dependency edges.
    """
    mapping = {}
    for v in ALL_VALIDATORS:
        for param in v.produces_parameters:
            mapping[param] = v.validator_id
    return mapping


PARAMETER_TO_PRODUCER = build_parameter_to_producer_map()


def get_producer_for_parameter(param: str) -> Optional[str]:
    """Get validator that produces a parameter."""
    return PARAMETER_TO_PRODUCER.get(param)
