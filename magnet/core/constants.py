"""
MAGNET Physical Constants and System Configuration

Constants used throughout the MAGNET system for physics calculations
and system configuration.
"""

from typing import Dict

# ==================== Physical Constants ====================

# Water properties
SEAWATER_DENSITY_KG_M3 = 1025.0  # kg/m³ at 15°C, 35 ppt salinity
FRESHWATER_DENSITY_KG_M3 = 1000.0  # kg/m³ at 15°C
WATER_KINEMATIC_VISCOSITY = 1.19e-6  # m²/s for seawater at 15°C

# Gravitational acceleration
GRAVITY_M_S2 = 9.81  # m/s²
GRAVITY_FT_S2 = 32.174  # ft/s²

# Air properties
AIR_DENSITY_KG_M3 = 1.225  # kg/m³ at sea level, 15°C
AIR_KINEMATIC_VISCOSITY = 1.48e-5  # m²/s at 15°C

# Unit conversions - Length
METERS_TO_FEET = 3.28084
FEET_TO_METERS = 0.3048
METERS_TO_INCHES = 39.3701
INCHES_TO_METERS = 0.0254
NM_TO_METERS = 1852.0  # Nautical miles to meters
METERS_TO_NM = 1 / NM_TO_METERS

# Unit conversions - Speed
KNOTS_TO_MS = 0.514444
MS_TO_KNOTS = 1.94384
KNOTS_TO_MPH = 1.15078
MPH_TO_KNOTS = 0.868976
KNOTS_TO_KMH = 1.852
KMH_TO_KNOTS = 0.539957

# Unit conversions - Mass/Force
KG_TO_LBS = 2.20462
LBS_TO_KG = 0.453592
MT_TO_LT = 0.984207  # Metric tons to long tons
LT_TO_MT = 1.01605
MT_TO_ST = 1.10231  # Metric tons to short tons
NEWTON_TO_KN = 0.001
KN_TO_NEWTON = 1000.0

# Unit conversions - Power
KW_TO_HP = 1.34102
HP_TO_KW = 0.745700
KW_TO_BHP = 1.34102  # Brake horsepower

# Unit conversions - Pressure
PA_TO_PSI = 0.000145038
PSI_TO_PA = 6894.76
PA_TO_BAR = 1e-5
BAR_TO_PA = 1e5
PA_TO_KPA = 0.001
KPA_TO_PA = 1000.0

# Unit conversions - Temperature
def celsius_to_fahrenheit(c: float) -> float:
    return c * 9/5 + 32

def fahrenheit_to_celsius(f: float) -> float:
    return (f - 32) * 5/9

def celsius_to_kelvin(c: float) -> float:
    return c + 273.15

def kelvin_to_celsius(k: float) -> float:
    return k - 273.15

# ==================== Naval Architecture Constants ====================

# Froude number thresholds
FROUDE_DISPLACEMENT_MAX = 0.4
FROUDE_SEMI_DISPLACEMENT_MAX = 0.9
FROUDE_PLANING_THRESHOLD = 1.0

# Hull coefficient typical ranges
CB_PLANING_TYPICAL = (0.35, 0.45)
CB_SEMI_DISPLACEMENT_TYPICAL = (0.45, 0.55)
CB_DISPLACEMENT_TYPICAL = (0.55, 0.85)

CP_TYPICAL_RANGE = (0.55, 0.75)
CM_TYPICAL_RANGE = (0.70, 0.98)
CWP_TYPICAL_RANGE = (0.65, 0.90)

# Deadrise angle typical ranges (degrees)
DEADRISE_PLANING_TYPICAL = (15, 25)
DEADRISE_SEMI_PLANING_TYPICAL = (10, 20)
DEADRISE_DISPLACEMENT_TYPICAL = (0, 15)

# ==================== Stability Constants ====================

# GM requirements (meters) - general guidelines
GM_MIN_PASSENGER = 0.35
GM_MIN_CARGO = 0.15
GM_MIN_FISHING = 0.35
GM_MIN_WORKBOAT = 0.50

