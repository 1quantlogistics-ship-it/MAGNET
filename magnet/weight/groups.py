"""
Weight Group Constants and Coefficients

Module 07 v1.1 - Weight Estimation Framework

SWBS group coefficients for parametric weight estimation:
- Hull structure (Watson-Gilfillan)
- Propulsion plant (specific weight method)
- Electrical, Command, Auxiliary, Outfit (percentage/parametric)
- Margin factors by vessel type
"""

from dataclasses import dataclass
from typing import Dict

# Re-export core types from items for backward compatibility
from .items import (
    SWBSGroup,
    WeightItem,
    WeightConfidence,
    GroupSummary,
    SWBS_GROUP_NAMES,
    create_weight_item,
)


# =============================================================================
# HULL STRUCTURE COEFFICIENTS (Group 100)
# =============================================================================

@dataclass(frozen=True)
class HullCoefficients:
    """Watson-Gilfillan hull structure coefficients."""

    # K factor for steel weight: W = E^1.36 * K
    # E = Lloyd's equipment numeral = L * (B + D)
    K_MONOHULL: float = 0.034
    K_CATAMARAN: float = 0.038  # Higher due to two hulls
    K_TRIMARAN: float = 0.042
    K_SWATH: float = 0.045      # Complex structure

    # Material factors (relative to steel = 1.0)
    MATERIAL_STEEL: float = 1.0
    MATERIAL_ALUMINUM: float = 0.55
    MATERIAL_FRP: float = 0.45
    MATERIAL_COMPOSITE: float = 0.40

    # Service factors for structural requirements
    SERVICE_COMMERCIAL: float = 1.0
    SERVICE_MILITARY: float = 1.15
    SERVICE_HIGH_SPEED: float = 1.10
    SERVICE_ICECLASS: float = 1.25

    # Exponent for Lloyd's E numeral
    EXPONENT: float = 1.36


HULL_COEFFICIENTS = HullCoefficients()


# K factor lookup by hull type
HULL_K_FACTOR: Dict[str, float] = {
    "monohull": HULL_COEFFICIENTS.K_MONOHULL,
    "catamaran": HULL_COEFFICIENTS.K_CATAMARAN,
    "trimaran": HULL_COEFFICIENTS.K_TRIMARAN,
    "swath": HULL_COEFFICIENTS.K_SWATH,
}

# Material factor lookup
MATERIAL_FACTOR: Dict[str, float] = {
    "steel": HULL_COEFFICIENTS.MATERIAL_STEEL,
    "aluminum": HULL_COEFFICIENTS.MATERIAL_ALUMINUM,
    "aluminium": HULL_COEFFICIENTS.MATERIAL_ALUMINUM,  # British spelling
    "frp": HULL_COEFFICIENTS.MATERIAL_FRP,
    "grp": HULL_COEFFICIENTS.MATERIAL_FRP,  # Glass reinforced plastic
    "composite": HULL_COEFFICIENTS.MATERIAL_COMPOSITE,
    "cfrp": HULL_COEFFICIENTS.MATERIAL_COMPOSITE,  # Carbon fiber
}

# Service factor lookup
SERVICE_FACTOR: Dict[str, float] = {
    "commercial": HULL_COEFFICIENTS.SERVICE_COMMERCIAL,
    "military": HULL_COEFFICIENTS.SERVICE_MILITARY,
    "naval": HULL_COEFFICIENTS.SERVICE_MILITARY,
    "high_speed": HULL_COEFFICIENTS.SERVICE_HIGH_SPEED,
    "hsv": HULL_COEFFICIENTS.SERVICE_HIGH_SPEED,
    "ice_class": HULL_COEFFICIENTS.SERVICE_ICECLASS,
    "iceclass": HULL_COEFFICIENTS.SERVICE_ICECLASS,
}


# =============================================================================
# PROPULSION PLANT COEFFICIENTS (Group 200)
# =============================================================================

@dataclass(frozen=True)
class PropulsionCoefficients:
    """Propulsion plant weight coefficients."""

    # Specific weight (kg per kW installed)
    SPECIFIC_WEIGHT_HSD: float = 2.5   # High-speed diesel
    SPECIFIC_WEIGHT_MSD: float = 4.0   # Medium-speed diesel
    SPECIFIC_WEIGHT_LSD: float = 8.0   # Low-speed diesel (large ships)
    SPECIFIC_WEIGHT_GT: float = 0.5    # Gas turbine
    SPECIFIC_WEIGHT_CODAG: float = 1.5 # Combined diesel and gas
    SPECIFIC_WEIGHT_CODLAG: float = 2.0 # Combined diesel-electric and gas
    SPECIFIC_WEIGHT_OUTBOARD: float = 1.5
    SPECIFIC_WEIGHT_WATERJET: float = 2.0
    SPECIFIC_WEIGHT_ELECTRIC: float = 3.0  # Battery electric

    # Component factors (fraction of engine weight)
    GEARBOX_FACTOR: float = 0.15
    SHAFTING_FACTOR: float = 0.10
    PROPELLER_FACTOR: float = 0.05
    EXHAUST_FACTOR: float = 0.08
    FUEL_SYSTEM_FACTOR: float = 0.05
    CONTROLS_FACTOR: float = 0.03


