"""
magnet/routing/router/capacity_calc.py - Capacity Calculator

Calculates trunk sizing based on system type and demand.
Provides pipe diameter, cable size, and duct dimensions.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import math

from ..schema.system_type import SystemType, get_system_properties

__all__ = [
    'CapacityCalculator',
    'calculate_pipe_diameter',
    'calculate_cable_size',
    'calculate_duct_size',
    'SizingResult',
]


# =============================================================================
# Sizing Tables - Standard sizes for naval applications
# =============================================================================

# Pipe sizes (nominal diameter in mm) - DN sizes
STANDARD_PIPE_SIZES_MM = [
    15, 20, 25, 32, 40, 50, 65, 80, 100, 125, 150, 200, 250, 300, 350, 400, 450, 500
]

# Cable sizes (cross-section in mm²) - IEC standard
STANDARD_CABLE_SIZES_MM2 = [
    1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300, 400, 500
]

# Duct sizes (width x height in mm) - rectangular
STANDARD_DUCT_SIZES_MM = [
    (100, 100), (150, 100), (200, 100), (200, 150), (250, 150),
    (300, 150), (300, 200), (400, 200), (400, 250), (500, 250),
    (500, 300), (600, 300), (600, 400), (800, 400), (800, 500),
    (1000, 500), (1000, 600), (1200, 600),
]

# Circular duct sizes (diameter in mm)
STANDARD_CIRCULAR_DUCT_MM = [
    100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000
]


# =============================================================================
# System-Specific Parameters
# =============================================================================

@dataclass(frozen=True)
class FluidSizingParams:
    """Parameters for fluid system sizing."""
    max_velocity_m_s: float  # Maximum allowed velocity
    min_velocity_m_s: float  # Minimum velocity (avoid sedimentation)
    density_kg_m3: float     # Fluid density
    viscosity_cp: float      # Dynamic viscosity (centipoise)


# Fluid parameters by system type
FLUID_PARAMS: Dict[SystemType, FluidSizingParams] = {
    SystemType.FUEL: FluidSizingParams(
        max_velocity_m_s=2.0,
        min_velocity_m_s=0.5,
        density_kg_m3=850.0,
        viscosity_cp=5.0,
    ),
    SystemType.FRESHWATER: FluidSizingParams(
        max_velocity_m_s=3.0,
        min_velocity_m_s=0.3,
        density_kg_m3=1000.0,
        viscosity_cp=1.0,
    ),
    SystemType.SEAWATER: FluidSizingParams(
        max_velocity_m_s=3.5,
        min_velocity_m_s=0.5,
        density_kg_m3=1025.0,
        viscosity_cp=1.1,
    ),
    SystemType.GREY_WATER: FluidSizingParams(
        max_velocity_m_s=2.0,
        min_velocity_m_s=0.6,
        density_kg_m3=1010.0,
        viscosity_cp=1.5,
    ),
    SystemType.BLACK_WATER: FluidSizingParams(
        max_velocity_m_s=1.5,
        min_velocity_m_s=0.8,
        density_kg_m3=1020.0,
        viscosity_cp=2.0,
    ),
    SystemType.LUBE_OIL: FluidSizingParams(
        max_velocity_m_s=1.5,
        min_velocity_m_s=0.3,
        density_kg_m3=900.0,
        viscosity_cp=100.0,
    ),
    SystemType.HYDRAULIC: FluidSizingParams(
        max_velocity_m_s=6.0,
        min_velocity_m_s=1.0,
        density_kg_m3=870.0,
        viscosity_cp=30.0,
    ),
    SystemType.BILGE: FluidSizingParams(
        max_velocity_m_s=2.5,
        min_velocity_m_s=0.5,
        density_kg_m3=1010.0,
        viscosity_cp=1.5,
    ),
    SystemType.FIREFIGHTING: FluidSizingParams(
        max_velocity_m_s=4.0,
        min_velocity_m_s=1.0,
        density_kg_m3=1000.0,
        viscosity_cp=1.0,
    ),
    SystemType.COMPRESSED_AIR: FluidSizingParams(
        max_velocity_m_s=15.0,
        min_velocity_m_s=3.0,
        density_kg_m3=1.2,
        viscosity_cp=0.018,
    ),
    SystemType.STEAM: FluidSizingParams(
        max_velocity_m_s=30.0,
        min_velocity_m_s=10.0,
        density_kg_m3=2.0,
        viscosity_cp=0.012,
    ),
}


@dataclass(frozen=True)
class ElectricalSizingParams:
    """Parameters for electrical system sizing."""
    voltage_v: float           # System voltage
    power_factor: float        # Power factor (0.8-1.0)
    derating_factor: float     # Cable derating factor
    max_voltage_drop_pct: float  # Maximum allowed voltage drop


ELECTRICAL_PARAMS: Dict[SystemType, ElectricalSizingParams] = {
    SystemType.ELECTRICAL_HV: ElectricalSizingParams(
        voltage_v=6600.0,
        power_factor=0.85,
        derating_factor=0.8,
        max_voltage_drop_pct=3.0,
    ),
    SystemType.ELECTRICAL_LV: ElectricalSizingParams(
        voltage_v=440.0,
        power_factor=0.85,
        derating_factor=0.8,
        max_voltage_drop_pct=5.0,
    ),
    SystemType.ELECTRICAL_DC: ElectricalSizingParams(
        voltage_v=24.0,
        power_factor=1.0,
        derating_factor=0.9,
        max_voltage_drop_pct=5.0,
    ),
    SystemType.FIRE_DETECTION: ElectricalSizingParams(
        voltage_v=24.0,
        power_factor=1.0,
        derating_factor=0.9,
        max_voltage_drop_pct=3.0,
    ),
}


@dataclass(frozen=True)
class HVACSizingParams:
    """Parameters for HVAC system sizing."""
    max_velocity_m_s: float   # Maximum air velocity
    min_velocity_m_s: float   # Minimum velocity
    friction_factor: float    # Friction loss factor


HVAC_PARAMS: Dict[SystemType, HVACSizingParams] = {
    SystemType.HVAC_SUPPLY: HVACSizingParams(
        max_velocity_m_s=8.0,
        min_velocity_m_s=3.0,
        friction_factor=0.02,
    ),
    SystemType.HVAC_RETURN: HVACSizingParams(
        max_velocity_m_s=6.0,
        min_velocity_m_s=2.5,
        friction_factor=0.02,
    ),
    SystemType.HVAC_EXHAUST: HVACSizingParams(
        max_velocity_m_s=10.0,
        min_velocity_m_s=4.0,
        friction_factor=0.025,
    ),
}


# =============================================================================
# Result Classes
# =============================================================================

@dataclass
class SizingResult:
    """Result of a sizing calculation."""
    system_type: SystemType
    demand: float              # Input demand value
    demand_unit: str           # Unit of demand

    # Calculated size
    calculated_size: float     # Exact calculated size
    selected_size: float       # Selected standard size
    size_unit: str             # Unit of size

    # Additional info
    velocity: Optional[float] = None     # Fluid/air velocity
    pressure_drop: Optional[float] = None  # Per unit length
    utilization_pct: float = 0.0         # Capacity utilization

    # Validation
    is_valid: bool = True
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


# =============================================================================
# Core Calculation Functions
# =============================================================================

def calculate_pipe_diameter(
    flow_rate_m3_h: float,
    system_type: SystemType,
    length_m: float = 100.0,
) -> SizingResult:
    """
    Calculate pipe diameter for fluid systems.

    Args:
        flow_rate_m3_h: Flow rate in cubic meters per hour
        system_type: Type of fluid system
        length_m: Pipe length for pressure drop calculation

    Returns:
        SizingResult with pipe diameter
    """
    warnings = []

    # Get fluid parameters
    params = FLUID_PARAMS.get(system_type)
    if params is None:
        return SizingResult(
            system_type=system_type,
            demand=flow_rate_m3_h,
            demand_unit="m³/h",
            calculated_size=0,
            selected_size=0,
            size_unit="mm",
            is_valid=False,
            warnings=[f"No fluid parameters for {system_type.value}"],
        )

    # Convert flow rate to m³/s
    flow_rate_m3_s = flow_rate_m3_h / 3600.0

    # Calculate diameter for target velocity (using middle of range)
    target_velocity = (params.max_velocity_m_s + params.min_velocity_m_s) / 2

    # A = Q / v, D = sqrt(4A/π)
    area_m2 = flow_rate_m3_s / target_velocity
    diameter_m = math.sqrt(4 * area_m2 / math.pi)
    diameter_mm = diameter_m * 1000

    # Select standard size (next size up)
    selected_diameter = diameter_mm
    for std_size in STANDARD_PIPE_SIZES_MM:
        if std_size >= diameter_mm:
            selected_diameter = std_size
            break
    else:
        selected_diameter = STANDARD_PIPE_SIZES_MM[-1]
        warnings.append(f"Flow exceeds maximum pipe size, using {selected_diameter}mm")

    # Calculate actual velocity with selected size
    selected_area = math.pi * (selected_diameter / 1000) ** 2 / 4
    actual_velocity = flow_rate_m3_s / selected_area if selected_area > 0 else 0

    # Check velocity limits
    if actual_velocity > params.max_velocity_m_s:
        warnings.append(f"Velocity {actual_velocity:.2f} m/s exceeds max {params.max_velocity_m_s}")
    if actual_velocity < params.min_velocity_m_s and flow_rate_m3_h > 0:
        warnings.append(f"Velocity {actual_velocity:.2f} m/s below min {params.min_velocity_m_s}")

    # Estimate pressure drop (Darcy-Weisbach simplified)
    friction = 0.02  # Approximate friction factor
    if selected_diameter > 0:
        pressure_drop_pa_m = (
            friction * (length_m / (selected_diameter / 1000)) *
            (params.density_kg_m3 * actual_velocity ** 2 / 2)
        ) / length_m
    else:
        pressure_drop_pa_m = 0

    # Calculate utilization
    max_area = math.pi * (selected_diameter / 1000) ** 2 / 4
    max_flow = max_area * params.max_velocity_m_s * 3600
    utilization = (flow_rate_m3_h / max_flow * 100) if max_flow > 0 else 0

    return SizingResult(
        system_type=system_type,
        demand=flow_rate_m3_h,
        demand_unit="m³/h",
        calculated_size=diameter_mm,
        selected_size=selected_diameter,
        size_unit="mm DN",
        velocity=actual_velocity,
        pressure_drop=pressure_drop_pa_m,
        utilization_pct=utilization,
        is_valid=len([w for w in warnings if "exceeds" in w]) == 0,
        warnings=warnings,
    )


def calculate_cable_size(
    power_kw: float,
    system_type: SystemType,
    length_m: float = 100.0,
) -> SizingResult:
    """
    Calculate cable cross-section for electrical systems.

    Args:
        power_kw: Power demand in kilowatts
        system_type: Type of electrical system
        length_m: Cable length for voltage drop calculation

    Returns:
        SizingResult with cable cross-section
    """
    warnings = []

    # Get electrical parameters
    params = ELECTRICAL_PARAMS.get(system_type)
    if params is None:
        return SizingResult(
            system_type=system_type,
            demand=power_kw,
            demand_unit="kW",
            calculated_size=0,
            selected_size=0,
            size_unit="mm²",
            is_valid=False,
            warnings=[f"No electrical parameters for {system_type.value}"],
        )

    # Calculate current
    # For 3-phase: I = P / (√3 × V × pf)
    # For DC: I = P / V
    if params.power_factor < 1.0:  # AC system
        current_a = (power_kw * 1000) / (math.sqrt(3) * params.voltage_v * params.power_factor)
    else:  # DC system
        current_a = (power_kw * 1000) / params.voltage_v

    # Apply derating
    design_current = current_a / params.derating_factor

    # Cable sizing based on current capacity
    # Approximate: 5 A/mm² for copper (conservative)
    current_density = 5.0  # A/mm²
    calculated_size = design_current / current_density

    # Select standard size
    selected_size = calculated_size
    for std_size in STANDARD_CABLE_SIZES_MM2:
        if std_size >= calculated_size:
            selected_size = std_size
            break
    else:
        selected_size = STANDARD_CABLE_SIZES_MM2[-1]
        warnings.append(f"Power exceeds maximum cable size, using {selected_size}mm²")

    # Check voltage drop
    # Approximate: ΔV = 2 × I × L × ρ / A (for copper ρ ≈ 0.0175 Ω·mm²/m)
    resistivity = 0.0175
    if selected_size > 0:
        voltage_drop_v = 2 * current_a * length_m * resistivity / selected_size
        voltage_drop_pct = (voltage_drop_v / params.voltage_v) * 100

        if voltage_drop_pct > params.max_voltage_drop_pct:
            warnings.append(
                f"Voltage drop {voltage_drop_pct:.1f}% exceeds max {params.max_voltage_drop_pct}%"
            )
            # May need larger cable for voltage drop
            min_size_vd = 2 * current_a * length_m * resistivity / (
                params.voltage_v * params.max_voltage_drop_pct / 100
            )
            if min_size_vd > selected_size:
                for std_size in STANDARD_CABLE_SIZES_MM2:
                    if std_size >= min_size_vd:
                        selected_size = std_size
                        warnings.append(f"Increased to {selected_size}mm² for voltage drop")
                        break
    else:
        voltage_drop_pct = 0

    # Calculate utilization
    max_current = selected_size * current_density * params.derating_factor
    utilization = (current_a / max_current * 100) if max_current > 0 else 0

    return SizingResult(
        system_type=system_type,
        demand=power_kw,
        demand_unit="kW",
        calculated_size=calculated_size,
        selected_size=selected_size,
        size_unit="mm²",
        velocity=current_a,  # Using velocity field for current
        pressure_drop=voltage_drop_pct,  # Using pressure_drop for voltage drop %
        utilization_pct=utilization,
        is_valid=len([w for w in warnings if "exceeds" in w.lower()]) == 0,
        warnings=warnings,
    )


def calculate_duct_size(
    airflow_m3_h: float,
    system_type: SystemType,
    prefer_circular: bool = False,
) -> SizingResult:
    """
    Calculate duct size for HVAC systems.

    Args:
        airflow_m3_h: Airflow rate in cubic meters per hour
        system_type: Type of HVAC system
        prefer_circular: If True, use circular ducts

    Returns:
        SizingResult with duct dimensions
    """
    warnings = []

    # Get HVAC parameters
    params = HVAC_PARAMS.get(system_type)
    if params is None:
        return SizingResult(
            system_type=system_type,
            demand=airflow_m3_h,
            demand_unit="m³/h",
            calculated_size=0,
            selected_size=0,
            size_unit="mm",
            is_valid=False,
            warnings=[f"No HVAC parameters for {system_type.value}"],
        )

    # Convert to m³/s
    airflow_m3_s = airflow_m3_h / 3600.0

    # Calculate required area
    target_velocity = (params.max_velocity_m_s + params.min_velocity_m_s) / 2
    required_area_m2 = airflow_m3_s / target_velocity
    required_area_mm2 = required_area_m2 * 1e6

    if prefer_circular:
        # Calculate circular duct diameter
        diameter_mm = math.sqrt(4 * required_area_mm2 / math.pi)

        # Select standard size
        selected_diameter = diameter_mm
        for std_size in STANDARD_CIRCULAR_DUCT_MM:
            if std_size >= diameter_mm:
                selected_diameter = std_size
                break
        else:
            selected_diameter = STANDARD_CIRCULAR_DUCT_MM[-1]
            warnings.append(f"Airflow exceeds max duct size, using {selected_diameter}mm")

        selected_area = math.pi * selected_diameter ** 2 / 4
        size_str = f"{selected_diameter}"
        size_unit = "mm dia"
    else:
        # Select rectangular duct
        selected_size = None
        for w, h in STANDARD_DUCT_SIZES_MM:
            area = w * h
            if area >= required_area_mm2:
                selected_size = (w, h)
                break

        if selected_size is None:
            selected_size = STANDARD_DUCT_SIZES_MM[-1]
            warnings.append(f"Airflow exceeds max duct size, using {selected_size}")

        selected_area = selected_size[0] * selected_size[1]
        size_str = f"{selected_size[0]}x{selected_size[1]}"
        size_unit = "mm WxH"

    # Calculate actual velocity
    actual_velocity = airflow_m3_s / (selected_area / 1e6) if selected_area > 0 else 0

    # Check velocity limits
    if actual_velocity > params.max_velocity_m_s:
        warnings.append(f"Velocity {actual_velocity:.1f} m/s exceeds max {params.max_velocity_m_s}")
    if actual_velocity < params.min_velocity_m_s and airflow_m3_h > 0:
        warnings.append(f"Velocity {actual_velocity:.1f} m/s below min {params.min_velocity_m_s}")

    # Estimate pressure drop (simplified)
    pressure_drop = params.friction_factor * actual_velocity ** 2

    # Calculate utilization
    max_flow = (selected_area / 1e6) * params.max_velocity_m_s * 3600
    utilization = (airflow_m3_h / max_flow * 100) if max_flow > 0 else 0

    return SizingResult(
        system_type=system_type,
        demand=airflow_m3_h,
        demand_unit="m³/h",
        calculated_size=required_area_mm2,
        selected_size=selected_area,
        size_unit=size_unit,
        velocity=actual_velocity,
        pressure_drop=pressure_drop,
        utilization_pct=utilization,
        is_valid=len([w for w in warnings if "exceeds" in w]) == 0,
        warnings=warnings,
    )


# =============================================================================
# Capacity Calculator Class
# =============================================================================

class CapacityCalculator:
    """
    Calculates trunk sizing for all system types.

    Provides unified interface for sizing pipes, cables, and ducts
    based on system type and downstream demand.

    Usage:
        calc = CapacityCalculator()

        # Pipe sizing
        result = calc.calculate_size(SystemType.FUEL, demand=50.0)
        print(f"Pipe: DN{result.selected_size}")

        # Cable sizing
        result = calc.calculate_size(SystemType.ELECTRICAL_LV, demand=100.0)
        print(f"Cable: {result.selected_size}mm²")
    """

    # System type categories
    FLUID_SYSTEMS = {
        SystemType.FUEL, SystemType.FRESHWATER, SystemType.SEAWATER,
        SystemType.GREY_WATER, SystemType.BLACK_WATER, SystemType.LUBE_OIL,
        SystemType.HYDRAULIC, SystemType.BILGE, SystemType.FIREFIGHTING,
        SystemType.COMPRESSED_AIR, SystemType.STEAM,
    }

    ELECTRICAL_SYSTEMS = {
        SystemType.ELECTRICAL_HV, SystemType.ELECTRICAL_LV,
        SystemType.ELECTRICAL_DC, SystemType.FIRE_DETECTION,
    }

    HVAC_SYSTEMS = {
        SystemType.HVAC_SUPPLY, SystemType.HVAC_RETURN, SystemType.HVAC_EXHAUST,
    }

    def __init__(self):
        """Initialize capacity calculator."""
        self._cache: Dict[Tuple[SystemType, float], SizingResult] = {}

    def calculate_size(
        self,
        system_type: SystemType,
        demand: float,
        length_m: float = 100.0,
        **kwargs,
    ) -> SizingResult:
        """
        Calculate trunk size for any system type.

        Args:
            system_type: Type of system
            demand: Demand value (units depend on system type)
                - Fluid systems: m³/h
                - Electrical systems: kW
                - HVAC systems: m³/h
            length_m: Length for pressure/voltage drop calculation
            **kwargs: Additional parameters passed to specific calculator

        Returns:
            SizingResult with calculated and selected sizes
        """
        # Check cache
        cache_key = (system_type, demand, length_m)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Route to appropriate calculator
        if system_type in self.FLUID_SYSTEMS:
            result = calculate_pipe_diameter(demand, system_type, length_m)
        elif system_type in self.ELECTRICAL_SYSTEMS:
            result = calculate_cable_size(demand, system_type, length_m)
        elif system_type in self.HVAC_SYSTEMS:
            result = calculate_duct_size(demand, system_type, **kwargs)
        else:
            result = SizingResult(
                system_type=system_type,
                demand=demand,
                demand_unit="units",
                calculated_size=0,
                selected_size=0,
                size_unit="unknown",
                is_valid=False,
                warnings=[f"Unknown system type: {system_type.value}"],
            )

        # Cache result
        self._cache[cache_key] = result
        return result

    def aggregate_demand(
        self,
        demands: List[float],
        system_type: SystemType,
        diversity_factor: float = 1.0,
    ) -> float:
        """
        Aggregate downstream demands with diversity factor.

        Args:
            demands: List of individual demand values
            system_type: System type for diversity defaults
            diversity_factor: Factor to account for non-simultaneous use
                             (1.0 = all simultaneous, 0.5 = 50% diversity)

        Returns:
            Aggregated demand value
        """
        if not demands:
            return 0.0

        total = sum(demands)

        # Apply diversity factor
        aggregated = total * diversity_factor

        return aggregated

    def get_diversity_factor(
        self,
        system_type: SystemType,
        consumer_count: int,
    ) -> float:
        """
        Get recommended diversity factor for a system type.

        Args:
            system_type: Type of system
            consumer_count: Number of downstream consumers

        Returns:
            Diversity factor (0.0 to 1.0)
        """
        # Base diversity factors by system type
        base_factors = {
            # Critical systems - always ready
            SystemType.FIREFIGHTING: 1.0,
            SystemType.FIRE_DETECTION: 1.0,
            SystemType.BILGE: 1.0,

            # Essential - high diversity
            SystemType.ELECTRICAL_HV: 0.9,
            SystemType.ELECTRICAL_LV: 0.8,
            SystemType.ELECTRICAL_DC: 0.85,

            # Utilities - medium diversity
            SystemType.FRESHWATER: 0.6,
            SystemType.HVAC_SUPPLY: 0.7,
            SystemType.HVAC_RETURN: 0.7,
            SystemType.HVAC_EXHAUST: 0.8,

            # Other - variable
            SystemType.FUEL: 0.5,
            SystemType.LUBE_OIL: 0.4,
            SystemType.HYDRAULIC: 0.6,
            SystemType.COMPRESSED_AIR: 0.5,
        }

        base = base_factors.get(system_type, 0.7)

        # Adjust for consumer count (more consumers = more diversity)
        if consumer_count <= 2:
            adjustment = 1.0
        elif consumer_count <= 5:
            adjustment = 0.95
        elif consumer_count <= 10:
            adjustment = 0.9
        else:
            adjustment = 0.85

        return min(1.0, base * adjustment)

    def calculate_trunk_capacity(
        self,
        system_type: SystemType,
        selected_size: float,
    ) -> float:
        """
        Calculate maximum capacity for a given trunk size.

        Args:
            system_type: Type of system
            selected_size: Selected trunk size (mm, mm², etc.)

        Returns:
            Maximum capacity in system-appropriate units
        """
        if system_type in self.FLUID_SYSTEMS:
            params = FLUID_PARAMS.get(system_type)
            if params:
                # Calculate max flow at max velocity
                area_m2 = math.pi * (selected_size / 1000) ** 2 / 4
                max_flow_m3_h = area_m2 * params.max_velocity_m_s * 3600
                return max_flow_m3_h

        elif system_type in self.ELECTRICAL_SYSTEMS:
            params = ELECTRICAL_PARAMS.get(system_type)
            if params:
                # Calculate max power at rated current
                current_density = 5.0  # A/mm²
                max_current = selected_size * current_density * params.derating_factor
                if params.power_factor < 1.0:
                    max_power_kw = math.sqrt(3) * params.voltage_v * max_current * params.power_factor / 1000
                else:
                    max_power_kw = params.voltage_v * max_current / 1000
                return max_power_kw

        elif system_type in self.HVAC_SYSTEMS:
            params = HVAC_PARAMS.get(system_type)
            if params:
                # Assuming selected_size is area in mm²
                area_m2 = selected_size / 1e6
                max_flow_m3_h = area_m2 * params.max_velocity_m_s * 3600
                return max_flow_m3_h

        return 0.0

    def clear_cache(self) -> None:
        """Clear the sizing cache."""
        self._cache.clear()

    def get_statistics(self) -> Dict[str, Any]:
        """Get calculator statistics."""
        return {
            'cache_size': len(self._cache),
            'fluid_systems': len(self.FLUID_SYSTEMS),
            'electrical_systems': len(self.ELECTRICAL_SYSTEMS),
            'hvac_systems': len(self.HVAC_SYSTEMS),
        }
