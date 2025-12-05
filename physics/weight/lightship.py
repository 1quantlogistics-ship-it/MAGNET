"""
Lightship weight estimation module.

Provides estimation methods for:
- Hull steel weight (Watson-Gilfillan, Schneekluth methods)
- Machinery weight (propulsion, auxiliaries)
- Outfit weight (accommodation, equipment)

References:
- Watson & Gilfillan (1977) - "Some Ship Design Methods"
- Schneekluth & Bertram (1998) - "Ship Design for Efficiency and Economy"
- Papanikolaou (2014) - "Ship Design: Methodologies of Preliminary Design"
"""

import math
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class VesselCategory(Enum):
    """Vessel category for weight estimation coefficients."""
    CARGO_GENERAL = "cargo_general"
    CARGO_CONTAINER = "cargo_container"
    TANKER = "tanker"
    BULK_CARRIER = "bulk_carrier"
    PASSENGER = "passenger"
    FERRY_RORO = "ferry_roro"
    OFFSHORE_SUPPLY = "offshore_supply"
    PATROL_MILITARY = "patrol_military"
    YACHT = "yacht"
    FISHING = "fishing"
    TUG = "tug"
    WORKBOAT = "workboat"


class PropulsionType(Enum):
    """Propulsion type for machinery weight estimation."""
    DIESEL_MECHANICAL = "diesel_mechanical"
    DIESEL_ELECTRIC = "diesel_electric"
    GAS_TURBINE = "gas_turbine"
    WATERJET = "waterjet"
    HYBRID = "hybrid"


@dataclass
class LightshipResult:
    """Result of lightship weight calculation."""
    hull_steel_weight: float  # tonnes
    machinery_weight: float   # tonnes
    outfit_weight: float      # tonnes
    lightship_weight: float   # tonnes
    margin_weight: float      # tonnes (design margin)
    total_lightship: float    # tonnes (including margin)

    # Component breakdown
    hull_structure: float     # tonnes
    hull_superstructure: float  # tonnes

    machinery_main: float     # tonnes (main engines)
    machinery_auxiliary: float  # tonnes (generators, pumps, etc.)
    machinery_shafting: float   # tonnes (shafts, gearbox, propeller)

    outfit_accommodation: float  # tonnes
    outfit_equipment: float      # tonnes
    outfit_systems: float        # tonnes (HVAC, piping, electrical)

    # Centers of gravity (estimated)
    kg_hull: float           # m above baseline
    kg_machinery: float      # m above baseline
    kg_outfit: float         # m above baseline
    kg_lightship: float      # m above baseline (combined)

    lcg_hull: float          # m from AP
    lcg_machinery: float     # m from AP
    lcg_outfit: float        # m from AP
    lcg_lightship: float     # m from AP (combined)

    # Estimation method used
    method: str
    vessel_category: str

    # Coefficients used
    coefficients: dict = field(default_factory=dict)


