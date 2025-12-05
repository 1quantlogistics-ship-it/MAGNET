"""
Deadweight calculation module.

Provides calculation of:
- Deadweight components (cargo, fuel, stores, water, crew)
- Displacement balance verification
- Loading conditions
- Design margins per classification rules

References:
- ISO 8217 - Fuel specifications
- SOLAS - Safety requirements affecting weights
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum


class FuelType(Enum):
    """Fuel type for consumption calculations."""
    MDO = "mdo"           # Marine Diesel Oil (0.89 t/m³)
    MGO = "mgo"           # Marine Gas Oil (0.85 t/m³)
    HFO = "hfo"           # Heavy Fuel Oil (0.95 t/m³)
    LNG = "lng"           # Liquefied Natural Gas (0.45 t/m³)
    METHANOL = "methanol"  # Alternative fuel (0.79 t/m³)


# Fuel densities (t/m³)
FUEL_DENSITIES = {
    FuelType.MDO: 0.89,
    FuelType.MGO: 0.85,
    FuelType.HFO: 0.95,
    FuelType.LNG: 0.45,
    FuelType.METHANOL: 0.79,
}


@dataclass
class DeadweightResult:
    """Result of deadweight calculation."""
    # Major components
    cargo_weight: float          # tonnes
    fuel_weight: float           # tonnes
    fresh_water_weight: float    # tonnes
    stores_weight: float         # tonnes (provisions, spares)
    crew_effects_weight: float   # tonnes
    ballast_weight: float        # tonnes

    # Totals
    deadweight: float            # tonnes (total DWT)
    payload: float               # tonnes (revenue-generating cargo)

    # Capacities
    fuel_capacity_m3: float      # m³
    fresh_water_capacity_m3: float  # m³
    ballast_capacity_m3: float   # m³

    # Endurance
    endurance_days: float
    endurance_nm: float

    # Consumption rates
    fuel_consumption_day: float  # tonnes/day
    water_consumption_day: float  # tonnes/day

    # Fuel details
    fuel_type: str
    fuel_density: float          # t/m³

    # Breakdown
    breakdown: Dict[str, float] = field(default_factory=dict)


@dataclass
class DisplacementBalance:
    """Displacement balance check result."""
    displacement: float          # tonnes (from hydrostatics)
    lightship: float             # tonnes
    deadweight: float            # tonnes
    total_weight: float          # tonnes (lightship + deadweight)

    margin: float                # tonnes (displacement - total_weight)
    margin_percent: float        # % of displacement

    is_balanced: bool            # True if margin >= 0
    utilization: float           # % of displacement used

    # Warnings
    warnings: List[str] = field(default_factory=list)


def calculate_fuel_requirement(
    installed_power: float,
    endurance_days: float,
    service_speed_kts: float,
    specific_fuel_consumption: float = 0.22,  # kg/kWh for modern diesel
    fuel_type: FuelType = FuelType.MDO,
    utilization_factor: float = 0.85,
    reserve_margin: float = 0.10,
) -> tuple[float, float, float]:
    """
    Calculate fuel requirement for endurance.

    Args:
        installed_power: Total installed power (kW)
        endurance_days: Required endurance (days)
        service_speed_kts: Service speed (knots)
        specific_fuel_consumption: SFC (kg/kWh), default 0.22 for modern diesel
        fuel_type: Type of fuel
        utilization_factor: Engine utilization at service speed (typically 0.80-0.90)
        reserve_margin: Reserve fuel margin (typically 0.10)

    Returns:
        Tuple of (fuel_weight_tonnes, fuel_volume_m3, daily_consumption_tonnes)
    """
    # Average power at service speed
    average_power = installed_power * utilization_factor

    # Daily fuel consumption
    hours_per_day = 24
    daily_consumption_kg = average_power * specific_fuel_consumption * hours_per_day
    daily_consumption_tonnes = daily_consumption_kg / 1000

    # Total fuel for endurance
    base_fuel = daily_consumption_tonnes * endurance_days

    # Add reserve margin
    total_fuel = base_fuel * (1 + reserve_margin)

    # Convert to volume
    fuel_density = FUEL_DENSITIES.get(fuel_type, 0.89)
    fuel_volume = total_fuel / fuel_density

    return total_fuel, fuel_volume, daily_consumption_tonnes


def calculate_fresh_water_requirement(
    crew_capacity: int,
    passenger_capacity: int,
    endurance_days: float,
    daily_consumption_per_person: float = 0.15,  # tonnes/person/day
    reserve_margin: float = 0.10,
) -> tuple[float, float, float]:
    """
    Calculate fresh water requirement.

    Args:
        crew_capacity: Number of crew
        passenger_capacity: Number of passengers
        endurance_days: Required endurance (days)
        daily_consumption_per_person: Water consumption (tonnes/person/day)
        reserve_margin: Reserve margin

    Returns:
        Tuple of (water_weight, water_volume, daily_consumption)
    """
    total_persons = crew_capacity + passenger_capacity

    daily_consumption = total_persons * daily_consumption_per_person
    base_water = daily_consumption * endurance_days
    total_water = base_water * (1 + reserve_margin)

    # Fresh water density ~1.0 t/m³
    water_volume = total_water

    return total_water, water_volume, daily_consumption


def calculate_stores_requirement(
    crew_capacity: int,
    passenger_capacity: int,
    endurance_days: float,
    stores_per_person_day: float = 0.01,  # tonnes/person/day
    spares_allowance: float = 2.0,  # tonnes base
    lubricants_factor: float = 0.02,  # fraction of fuel weight
    fuel_weight: float = 0.0,
) -> float:
    """
    Calculate stores weight (provisions, spares, lubricants).

    Args:
        crew_capacity: Number of crew
        passenger_capacity: Number of passengers
        endurance_days: Required endurance
        stores_per_person_day: Provisions per person per day
        spares_allowance: Base weight for spare parts
        lubricants_factor: Lubricants as fraction of fuel
        fuel_weight: Fuel weight for lubricants calculation

    Returns:
        Total stores weight (tonnes)
    """
    total_persons = crew_capacity + passenger_capacity

    # Provisions
    provisions = total_persons * stores_per_person_day * endurance_days

    # Lubricants
    lubricants = fuel_weight * lubricants_factor

    # Spares and consumables
    spares = spares_allowance

    return provisions + lubricants + spares


def calculate_crew_effects(
    crew_capacity: int,
    effects_per_person: float = 0.15,  # tonnes per person
) -> float:
    """Calculate weight of crew effects and personal belongings."""
    return crew_capacity * effects_per_person


def calculate_deadweight(
    displacement: float,
    lightship: float,
    cargo_capacity: float = 0.0,
    installed_power: float = 0.0,
    service_speed_kts: float = 12.0,
    endurance_days: float = 14.0,
    crew_capacity: int = 10,
    passenger_capacity: int = 0,
    fuel_type: FuelType = FuelType.MDO,
    specific_fuel_consumption: float = 0.22,
    include_ballast: bool = True,
    ballast_capacity_m3: float = 0.0,
) -> DeadweightResult:
    """
    Calculate deadweight breakdown.

    Args:
        displacement: Design displacement (tonnes)
        lightship: Lightship weight (tonnes)
        cargo_capacity: Cargo capacity (tonnes) - if 0, calculated as remainder
        installed_power: Installed power (kW)
        service_speed_kts: Service speed (knots)
        endurance_days: Design endurance (days)
        crew_capacity: Number of crew
        passenger_capacity: Number of passengers
        fuel_type: Type of fuel
        specific_fuel_consumption: SFC (kg/kWh)
        include_ballast: Whether to include ballast capacity
        ballast_capacity_m3: Ballast tank capacity (m³)

    Returns:
        DeadweightResult with full breakdown
    """
    # Available deadweight
    available_dwt = displacement - lightship

    # Calculate fuel requirement
    fuel_weight, fuel_volume, fuel_daily = calculate_fuel_requirement(
        installed_power=installed_power,
        endurance_days=endurance_days,
        service_speed_kts=service_speed_kts,
        specific_fuel_consumption=specific_fuel_consumption,
        fuel_type=fuel_type,
    )

    # Calculate fresh water requirement
    water_weight, water_volume, water_daily = calculate_fresh_water_requirement(
        crew_capacity=crew_capacity,
        passenger_capacity=passenger_capacity,
        endurance_days=endurance_days,
    )

    # Calculate stores
    stores_weight = calculate_stores_requirement(
        crew_capacity=crew_capacity,
        passenger_capacity=passenger_capacity,
        endurance_days=endurance_days,
        fuel_weight=fuel_weight,
    )

    # Crew effects
    crew_effects = calculate_crew_effects(crew_capacity)

    # Ballast
    if include_ballast and ballast_capacity_m3 > 0:
        # Seawater density ~1.025 t/m³
        ballast_weight = ballast_capacity_m3 * 1.025
    else:
        ballast_weight = 0.0

    # Consumables total
    consumables = fuel_weight + water_weight + stores_weight + crew_effects

    # Cargo capacity
    if cargo_capacity <= 0:
        # Calculate available cargo capacity
        cargo_weight = max(0, available_dwt - consumables - ballast_weight)
    else:
        cargo_weight = cargo_capacity

    # Total deadweight
    deadweight = cargo_weight + consumables + ballast_weight

    # Endurance in nautical miles
    endurance_nm = endurance_days * 24 * service_speed_kts

    # Payload (revenue cargo)
    payload = cargo_weight

    # Build breakdown
    breakdown = {
        "cargo": cargo_weight,
        "fuel": fuel_weight,
        "fresh_water": water_weight,
        "stores": stores_weight,
        "crew_effects": crew_effects,
        "ballast": ballast_weight,
        "consumables_subtotal": consumables,
    }

    fuel_density = FUEL_DENSITIES.get(fuel_type, 0.89)

    return DeadweightResult(
        cargo_weight=cargo_weight,
        fuel_weight=fuel_weight,
        fresh_water_weight=water_weight,
        stores_weight=stores_weight,
        crew_effects_weight=crew_effects,
        ballast_weight=ballast_weight,
        deadweight=deadweight,
        payload=payload,
        fuel_capacity_m3=fuel_volume,
        fresh_water_capacity_m3=water_volume,
        ballast_capacity_m3=ballast_capacity_m3,
        endurance_days=endurance_days,
        endurance_nm=endurance_nm,
        fuel_consumption_day=fuel_daily,
        water_consumption_day=water_daily,
        fuel_type=fuel_type.value,
        fuel_density=fuel_density,
        breakdown=breakdown,
    )


def calculate_displacement_balance(
    displacement: float,
    lightship: float,
    deadweight: float,
    acceptable_margin_percent: float = 2.0,
) -> DisplacementBalance:
    """
    Check displacement balance.

    Args:
        displacement: Design displacement (tonnes)
        lightship: Lightship weight (tonnes)
        deadweight: Deadweight (tonnes)
        acceptable_margin_percent: Acceptable margin as % of displacement

    Returns:
        DisplacementBalance with verification result
    """
    total_weight = lightship + deadweight
    margin = displacement - total_weight
    margin_percent = (margin / displacement) * 100 if displacement > 0 else 0
    utilization = (total_weight / displacement) * 100 if displacement > 0 else 0

    is_balanced = margin >= 0

    warnings = []

    if margin < 0:
        warnings.append(f"OVERWEIGHT: Total weight exceeds displacement by {abs(margin):.1f} t")

    if margin_percent < 0:
        warnings.append("Design is not feasible - reduce lightship or deadweight")
    elif margin_percent < 1.0:
        warnings.append("Very tight margin - consider design review")
    elif margin_percent > 10.0:
        warnings.append("Large margin - displacement may be overestimated")

    if utilization < 85:
        warnings.append(f"Low utilization ({utilization:.1f}%) - may optimize displacement")
    elif utilization > 98:
        warnings.append(f"High utilization ({utilization:.1f}%) - limited growth margin")

    return DisplacementBalance(
        displacement=displacement,
        lightship=lightship,
        deadweight=deadweight,
        total_weight=total_weight,
        margin=margin,
        margin_percent=margin_percent,
        is_balanced=is_balanced,
        utilization=utilization,
        warnings=warnings,
    )


def generate_deadweight_report(result: DeadweightResult, vessel_name: str = "Vessel") -> str:
    """Generate human-readable deadweight report."""
    lines = [
        f"DEADWEIGHT REPORT - {vessel_name}",
        "=" * 50,
        "",
        "DEADWEIGHT BREAKDOWN",
        "-" * 30,
        f"Cargo:           {result.cargo_weight:8.1f} t",
        f"Fuel ({result.fuel_type.upper()}):      {result.fuel_weight:8.1f} t  ({result.fuel_capacity_m3:.0f} m³)",
        f"Fresh Water:     {result.fresh_water_weight:8.1f} t  ({result.fresh_water_capacity_m3:.0f} m³)",
        f"Stores:          {result.stores_weight:8.1f} t",
        f"Crew Effects:    {result.crew_effects_weight:8.1f} t",
        f"Ballast:         {result.ballast_weight:8.1f} t  ({result.ballast_capacity_m3:.0f} m³)",
        "-" * 30,
        f"TOTAL DWT:       {result.deadweight:8.1f} t",
        f"Payload:         {result.payload:8.1f} t",
        "",
        "ENDURANCE",
        "-" * 30,
        f"Days:            {result.endurance_days:8.1f}",
        f"Range:           {result.endurance_nm:8.0f} nm",
        f"Fuel/day:        {result.fuel_consumption_day:8.2f} t/day",
        f"Water/day:       {result.water_consumption_day:8.2f} t/day",
        "",
    ]
    return "\n".join(lines)


def generate_balance_report(balance: DisplacementBalance, vessel_name: str = "Vessel") -> str:
    """Generate displacement balance report."""
    status = "✓ BALANCED" if balance.is_balanced else "✗ OVERWEIGHT"

    lines = [
        f"DISPLACEMENT BALANCE - {vessel_name}",
        "=" * 50,
        "",
        f"Displacement:    {balance.displacement:8.1f} t",
        f"Lightship:       {balance.lightship:8.1f} t",
        f"Deadweight:      {balance.deadweight:8.1f} t",
        "-" * 30,
        f"Total Weight:    {balance.total_weight:8.1f} t",
        f"Margin:          {balance.margin:8.1f} t ({balance.margin_percent:+.1f}%)",
        "-" * 30,
        f"Utilization:     {balance.utilization:8.1f}%",
        f"Status:          {status}",
        "",
    ]

    if balance.warnings:
        lines.append("WARNINGS:")
        for warning in balance.warnings:
            lines.append(f"  ⚠ {warning}")
        lines.append("")

    return "\n".join(lines)