# GZ curve requirements (IMO A.749)
AREA_0_30_MIN = 0.055  # m-rad
AREA_0_40_MIN = 0.090  # m-rad
AREA_30_40_MIN = 0.030  # m-rad
GZ_AT_30_MIN = 0.20  # m
ANGLE_GZ_MAX_MIN = 25  # degrees

# Maximum allowable heel angles
HEEL_PASSENGER_MAX = 10  # degrees
HEEL_CARGO_MAX = 15  # degrees
HEEL_WIND_MAX = 16  # degrees

# ==================== Structural Constants ====================

# Material properties (typical values)
ALUMINUM_5083_YIELD_MPA = 215
ALUMINUM_5083_UTS_MPA = 305
ALUMINUM_5083_DENSITY_KG_M3 = 2660
ALUMINUM_5083_E_GPA = 70

ALUMINUM_6061_YIELD_MPA = 276
ALUMINUM_6061_UTS_MPA = 310
ALUMINUM_6061_DENSITY_KG_M3 = 2700
ALUMINUM_6061_E_GPA = 68.9

STEEL_A36_YIELD_MPA = 250
STEEL_A36_UTS_MPA = 400
STEEL_DENSITY_KG_M3 = 7850
STEEL_E_GPA = 200

# Weld efficiency factors
WELD_EFFICIENCY_FULL_PENETRATION = 1.0
WELD_EFFICIENCY_FILLET = 0.7
WELD_EFFICIENCY_PLUG = 0.5

# Safety factors
SF_PLATING = 2.5
SF_STIFFENERS = 2.0
SF_PRIMARY_STRUCTURE = 2.5
SF_CRITICAL_JOINTS = 3.0

# ==================== Propulsion Constants ====================

# Propeller efficiency typical ranges
PROPELLER_EFFICIENCY_TYPICAL = (0.55, 0.75)
WATERJET_EFFICIENCY_TYPICAL = (0.60, 0.80)
POD_EFFICIENCY_TYPICAL = (0.65, 0.85)

# Wake fraction typical ranges
WAKE_FRACTION_SINGLE_SCREW = (0.20, 0.40)
WAKE_FRACTION_TWIN_SCREW = (0.05, 0.15)
WAKE_FRACTION_WATERJET = (0.05, 0.10)

# Thrust deduction typical ranges
THRUST_DEDUCTION_SINGLE = (0.15, 0.25)
THRUST_DEDUCTION_TWIN = (0.10, 0.20)

# Hull efficiency
HULL_EFFICIENCY_TYPICAL = (1.0, 1.2)

# Relative rotative efficiency
RRE_TYPICAL = (0.95, 1.05)

# ==================== System Configuration ====================

# Version information
DESIGN_STATE_VERSION = "1.19.0"
PHASE_MACHINE_VERSION = "1.1.0"
MAGNET_VERSION = "1.0.0"

# Default tolerances
TOLERANCE_LENGTH_M = 0.001  # 1mm
TOLERANCE_MASS_KG = 0.1
TOLERANCE_ANGLE_DEG = 0.01
TOLERANCE_PERCENTAGE = 0.01  # 1%

# Phase configuration
DESIGN_PHASES = [
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

# Section names for DesignState
DESIGN_STATE_SECTIONS = [
    "mission",
    "hull",
    "structural_design",
    "structural_loads",
    "propulsion",
    "weight",
    "stability",
    "loading",
    "arrangement",
    "compliance",
    "production",
    "cost",
    "optimization",
    "reports",
    "kernel",
    "analysis",
    "performance",
    "systems",
    "outfitting",
    "environmental",
    "deck_equipment",
    "vision",
    "resistance",
    "seakeeping",
    "maneuvering",
    "electrical",
    "safety",
]

# Maximum values for validation
MAX_LOA_M = 500.0
MAX_BEAM_M = 100.0
MAX_DRAFT_M = 30.0
MAX_SPEED_KTS = 100.0
MAX_DISPLACEMENT_MT = 500000.0
MAX_POWER_KW = 100000.0

# Minimum values for validation
MIN_LOA_M = 1.0
MIN_BEAM_M = 0.5
MIN_DRAFT_M = 0.1
MIN_SPEED_KTS = 0.1