def calculate_hull_steel_weight(
    length_bp: float,
    beam: float,
    depth: float,
    block_coefficient: float,
    vessel_category: VesselCategory = VesselCategory.WORKBOAT,
    has_superstructure: bool = True,
    superstructure_length: Optional[float] = None,
    superstructure_breadth: Optional[float] = None,
    superstructure_height: Optional[float] = None,
) -> tuple[float, float, dict]:
    """
    Calculate hull steel weight using Watson-Gilfillan method.

    Args:
        length_bp: Length between perpendiculars (m)
        beam: Beam at waterline (m)
        depth: Depth to main deck (m)
        block_coefficient: Block coefficient Cb
        vessel_category: Type of vessel for coefficient selection
        has_superstructure: Whether vessel has superstructure
        superstructure_length: Length of superstructure (m)
        superstructure_breadth: Breadth of superstructure (m)
        superstructure_height: Height of superstructure (m)

    Returns:
        Tuple of (hull_weight, superstructure_weight, coefficients_used)
    """
    # Watson-Gilfillan coefficients by vessel type
    # K1 coefficients for Ws = K1 * E^1.36
    # where E = L(B + T) + 0.85L(D - T) + 0.85(l1*h1) + 0.75(l2*h2)

    k1_coefficients = {
        VesselCategory.CARGO_GENERAL: 0.029,
        VesselCategory.CARGO_CONTAINER: 0.033,
        VesselCategory.TANKER: 0.032,
        VesselCategory.BULK_CARRIER: 0.028,
        VesselCategory.PASSENGER: 0.038,
        VesselCategory.FERRY_RORO: 0.035,
        VesselCategory.OFFSHORE_SUPPLY: 0.036,
        VesselCategory.PATROL_MILITARY: 0.042,
        VesselCategory.YACHT: 0.045,
        VesselCategory.FISHING: 0.034,
        VesselCategory.TUG: 0.040,
        VesselCategory.WORKBOAT: 0.038,
    }

    k1 = k1_coefficients.get(vessel_category, 0.035)

    # Estimate draft from depth (typical ratio)
    draft = depth * 0.65

    # Calculate Lloyd's Equipment Numeral E (simplified)
    # E = L(B + T) + 0.85L(D - T) + superstructure terms
    e_hull = length_bp * (beam + draft) + 0.85 * length_bp * (depth - draft)

    # Superstructure contribution
    e_super = 0.0
    if has_superstructure:
        if superstructure_length is None:
            superstructure_length = length_bp * 0.25
        if superstructure_breadth is None:
            superstructure_breadth = beam * 0.85
        if superstructure_height is None:
            superstructure_height = 2.5

        e_super = 0.85 * superstructure_length * superstructure_height

    e_total = e_hull + e_super

    # Watson-Gilfillan formula
    # Ws = K1 * E^1.36
    total_steel = k1 * (e_total ** 1.36)

    # Cb correction factor (heavier structure for finer hulls)
    cb_correction = 1.0 + 0.5 * (0.70 - block_coefficient)
    cb_correction = max(0.9, min(1.2, cb_correction))

    total_steel *= cb_correction

    # Split hull vs superstructure
    if e_super > 0:
        super_fraction = (e_super / e_total) * 0.7  # Superstructure lighter per m²
        superstructure_weight = total_steel * super_fraction
        hull_weight = total_steel - superstructure_weight
    else:
        hull_weight = total_steel
        superstructure_weight = 0.0

    coefficients = {
        "k1": k1,
        "cb_correction": cb_correction,
        "e_hull": e_hull,
        "e_super": e_super,
        "e_total": e_total,
    }

    return hull_weight, superstructure_weight, coefficients