PROPULSION_COEFFICIENTS = PropulsionCoefficients()


# Specific weight lookup by engine type
ENGINE_SPECIFIC_WEIGHT: Dict[str, float] = {
    "hsd": PROPULSION_COEFFICIENTS.SPECIFIC_WEIGHT_HSD,
    "high_speed_diesel": PROPULSION_COEFFICIENTS.SPECIFIC_WEIGHT_HSD,
    "msd": PROPULSION_COEFFICIENTS.SPECIFIC_WEIGHT_MSD,
    "medium_speed_diesel": PROPULSION_COEFFICIENTS.SPECIFIC_WEIGHT_MSD,
    "lsd": PROPULSION_COEFFICIENTS.SPECIFIC_WEIGHT_LSD,
    "low_speed_diesel": PROPULSION_COEFFICIENTS.SPECIFIC_WEIGHT_LSD,
    "gt": PROPULSION_COEFFICIENTS.SPECIFIC_WEIGHT_GT,
    "gas_turbine": PROPULSION_COEFFICIENTS.SPECIFIC_WEIGHT_GT,
    "codag": PROPULSION_COEFFICIENTS.SPECIFIC_WEIGHT_CODAG,
    "codlag": PROPULSION_COEFFICIENTS.SPECIFIC_WEIGHT_CODLAG,
    "outboard": PROPULSION_COEFFICIENTS.SPECIFIC_WEIGHT_OUTBOARD,
    "waterjet": PROPULSION_COEFFICIENTS.SPECIFIC_WEIGHT_WATERJET,
    "electric": PROPULSION_COEFFICIENTS.SPECIFIC_WEIGHT_ELECTRIC,
    "diesel_electric": PROPULSION_COEFFICIENTS.SPECIFIC_WEIGHT_ELECTRIC,
}


# =============================================================================
# ELECTRICAL PLANT COEFFICIENTS (Group 300)
# =============================================================================

@dataclass(frozen=True)
class ElectricalCoefficients:
    """Electrical plant weight coefficients."""

    # Specific weight for generators (kg per kW)
    GENERATOR_SPECIFIC_WEIGHT: float = 5.0

    # Electrical load factors
    SWITCHGEAR_FACTOR: float = 0.20   # Fraction of generator weight
    CABLING_FACTOR: float = 0.25
    LIGHTING_FACTOR: float = 0.10
    BATTERY_FACTOR: float = 0.15

    # Battery specific weight (kg per kWh)
    BATTERY_SPECIFIC_WEIGHT: float = 8.0  # Lead-acid
    BATTERY_LITHIUM_WEIGHT: float = 5.0   # Lithium-ion


ELECTRICAL_COEFFICIENTS = ElectricalCoefficients()


# =============================================================================
# COMMAND & SURVEILLANCE COEFFICIENTS (Group 400)
# =============================================================================

@dataclass(frozen=True)
class CommandCoefficients:
    """Command and surveillance weight coefficients."""

    # Base weights (kg) for standard equipment
    NAVIGATION_BASE: float = 500.0
    COMMUNICATION_BASE: float = 300.0
    FIRE_CONTROL_BASE: float = 0.0  # Military only

    # Scaling factors
    LENGTH_FACTOR: float = 5.0  # kg per meter LOA
    MILITARY_MULTIPLIER: float = 3.0


COMMAND_COEFFICIENTS = CommandCoefficients()


# =============================================================================
# AUXILIARY SYSTEMS COEFFICIENTS (Group 500)
# =============================================================================

@dataclass(frozen=True)
class AuxiliaryCoefficients:
    """Auxiliary systems weight coefficients."""

    # HVAC specific weight (kg per m³ interior volume)
    HVAC_SPECIFIC_WEIGHT: float = 2.0

    # Piping factors
    PIPING_FACTOR: float = 0.02  # Fraction of displacement

    # Anchor and mooring (kg per meter LOA)
    ANCHOR_FACTOR: float = 15.0

    # Fire fighting (kg per m² deck area)
    FIREFIGHTING_FACTOR: float = 1.5

    # Steering gear (kg per tonne displacement)
    STEERING_FACTOR: float = 0.5


AUXILIARY_COEFFICIENTS = AuxiliaryCoefficients()


