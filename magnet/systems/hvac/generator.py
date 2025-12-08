"""
systems/hvac/generator.py - HVAC system generation.

BRAVO OWNS THIS FILE.

Module 28 v1.0 - HVAC System Generator.
"""

from typing import List, TYPE_CHECKING

from .schema import HVACZoneType, HVACZone, ACUnit, VentilationFan, HVACSystem

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class HVACSystemGenerator:
    """Generate HVAC system from vessel parameters."""

    # Heat load assumptions (kW/m^2)
    HEAT_LOAD_FACTORS = {
        HVACZoneType.BRIDGE: 0.15,
        HVACZoneType.ACCOMMODATION: 0.10,
        HVACZoneType.ENGINE_ROOM: 0.05,  # Ventilation only
        HVACZoneType.CARGO: 0.02,
        HVACZoneType.GALLEY: 0.25,
        HVACZoneType.MACHINERY: 0.08,
        HVACZoneType.ELECTRONICS: 0.20,
        HVACZoneType.PASSENGER: 0.12,
    }

    # Air changes per hour by zone type
    AIR_CHANGES = {
        HVACZoneType.BRIDGE: 10,
        HVACZoneType.ACCOMMODATION: 6,
        HVACZoneType.ENGINE_ROOM: 30,
        HVACZoneType.CARGO: 4,
        HVACZoneType.GALLEY: 20,
        HVACZoneType.MACHINERY: 20,
        HVACZoneType.ELECTRONICS: 15,
        HVACZoneType.PASSENGER: 8,
    }

    def __init__(self, state: 'StateManager'):
        self.state = state

        # Get vessel parameters
        self.lwl = state.get("hull.lwl", 24)
        self.beam = state.get("hull.beam", 6)
        self.depth = state.get("hull.depth", 3)
        self.vessel_type = state.get("mission.vessel_type", "patrol")
        self.crew = state.get("mission.crew", 8)
        self.passengers = state.get("mission.passengers", 0)

    def generate(self) -> HVACSystem:
        """Generate complete HVAC system."""
        system = HVACSystem(system_id="HVAC-001")

        # Generate zones based on vessel type
        system.zones = self._generate_zones()

        # Calculate zone loads
        for zone in system.zones:
            self._calculate_zone_load(zone)

        # Generate AC units
        system.ac_units = self._generate_ac_units(system.zones)

        # Generate ventilation fans
        system.fans = self._generate_fans(system.zones)

        # Calculate totals
        system.calculate_totals()

        return system

    def _generate_zones(self) -> List[HVACZone]:
        """Generate HVAC zones based on vessel type."""
        zones = []

        # Bridge zone (all vessels)
        bridge = HVACZone(
            zone_id="HVAC-BRIDGE",
            zone_type=HVACZoneType.BRIDGE,
            zone_name="Bridge",
            volume_m3=self.beam * 4 * 2.4,  # ~4m long, 2.4m high
            floor_area_m2=self.beam * 4,
            design_temp_c=22.0,
            occupancy=3,
            min_air_changes_per_hour=self.AIR_CHANGES[HVACZoneType.BRIDGE],
        )
        zones.append(bridge)

        # Engine room (all vessels)
        er_length = self.lwl * 0.2
        er = HVACZone(
            zone_id="HVAC-ER",
            zone_type=HVACZoneType.ENGINE_ROOM,
            zone_name="Engine Room",
            volume_m3=self.beam * er_length * (self.depth - 0.5),
            floor_area_m2=self.beam * er_length,
            design_temp_c=40.0,  # Higher for ER
            occupancy=0,
            min_air_changes_per_hour=self.AIR_CHANGES[HVACZoneType.ENGINE_ROOM],
        )
        zones.append(er)

        # Accommodation (if crew > 0)
        if self.crew > 0:
            accom_area = self.crew * 6  # ~6 m^2 per person
            accom = HVACZone(
                zone_id="HVAC-ACCOM",
                zone_type=HVACZoneType.ACCOMMODATION,
                zone_name="Crew Accommodation",
                volume_m3=accom_area * 2.2,
                floor_area_m2=accom_area,
                design_temp_c=22.0,
                occupancy=self.crew,
                min_air_changes_per_hour=self.AIR_CHANGES[HVACZoneType.ACCOMMODATION],
            )
            zones.append(accom)

        # Passenger space (if passengers > 0)
        if self.passengers > 0:
            pax_area = self.passengers * 1.5  # ~1.5 m^2 per passenger
            pax = HVACZone(
                zone_id="HVAC-PAX",
                zone_type=HVACZoneType.PASSENGER,
                zone_name="Passenger Cabin",
                volume_m3=pax_area * 2.4,
                floor_area_m2=pax_area,
                design_temp_c=22.0,
                occupancy=self.passengers,
                min_air_changes_per_hour=self.AIR_CHANGES[HVACZoneType.PASSENGER],
            )
            zones.append(pax)

        # Galley (if crew > 4)
        if self.crew > 4:
            galley = HVACZone(
                zone_id="HVAC-GALLEY",
                zone_type=HVACZoneType.GALLEY,
                zone_name="Galley",
                volume_m3=12 * 2.2,
                floor_area_m2=12,
                design_temp_c=24.0,
                occupancy=2,
                min_air_changes_per_hour=self.AIR_CHANGES[HVACZoneType.GALLEY],
            )
            zones.append(galley)

        # Electronics room
        elec = HVACZone(
            zone_id="HVAC-ELEC",
            zone_type=HVACZoneType.ELECTRONICS,
            zone_name="Electronics Room",
            volume_m3=8 * 2.2,
            floor_area_m2=8,
            design_temp_c=20.0,
            occupancy=0,
            min_air_changes_per_hour=self.AIR_CHANGES[HVACZoneType.ELECTRONICS],
        )
        zones.append(elec)

        return zones

    def _calculate_zone_load(self, zone: HVACZone) -> None:
        """Calculate heating/cooling load for zone."""
        # Base load from area
        load_factor = self.HEAT_LOAD_FACTORS.get(zone.zone_type, 0.1)
        area_load = zone.floor_area_m2 * load_factor

        # Occupancy load (~100W sensible, 50W latent per person)
        sensible_occupancy = zone.occupancy * 0.1
        latent_occupancy = zone.occupancy * 0.05

        # Equipment load (assume 50% of area load)
        equipment_load = area_load * 0.5

        zone.sensible_load_kw = area_load + sensible_occupancy + equipment_load
        zone.latent_load_kw = latent_occupancy

    def _generate_ac_units(self, zones: List[HVACZone]) -> List[ACUnit]:
        """Generate AC units for zones."""
        units = []
        unit_counter = 1

        # Group zones by type for sizing
        conditioned_zones = [z for z in zones if z.zone_type != HVACZoneType.ENGINE_ROOM]

        # Main AC unit for accommodation and bridge
        main_zones = [z for z in conditioned_zones
                     if z.zone_type in [HVACZoneType.BRIDGE, HVACZoneType.ACCOMMODATION,
                                        HVACZoneType.PASSENGER]]
        if main_zones:
            total_load = sum(z.total_load_kw for z in main_zones)
            total_airflow = sum(z.required_airflow_m3h for z in main_zones)

            # Size unit with 20% margin
            capacity = total_load * 1.2
            power = capacity / 3.0  # Assume COP of 3

            main_unit = ACUnit(
                unit_id=f"AC-{unit_counter:02d}",
                unit_type="split" if capacity < 20 else "packaged",
                cooling_capacity_kw=capacity,
                heating_capacity_kw=capacity * 0.8,
                airflow_m3h=total_airflow,
                power_consumption_kw=power,
                zones_served=[z.zone_id for z in main_zones],
            )
            units.append(main_unit)
            unit_counter += 1

        # Separate unit for galley (high load)
        galley_zones = [z for z in conditioned_zones if z.zone_type == HVACZoneType.GALLEY]
        for zone in galley_zones:
            galley_unit = ACUnit(
                unit_id=f"AC-{unit_counter:02d}",
                unit_type="split",
                cooling_capacity_kw=zone.total_load_kw * 1.3,
                heating_capacity_kw=0,  # No heating for galley
                airflow_m3h=zone.required_airflow_m3h,
                power_consumption_kw=zone.total_load_kw * 1.3 / 2.5,
                zones_served=[zone.zone_id],
            )
            units.append(galley_unit)
            unit_counter += 1

        # Electronics room unit
        elec_zones = [z for z in conditioned_zones if z.zone_type == HVACZoneType.ELECTRONICS]
        for zone in elec_zones:
            elec_unit = ACUnit(
                unit_id=f"AC-{unit_counter:02d}",
                unit_type="split",
                cooling_capacity_kw=zone.total_load_kw * 1.5,
                heating_capacity_kw=0,
                airflow_m3h=zone.required_airflow_m3h,
                power_consumption_kw=zone.total_load_kw * 1.5 / 3.5,
                zones_served=[zone.zone_id],
            )
            units.append(elec_unit)
            unit_counter += 1

        return units

    def _generate_fans(self, zones: List[HVACZone]) -> List[VentilationFan]:
        """Generate ventilation fans for zones."""
        fans = []
        fan_counter = 1

        for zone in zones:
            # Supply fan
            supply_fan = VentilationFan(
                fan_id=f"FAN-S{fan_counter:02d}",
                fan_type="supply",
                airflow_m3h=zone.required_airflow_m3h,
                static_pressure_pa=250,
                power_kw=zone.required_airflow_m3h / 3600 * 250 / 1000 / 0.6,  # ~60% efficiency
                zone_id=zone.zone_id,
                is_explosion_proof=(zone.zone_type in [HVACZoneType.ENGINE_ROOM, HVACZoneType.MACHINERY]),
            )
            fans.append(supply_fan)

            # Exhaust fan (same capacity)
            exhaust_fan = VentilationFan(
                fan_id=f"FAN-E{fan_counter:02d}",
                fan_type="exhaust",
                airflow_m3h=zone.required_airflow_m3h,
                static_pressure_pa=200,
                power_kw=zone.required_airflow_m3h / 3600 * 200 / 1000 / 0.6,
                zone_id=zone.zone_id,
                is_explosion_proof=(zone.zone_type in [HVACZoneType.ENGINE_ROOM, HVACZoneType.MACHINERY]),
            )
            fans.append(exhaust_fan)

            fan_counter += 1

        return fans
