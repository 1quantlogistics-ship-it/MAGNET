"""
MAGNET Built-in Validators

Module 04 v1.2 - Production-Ready

Registry of built-in validator definitions.

v1.1: FIX #2 - All parameter names normalized to Section 1 conventions.
v1.2: Updated stability validators with:
      - hull.bmt → hull.bm_m (hydrostatics v1.2 output)
      - stability.kg_m for weight integration (KG sourcing priority)
      - Explicit m-rad units for GZ area fields
      - Extended validator outputs

# =============================================================================
# VALIDATOR IMPLEMENTATION STATUS
#
# These define ALL validators in the MAGNET system. Not all have implementations.
# Validators without implementations return ValidatorState.NOT_IMPLEMENTED.
#
# Implemented validators (12):
#   - physics/hydrostatics, physics/resistance
#   - stability/intact_gm, stability/gz_curve, stability/damage, stability/weather_criterion
#   - weight/estimation, compliance/regulatory
#   - arrangement/generator, loading/computer
#   - production/planning, cost/estimation
#
# NOT_IMPLEMENTED validators (16) - definitions retained for topology integrity:
#   - bounds/hull_parameters, bounds/mission_parameters, bounds/weight_margins, bounds/design_intent
#   - physics/powering, physics/structural_loads, physics/scantlings
#   - class/abs_hsv, class/dnv_hslc, class/uscg_subchapter_t
#   - production/plate_nesting, production/weld_accessibility
#   - weight/stability_check, compliance/stability
#   - optimization/design, reporting/generator
#
# These definitions are retained because:
#   1. Topology edges reference them for dependency management
#   2. NOT_IMPLEMENTED state provides clear feedback to users
#   3. They serve as placeholders for future implementation
# =============================================================================
"""

from typing import Dict, List, Optional

from .taxonomy import (
    ValidatorDefinition,
    ValidatorCategory,
    ValidatorPriority,
    ResultSeverity,
    ResourceRequirements,
    GateRequirement,
)


# =============================================================================
# PHYSICS VALIDATORS (FIX #2: Normalized parameter names)
# =============================================================================