# =============================================================================
# OUTFIT & FURNISHINGS COEFFICIENTS (Group 600)
# =============================================================================

@dataclass(frozen=True)
class OutfitCoefficients:
    """Outfit and furnishings weight coefficients."""

    # Per-person weights (kg)
    ACCOMMODATION_PER_PERSON: float = 150.0  # Basic
    ACCOMMODATION_LUXURY: float = 300.0      # High standard

    # Paint and coating (kg per m² wetted surface)
    PAINT_FACTOR: float = 0.5

    # Insulation (kg per m² hull area)
    INSULATION_FACTOR: float = 2.0

    # Deck covering (kg per m² deck area)
    DECK_COVERING_FACTOR: float = 3.0


OUTFIT_COEFFICIENTS = OutfitCoefficients()


# =============================================================================
# MARGIN FACTORS
# =============================================================================

# Design margin as percentage of base lightship weight
MARGIN_PERCENT: Dict[str, float] = {
    "commercial": 0.05,      # 5% margin
    "military": 0.10,        # 10% margin (growth allowance)
    "naval": 0.10,
    "prototype": 0.15,       # 15% margin for uncertainty
    "concept": 0.20,         # 20% margin for early design
    "detailed": 0.03,        # 3% margin for detailed design
}

# VCG factor for margin weight (placed higher than average)
MARGIN_VCG_FACTOR: float = 1.05

# LCG factor for margin weight (placed slightly aft)
MARGIN_LCG_FACTOR: float = 1.02


# =============================================================================
# DEFAULT CG FRACTIONS
# =============================================================================

# Default VCG as fraction of depth by SWBS group
DEFAULT_VCG_FRACTION: Dict[SWBSGroup, float] = {
    SWBSGroup.GROUP_100: 0.45,  # Hull structure - near mid-depth
    SWBSGroup.GROUP_200: 0.30,  # Propulsion - low in hull
    SWBSGroup.GROUP_300: 0.50,  # Electrical - mid-height
    SWBSGroup.GROUP_400: 0.85,  # Command - high (bridge)
    SWBSGroup.GROUP_500: 0.40,  # Auxiliary - below mid
    SWBSGroup.GROUP_600: 0.60,  # Outfit - above mid
    SWBSGroup.GROUP_700: 0.70,  # Armament - upper decks
    SWBSGroup.MARGIN: 0.50,     # Margin - at lightship VCG
}

# Default LCG as fraction of LWL from FP by SWBS group
DEFAULT_LCG_FRACTION: Dict[SWBSGroup, float] = {
    SWBSGroup.GROUP_100: 0.50,  # Hull structure - amidships
    SWBSGroup.GROUP_200: 0.70,  # Propulsion - aft
    SWBSGroup.GROUP_300: 0.55,  # Electrical - slightly aft
    SWBSGroup.GROUP_400: 0.25,  # Command - forward (bridge)
    SWBSGroup.GROUP_500: 0.50,  # Auxiliary - distributed
    SWBSGroup.GROUP_600: 0.45,  # Outfit - forward of midships
    SWBSGroup.GROUP_700: 0.40,  # Armament - forward
    SWBSGroup.MARGIN: 0.50,     # Margin - at lightship LCG
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_hull_k_factor(hull_type: str) -> float:
    """Get Watson-Gilfillan K factor for hull type."""
    return HULL_K_FACTOR.get(hull_type.lower(), HULL_COEFFICIENTS.K_MONOHULL)


def get_material_factor(material: str) -> float:
    """Get material weight factor."""
    return MATERIAL_FACTOR.get(material.lower(), HULL_COEFFICIENTS.MATERIAL_STEEL)


def get_service_factor(service: str) -> float:
    """Get service factor for structural requirements."""
    return SERVICE_FACTOR.get(service.lower(), HULL_COEFFICIENTS.SERVICE_COMMERCIAL)


def get_engine_specific_weight(engine_type: str) -> float:
    """Get engine specific weight in kg/kW."""
    return ENGINE_SPECIFIC_WEIGHT.get(
        engine_type.lower(),
        PROPULSION_COEFFICIENTS.SPECIFIC_WEIGHT_HSD
    )


def get_margin_percent(design_stage: str) -> float:
    """Get margin percentage for design stage."""
    return MARGIN_PERCENT.get(design_stage.lower(), 0.10)


def get_default_vcg_fraction(group: SWBSGroup) -> float:
    """Get default VCG fraction for SWBS group."""
    return DEFAULT_VCG_FRACTION.get(group, 0.50)


def get_default_lcg_fraction(group: SWBSGroup) -> float:
    """Get default LCG fraction for SWBS group."""
    return DEFAULT_LCG_FRACTION.get(group, 0.50)
