"""
Weight distribution module.

Provides:
- Individual weight item tracking with position
- Weight distribution calculations (KG, LCG, TCG)
- Loading condition analysis
- Trim and stability verification

References:
- Intact Stability Code (IS Code 2008)
- Classification society rules for weight distribution
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum
import math


class WeightCategory(Enum):
    """Category of weight item for grouping."""
    HULL_STRUCTURE = "hull_structure"
    SUPERSTRUCTURE = "superstructure"
    MACHINERY_MAIN = "machinery_main"
    MACHINERY_AUXILIARY = "machinery_auxiliary"
    SHAFTING = "shafting"
    OUTFIT_ACCOMMODATION = "outfit_accommodation"
    OUTFIT_EQUIPMENT = "outfit_equipment"
    OUTFIT_SYSTEMS = "outfit_systems"
    CARGO = "cargo"
    FUEL = "fuel"
    FRESH_WATER = "fresh_water"
    BALLAST = "ballast"
    STORES = "stores"
    CREW = "crew"
    PASSENGERS = "passengers"
    MARGIN = "margin"
    OTHER = "other"


@dataclass
class WeightItem:
    """Individual weight item with location."""
    name: str
    weight: float              # tonnes
    lcg: float                 # m from AP (longitudinal center of gravity)
    vcg: float                 # m above baseline (vertical center of gravity)
    tcg: float = 0.0           # m from centerline (transverse, + = starboard)
    category: WeightCategory = WeightCategory.OTHER

    # Optional free surface moment (for tanks)
    free_surface_moment: float = 0.0  # t-m (for liquid tanks)

    # Optional bounds
    lcg_fwd: Optional[float] = None   # Forward extent from AP
    lcg_aft: Optional[float] = None   # Aft extent from AP
    vcg_top: Optional[float] = None   # Top extent
    vcg_bottom: Optional[float] = None  # Bottom extent

    # Metadata
    is_consumable: bool = False       # Changes during voyage
    fill_percentage: float = 100.0    # For tanks


@dataclass
class WeightDistribution:
    """Complete weight distribution result."""
    # Items
    items: List[WeightItem]

    # Totals
    total_weight: float        # tonnes
    lightship_weight: float    # tonnes
    deadweight: float          # tonnes

    # Centers of gravity
    lcg: float                 # m from AP
    vcg: float                 # m above baseline (KG)
    tcg: float                 # m from centerline

    # Moments
    moment_lcg: float          # t-m
    moment_vcg: float          # t-m
    moment_tcg: float          # t-m

    # Free surface correction
    free_surface_moment: float  # t-m
    free_surface_correction: float  # m (GG' = FSM / displacement)
    vcg_corrected: float       # m (KG corrected for free surface)

    # Category summaries
    category_weights: Dict[str, float] = field(default_factory=dict)
    category_lcg: Dict[str, float] = field(default_factory=dict)
    category_vcg: Dict[str, float] = field(default_factory=dict)

    # Trim related (requires hydrostatics)
    trim_moment: Optional[float] = None  # t-m about LCF
    estimated_trim: Optional[float] = None  # m (+ = stern trim)

    # Heel related
    heel_moment: float = 0.0   # t-m
    estimated_heel: float = 0.0  # degrees

    # Warnings
    warnings: List[str] = field(default_factory=list)


def calculate_weight_distribution(
    items: List[WeightItem],
    displacement: float = 0.0,
    lcf: float = 0.0,
    mct: float = 0.0,
    gm: float = 0.0,
) -> WeightDistribution:
    """
    Calculate weight distribution from list of items.

    Args:
        items: List of WeightItem objects
        displacement: Design displacement for free surface correction
        lcf: Longitudinal center of flotation (m from AP) for trim
        mct: Moment to change trim 1 cm (t-m/cm) for trim calculation
        gm: Metacentric height (m) for heel calculation

    Returns:
        WeightDistribution with complete analysis
    """
    if not items:
        return WeightDistribution(
            items=[],
            total_weight=0,
            lightship_weight=0,
            deadweight=0,
            lcg=0,
            vcg=0,
            tcg=0,
            moment_lcg=0,
            moment_vcg=0,
            moment_tcg=0,
            free_surface_moment=0,
            free_surface_correction=0,
            vcg_corrected=0,
        )

    # Calculate moments
    total_weight = 0.0
    moment_lcg = 0.0
    moment_vcg = 0.0
    moment_tcg = 0.0
    free_surface_moment = 0.0

    lightship_weight = 0.0
    deadweight = 0.0

    # Category accumulators
    category_weights: Dict[str, float] = {}
    category_moment_lcg: Dict[str, float] = {}
    category_moment_vcg: Dict[str, float] = {}

    lightship_categories = {
        WeightCategory.HULL_STRUCTURE,
        WeightCategory.SUPERSTRUCTURE,
        WeightCategory.MACHINERY_MAIN,
        WeightCategory.MACHINERY_AUXILIARY,
        WeightCategory.SHAFTING,
        WeightCategory.OUTFIT_ACCOMMODATION,
        WeightCategory.OUTFIT_EQUIPMENT,
        WeightCategory.OUTFIT_SYSTEMS,
        WeightCategory.MARGIN,
    }

    for item in items:
        weight = item.weight
        total_weight += weight
        moment_lcg += weight * item.lcg
        moment_vcg += weight * item.vcg
        moment_tcg += weight * item.tcg
        free_surface_moment += item.free_surface_moment

        # Category accumulation
        cat_name = item.category.value
        category_weights[cat_name] = category_weights.get(cat_name, 0) + weight
        category_moment_lcg[cat_name] = category_moment_lcg.get(cat_name, 0) + weight * item.lcg
        category_moment_vcg[cat_name] = category_moment_vcg.get(cat_name, 0) + weight * item.vcg

        # Lightship vs deadweight
        if item.category in lightship_categories:
            lightship_weight += weight
        else:
            deadweight += weight

    # Calculate centers of gravity
    if total_weight > 0:
        lcg = moment_lcg / total_weight
        vcg = moment_vcg / total_weight
        tcg = moment_tcg / total_weight
    else:
        lcg = vcg = tcg = 0.0

    # Category centers of gravity
    category_lcg = {}
    category_vcg = {}
    for cat_name in category_weights:
        cat_weight = category_weights[cat_name]
        if cat_weight > 0:
            category_lcg[cat_name] = category_moment_lcg[cat_name] / cat_weight
            category_vcg[cat_name] = category_moment_vcg[cat_name] / cat_weight
        else:
            category_lcg[cat_name] = 0
            category_vcg[cat_name] = 0

    # Free surface correction
    if displacement > 0:
        free_surface_correction = free_surface_moment / displacement
    else:
        free_surface_correction = 0.0

    vcg_corrected = vcg + free_surface_correction

    # Trim calculation
    trim_moment = None
    estimated_trim = None
    if lcf > 0 and mct > 0:
        # Trim moment about LCF
        trim_moment = total_weight * (lcg - lcf)
        # Trim in meters (positive = stern down)
        estimated_trim = trim_moment / (mct * 100)  # MCT is per cm

    # Heel calculation
    heel_moment = moment_tcg
    estimated_heel = 0.0
    if gm > 0 and total_weight > 0:
        # tan(heel) = heeling moment / (W * GM)
        tan_heel = heel_moment / (total_weight * gm)
        estimated_heel = math.degrees(math.atan(tan_heel))

    # Generate warnings
    warnings = []

    if tcg != 0:
        if abs(tcg) > 0.1:
            warnings.append(f"Significant transverse offset: TCG = {tcg:.2f} m")
        if abs(estimated_heel) > 1.0:
            warnings.append(f"Initial heel: {estimated_heel:.1f}°")

    if free_surface_correction > 0.1:
        warnings.append(f"Significant free surface effect: {free_surface_correction:.2f} m")

    if estimated_trim is not None and abs(estimated_trim) > 1.0:
        trim_direction = "by stern" if estimated_trim > 0 else "by bow"
        warnings.append(f"Significant trim: {abs(estimated_trim):.2f} m {trim_direction}")

    return WeightDistribution(
        items=items,
        total_weight=total_weight,
        lightship_weight=lightship_weight,
        deadweight=deadweight,
        lcg=lcg,
        vcg=vcg,
        tcg=tcg,
        moment_lcg=moment_lcg,
        moment_vcg=moment_vcg,
        moment_tcg=moment_tcg,
        free_surface_moment=free_surface_moment,
        free_surface_correction=free_surface_correction,
        vcg_corrected=vcg_corrected,
        category_weights=category_weights,
        category_lcg=category_lcg,
        category_vcg=category_vcg,
        trim_moment=trim_moment,
        estimated_trim=estimated_trim,
        heel_moment=heel_moment,
        estimated_heel=estimated_heel,
        warnings=warnings,
    )


def create_lightship_items(
    lightship_result,  # LightshipResult from lightship.py
    length_bp: float,
) -> List[WeightItem]:
    """
    Create weight items from LightshipResult.

    Args:
        lightship_result: Result from calculate_lightship_weight()
        length_bp: Length between perpendiculars (m)

    Returns:
        List of WeightItem objects
    """
    items = []

    # Hull structure
    items.append(WeightItem(
        name="Hull Structure",
        weight=lightship_result.hull_structure,
        lcg=lightship_result.lcg_hull,
        vcg=lightship_result.kg_hull,
        category=WeightCategory.HULL_STRUCTURE,
    ))

    # Superstructure
    if lightship_result.hull_superstructure > 0:
        items.append(WeightItem(
            name="Superstructure",
            weight=lightship_result.hull_superstructure,
            lcg=length_bp * 0.55,  # Typically forward of midship
            vcg=lightship_result.kg_hull * 1.3,  # Above hull VCG
            category=WeightCategory.SUPERSTRUCTURE,
        ))

    # Main engines
    items.append(WeightItem(
        name="Main Engines",
        weight=lightship_result.machinery_main,
        lcg=lightship_result.lcg_machinery,
        vcg=lightship_result.kg_machinery,
        category=WeightCategory.MACHINERY_MAIN,
    ))

    # Auxiliary machinery
    items.append(WeightItem(
        name="Auxiliary Machinery",
        weight=lightship_result.machinery_auxiliary,
        lcg=lightship_result.lcg_machinery * 1.05,  # Slightly forward
        vcg=lightship_result.kg_machinery * 1.1,
        category=WeightCategory.MACHINERY_AUXILIARY,
    ))

    # Shafting and propulsion
    items.append(WeightItem(
        name="Shafting & Propellers",
        weight=lightship_result.machinery_shafting,
        lcg=length_bp * 0.20,  # Aft of engine room
        vcg=lightship_result.kg_machinery * 0.7,  # Low in hull
        category=WeightCategory.SHAFTING,
    ))

    # Accommodation
    items.append(WeightItem(
        name="Accommodation",
        weight=lightship_result.outfit_accommodation,
        lcg=length_bp * 0.60,  # Typically in superstructure area
        vcg=lightship_result.kg_outfit,
        category=WeightCategory.OUTFIT_ACCOMMODATION,
    ))

    # Equipment
    items.append(WeightItem(
        name="Deck Equipment",
        weight=lightship_result.outfit_equipment,
        lcg=length_bp * 0.50,  # Distributed
        vcg=lightship_result.kg_outfit * 0.9,
        category=WeightCategory.OUTFIT_EQUIPMENT,
    ))

    # Systems
    items.append(WeightItem(
        name="Ship Systems",
        weight=lightship_result.outfit_systems,
        lcg=length_bp * 0.48,  # Distributed throughout
        vcg=lightship_result.kg_outfit * 0.85,
        category=WeightCategory.OUTFIT_SYSTEMS,
    ))

    # Design margin
    if lightship_result.margin_weight > 0:
        items.append(WeightItem(
            name="Design Margin",
            weight=lightship_result.margin_weight,
            lcg=lightship_result.lcg_lightship,  # At lightship LCG
            vcg=lightship_result.kg_lightship,  # At lightship KG
            category=WeightCategory.MARGIN,
        ))

    return items


def create_deadweight_items(
    deadweight_result,  # DeadweightResult from deadweight.py
    length_bp: float,
    depth: float,
    fuel_tank_lcg: Optional[float] = None,
    fuel_tank_vcg: Optional[float] = None,
    cargo_lcg: Optional[float] = None,
    cargo_vcg: Optional[float] = None,
) -> List[WeightItem]:
    """
    Create weight items from DeadweightResult.

    Args:
        deadweight_result: Result from calculate_deadweight()
        length_bp: Length between perpendiculars (m)
        depth: Depth (m)
        fuel_tank_lcg: LCG of fuel tanks (m from AP)
        fuel_tank_vcg: VCG of fuel tanks (m above baseline)
        cargo_lcg: LCG of cargo (m from AP)
        cargo_vcg: VCG of cargo (m above baseline)

    Returns:
        List of WeightItem objects
    """
    items = []

    # Default tank positions if not specified
    if fuel_tank_lcg is None:
        fuel_tank_lcg = length_bp * 0.35  # Near engine room
    if fuel_tank_vcg is None:
        fuel_tank_vcg = depth * 0.25  # Double bottom tanks

    if cargo_lcg is None:
        cargo_lcg = length_bp * 0.50  # Midship
    if cargo_vcg is None:
        cargo_vcg = depth * 0.40  # Hold level

    # Cargo
    if deadweight_result.cargo_weight > 0:
        items.append(WeightItem(
            name="Cargo",
            weight=deadweight_result.cargo_weight,
            lcg=cargo_lcg,
            vcg=cargo_vcg,
            category=WeightCategory.CARGO,
            is_consumable=False,
        ))

    # Fuel
    if deadweight_result.fuel_weight > 0:
        # Estimate free surface moment for fuel tanks
        # Simplified: assume 2 wing tanks
        tank_breadth = 3.0  # Assumed tank breadth (m)
        tank_length = 8.0   # Assumed tank length (m)
        fsm = 2 * (1/12) * tank_length * (tank_breadth ** 3) * 1.025  # t-m per tank pair

        items.append(WeightItem(
            name=f"Fuel ({deadweight_result.fuel_type.upper()})",
            weight=deadweight_result.fuel_weight,
            lcg=fuel_tank_lcg,
            vcg=fuel_tank_vcg,
            category=WeightCategory.FUEL,
            is_consumable=True,
            free_surface_moment=fsm,
        ))

    # Fresh water
    if deadweight_result.fresh_water_weight > 0:
        items.append(WeightItem(
            name="Fresh Water",
            weight=deadweight_result.fresh_water_weight,
            lcg=length_bp * 0.45,
            vcg=depth * 0.30,
            category=WeightCategory.FRESH_WATER,
            is_consumable=True,
            free_surface_moment=5.0,  # Simplified estimate
        ))

    # Stores
    if deadweight_result.stores_weight > 0:
        items.append(WeightItem(
            name="Stores & Provisions",
            weight=deadweight_result.stores_weight,
            lcg=length_bp * 0.55,
            vcg=depth * 0.50,
            category=WeightCategory.STORES,
            is_consumable=True,
        ))

    # Crew effects
    if deadweight_result.crew_effects_weight > 0:
        items.append(WeightItem(
            name="Crew Effects",
            weight=deadweight_result.crew_effects_weight,
            lcg=length_bp * 0.60,
            vcg=depth * 0.70,  # Accommodation deck
            category=WeightCategory.CREW,
        ))

    # Ballast
    if deadweight_result.ballast_weight > 0:
        items.append(WeightItem(
            name="Ballast Water",
            weight=deadweight_result.ballast_weight,
            lcg=length_bp * 0.45,
            vcg=depth * 0.20,  # Double bottom
            category=WeightCategory.BALLAST,
            free_surface_moment=20.0,  # Significant for large tanks
        ))

    return items


def generate_distribution_report(dist: WeightDistribution, vessel_name: str = "Vessel") -> str:
    """Generate weight distribution report."""
    lines = [
        f"WEIGHT DISTRIBUTION REPORT - {vessel_name}",
        "=" * 60,
        "",
        "SUMMARY",
        "-" * 40,
        f"Total Weight:     {dist.total_weight:10.1f} t",
        f"  Lightship:      {dist.lightship_weight:10.1f} t",
        f"  Deadweight:     {dist.deadweight:10.1f} t",
        "",
        "CENTERS OF GRAVITY",
        "-" * 40,
        f"LCG (from AP):    {dist.lcg:10.2f} m",
        f"VCG (KG):         {dist.vcg:10.2f} m",
        f"TCG:              {dist.tcg:10.2f} m",
        "",
        "FREE SURFACE EFFECT",
        "-" * 40,
        f"FSM Total:        {dist.free_surface_moment:10.1f} t-m",
        f"FS Correction:    {dist.free_surface_correction:10.3f} m",
        f"KG Corrected:     {dist.vcg_corrected:10.2f} m",
        "",
    ]

    if dist.estimated_trim is not None:
        lines.extend([
            "TRIM",
            "-" * 40,
            f"Trim Moment:      {dist.trim_moment:10.1f} t-m",
            f"Estimated Trim:   {dist.estimated_trim:10.2f} m",
            "",
        ])

    if abs(dist.estimated_heel) > 0.01:
        lines.extend([
            "HEEL",
            "-" * 40,
            f"Heel Moment:      {dist.heel_moment:10.1f} t-m",
            f"Estimated Heel:   {dist.estimated_heel:10.2f}°",
            "",
        ])

    # Category breakdown
    lines.extend([
        "WEIGHT BY CATEGORY",
        "-" * 40,
    ])

    for cat_name, cat_weight in sorted(dist.category_weights.items()):
        cat_lcg = dist.category_lcg.get(cat_name, 0)
        cat_vcg = dist.category_vcg.get(cat_name, 0)
        lines.append(f"{cat_name:20s} {cat_weight:8.1f} t  LCG:{cat_lcg:6.1f}m  VCG:{cat_vcg:5.1f}m")

    lines.append("")

    # Warnings
    if dist.warnings:
        lines.extend([
            "WARNINGS",
            "-" * 40,
        ])
        for warning in dist.warnings:
            lines.append(f"  ⚠ {warning}")
        lines.append("")

    return "\n".join(lines)