PHYSICS_VALIDATORS = [
    ValidatorDefinition(
        validator_id="physics/hydrostatics",
        name="Hydrostatics Calculator",
        description="Computes displacement, centers, stability parameters (v1.2)",
        category=ValidatorCategory.PHYSICS,
        priority=ValidatorPriority.CRITICAL,
        phase="hull",  # Canonical name (not "hull_form")
        is_gate_condition=True,
        gate_requirement=GateRequirement.REQUIRED,  # v1.1: MUST pass for hull phase
        # v1.2: Extended input parameters
        depends_on_parameters=[
            "hull.loa", "hull.lwl", "hull.beam", "hull.depth", "hull.draft",
            "hull.cb", "hull.cp", "hull.cm", "hull.cwp",
            "hull.hull_type", "hull.deadrise_deg"
        ],
        # v1.2: Updated from 5 to 11 outputs
        produces_parameters=[
            "hull.displacement_m3",      # Displaced volume
            "hull.kb_m",                 # NEW v1.2: Center of buoyancy height
            "hull.bm_m",                 # NEW v1.2: Metacentric radius
            "hull.lcb_from_ap_m",        # Longitudinal center of buoyancy
            "hull.vcb_m",                # Vertical center of buoyancy
            "hull.tpc",                  # NEW v1.2: Tonnes per cm immersion
            "hull.mct",                  # NEW v1.2: Moment to change trim 1cm
            "hull.lcf_from_ap_m",        # NEW v1.2: Longitudinal center of flotation
            "hull.waterplane_area_m2",   # Waterplane area
            "hull.wetted_surface_m2",    # Wetted surface area
            "hull.freeboard",            # NEW v1.2: Freeboard at midship
        ],
        timeout_seconds=120,
        resource_requirements=ResourceRequirements(cpu_cores=2, ram_gb=1.0),
        tags=["core", "hull", "buoyancy", "v1.2"],
    ),

    ValidatorDefinition(
        validator_id="physics/resistance",
        name="Resistance Prediction",
        description="Calculates hull resistance using Holtrop-Mennen or similar",
        category=ValidatorCategory.PHYSICS,
        priority=ValidatorPriority.CRITICAL,
        phase="hull",  # Canonical name (not "hull_form")
        is_gate_condition=True,
        gate_requirement=GateRequirement.REQUIRED,  # v1.1: MUST pass for hull phase
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
        phase="hull",  # Canonical name (not "hull_form")
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
# STABILITY VALIDATORS (v1.2: Updated parameter names and outputs)
# =============================================================================

STABILITY_VALIDATORS = [
    ValidatorDefinition(
        validator_id="stability/intact_gm",
        name="Intact GM Calculator",
        description="Calculates metacentric height for intact stability (v1.2)",
        category=ValidatorCategory.STABILITY,
        priority=ValidatorPriority.CRITICAL,
        phase="stability",
        is_gate_condition=True,
        gate_requirement=GateRequirement.REQUIRED,  # v1.1: MUST pass for stability phase
        depends_on_validators=["physics/hydrostatics"],
        # v1.2: hull.bmt → hull.bm_m
        # Note: stability.kg_m is optional - validator falls back to weight.lightship_vcg_m
        depends_on_parameters=[
            "hull.kb_m", "hull.bm_m", "hull.displacement_mt",
            "weight.lightship_vcg_m"  # Primary KG source (fallback to estimate if missing)
        ],
        # v1.2: Extended outputs - matches stability/validators.py IntactGMValidator
        produces_parameters=[
            "stability.gm_transverse_m",  # GM (canonical name for contracts)
            "stability.gm_corrected_m",   # GM corrected for FSC
            "stability.kg_m",             # Vertical center of gravity
            "stability.kb_m",             # Vertical center of buoyancy
            "stability.bm_m",             # Metacentric radius
        ],
        timeout_seconds=60,
        tags=["stability", "intact", "v1.2"],
    ),

    ValidatorDefinition(
        validator_id="stability/gz_curve",
        name="GZ Curve Generator",
        description="Generates righting arm curve with IMO criteria (v1.2)",
        category=ValidatorCategory.STABILITY,
        priority=ValidatorPriority.HIGH,
        phase="stability",
        is_gate_condition=True,
        depends_on_validators=["stability/intact_gm", "physics/hydrostatics"],
        depends_on_parameters=[
            "stability.gm_transverse_m", "hull.bm_m", "hull.beam", "hull.freeboard"
        ],
        # v1.2 FIX #2: Explicit m-rad units for area fields
        produces_parameters=[
            "stability.gz_curve",           # List of GZPoint
            "stability.gz_max_m",           # Maximum GZ
            "stability.gz_30_m",            # GZ at 30°
            "stability.angle_gz_max_deg",   # Angle of GZmax
            "stability.angle_vanishing_deg",  # Vanishing angle
            "stability.range_deg",          # Range of stability
            "stability.area_0_30_m_rad",    # Area 0-30° (m-rad)
            "stability.area_0_40_m_rad",    # Area 0-40° (m-rad)
            "stability.area_30_40_m_rad",   # Area 30-40° (m-rad)
            "stability.passes_gz_criteria",  # All 5 IMO criteria
        ],
        timeout_seconds=120,
        resource_requirements=ResourceRequirements(cpu_cores=2, ram_gb=1.5),
        tags=["stability", "gz", "imo", "v1.2"],
    ),

    ValidatorDefinition(
        validator_id="stability/damage",
        name="Damage Stability Analysis",
        description="Evaluates stability under 4 standard damage cases (v1.2)",
        category=ValidatorCategory.STABILITY,
        priority=ValidatorPriority.HIGH,
        phase="stability",
        is_gate_condition=True,
        # Note: depends on gz_curve because it needs stability.gz_max_m
        depends_on_validators=["stability/gz_curve"],
        depends_on_parameters=[
            "hull.displacement_mt",
            "stability.gm_transverse_m", "stability.gz_max_m"
        ],
        # v1.2: Extended damage outputs
        produces_parameters=[
            "stability.damage_cases_evaluated",  # Number of cases
            "stability.damage_all_pass",         # All cases pass
            "stability.damage_worst_case",       # ID of worst case
            "stability.damage_results",          # Full results dict
        ],
        timeout_seconds=300,
        resource_requirements=ResourceRequirements(cpu_cores=4, ram_gb=4.0),
        tags=["stability", "damage", "compliance", "v1.2"],
    ),

    ValidatorDefinition(
        validator_id="stability/weather_criterion",
        name="Weather Criterion Check",
        description="IMO severe wind and rolling criterion (v1.2)",
        category=ValidatorCategory.STABILITY,
        priority=ValidatorPriority.NORMAL,
        phase="stability",
        is_gate_condition=True,
        gate_severity=ResultSeverity.WARNING,  # Advisory
        depends_on_validators=["stability/gz_curve"],
        depends_on_parameters=[
            "hull.beam", "hull.draft", "hull.displacement_mt",
            "stability.gm_transverse_m", "stability.gz_curve",
            "hull.projected_lateral_area_m2",
            "hull.height_of_wind_pressure_m"
        ],
        # v1.2: Weather criterion outputs
        produces_parameters=[
            "stability.weather_area_a_m_rad",   # Heeling energy
            "stability.weather_area_b_m_rad",   # Righting energy
            "stability.weather_ratio",          # b/a ratio
            "stability.weather_passes",         # Passes criterion
        ],
        timeout_seconds=60,
        tags=["stability", "imo", "weather", "v1.2"],
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
        validator_id="production/planning",
        name="Production Planning",
        description="Generate material takeoff, assembly sequence, and build schedule (v1.1)",
        category=ValidatorCategory.PRODUCTION,
        priority=ValidatorPriority.LOW,
        phase="production",
        is_gate_condition=False,
        depends_on_parameters=[
            "hull.lwl", "hull.beam", "hull.depth",
            "structure.material", "structure.frame_spacing_mm",
        ],
        produces_parameters=[
            "production.material_takeoff",
            "production.assembly_sequence",
            "production.build_schedule",
            "production.summary",
        ],
        timeout_seconds=120,
        resource_requirements=ResourceRequirements(cpu_cores=1, ram_gb=0.5),
        tags=["production", "planning", "material", "schedule", "v1.1"],
    ),

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
# WEIGHT VALIDATORS (v1.1)
# =============================================================================

WEIGHT_VALIDATORS = [
    ValidatorDefinition(
        validator_id="weight/estimation",
        name="Parametric Weight Estimator",
        description="SWBS parametric weight estimation (v1.1)",
        category=ValidatorCategory.WEIGHT,
        priority=ValidatorPriority.HIGH,
        phase="weight",
        is_gate_condition=True,
        depends_on_validators=["physics/hydrostatics"],
        depends_on_parameters=[
            "hull.lwl", "hull.beam", "hull.depth", "hull.draft", "hull.cb",
            "propulsion.installed_power_kw", "propulsion.number_of_engines",
            "mission.crew_size", "mission.passengers", "mission.vessel_type",
        ],
        produces_parameters=[
            "weight.lightship_mt", "weight.lightship_lcg_m",
            "weight.lightship_vcg_m", "weight.lightship_tcg_m",
            "weight.group_100_mt", "weight.group_200_mt",
            "weight.group_300_mt", "weight.group_400_mt",
            "weight.group_500_mt", "weight.group_600_mt",
            "weight.margin_mt", "weight.average_confidence",
            "weight.summary_data",
        ],
        timeout_seconds=120,
        resource_requirements=ResourceRequirements(cpu_cores=1, ram_gb=0.5),
        tags=["weight", "swbs", "parametric", "v1.1"],
    ),

    ValidatorDefinition(
        validator_id="weight/stability_check",
        name="Weight-Stability Compatibility",
        description="Validates weight for stability and writes KG (v1.1)",
        category=ValidatorCategory.WEIGHT,
        priority=ValidatorPriority.HIGH,
        phase="weight",
        is_gate_condition=True,
        depends_on_validators=["weight/estimation", "physics/hydrostatics"],
        depends_on_parameters=[
            "weight.lightship_vcg_m", "weight.lightship_mt",
            "hull.displacement_mt", "hull.kb_m", "hull.bm_m",
        ],
        produces_parameters=[
            "weight.estimated_gm_m",
            "weight.stability_ready",
            "stability.kg_m",  # NEW v1.1
        ],
        timeout_seconds=30,
        resource_requirements=ResourceRequirements(cpu_cores=1, ram_gb=0.2),
        tags=["weight", "stability", "v1.1"],
    ),
]


# =============================================================================
# ARRANGEMENT VALIDATORS (v1.1)
# =============================================================================

ARRANGEMENT_VALIDATORS = [
    ValidatorDefinition(
        validator_id="arrangement/generator",
        name="General Arrangement Generator",
        description="Generates parametric general arrangement with tanks and compartments (v1.1)",
        category=ValidatorCategory.ARRANGEMENT,
        priority=ValidatorPriority.HIGH,
        phase="arrangement",
        is_gate_condition=True,
        depends_on_validators=["physics/hydrostatics"],
        depends_on_parameters=[
            "hull.lwl", "hull.beam", "hull.depth", "hull.draft",
            "mission.range_nm", "mission.crew_size", "mission.vessel_type",
            "mission.endurance_days", "propulsion.installed_power_kw",
        ],
        produces_parameters=[
            "arrangement.data",
            "arrangement.compartment_count",
            "arrangement.collision_bulkhead_m",
            "arrangement.tanks",
            "arrangement.compartments",
            "arrangement.tank_summary",
        ],
        timeout_seconds=60,
        resource_requirements=ResourceRequirements(cpu_cores=1, ram_gb=0.5),
        tags=["arrangement", "tanks", "compartments", "v1.1"],
    ),
]


# =============================================================================
# LOADING VALIDATORS (v1.1)
# =============================================================================

LOADING_VALIDATORS = [
    ValidatorDefinition(
        validator_id="loading/computer",
        name="Loading Computer",
        description="Calculates loading conditions with stability checks (v1.1)",
        category=ValidatorCategory.LOADING,
        priority=ValidatorPriority.HIGH,
        phase="loading",
        is_gate_condition=True,
        depends_on_validators=["weight/estimation", "arrangement/generator", "physics/hydrostatics"],
        depends_on_parameters=[
            "weight.lightship_mt", "weight.lightship_lcg_m", "weight.lightship_vcg_m",
            "hull.depth", "hull.lwl", "hull.draft", "hull.tpc", "hull.mct",
            "hull.kb_m", "hull.bm_m", "hull.displacement_mt",
            "arrangement.tanks", "mission.crew_size",
        ],
        produces_parameters=[
            "loading.full_load_departure",
            "loading.full_load_arrival",
            "loading.minimum_operating",
            "loading.lightship",
            "loading.all_conditions_pass",
            "loading.worst_case_gm_m",
            "loading.worst_case_condition",
            "stability.kg_m",  # Updated from worst loading condition
        ],
        timeout_seconds=120,
        resource_requirements=ResourceRequirements(cpu_cores=1, ram_gb=0.5),
        tags=["loading", "stability", "deadweight", "v1.1"],
    ),
]


# =============================================================================
# COMPLIANCE VALIDATORS (v1.1)
# =============================================================================

COMPLIANCE_VALIDATORS = [
    ValidatorDefinition(
        validator_id="compliance/regulatory",
        name="Regulatory Compliance Engine",
        description="Evaluates design against ABS HSNC, HSC Code, USCG rules (v1.1)",
        category=ValidatorCategory.REGULATORY,
        priority=ValidatorPriority.HIGH,
        phase="compliance",
        is_gate_condition=True,
        depends_on_validators=["stability/intact_gm", "stability/gz_curve"],
        depends_on_parameters=[
            "hull.lwl", "hull.beam", "mission.vessel_type",
            "stability.gm_transverse_m", "stability.gz_max_m", "stability.angle_of_max_gz_deg",
            "stability.area_0_30_m_rad", "stability.area_0_40_m_rad", "stability.area_30_40_m_rad",
        ],
        produces_parameters=[
            "compliance.status",
            "compliance.pass_count",
            "compliance.fail_count",
            "compliance.incomplete_count",
            "compliance.findings",
            "compliance.report",
            "compliance.frameworks_checked",
            "compliance.pass_rate",
        ],
        timeout_seconds=120,
        resource_requirements=ResourceRequirements(cpu_cores=1, ram_gb=0.5),
        tags=["compliance", "regulatory", "abs", "hsc", "uscg", "v1.1"],
    ),

    ValidatorDefinition(
        validator_id="compliance/stability",
        name="Stability Compliance Check",
        description="Focused stability rules compliance check (v1.1)",
        category=ValidatorCategory.REGULATORY,
        priority=ValidatorPriority.NORMAL,
        phase="compliance",
        is_gate_condition=False,
        depends_on_validators=["stability/gz_curve"],
        depends_on_parameters=[
            "stability.gm_transverse_m", "stability.gz_max_m",
        ],
        produces_parameters=[
            "compliance.stability_status",
            "compliance.stability_pass_count",
            "compliance.stability_fail_count",
        ],
        timeout_seconds=60,
        resource_requirements=ResourceRequirements(cpu_cores=1, ram_gb=0.2),
        tags=["compliance", "stability", "v1.1"],
    ),
]


# =============================================================================
# COST VALIDATORS (v1.1)
# =============================================================================

COST_VALIDATORS = [
    ValidatorDefinition(
        validator_id="cost/estimation",
        name="Cost Estimation Engine",
        description="Generates comprehensive cost estimate for vessel design (v1.1)",
        category=ValidatorCategory.ECONOMICS,
        priority=ValidatorPriority.NORMAL,
        phase="cost",
        is_gate_condition=False,
        depends_on_validators=["production/planning", "weight/estimation"],
        depends_on_parameters=[
            "hull.lwl", "hull.beam", "hull.depth",
            "propulsion.installed_power_kw",
            "structure.material",
            "mission.vessel_type", "mission.crew_size",
        ],
        produces_parameters=[
            "cost.estimate",
            "cost.total_price",
            "cost.acquisition_cost",
            "cost.lifecycle_npv",
            "cost.subtotal_material",
            "cost.subtotal_labor",
            "cost.subtotal_equipment",
            "cost.summary",
            "cost.confidence",
        ],
        timeout_seconds=60,
        resource_requirements=ResourceRequirements(cpu_cores=1, ram_gb=0.25),
        tags=["cost", "economics", "estimation", "v1.1"],
    ),
]


# =============================================================================
# OPTIMIZATION VALIDATORS (v1.1)
# =============================================================================

OPTIMIZATION_VALIDATORS = [
    ValidatorDefinition(
        validator_id="optimization/design",
        name="Design Optimization",
        description="Multi-objective design optimization using NSGA-II (v1.1)",
        category=ValidatorCategory.OPTIMIZATION,
        priority=ValidatorPriority.LOW,
        phase="optimization",
        is_gate_condition=False,
        depends_on_validators=["cost/estimation"],
        depends_on_parameters=[
            "hull.lwl", "hull.beam", "hull.depth",
            "cost.total_price", "weight.lightship_mt",
        ],
        produces_parameters=[
            "optimization.problem",
            "optimization.result",
            "optimization.pareto_front",
            "optimization.selected_solution",
            "optimization.status",
            "optimization.iterations",
            "optimization.evaluations",
            "optimization.metrics",
        ],
        timeout_seconds=600,
        resource_requirements=ResourceRequirements(cpu_cores=2, ram_gb=1.0),
        tags=["optimization", "nsga-ii", "pareto", "multi-objective", "v1.1"],
    ),
]


# =============================================================================
# REPORTING VALIDATORS (v1.1)
# =============================================================================

REPORTING_VALIDATORS = [
    ValidatorDefinition(
        validator_id="reporting/generator",
        name="Report Generator",
        description="Generates design, compliance, cost, and full reports (v1.1)",
        category=ValidatorCategory.REPORTING,
        priority=ValidatorPriority.LOW,
        phase="reporting",
        is_gate_condition=False,
        depends_on_validators=["compliance/regulatory", "cost/estimation"],
        depends_on_parameters=[
            "hull.lwl", "hull.beam", "hull.depth", "hull.draft",
            "mission.vessel_type", "mission.max_speed_kts",
            "compliance.status", "cost.total_price",
        ],
        produces_parameters=[
            "reporting.available_types",
            "reporting.generated_reports",
            "reporting.last_report_type",
            "reporting.design_summary",
        ],
        timeout_seconds=60,
        resource_requirements=ResourceRequirements(cpu_cores=1, ram_gb=0.25),
        tags=["reporting", "export", "documentation", "v1.1"],
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
    PRODUCTION_VALIDATORS +
    WEIGHT_VALIDATORS +
    ARRANGEMENT_VALIDATORS +
    LOADING_VALIDATORS +
    COMPLIANCE_VALIDATORS +
    COST_VALIDATORS +
    OPTIMIZATION_VALIDATORS +
    REPORTING_VALIDATORS
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
