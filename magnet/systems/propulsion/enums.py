"""
systems/propulsion/enums.py - Propulsion system enumerations
ALPHA OWNS THIS FILE.

Section 26: Propulsion System
"""

from enum import Enum


class EngineType(Enum):
    """Main engine type classification."""
    DIESEL_HIGH_SPEED = "diesel_high_speed"
    DIESEL_MEDIUM_SPEED = "diesel_medium_speed"
    GAS_TURBINE = "gas_turbine"
    DIESEL_ELECTRIC = "diesel_electric"
    HYBRID = "hybrid"


class PropulsorType(Enum):
    """Propulsor classification."""
    FIXED_PITCH_PROPELLER = "fpp"
    CONTROLLABLE_PITCH_PROPELLER = "cpp"
    WATERJET = "waterjet"
    SURFACE_DRIVE = "surface_drive"
    POD_DRIVE = "pod_drive"
    OUTBOARD = "outboard"
    STERN_DRIVE = "stern_drive"


class GearboxType(Enum):
    """Reduction gear type."""
    SINGLE_SPEED = "single_speed"
    TWO_SPEED = "two_speed"
    DIRECT_DRIVE = "direct_drive"


class ShaftMaterial(Enum):
    """Propeller shaft material."""
    STAINLESS_316 = "ss316"
    STAINLESS_17_4PH = "ss17-4ph"
    MONEL_K500 = "monel_k500"
    AQUAMET_22 = "aquamet_22"


class PropellerMaterial(Enum):
    """Propeller material."""
    NIBRAL = "nibral"
    MANGANESE_BRONZE = "mn_bronze"
    STAINLESS_STEEL = "stainless"
    COMPOSITE = "composite"


class FuelType(Enum):
    """Fuel type."""
    MGO = "mgo"
    MDO = "mdo"
    HFO = "hfo"
    LNG = "lng"
    METHANOL = "methanol"
    BATTERY = "battery"