def calculate_machinery_weight(
    installed_power: float,
    propulsion_type: PropulsionType = PropulsionType.DIESEL_MECHANICAL,
    length_bp: float = 0.0,
    num_engines: int = 2,
    num_shafts: int = 2,
    has_gearbox: bool = True,
) -> tuple[float, float, float, dict]:
    """
    Calculate machinery weight.

    Args:
        installed_power: Total installed power (kW)
        propulsion_type: Type of propulsion system
        length_bp: Length between perpendiculars (m) - for shafting estimate
        num_engines: Number of main engines
        num_shafts: Number of propeller shafts
        has_gearbox: Whether reduction gearbox is installed

    Returns:
        Tuple of (main_engine_weight, auxiliary_weight, shafting_weight, coefficients)
    """
    # Specific weight coefficients (kg/kW) by propulsion type
    specific_weights = {
        PropulsionType.DIESEL_MECHANICAL: 8.0,    # Medium-speed diesel
        PropulsionType.DIESEL_ELECTRIC: 12.0,     # Includes generators + motors
        PropulsionType.GAS_TURBINE: 2.5,          # Lightweight but needs more fuel
        PropulsionType.WATERJET: 6.0,             # Including jet units
        PropulsionType.HYBRID: 10.0,              # Mixed system
    }

    specific_weight = specific_weights.get(propulsion_type, 8.0)

    # Main engine weight
    main_engine_weight = (installed_power * specific_weight) / 1000  # tonnes

    # Auxiliary machinery (generators, pumps, compressors, etc.)
    # Typically 15-25% of main engine weight
    auxiliary_factor = 0.20
    if propulsion_type == PropulsionType.DIESEL_ELECTRIC:
        auxiliary_factor = 0.10  # Less auxiliaries, more integrated

    auxiliary_weight = main_engine_weight * auxiliary_factor

    # Shafting, gearbox, propellers
    shafting_weight = 0.0

    if propulsion_type != PropulsionType.WATERJET:
        # Shafting weight estimation
        # Roughly 0.5-1.0 tonnes per meter of shaft length per shaft
        if length_bp > 0:
            engine_room_position = 0.4 * length_bp  # Typical ER position from AP
            shaft_length = engine_room_position * 0.8
            shafting_weight += num_shafts * shaft_length * 0.06  # tonnes per meter
        else:
            shafting_weight += num_shafts * 3.0  # Default estimate

        # Gearbox weight
        if has_gearbox:
            # Gearbox roughly 3-5% of engine weight per shaft
            gearbox_weight = main_engine_weight * 0.04 * num_shafts
            shafting_weight += gearbox_weight

        # Propeller weight (simplified)
        # Prop weight ~ (D^3) * 0.01 tonnes, D typically L/20 to L/15
        if length_bp > 0:
            prop_diameter = length_bp / 18
            prop_weight = num_shafts * (prop_diameter ** 3) * 0.012
            shafting_weight += prop_weight
        else:
            shafting_weight += num_shafts * 1.5  # Default
    else:
        # Waterjet units weight (included in specific weight already)
        shafting_weight = installed_power * 0.001  # Minimal additional

    coefficients = {
        "specific_weight_kg_kW": specific_weight,
        "auxiliary_factor": auxiliary_factor,
        "num_engines": num_engines,
        "num_shafts": num_shafts,
    }

    return main_engine_weight, auxiliary_weight, shafting_weight, coefficients


def calculate_outfit_weight(
    length_bp: float,
    beam: float,
    depth: float,
    vessel_category: VesselCategory = VesselCategory.WORKBOAT,
    crew_capacity: int = 10,
    passenger_capacity: int = 0,
) -> tuple[float, float, float, dict]:
    """
    Calculate outfit weight.

    Args:
        length_bp: Length between perpendiculars (m)
        beam: Beam (m)
        depth: Depth (m)
        vessel_category: Type of vessel
        crew_capacity: Number of crew
        passenger_capacity: Number of passengers

    Returns:
        Tuple of (accommodation_weight, equipment_weight, systems_weight, coefficients)
    """
    # Volume approximation
    volume = length_bp * beam * depth

    # Outfit coefficients by vessel type (kg/m³ of hull volume)
    outfit_coefficients = {
        VesselCategory.CARGO_GENERAL: 25,
        VesselCategory.CARGO_CONTAINER: 20,
        VesselCategory.TANKER: 18,
        VesselCategory.BULK_CARRIER: 15,
        VesselCategory.PASSENGER: 55,
        VesselCategory.FERRY_RORO: 45,
        VesselCategory.OFFSHORE_SUPPLY: 35,
        VesselCategory.PATROL_MILITARY: 50,
        VesselCategory.YACHT: 60,
        VesselCategory.FISHING: 30,
        VesselCategory.TUG: 40,
        VesselCategory.WORKBOAT: 35,
    }

    outfit_coeff = outfit_coefficients.get(vessel_category, 35)

    # Base outfit weight
    base_outfit = (volume * outfit_coeff) / 1000  # tonnes

    # Accommodation weight
    # Per person weights (tonnes)
    crew_weight_per_person = 0.8  # Full cabin, facilities
    passenger_weight_per_person = 0.3  # Lighter accommodation

    accommodation_weight = (
        crew_capacity * crew_weight_per_person +
        passenger_capacity * passenger_weight_per_person
    )

    # Equipment weight (deck machinery, mooring, anchoring)
    # Scales with vessel size
    equipment_weight = 0.02 * length_bp * beam  # tonnes

    # Systems weight (HVAC, piping, electrical)
    # Remainder of outfit
    systems_weight = max(0, base_outfit - accommodation_weight - equipment_weight)

    # Minimum systems weight
    if systems_weight < 0.1 * base_outfit:
        systems_weight = 0.15 * base_outfit

    coefficients = {
        "outfit_coeff_kg_m3": outfit_coeff,
        "volume_m3": volume,
        "crew_weight_per_person": crew_weight_per_person,
        "passenger_weight_per_person": passenger_weight_per_person,
    }

    return accommodation_weight, equipment_weight, systems_weight, coefficients


