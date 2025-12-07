"""
MAGNET State Dataclasses

27 dataclasses representing all aspects of vessel design state.
Each dataclass includes to_dict() and from_dict() for serialization.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from magnet.core.enums import (
    VesselType,
    HullType,
    PropulsionType,
    MaterialType,
    ClassificationSociety,
    SeaState,
    LoadCondition,
    ComplianceStatus,
    StructuralZone,
)


# ==================== 1. MissionConfig ====================

@dataclass
class MissionConfig:
    """
    Mission requirements and operational parameters.
    Phase: mission
    """
    # Vessel classification
    vessel_type: Optional[str] = None  # VesselType enum value
    vessel_name: Optional[str] = None
    hull_number: Optional[str] = None

    # Speed requirements
    max_speed_kts: Optional[float] = None
    cruise_speed_kts: Optional[float] = None
    economical_speed_kts: Optional[float] = None

    # Range and endurance
    range_nm: Optional[float] = None
    endurance_hours: Optional[float] = None

    # Capacity
    crew_berthed: Optional[int] = None
    crew_day: Optional[int] = None
    passengers: Optional[int] = None
    passengers_seated: Optional[int] = None

    # Cargo
    cargo_capacity_mt: Optional[float] = None
    cargo_volume_m3: Optional[float] = None
    deck_cargo_area_m2: Optional[float] = None

    # Operational
    operating_area: Optional[str] = None
    design_sea_state: Optional[str] = None
    service_notation: Optional[str] = None

    # Classification
    classification_society: Optional[str] = None
    class_notation: Optional[str] = None
    flag_state: Optional[str] = None

    # Special requirements
    special_features: List[str] = field(default_factory=list)
    operational_profile: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MissionConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 2. HullState ====================

@dataclass
class HullState:
    """
    Hull geometry and form coefficients.
    Phase: hull_form
    """
    # Principal dimensions
    loa: Optional[float] = None  # Length overall (m)
    lwl: Optional[float] = None  # Length waterline (m)
    lbp: Optional[float] = None  # Length between perpendiculars (m)
    beam: Optional[float] = None  # Beam overall (m)
    beam_wl: Optional[float] = None  # Beam at waterline (m)
    draft: Optional[float] = None  # Design draft (m)
    draft_max: Optional[float] = None  # Maximum draft (m)
    depth: Optional[float] = None  # Depth to main deck (m)
    freeboard: Optional[float] = None  # Minimum freeboard (m)

    # Hull form type
    hull_type: Optional[str] = None  # HullType enum value

    # Form coefficients
    cb: Optional[float] = None  # Block coefficient
    cp: Optional[float] = None  # Prismatic coefficient
    cm: Optional[float] = None  # Midship coefficient
    cwp: Optional[float] = None  # Waterplane coefficient
    cvp: Optional[float] = None  # Vertical prismatic coefficient

    # Hull angles
    deadrise_deg: Optional[float] = None  # Deadrise at transom
    deadrise_midship_deg: Optional[float] = None
    entrance_angle_deg: Optional[float] = None  # Half angle of entrance

    # Derived values
    displacement_m3: Optional[float] = None  # Volume displacement
    wetted_surface_m2: Optional[float] = None
    waterplane_area_m2: Optional[float] = None

    # Centroids
    lcb_from_ap_m: Optional[float] = None  # Longitudinal center of buoyancy
    lcf_from_ap_m: Optional[float] = None  # Longitudinal center of flotation
    vcb_m: Optional[float] = None  # Vertical center of buoyancy (KB)

    # Hydrostatics
    bmt: Optional[float] = None  # Transverse metacentric radius
    bml: Optional[float] = None  # Longitudinal metacentric radius
    kmt: Optional[float] = None  # Height of transverse metacenter
    kml: Optional[float] = None  # Height of longitudinal metacenter
    tpc: Optional[float] = None  # Tonnes per cm immersion
    mct: Optional[float] = None  # Moment to change trim 1cm

    # Multi-hull specific
    hull_spacing_m: Optional[float] = None  # For catamarans
    demi_hull_beam_m: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HullState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 3. StructuralDesign ====================

@dataclass
class PlatingZone:
    """Individual plating zone specification."""
    zone_name: str = ""
    location: str = ""
    material: str = ""
    thickness_mm: float = 0.0
    area_m2: float = 0.0
    weight_kg: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlatingZone":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Stiffener:
    """Stiffener specification."""
    name: str = ""
    profile: str = ""  # e.g., "L 75x50x6"
    material: str = ""
    spacing_mm: float = 0.0
    span_m: float = 0.0
    section_modulus_cm3: float = 0.0
    moment_of_inertia_cm4: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Stiffener":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class StructuralDesign:
    """
    Structural scantlings and framing.
    Phase: structure
    """
    # Material
    hull_material: Optional[str] = None  # MaterialType enum value
    superstructure_material: Optional[str] = None

    # Plating
    plating_zones: List[Dict[str, Any]] = field(default_factory=list)
    bottom_plating_mm: Optional[float] = None
    side_plating_mm: Optional[float] = None
    deck_plating_mm: Optional[float] = None
    keel_plating_mm: Optional[float] = None
    transom_plating_mm: Optional[float] = None

    # Framing
    framing_type: Optional[str] = None  # transverse, longitudinal, combined
    frame_spacing_mm: Optional[float] = None
    web_frame_spacing_m: Optional[float] = None

    # Stiffeners
    longitudinals: List[Dict[str, Any]] = field(default_factory=list)
    transverse_frames: List[Dict[str, Any]] = field(default_factory=list)

    # Bulkheads
    watertight_bulkheads: int = 0
    bulkhead_positions_m: List[float] = field(default_factory=list)
    collision_bulkhead_pos_m: Optional[float] = None

    # Structural weight
    hull_steel_weight_kg: Optional[float] = None
    superstructure_weight_kg: Optional[float] = None

    # Design basis
    design_pressure_kpa: Optional[float] = None
    design_acceleration_g: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StructuralDesign":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 4. StructuralLoads ====================

@dataclass
class StructuralLoads:
    """
    Design loads for structural analysis.
    Phase: structure
    """
    # Slamming loads
    slamming_pressure_kpa: Optional[float] = None
    slamming_area_m2: Optional[float] = None
    design_vertical_acceleration_g: Optional[float] = None

    # Hydrostatic loads
    hydrostatic_pressure_kpa: Optional[float] = None
    max_still_water_bm_knm: Optional[float] = None
    max_wave_bm_knm: Optional[float] = None

    # Global loads
    design_bending_moment_knm: Optional[float] = None
    design_shear_force_kn: Optional[float] = None
    design_torsion_knm: Optional[float] = None

    # Local loads
    deck_load_kpa: Optional[float] = None
    tank_pressure_kpa: Optional[float] = None

    # Dynamic loads
    pitch_acceleration_deg_s2: Optional[float] = None
    roll_acceleration_deg_s2: Optional[float] = None
    heave_acceleration_g: Optional[float] = None

    # Impact loads
    berthing_energy_kj: Optional[float] = None
    mooring_load_kn: Optional[float] = None

    # Load combinations
    load_cases: List[Dict[str, Any]] = field(default_factory=list)
    governing_load_case: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StructuralLoads":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 5. PropulsionState ====================

@dataclass
class PropulsionState:
    """
    Propulsion system configuration.
    Phase: propulsion
    """
    # System type
    propulsion_type: Optional[str] = None  # PropulsionType enum value

    # Power
    total_installed_power_kw: Optional[float] = None
    mcr_power_kw: Optional[float] = None  # Maximum continuous rating
    service_power_kw: Optional[float] = None

    # Engines
    num_engines: int = 0
    engine_make: Optional[str] = None
    engine_model: Optional[str] = None
    engine_power_kw: Optional[float] = None
    engine_rpm: Optional[float] = None
    engine_weight_kg: Optional[float] = None

    # Gearbox
    gearbox_ratio: Optional[float] = None
    gearbox_efficiency: Optional[float] = None

    # Propellers/Waterjets
    num_propellers: int = 0
    propeller_diameter_m: Optional[float] = None
    propeller_pitch_m: Optional[float] = None
    propeller_rpm: Optional[float] = None
    propeller_type: Optional[str] = None  # FPP, CPP
    propeller_material: Optional[str] = None
    num_blades: int = 0

    # Waterjets
    waterjet_make: Optional[str] = None
    waterjet_model: Optional[str] = None
    impeller_diameter_m: Optional[float] = None

    # Efficiency
    propulsive_efficiency: Optional[float] = None
    hull_efficiency: Optional[float] = None
    propeller_efficiency: Optional[float] = None
    relative_rotative_efficiency: Optional[float] = None

    # Shaft
    shaft_diameter_mm: Optional[float] = None
    shaft_material: Optional[str] = None
    shaft_length_m: Optional[float] = None

    # Fuel
    fuel_type: Optional[str] = None
    sfc_g_kwh: Optional[float] = None  # Specific fuel consumption

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PropulsionState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 6. WeightEstimate ====================

@dataclass
class WeightItem:
    """Individual weight item."""
    name: str = ""
    category: str = ""
    weight_kg: float = 0.0
    lcg_m: float = 0.0
    tcg_m: float = 0.0
    vcg_m: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeightItem":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class WeightEstimate:
    """
    Weight breakdown and centers of gravity.
    Phase: weight
    """
    # Summary weights (metric tons)
    lightship_weight_mt: Optional[float] = None
    full_load_displacement_mt: Optional[float] = None
    deadweight_mt: Optional[float] = None

    # Weight groups
    hull_structure_mt: Optional[float] = None
    superstructure_mt: Optional[float] = None
    machinery_mt: Optional[float] = None
    outfit_mt: Optional[float] = None
    electrical_mt: Optional[float] = None

    # Deadweight items
    fuel_mt: Optional[float] = None
    fresh_water_mt: Optional[float] = None
    lube_oil_mt: Optional[float] = None
    stores_mt: Optional[float] = None
    crew_effects_mt: Optional[float] = None
    cargo_mt: Optional[float] = None
    ballast_mt: Optional[float] = None

    # Centers of gravity - Lightship
    lightship_lcg_m: Optional[float] = None
    lightship_tcg_m: Optional[float] = None
    lightship_vcg_m: Optional[float] = None

    # Centers of gravity - Full load
    full_load_lcg_m: Optional[float] = None
    full_load_tcg_m: Optional[float] = None
    full_load_vcg_m: Optional[float] = None

    # Margins
    design_margin_percent: float = 5.0
    growth_margin_percent: float = 3.0

    # Detailed breakdown
    weight_items: List[Dict[str, Any]] = field(default_factory=list)

    # Free surface effects
    free_surface_moment_mt_m: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeightEstimate":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 7. StabilityState ====================

@dataclass
class GZCurvePoint:
    """Point on GZ curve."""
    heel_deg: float = 0.0
    gz_m: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GZCurvePoint":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class StabilityState:
    """
    Intact and damaged stability results.
    Phase: stability
    """
    # Metacentric height
    gm_transverse_m: Optional[float] = None
    gm_longitudinal_m: Optional[float] = None
    gm_corrected_m: Optional[float] = None  # After free surface correction

    # GZ curve characteristics
    gz_max_m: Optional[float] = None
    angle_of_max_gz_deg: Optional[float] = None
    angle_of_vanishing_stability_deg: Optional[float] = None

    # Areas under GZ curve
    area_0_30_m_rad: Optional[float] = None
    area_0_40_m_rad: Optional[float] = None
    area_30_40_m_rad: Optional[float] = None

    # Key heights
    kg_m: Optional[float] = None
    kb_m: Optional[float] = None
    bm_m: Optional[float] = None

    # GZ curve data
    gz_curve: List[Dict[str, float]] = field(default_factory=list)

    # Dynamic stability
    dynamic_stability_m_rad: Optional[float] = None

    # Wind heeling
    steady_wind_heel_deg: Optional[float] = None
    gust_wind_heel_deg: Optional[float] = None

    # Passenger crowding
    crowding_heel_deg: Optional[float] = None

    # Damage stability
    damage_cases: List[Dict[str, Any]] = field(default_factory=list)
    damage_gm_min_m: Optional[float] = None
    damage_range_deg: Optional[float] = None

    # Compliance
    imo_intact_passed: bool = False
    imo_damage_passed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StabilityState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 8. LoadingState ====================

@dataclass
class LoadingCondition:
    """Individual loading condition."""
    name: str = ""
    displacement_mt: float = 0.0
    draft_m: float = 0.0
    trim_m: float = 0.0
    heel_deg: float = 0.0
    gm_m: float = 0.0
    lcg_m: float = 0.0
    vcg_m: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoadingCondition":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class LoadingState:
    """
    Loading conditions and tank states.
    Phase: stability
    """
    # Current condition
    current_condition: Optional[str] = None  # LoadCondition enum value

    # Standard conditions
    loading_conditions: List[Dict[str, Any]] = field(default_factory=list)

    # Tank states
    tank_states: Dict[str, float] = field(default_factory=dict)  # tank_id -> fill %

    # Current values
    current_displacement_mt: Optional[float] = None
    current_draft_fwd_m: Optional[float] = None
    current_draft_aft_m: Optional[float] = None
    current_trim_m: Optional[float] = None
    current_heel_deg: Optional[float] = None

    # Limits
    max_draft_m: Optional[float] = None
    max_trim_m: Optional[float] = None
    min_freeboard_m: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoadingState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 9. ArrangementState ====================

@dataclass
class Compartment:
    """Individual compartment definition."""
    name: str = ""
    type: str = ""  # tank, void, machinery, accommodation, etc.
    deck: str = ""
    frame_start: float = 0.0
    frame_end: float = 0.0
    volume_m3: float = 0.0
    area_m2: float = 0.0
    lcg_m: float = 0.0
    vcg_m: float = 0.0
    tcg_m: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Compartment":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ArrangementState:
    """
    General arrangement and compartmentation.
    Phase: arrangement
    """
    # Deck definitions
    deck_layouts: List[Dict[str, Any]] = field(default_factory=list)
    num_decks: int = 0
    deck_heights: Dict[str, float] = field(default_factory=dict)

    # Compartments
    compartments: List[Dict[str, Any]] = field(default_factory=list)

    # Tanks
    fuel_tanks: List[Dict[str, Any]] = field(default_factory=list)
    fresh_water_tanks: List[Dict[str, Any]] = field(default_factory=list)
    ballast_tanks: List[Dict[str, Any]] = field(default_factory=list)

    # Tank capacities
    total_fuel_capacity_l: Optional[float] = None
    total_fw_capacity_l: Optional[float] = None
    total_ballast_capacity_l: Optional[float] = None

    # Spaces
    engine_room_volume_m3: Optional[float] = None
    accommodation_area_m2: Optional[float] = None
    cargo_hold_volume_m3: Optional[float] = None

    # Access
    escape_routes: List[str] = field(default_factory=list)
    watertight_doors: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArrangementState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 10. ComplianceState ====================

@dataclass
class ComplianceCheck:
    """Individual compliance check result."""
    rule_id: str = ""
    rule_name: str = ""
    category: str = ""
    status: str = "not_checked"  # ComplianceStatus
    required_value: Optional[float] = None
    actual_value: Optional[float] = None
    margin_percent: Optional[float] = None
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComplianceCheck":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ComplianceState:
    """
    Regulatory compliance status.
    Phase: compliance
    """
    # Overall status
    overall_passed: bool = False

    # Check results
    checks: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # By category
    stability_checks_passed: bool = False
    structural_checks_passed: bool = False
    safety_checks_passed: bool = False
    environmental_checks_passed: bool = False

    # Applicable rules
    class_rules: Optional[str] = None
    flag_state_rules: Optional[str] = None
    imo_conventions: List[str] = field(default_factory=list)

    # Exemptions
    exemptions: List[str] = field(default_factory=list)

    # Certification
    certifications_required: List[str] = field(default_factory=list)
    certifications_obtained: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComplianceState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 11. ProductionState ====================

@dataclass
class ProductionState:
    """
    Production planning and cost tracking.
    Phase: production
    """
    # Build hours
    build_hours: Optional[float] = None
    hull_hours: Optional[float] = None
    outfitting_hours: Optional[float] = None
    systems_hours: Optional[float] = None
    testing_hours: Optional[float] = None

    # Material quantities
    steel_weight_kg: Optional[float] = None
    aluminum_weight_kg: Optional[float] = None
    weld_length_m: Optional[float] = None
    paint_area_m2: Optional[float] = None

    # Costs
    material_cost: Optional[float] = None
    labor_cost: Optional[float] = None
    equipment_cost: Optional[float] = None
    overhead_cost: Optional[float] = None

    # Schedule
    build_duration_days: Optional[int] = None
    hull_start_date: Optional[str] = None
    launch_date: Optional[str] = None
    delivery_date: Optional[str] = None

    # Milestones
    milestones: List[Dict[str, Any]] = field(default_factory=list)

    # Yard information
    yard_name: Optional[str] = None
    yard_location: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductionState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 12. CostState ====================

@dataclass
class CostState:
    """
    Cost estimation and tracking.
    Phase: production
    """
    # Total costs
    total_cost: Optional[float] = None
    currency: str = "USD"

    # Cost breakdown
    material_cost: Optional[float] = None
    labor_cost: Optional[float] = None
    equipment_cost: Optional[float] = None
    engineering_cost: Optional[float] = None
    classification_cost: Optional[float] = None
    testing_cost: Optional[float] = None

    # By system
    hull_cost: Optional[float] = None
    machinery_cost: Optional[float] = None
    electrical_cost: Optional[float] = None
    outfit_cost: Optional[float] = None
    paint_cost: Optional[float] = None

    # Contingency
    contingency_percent: float = 10.0
    contingency_amount: Optional[float] = None

    # Operating costs
    annual_fuel_cost: Optional[float] = None
    annual_crew_cost: Optional[float] = None
    annual_maintenance_cost: Optional[float] = None
    annual_insurance_cost: Optional[float] = None

    # Cost per unit
    cost_per_gt: Optional[float] = None
    cost_per_meter: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CostState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 13. OptimizationState ====================

@dataclass
class OptimizationState:
    """
    Optimization objectives and results.
    """
    # Objectives
    objectives: List[str] = field(default_factory=list)
    objective_weights: Dict[str, float] = field(default_factory=dict)

    # Constraints
    constraints: List[Dict[str, Any]] = field(default_factory=list)

    # Variables
    design_variables: List[str] = field(default_factory=list)
    variable_bounds: Dict[str, Tuple[float, float]] = field(default_factory=dict)

    # Results
    optimal_values: Dict[str, float] = field(default_factory=dict)
    objective_values: Dict[str, float] = field(default_factory=dict)

    # History
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    converged: bool = False

    # Method
    optimization_method: Optional[str] = None
    convergence_tolerance: float = 1e-6

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        # Convert tuple bounds to lists for JSON serialization
        result["variable_bounds"] = {k: list(v) for k, v in self.variable_bounds.items()}
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OptimizationState":
        # Convert list bounds back to tuples
        if "variable_bounds" in data:
            data["variable_bounds"] = {k: tuple(v) for k, v in data["variable_bounds"].items()}
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 14. ReportsState ====================

@dataclass
class ReportsState:
    """
    Generated reports and documentation.
    """
    # Report flags
    generated: bool = False

    # Report paths/content
    design_summary: Optional[str] = None
    compliance_report: Optional[str] = None
    stability_report: Optional[str] = None
    structural_report: Optional[str] = None
    weight_report: Optional[str] = None

    # Report metadata
    reports_generated: List[str] = field(default_factory=list)
    generation_timestamps: Dict[str, str] = field(default_factory=dict)

    # Export formats
    export_formats: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReportsState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 15. KernelState ====================

@dataclass
class KernelState:
    """
    System kernel status and mode.
    """
    # Status
    status: str = "idle"  # idle, running, paused, error
    mode: str = "interactive"  # interactive, batch, api

    # Phase tracking
    phases: Dict[str, str] = field(default_factory=dict)
    current_phase: Optional[str] = None

    # Issues
    issues: List[Dict[str, Any]] = field(default_factory=list)
    warnings_count: int = 0
    errors_count: int = 0

    # Session
    session_id: Optional[str] = None
    started_at: Optional[str] = None
    last_activity: Optional[str] = None

    # Performance
    computation_time_s: float = 0.0
    memory_usage_mb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KernelState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 16. AnalysisState ====================

@dataclass
class AnalysisState:
    """
    Analysis results (operability, noise, vibration).
    """
    # Operability
    operability_index: Optional[float] = None
    operability_by_heading: Dict[str, float] = field(default_factory=dict)
    limiting_criteria: Optional[str] = None

    # Motion responses
    roll_amplitude_deg: Optional[float] = None
    pitch_amplitude_deg: Optional[float] = None
    heave_amplitude_m: Optional[float] = None

    # Accelerations
    vertical_acceleration_g: Optional[float] = None
    lateral_acceleration_g: Optional[float] = None

    # Motion sickness
    msi_percent: Optional[float] = None  # Motion Sickness Incidence

    # Noise
    noise_level_db: Optional[float] = None
    noise_by_location: Dict[str, float] = field(default_factory=dict)

    # Vibration
    vibration_level: Optional[float] = None

    # Analysis conditions
    analysis_sea_state: Optional[str] = None
    analysis_speed_kts: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 17. PerformanceState ====================

@dataclass
class PerformanceState:
    """
    Speed-power performance results.
    """
    # Speed-power curve
    speed_power_curve: List[Dict[str, float]] = field(default_factory=list)

    # Design point
    design_speed_kts: Optional[float] = None
    design_power_kw: Optional[float] = None

    # Resistance
    total_resistance_kn: Optional[float] = None
    frictional_resistance_kn: Optional[float] = None
    residuary_resistance_kn: Optional[float] = None
    air_resistance_kn: Optional[float] = None
    appendage_resistance_kn: Optional[float] = None

    # Range
    range_at_cruise_nm: Optional[float] = None
    range_at_max_nm: Optional[float] = None
    endurance_at_cruise_hr: Optional[float] = None

    # Fuel consumption
    fuel_consumption_cruise_lph: Optional[float] = None
    fuel_consumption_max_lph: Optional[float] = None

    # Bollard pull (for tugs/workboats)
    bollard_pull_kn: Optional[float] = None

    # Trial results
    trial_speed_kts: Optional[float] = None
    trial_power_kw: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerformanceState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 18. SystemsState ====================

@dataclass
class SystemsState:
    """
    Ship systems configuration.
    """
    # Electrical
    electrical_load_kw: Optional[float] = None
    generator_capacity_kw: Optional[float] = None
    num_generators: int = 0
    battery_capacity_kwh: Optional[float] = None
    shore_power_kw: Optional[float] = None

    # Fuel system
    fuel_tank_capacity_l: Optional[float] = None
    fuel_transfer_rate_lph: Optional[float] = None
    fuel_type: Optional[str] = None

    # Fresh water
    fw_tank_capacity_l: Optional[float] = None
    watermaker_capacity_lpd: Optional[float] = None

    # HVAC
    hvac_cooling_capacity_kw: Optional[float] = None
    hvac_heating_capacity_kw: Optional[float] = None
    ventilation_rate_m3h: Optional[float] = None

    # Bilge and ballast
    bilge_pump_capacity_m3h: Optional[float] = None
    ballast_pump_capacity_m3h: Optional[float] = None

    # Fire fighting
    fire_pump_capacity_m3h: Optional[float] = None
    fire_suppression_type: Optional[str] = None

    # Steering
    steering_type: Optional[str] = None
    rudder_area_m2: Optional[float] = None

    # Auxiliary
    bow_thruster_kw: Optional[float] = None
    stern_thruster_kw: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemsState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 19. OutfittingState ====================

@dataclass
class OutfittingState:
    """
    Interior outfitting and accommodation.
    """
    # Berths
    berth_count: int = 0
    cabin_count: int = 0
    cabin_types: Dict[str, int] = field(default_factory=dict)

    # Bridge
    helm_seats: int = 0
    nav_equipment: List[str] = field(default_factory=list)

    # Galley
    galley_equipped: bool = False
    galley_appliances: List[str] = field(default_factory=list)

    # Heads
    head_count: int = 0
    shower_count: int = 0

    # Seating
    indoor_seats: int = 0
    outdoor_seats: int = 0

    # Other spaces
    mess_seats: int = 0
    lounge_area_m2: Optional[float] = None

    # Finish level
    finish_level: Optional[str] = None  # basic, standard, premium, luxury

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OutfittingState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 20. EnvironmentalState ====================

@dataclass
class EnvironmentalState:
    """
    Environmental design conditions.
    """
    # Sea state
    design_sea_state: Optional[str] = None  # SeaState enum
    design_wave_height_m: Optional[float] = None
    design_wave_period_s: Optional[float] = None

    # Wind
    design_wind_speed_kts: Optional[float] = None
    max_wind_speed_kts: Optional[float] = None

    # Current
    design_current_kts: Optional[float] = None

    # Water properties
    water_density_kg_m3: float = 1025.0
    water_temperature_c: float = 15.0
    salinity_ppt: float = 35.0

    # Air
    air_temperature_c: float = 20.0
    air_density_kg_m3: float = 1.225

    # Operating limits
    max_operating_sea_state: Optional[str] = None
    survival_sea_state: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnvironmentalState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 21. DeckEquipmentState ====================

@dataclass
class DeckEquipmentState:
    """
    Deck equipment and fittings.
    """
    # Anchoring
    windlass_type: Optional[str] = None
    anchor_weight_kg: Optional[float] = None
    anchor_type: Optional[str] = None
    chain_diameter_mm: Optional[float] = None
    chain_length_m: Optional[float] = None

    # Mooring
    cleats_count: int = 0
    bollard_capacity_kn: Optional[float] = None
    fairleads_count: int = 0

    # Fenders
    fender_type: Optional[str] = None
    fender_count: int = 0

    # Davits/Cranes
    crane_capacity_kg: Optional[float] = None
    davit_capacity_kg: Optional[float] = None
    rescue_boat: bool = False

    # Towing
    towing_hook_kn: Optional[float] = None
    towing_winch_kn: Optional[float] = None

    # Capstans
    capstan_pull_kn: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeckEquipmentState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 22. VisionState ====================

@dataclass
class VisionState:
    """
    3D geometry and visualization state.
    """
    # Geometry status
    geometry_generated: bool = False
    mesh_valid: bool = False

    # Mesh statistics
    vertex_count: int = 0
    face_count: int = 0
    edge_count: int = 0

    # File references
    hull_mesh_path: Optional[str] = None
    deck_mesh_path: Optional[str] = None
    full_model_path: Optional[str] = None

    # Snapshots
    snapshots: List[str] = field(default_factory=list)

    # Render settings
    render_quality: str = "medium"
    show_waterline: bool = True
    show_sections: bool = False

    # Last update
    last_generated: Optional[str] = None
    generation_time_s: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VisionState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 23. ResistanceState ====================

@dataclass
class ResistanceState:
    """
    Resistance calculation results.
    """
    # Total resistance
    total_resistance_kn: Optional[float] = None

    # Components
    frictional_resistance_kn: Optional[float] = None
    residuary_resistance_kn: Optional[float] = None
    wave_resistance_kn: Optional[float] = None
    form_resistance_kn: Optional[float] = None
    air_resistance_kn: Optional[float] = None
    appendage_resistance_kn: Optional[float] = None
    correlation_allowance_kn: Optional[float] = None

    # Coefficients
    ct: Optional[float] = None  # Total resistance coefficient
    cf: Optional[float] = None  # Frictional coefficient
    cr: Optional[float] = None  # Residuary coefficient
    cw: Optional[float] = None  # Wave coefficient

    # Speed-resistance curve
    resistance_curve: List[Dict[str, float]] = field(default_factory=list)

    # Calculation method
    method: Optional[str] = None  # Holtrop, Savitsky, CFD, etc.

    # Reynolds/Froude numbers
    reynolds_number: Optional[float] = None
    froude_number: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResistanceState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 24. SeakeepingState ====================

@dataclass
class SeakeepingState:
    """
    Seakeeping analysis results.
    """
    # Natural periods
    roll_period_s: Optional[float] = None
    pitch_period_s: Optional[float] = None
    heave_period_s: Optional[float] = None

    # RAOs (Response Amplitude Operators)
    roll_rao: List[Dict[str, float]] = field(default_factory=list)
    pitch_rao: List[Dict[str, float]] = field(default_factory=list)
    heave_rao: List[Dict[str, float]] = field(default_factory=list)

    # Significant responses
    significant_roll_deg: Optional[float] = None
    significant_pitch_deg: Optional[float] = None
    significant_heave_m: Optional[float] = None

    # Accelerations
    max_vertical_accel_g: Optional[float] = None
    max_lateral_accel_g: Optional[float] = None

    # Added mass and damping
    added_mass_heave_kg: Optional[float] = None
    damping_roll: Optional[float] = None

    # Analysis spectrum
    spectrum_type: Optional[str] = None  # Bretschneider, JONSWAP, etc.
    significant_wave_height_m: Optional[float] = None
    peak_period_s: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SeakeepingState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 25. ManeuveringState ====================

@dataclass
class ManeuveringState:
    """
    Maneuvering characteristics.
    """
    # Turning circle
    tactical_diameter_m: Optional[float] = None
    advance_m: Optional[float] = None
    transfer_m: Optional[float] = None
    turning_radius_m: Optional[float] = None

    # Stopping
    crash_stop_distance_m: Optional[float] = None
    crash_stop_time_s: Optional[float] = None

    # Zig-zag
    first_overshoot_deg: Optional[float] = None
    second_overshoot_deg: Optional[float] = None

    # Speed
    speed_in_turn_kts: Optional[float] = None
    heel_in_turn_deg: Optional[float] = None

    # Low speed
    min_steerage_speed_kts: Optional[float] = None

    # Thrusters effect
    thruster_turning_effect: Optional[float] = None

    # IMO compliance
    imo_maneuvering_passed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ManeuveringState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 26. ElectricalState ====================

@dataclass
class ElectricalState:
    """
    Electrical system design.
    """
    # Load analysis
    connected_load_kw: Optional[float] = None
    running_load_kw: Optional[float] = None
    peak_load_kw: Optional[float] = None

    # Generation
    main_generator_kw: Optional[float] = None
    aux_generator_kw: Optional[float] = None
    emergency_generator_kw: Optional[float] = None
    num_main_generators: int = 0

    # Distribution
    main_bus_voltage: Optional[float] = None
    distribution_voltage: Optional[float] = None
    frequency_hz: float = 60.0

    # Battery
    battery_bank_kwh: Optional[float] = None
    battery_type: Optional[str] = None
    battery_autonomy_hr: Optional[float] = None

    # Shore power
    shore_connection_kw: Optional[float] = None
    shore_voltage: Optional[float] = None

    # UPS
    ups_capacity_kva: Optional[float] = None
    ups_autonomy_min: Optional[float] = None

    # Load groups
    load_by_system: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ElectricalState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 27. SafetyState ====================

@dataclass
class SafetyState:
    """
    Safety equipment and systems.
    """
    # Life saving
    liferaft_capacity: int = 0
    num_liferafts: int = 0
    lifejackets: int = 0
    immersion_suits: int = 0
    lifebuoys: int = 0

    # Rescue
    rescue_boat: bool = False
    rescue_boat_capacity: int = 0
    man_overboard_system: bool = False

    # Fire safety
    fire_detection_zones: int = 0
    fire_extinguishers: int = 0
    fixed_fire_suppression: bool = False
    fire_pump_capacity_m3h: Optional[float] = None

    # Navigation safety
    radar_systems: int = 0
    ais_class: Optional[str] = None
    epirb: bool = False
    sart: int = 0

    # Communication
    vhf_radios: int = 0
    satellite_comm: bool = False

    # Alarms
    bilge_alarm: bool = False
    fire_alarm: bool = False
    general_alarm: bool = False

    # Escape
    escape_routes: int = 0
    emergency_lighting: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SafetyState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== Export all dataclasses ====================

__all__ = [
    # Main state classes
    "MissionConfig",
    "HullState",
    "StructuralDesign",
    "StructuralLoads",
    "PropulsionState",
    "WeightEstimate",
    "StabilityState",
    "LoadingState",
    "ArrangementState",
    "ComplianceState",
    "ProductionState",
    "CostState",
    "OptimizationState",
    "ReportsState",
    "KernelState",
    "AnalysisState",
    "PerformanceState",
    "SystemsState",
    "OutfittingState",
    "EnvironmentalState",
    "DeckEquipmentState",
    "VisionState",
    "ResistanceState",
    "SeakeepingState",
    "ManeuveringState",
    "ElectricalState",
    "SafetyState",
    # Supporting classes
    "PlatingZone",
    "Stiffener",
    "WeightItem",
    "GZCurvePoint",
    "LoadingCondition",
    "Compartment",
    "ComplianceCheck",
]
