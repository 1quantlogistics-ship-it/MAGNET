"""
systems/fuel/generator.py - Fuel system generation.

BRAVO OWNS THIS FILE.

Module 29 v1.1 - Fuel System Generator.
"""

from typing import List, TYPE_CHECKING

from .schema import TankType, FluidType, Tank, Pump, FuelSystem

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class FuelSystemGenerator:
    """Generate fuel system from vessel parameters."""

    def __init__(self, state: 'StateManager'):
        self.state = state

        # Get vessel parameters
        self.lwl = state.get("hull.lwl", 24)
        self.beam = state.get("hull.beam", 6)
        self.depth = state.get("hull.depth", 3)
        self.draft = state.get("hull.draft", 1.5)

        # Get mission parameters
        self.range_nm = state.get("mission.range_nm", 500)
        self.speed_kts = state.get("mission.max_speed_kts", 30)
        self.crew = state.get("mission.crew", 8)
        self.endurance_days = state.get("mission.endurance_days", 3)

        # Get propulsion parameters
        self.installed_power_kw = state.get("propulsion.installed_power_kw") or \
                                   state.get("propulsion.total_installed_power_kw", 2000)

    def generate(self) -> FuelSystem:
        """Generate complete fuel system."""
        system = FuelSystem(system_id="FUEL-001")

        # Calculate fuel requirement
        fuel_required_m3 = self._calculate_fuel_requirement()

        # Generate fuel tanks
        system.tanks.extend(self._generate_fuel_tanks(fuel_required_m3))

        # Generate lube oil tanks
        system.tanks.extend(self._generate_lube_oil_tanks())

        # Generate fresh water tanks
        system.tanks.extend(self._generate_fresh_water_tanks())

        # Generate waste tanks
        system.tanks.extend(self._generate_waste_tanks())

        # Generate pumps
        system.pumps = self._generate_pumps(system.tanks)

        # Set consumption rate
        system.fuel_consumption_rate_lph = self._calculate_fuel_consumption_rate()

        # Calculate totals
        system.calculate_totals()

        return system

    def _calculate_fuel_requirement(self) -> float:
        """Calculate required fuel capacity (m^3)."""
        # SFC assumption: 220 g/kWh for high-speed diesel
        sfc_gkwh = 220

        # Operating hours from range
        operating_hours = self.range_nm / self.speed_kts

        # Average power factor (assume 85% MCR for cruise)
        power_factor = 0.85

        # Fuel consumption (kg)
        fuel_kg = self.installed_power_kw * power_factor * operating_hours * sfc_gkwh / 1000

        # Convert to volume (density ~850 kg/m3 for MGO)
        fuel_m3 = fuel_kg / 850

        # Add 15% reserve
        return fuel_m3 * 1.15

    def _calculate_fuel_consumption_rate(self) -> float:
        """Calculate fuel consumption rate (L/h)."""
        sfc_gkwh = 220
        power_factor = 0.85
        fuel_kg_h = self.installed_power_kw * power_factor * sfc_gkwh / 1000
        fuel_l_h = fuel_kg_h / 0.85  # density in kg/L
        return fuel_l_h

    def _generate_fuel_tanks(self, required_m3: float) -> List[Tank]:
        """Generate fuel tanks."""
        tanks = []

        # Day tank (10% of total, max 2 m3)
        day_tank_m3 = min(required_m3 * 0.1, 2.0)

        day_tank = Tank(
            tank_id="TANK-FUEL-DAY",
            tank_type=TankType.FUEL_DAY,
            tank_name="Fuel Day Tank",
            fluid_type=FluidType.MGO,
            capacity_m3=day_tank_m3,
            usable_capacity_m3=day_tank_m3 * 0.95,
            x_position=self.lwl * 0.3,
            z_position=self.depth * 0.3,
            is_integral=False,
        )
        tanks.append(day_tank)

        # Storage tanks (remaining fuel, split P/S)
        storage_m3 = required_m3 - day_tank_m3
        storage_per_side = storage_m3 / 2

        for side, y_mult in [("P", -1), ("S", 1)]:
            storage_tank = Tank(
                tank_id=f"TANK-FUEL-{side}",
                tank_type=TankType.FUEL_STORAGE,
                tank_name=f"Fuel Storage Tank ({side})",
                fluid_type=FluidType.MGO,
                capacity_m3=storage_per_side,
                usable_capacity_m3=storage_per_side * 0.97,
                x_position=self.lwl * 0.25,
                y_position=y_mult * self.beam * 0.3,
                z_position=self.draft * 0.5,
                is_integral=True,
            )
            tanks.append(storage_tank)

        # Service tank
        service_m3 = min(required_m3 * 0.05, 0.5)
        service_tank = Tank(
            tank_id="TANK-FUEL-SVC",
            tank_type=TankType.FUEL_SERVICE,
            tank_name="Fuel Service Tank",
            fluid_type=FluidType.MGO,
            capacity_m3=service_m3,
            usable_capacity_m3=service_m3 * 0.95,
            x_position=self.lwl * 0.28,
            z_position=self.depth * 0.4,
            is_integral=False,
        )
        tanks.append(service_tank)

        return tanks

    def _generate_lube_oil_tanks(self) -> List[Tank]:
        """Generate lube oil tanks."""
        tanks = []

        # Main lube oil (based on engine size)
        lube_m3 = self.installed_power_kw / 1000 * 0.2  # ~0.2 m3 per 1000 kW

        main_lube = Tank(
            tank_id="TANK-LUBE-MAIN",
            tank_type=TankType.LUBE_OIL,
            tank_name="Main Lube Oil Tank",
            fluid_type=FluidType.LUBE_OIL,
            capacity_m3=lube_m3,
            usable_capacity_m3=lube_m3 * 0.95,
            x_position=self.lwl * 0.25,
            z_position=self.depth * 0.2,
            is_integral=False,
        )
        tanks.append(main_lube)

        # Dirty oil tank
        dirty_lube = Tank(
            tank_id="TANK-LUBE-DIRTY",
            tank_type=TankType.LUBE_OIL,
            tank_name="Dirty Lube Oil Tank",
            fluid_type=FluidType.LUBE_OIL,
            capacity_m3=lube_m3 * 0.5,
            usable_capacity_m3=lube_m3 * 0.5,
            x_position=self.lwl * 0.22,
            z_position=self.depth * 0.15,
            is_integral=False,
            fill_level_pct=0,
        )
        tanks.append(dirty_lube)

        return tanks

    def _generate_fresh_water_tanks(self) -> List[Tank]:
        """Generate fresh water tanks."""
        tanks = []

        # Fresh water: ~100L per person per day
        fw_m3 = self.crew * 0.1 * self.endurance_days * 1.2  # 20% margin

        # Split into two tanks
        fw_per_tank = fw_m3 / 2

        for side, y_mult in [("P", -1), ("S", 1)]:
            fw_tank = Tank(
                tank_id=f"TANK-FW-{side}",
                tank_type=TankType.FRESH_WATER,
                tank_name=f"Fresh Water Tank ({side})",
                fluid_type=FluidType.FRESH_WATER,
                capacity_m3=fw_per_tank,
                usable_capacity_m3=fw_per_tank * 0.95,
                x_position=self.lwl * 0.5,
                y_position=y_mult * self.beam * 0.25,
                z_position=self.draft * 0.6,
                is_integral=True,
            )
            tanks.append(fw_tank)

        return tanks

    def _generate_waste_tanks(self) -> List[Tank]:
        """Generate waste tanks."""
        tanks = []

        # Grey water: ~80% of fresh water consumption
        fw_consumption = self.crew * 0.1 * self.endurance_days
        grey_m3 = fw_consumption * 0.8

        grey_tank = Tank(
            tank_id="TANK-GREY",
            tank_type=TankType.GREY_WATER,
            tank_name="Grey Water Tank",
            fluid_type=FluidType.GREY_WATER,
            capacity_m3=grey_m3,
            usable_capacity_m3=grey_m3,
            x_position=self.lwl * 0.45,
            z_position=self.draft * 0.3,
            is_integral=True,
            fill_level_pct=0,
        )
        tanks.append(grey_tank)

        # Black water: ~20% of fresh water
        black_m3 = fw_consumption * 0.2

        black_tank = Tank(
            tank_id="TANK-BLACK",
            tank_type=TankType.BLACK_WATER,
            tank_name="Black Water Tank",
            fluid_type=FluidType.BLACK_WATER,
            capacity_m3=black_m3,
            usable_capacity_m3=black_m3,
            x_position=self.lwl * 0.4,
            z_position=self.draft * 0.3,
            is_integral=True,
            fill_level_pct=0,
        )
        tanks.append(black_tank)

        # Bilge holding
        bilge_m3 = self.lwl * self.beam * 0.01  # ~1% of waterplane area

        bilge_tank = Tank(
            tank_id="TANK-BILGE",
            tank_type=TankType.BILGE,
            tank_name="Bilge Holding Tank",
            fluid_type=FluidType.SEA_WATER,
            capacity_m3=bilge_m3,
            usable_capacity_m3=bilge_m3,
            x_position=self.lwl * 0.2,
            z_position=0.1,
            is_integral=True,
            fill_level_pct=0,
        )
        tanks.append(bilge_tank)

        return tanks

    def _generate_pumps(self, tanks: List[Tank]) -> List[Pump]:
        """Generate transfer and service pumps."""
        pumps = []

        # Fuel transfer pump
        fuel_tanks = [t for t in tanks if t.tank_type in
                     [TankType.FUEL_STORAGE, TankType.FUEL_SERVICE, TankType.FUEL_DAY]]
        if fuel_tanks:
            transfer_pump = Pump(
                pump_id="PUMP-FUEL-XFER",
                pump_type="transfer",
                fluid_type=FluidType.MGO,
                flow_rate_m3h=2.0,
                head_m=20,
                power_kw=1.5,
                source_tanks=[t.tank_id for t in tanks if t.tank_type == TankType.FUEL_STORAGE],
                destination_tanks=["TANK-FUEL-DAY", "TANK-FUEL-SVC"],
            )
            pumps.append(transfer_pump)

        # Fuel supply pump (to engines)
        supply_pump = Pump(
            pump_id="PUMP-FUEL-SUPPLY",
            pump_type="service",
            fluid_type=FluidType.MGO,
            flow_rate_m3h=self._calculate_fuel_consumption_rate() / 1000 * 1.5,  # 50% margin
            head_m=30,
            power_kw=0.75,
            source_tanks=["TANK-FUEL-DAY"],
            destination_tanks=["ENGINE"],
        )
        pumps.append(supply_pump)

        # Fresh water pump
        fw_tanks = [t for t in tanks if t.tank_type == TankType.FRESH_WATER]
        if fw_tanks:
            fw_pump = Pump(
                pump_id="PUMP-FW",
                pump_type="service",
                fluid_type=FluidType.FRESH_WATER,
                flow_rate_m3h=0.5,
                head_m=30,
                power_kw=0.5,
                source_tanks=[t.tank_id for t in fw_tanks],
                destination_tanks=["FW_SYSTEM"],
            )
            pumps.append(fw_pump)

        # Bilge pump
        bilge_pump = Pump(
            pump_id="PUMP-BILGE",
            pump_type="emergency",
            fluid_type=FluidType.SEA_WATER,
            flow_rate_m3h=10.0,  # Class requirement
            head_m=15,
            power_kw=2.0,
            source_tanks=["BILGE"],
            destination_tanks=["OVERBOARD"],
        )
        pumps.append(bilge_pump)

        # Grey water pump
        grey_pump = Pump(
            pump_id="PUMP-GREY",
            pump_type="transfer",
            fluid_type=FluidType.GREY_WATER,
            flow_rate_m3h=2.0,
            head_m=10,
            power_kw=0.5,
            source_tanks=["TANK-GREY"],
            destination_tanks=["SHORE"],
        )
        pumps.append(grey_pump)

        return pumps