def calculate_lightship_weight(
    length_bp: float,
    beam: float,
    depth: float,
    block_coefficient: float,
    installed_power: float,
    vessel_category: VesselCategory = VesselCategory.WORKBOAT,
    propulsion_type: PropulsionType = PropulsionType.DIESEL_MECHANICAL,
    crew_capacity: int = 10,
    passenger_capacity: int = 0,
    design_margin: float = 0.05,
    has_superstructure: bool = True,
    superstructure_length: Optional[float] = None,
    num_engines: int = 2,
    num_shafts: int = 2,
) -> LightshipResult:
    """
    Calculate complete lightship weight with breakdown.

    Args:
        length_bp: Length between perpendiculars (m)
        beam: Beam (m)
        depth: Depth to main deck (m)
        block_coefficient: Block coefficient Cb
        installed_power: Total installed power (kW)
        vessel_category: Type of vessel
        propulsion_type: Type of propulsion
        crew_capacity: Number of crew
        passenger_capacity: Number of passengers
        design_margin: Design margin fraction (typically 0.03-0.10)
        has_superstructure: Whether vessel has superstructure
        superstructure_length: Length of superstructure (m)
        num_engines: Number of main engines
        num_shafts: Number of propeller shafts

    Returns:
        LightshipResult with complete breakdown
    """
    # Calculate hull steel weight
    hull_structure, hull_superstructure, hull_coeffs = calculate_hull_steel_weight(
        length_bp=length_bp,
        beam=beam,
        depth=depth,
        block_coefficient=block_coefficient,
        vessel_category=vessel_category,
        has_superstructure=has_superstructure,
        superstructure_length=superstructure_length,
    )
    hull_steel_weight = hull_structure + hull_superstructure

    # Calculate machinery weight
    machinery_main, machinery_auxiliary, machinery_shafting, mach_coeffs = calculate_machinery_weight(
        installed_power=installed_power,
        propulsion_type=propulsion_type,
        length_bp=length_bp,
        num_engines=num_engines,
        num_shafts=num_shafts,
    )
    machinery_weight = machinery_main + machinery_auxiliary + machinery_shafting

    # Calculate outfit weight
    outfit_accommodation, outfit_equipment, outfit_systems, outfit_coeffs = calculate_outfit_weight(
        length_bp=length_bp,
        beam=beam,
        depth=depth,
        vessel_category=vessel_category,
        crew_capacity=crew_capacity,
        passenger_capacity=passenger_capacity,
    )
    outfit_weight = outfit_accommodation + outfit_equipment + outfit_systems

    # Total lightship
    lightship_weight = hull_steel_weight + machinery_weight + outfit_weight
    margin_weight = lightship_weight * design_margin
    total_lightship = lightship_weight + margin_weight

    # Estimate centers of gravity
    draft = depth * 0.65

    # Hull KG typically at 0.55-0.65 of depth
    kg_hull = depth * 0.58

    # Machinery KG depends on engine room height
    # Typically in lower portion of vessel
    kg_machinery = depth * 0.35

    # Outfit KG typically higher (superstructure, deck equipment)
    kg_outfit = depth * 0.75

    # Combined KG (weighted average)
    if lightship_weight > 0:
        kg_lightship = (
            hull_steel_weight * kg_hull +
            machinery_weight * kg_machinery +
            outfit_weight * kg_outfit
        ) / lightship_weight
    else:
        kg_lightship = depth * 0.55

    # LCG estimates (from AP)
    # Hull LCG typically at 0.50-0.52 Lbp from AP
    lcg_hull = length_bp * 0.51

    # Machinery LCG (engine room typically 0.35-0.45 Lbp from AP)
    lcg_machinery = length_bp * 0.40

    # Outfit LCG (spread throughout, slightly aft of midship)
    lcg_outfit = length_bp * 0.48

    # Combined LCG
    if lightship_weight > 0:
        lcg_lightship = (
            hull_steel_weight * lcg_hull +
            machinery_weight * lcg_machinery +
            outfit_weight * lcg_outfit
        ) / lightship_weight
    else:
        lcg_lightship = length_bp * 0.50

    # Combine coefficients
    all_coefficients = {
        "hull": hull_coeffs,
        "machinery": mach_coeffs,
        "outfit": outfit_coeffs,
        "design_margin": design_margin,
    }

    return LightshipResult(
        hull_steel_weight=hull_steel_weight,
        machinery_weight=machinery_weight,
        outfit_weight=outfit_weight,
        lightship_weight=lightship_weight,
        margin_weight=margin_weight,
        total_lightship=total_lightship,
        hull_structure=hull_structure,
        hull_superstructure=hull_superstructure,
        machinery_main=machinery_main,
        machinery_auxiliary=machinery_auxiliary,
        machinery_shafting=machinery_shafting,
        outfit_accommodation=outfit_accommodation,
        outfit_equipment=outfit_equipment,
        outfit_systems=outfit_systems,
        kg_hull=kg_hull,
        kg_machinery=kg_machinery,
        kg_outfit=kg_outfit,
        kg_lightship=kg_lightship,
        lcg_hull=lcg_hull,
        lcg_machinery=lcg_machinery,
        lcg_outfit=lcg_outfit,
        lcg_lightship=lcg_lightship,
        method="Watson-Gilfillan",
        vessel_category=vessel_category.value,
        coefficients=all_coefficients,
    )


def generate_lightship_report(result: LightshipResult, vessel_name: str = "Vessel") -> str:
    """Generate human-readable lightship weight report."""
    lines = [
        f"LIGHTSHIP WEIGHT REPORT - {vessel_name}",
        "=" * 50,
        "",
        f"Method: {result.method}",
        f"Vessel Category: {result.vessel_category}",
        "",
        "WEIGHT SUMMARY",
        "-" * 30,
        f"Hull Steel:      {result.hull_steel_weight:8.1f} t",
        f"  - Structure:   {result.hull_structure:8.1f} t",
        f"  - Superstr:    {result.hull_superstructure:8.1f} t",
        "",
        f"Machinery:       {result.machinery_weight:8.1f} t",
        f"  - Main Eng:    {result.machinery_main:8.1f} t",
        f"  - Auxiliary:   {result.machinery_auxiliary:8.1f} t",
        f"  - Shafting:    {result.machinery_shafting:8.1f} t",
        "",
        f"Outfit:          {result.outfit_weight:8.1f} t",
        f"  - Accommod:    {result.outfit_accommodation:8.1f} t",
        f"  - Equipment:   {result.outfit_equipment:8.1f} t",
        f"  - Systems:     {result.outfit_systems:8.1f} t",
        "",
        "-" * 30,
        f"Lightship:       {result.lightship_weight:8.1f} t",
        f"Design Margin:   {result.margin_weight:8.1f} t",
        "-" * 30,
        f"TOTAL LIGHTSHIP: {result.total_lightship:8.1f} t",
        "",
        "CENTER OF GRAVITY",
        "-" * 30,
        f"KG Lightship:    {result.kg_lightship:8.2f} m",
        f"LCG Lightship:   {result.lcg_lightship:8.2f} m (from AP)",
        "",
    ]
    return "\n".join(lines)
