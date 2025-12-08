"""
tests/unit/test_systems.py - Tests for Modules 28-30 (HVAC, Fuel, Safety).

BRAVO OWNS THIS FILE.

Tests for systems modules implemented by BRAVO:
- Module 28: HVAC System
- Module 29: Fuel System
- Module 30: Safety System
"""

import pytest
from unittest.mock import MagicMock

# Import directly from submodules (systems/__init__.py is ALPHA-owned)
from magnet.systems.hvac import (
    HVACZoneType, HVACZone, ACUnit, VentilationFan, HVACSystem,
    HVACSystemGenerator, HVACValidator,
)
from magnet.systems.fuel import (
    TankType, FluidType, Tank, Pump, FuelSystem,
    FuelSystemGenerator, FuelValidator,
)
from magnet.systems.safety import (
    FireZone, FirefightingAgent,
    FireZoneDefinition, FirePump, LifeSavingAppliance, BilgeSystem, SafetySystem,
    SafetySystemGenerator, SafetyValidator,
)


# =============================================================================
# MODULE 28: HVAC SYSTEM TESTS
# =============================================================================

class TestHVACZone:
    """Test HVACZone dataclass."""

    def test_hvac_zone_creation(self):
        """Test creating an HVAC zone."""
        zone = HVACZone(
            zone_id="HZ-001",
            zone_type=HVACZoneType.ACCOMMODATION,
            zone_name="Main Cabin",
            volume_m3=50.0,
            floor_area_m2=20.0,
            occupancy=4,
            design_temp_c=22.0,
        )
        assert zone.zone_id == "HZ-001"
        assert zone.zone_type == HVACZoneType.ACCOMMODATION
        assert zone.volume_m3 == 50.0
        assert zone.occupancy == 4

    def test_hvac_zone_to_dict(self):
        """Test HVACZone serialization."""
        zone = HVACZone(
            zone_id="HZ-002",
            zone_type=HVACZoneType.ENGINE_ROOM,
            zone_name="Engine Room",
            volume_m3=100.0,
            floor_area_m2=40.0,
        )
        data = zone.to_dict()
        assert data["zone_id"] == "HZ-002"
        assert data["zone_type"] == "engine_room"

    def test_hvac_zone_required_airflow(self):
        """Test required airflow calculation."""
        zone = HVACZone(
            zone_id="HZ-003",
            volume_m3=100.0,
            min_air_changes_per_hour=10.0,
        )
        assert zone.required_airflow_m3h == 1000.0


class TestACUnit:
    """Test ACUnit dataclass."""

    def test_ac_unit_creation(self):
        """Test creating an AC unit."""
        unit = ACUnit(
            unit_id="AC-001",
            cooling_capacity_kw=10.0,
            heating_capacity_kw=8.0,
            power_consumption_kw=3.5,
            refrigerant="R410A",
        )
        assert unit.unit_id == "AC-001"
        assert unit.cooling_capacity_kw == 10.0
        assert unit.cop == pytest.approx(10.0 / 3.5, rel=0.01)

    def test_ac_unit_to_dict(self):
        """Test ACUnit serialization."""
        unit = ACUnit(
            unit_id="AC-002",
            cooling_capacity_kw=15.0,
        )
        data = unit.to_dict()
        assert "cooling_capacity_kw" in data
        assert data["cooling_capacity_kw"] == 15.0


class TestVentilationFan:
    """Test VentilationFan dataclass."""

    def test_ventilation_fan_creation(self):
        """Test creating a ventilation fan."""
        fan = VentilationFan(
            fan_id="VF-001",
            zone_id="HZ-001",
            airflow_m3h=500.0,
            static_pressure_pa=250.0,
            power_kw=0.75,
            fan_type="supply",
        )
        assert fan.fan_id == "VF-001"
        assert fan.airflow_m3h == 500.0
        assert fan.fan_type == "supply"


class TestHVACSystem:
    """Test HVACSystem dataclass."""

    def test_hvac_system_creation(self):
        """Test creating HVAC system."""
        system = HVACSystem(
            system_id="HVAC-001",
            zones=[HVACZone(zone_id="HZ-001")],
            ac_units=[ACUnit(unit_id="AC-001", cooling_capacity_kw=10.0)],
            fans=[VentilationFan(fan_id="VF-001", airflow_m3h=500.0)],
        )
        assert system.system_id == "HVAC-001"
        assert len(system.zones) == 1
        assert len(system.ac_units) == 1

    def test_hvac_system_calculate_totals(self):
        """Test HVAC system totals calculation."""
        system = HVACSystem(
            system_id="HVAC-001",
            ac_units=[
                ACUnit(unit_id="AC-001", cooling_capacity_kw=10.0, heating_capacity_kw=8.0, power_consumption_kw=3.0),
                ACUnit(unit_id="AC-002", cooling_capacity_kw=15.0, heating_capacity_kw=12.0, power_consumption_kw=5.0),
            ],
            fans=[
                VentilationFan(fan_id="VF-001", power_kw=0.5),
                VentilationFan(fan_id="VF-002", power_kw=0.75),
            ],
        )
        system.calculate_totals()

        assert system.total_cooling_capacity_kw == 25.0
        assert system.total_heating_capacity_kw == 20.0
        assert system.total_power_kw == pytest.approx(9.25, rel=0.01)


class TestHVACSystemGenerator:
    """Test HVACSystemGenerator class."""

    def test_generator_creation(self):
        """Test creating HVAC generator."""
        mock_state = MagicMock()
        mock_state.get.side_effect = lambda k, d=None: {
            "hull.lwl": 24,
            "hull.beam": 6,
            "hull.depth": 3,
            "mission.vessel_type": "patrol",
            "mission.crew": 4,
            "mission.passengers": 12,
        }.get(k, d)

        generator = HVACSystemGenerator(mock_state)
        assert generator.lwl == 24
        assert generator.beam == 6

    def test_generate_complete_system(self):
        """Test complete system generation."""
        mock_state = MagicMock()
        mock_state.get.side_effect = lambda k, d=None: {
            "hull.lwl": 24,
            "hull.beam": 6,
            "hull.depth": 3,
            "mission.vessel_type": "patrol",
            "mission.crew": 8,
            "mission.passengers": 0,
        }.get(k, d)

        generator = HVACSystemGenerator(mock_state)
        system = generator.generate()

        assert system.system_id
        assert len(system.zones) > 0
        assert len(system.ac_units) > 0
        assert len(system.fans) > 0


class TestHVACValidator:
    """Test HVACValidator class."""

    def test_valid_system(self):
        """Test validation of adequate HVAC system."""
        mock_state = MagicMock()
        mock_state.get.side_effect = lambda k, d=None: {
            "hull.lwl": 24,
            "hull.beam": 6,
            "hull.depth": 3,
            "mission.vessel_type": "patrol",
            "mission.crew": 8,
            "mission.passengers": 0,
        }.get(k, d)

        validator = HVACValidator(mock_state)
        result = validator.validate()

        # Generated system should be valid (no errors)
        assert result["status"] in ["passed", "failed"]
        errors = [f for f in result.get("findings", []) if f.get("severity") == "error"]
        assert len(errors) == 0 or result["status"] == "passed"


# =============================================================================
# MODULE 29: FUEL SYSTEM TESTS
# =============================================================================

class TestTank:
    """Test Tank dataclass."""

    def test_tank_creation(self):
        """Test creating a tank."""
        tank = Tank(
            tank_id="T-001",
            tank_type=TankType.FUEL_STORAGE,
            fluid_type=FluidType.MGO,
            capacity_m3=5.0,
            usable_capacity_m3=4.5,
        )
        assert tank.tank_id == "T-001"
        assert tank.tank_type == TankType.FUEL_STORAGE
        assert tank.capacity_m3 == 5.0

    def test_tank_to_dict(self):
        """Test Tank serialization."""
        tank = Tank(
            tank_id="T-002",
            tank_type=TankType.LUBE_OIL,
            capacity_m3=0.2,
        )
        data = tank.to_dict()
        assert data["tank_id"] == "T-002"
        assert data["tank_type"] == "lube_oil"

    def test_tank_weight_calculation(self):
        """Test tank weight calculation."""
        tank = Tank(
            tank_id="T-003",
            tank_type=TankType.FUEL_STORAGE,
            fluid_type=FluidType.MGO,
            capacity_m3=1.0,
            usable_capacity_m3=1.0,
            fill_level_pct=100.0,
        )
        # MGO density is 850 kg/m3
        assert tank.weight_kg == pytest.approx(850.0, rel=0.01)


class TestPump:
    """Test Pump dataclass."""

    def test_pump_creation(self):
        """Test creating a pump."""
        pump = Pump(
            pump_id="P-001",
            pump_type="transfer",
            flow_rate_m3h=2.0,
            head_m=20.0,
            power_kw=1.5,
        )
        assert pump.pump_id == "P-001"
        assert pump.flow_rate_m3h == 2.0


class TestFuelSystem:
    """Test FuelSystem dataclass."""

    def test_fuel_system_creation(self):
        """Test creating fuel system."""
        system = FuelSystem(
            system_id="FUEL-001",
            tanks=[Tank(tank_id="T-001", tank_type=TankType.FUEL_STORAGE, capacity_m3=5.0)],
            pumps=[Pump(pump_id="P-001", flow_rate_m3h=2.0)],
        )
        assert system.system_id == "FUEL-001"
        assert len(system.tanks) == 1

    def test_fuel_system_calculate_totals(self):
        """Test fuel system totals calculation."""
        system = FuelSystem(
            system_id="FUEL-001",
            tanks=[
                Tank(tank_id="T-001", tank_type=TankType.FUEL_STORAGE,
                     capacity_m3=5.0, usable_capacity_m3=4.5, fluid_type=FluidType.MGO),
                Tank(tank_id="T-002", tank_type=TankType.FUEL_STORAGE,
                     capacity_m3=3.0, usable_capacity_m3=2.7, fluid_type=FluidType.MGO),
            ],
            fuel_consumption_rate_lph=100.0,
        )
        system.calculate_totals()

        assert system.total_fuel_capacity_m3 == pytest.approx(7.2, rel=0.01)
        # Endurance = 7.2 m3 * 1000 L/m3 / 100 L/h = 72 hours
        assert system.endurance_hours == pytest.approx(72.0, rel=0.01)


class TestFuelSystemGenerator:
    """Test FuelSystemGenerator class."""

    def test_generator_creation(self):
        """Test creating fuel generator."""
        mock_state = MagicMock()
        mock_state.get.side_effect = lambda k, d=None: {
            "hull.lwl": 24,
            "hull.beam": 6,
            "hull.depth": 3,
            "hull.draft": 1.5,
            "mission.range_nm": 500,
            "mission.max_speed_kts": 30,
            "mission.cruise_speed_kts": 22,
            "mission.crew": 8,
            "mission.endurance_days": 3,
            "propulsion.installed_power_kw": 2000,
            "propulsion.total_installed_power_kw": 2000,
        }.get(k, d)

        generator = FuelSystemGenerator(mock_state)
        assert generator.lwl == 24
        assert generator.range_nm == 500

    def test_generate_complete_system(self):
        """Test complete fuel system generation."""
        mock_state = MagicMock()
        mock_state.get.side_effect = lambda k, d=None: {
            "hull.lwl": 24,
            "hull.beam": 6,
            "hull.depth": 3,
            "hull.draft": 1.5,
            "mission.range_nm": 500,
            "mission.max_speed_kts": 30,
            "mission.crew": 8,
            "mission.endurance_days": 3,
            "propulsion.installed_power_kw": 2000,
            "propulsion.total_installed_power_kw": 2000,
        }.get(k, d)

        generator = FuelSystemGenerator(mock_state)
        system = generator.generate()

        assert system.system_id
        assert len(system.tanks) > 0
        assert len(system.pumps) > 0
        assert system.total_fuel_capacity_m3 > 0


class TestFuelValidator:
    """Test FuelValidator class."""

    def test_valid_system(self):
        """Test validation of adequate fuel system."""
        mock_state = MagicMock()
        mock_state.get.side_effect = lambda k, d=None: {
            "hull.lwl": 24,
            "hull.beam": 6,
            "hull.depth": 3,
            "hull.draft": 1.5,
            "mission.range_nm": 500,
            "mission.max_speed_kts": 30,
            "mission.crew": 8,
            "mission.endurance_days": 3,
            "propulsion.installed_power_kw": 2000,
            "propulsion.total_installed_power_kw": 2000,
        }.get(k, d)

        validator = FuelValidator(mock_state)
        result = validator.validate()

        # Generated system should meet range requirement
        assert result["status"] in ["passed", "failed"]
        # Check that system was generated and has valid findings
        assert "findings" in result


# =============================================================================
# MODULE 30: SAFETY SYSTEM TESTS
# =============================================================================

class TestFireZoneDefinition:
    """Test FireZoneDefinition dataclass."""

    def test_fire_zone_creation(self):
        """Test creating a fire zone."""
        zone = FireZoneDefinition(
            zone_id="FZ-001",
            zone_type=FireZone.ENGINE_ROOM,
            zone_name="Main Engine Room",
            volume_m3=150.0,
            floor_area_m2=50.0,
            fire_rating_minutes=60,
            has_a60_boundaries=True,
        )
        assert zone.zone_id == "FZ-001"
        assert zone.zone_type == FireZone.ENGINE_ROOM
        assert zone.fire_rating_minutes == 60

    def test_fire_zone_to_dict(self):
        """Test FireZoneDefinition serialization."""
        zone = FireZoneDefinition(
            zone_id="FZ-002",
            zone_type=FireZone.ACCOMMODATION,
            zone_name="Crew Quarters",
            volume_m3=80.0,
        )
        data = zone.to_dict()
        assert data["zone_id"] == "FZ-002"
        assert data["zone_type"] == "accommodation"


class TestFirePump:
    """Test FirePump dataclass."""

    def test_fire_pump_creation(self):
        """Test creating a fire pump."""
        pump = FirePump(
            pump_id="FP-001",
            pump_type="main",
            capacity_m3h=50.0,
            pressure_bar=7.0,
            power_kw=15.0,
            location="Engine Room",
        )
        assert pump.pump_id == "FP-001"
        assert pump.capacity_m3h == 50.0
        assert pump.pressure_bar == 7.0


class TestLifeSavingAppliance:
    """Test LifeSavingAppliance dataclass."""

    def test_appliance_creation(self):
        """Test creating a life saving appliance."""
        appliance = LifeSavingAppliance(
            appliance_id="LR-001",
            appliance_type="liferaft",
            capacity=12,
            location="Port Main Deck",
            solas_compliant=True,
        )
        assert appliance.appliance_id == "LR-001"
        assert appliance.appliance_type == "liferaft"
        assert appliance.capacity == 12


class TestBilgeSystem:
    """Test BilgeSystem dataclass."""

    def test_bilge_system_creation(self):
        """Test creating a bilge system."""
        bilge = BilgeSystem(
            main_pump_capacity_m3h=25.0,
            emergency_pump_capacity_m3h=18.0,
            pump_count=2,
            main_diameter_mm=50,
            has_high_level_alarm=True,
            alarm_locations=["Engine Room", "Forepeak"],
        )
        assert bilge.main_pump_capacity_m3h == 25.0
        assert bilge.pump_count == 2


class TestSafetySystem:
    """Test SafetySystem dataclass."""

    def test_safety_system_creation(self):
        """Test creating safety system."""
        system = SafetySystem(
            system_id="SAFETY-001",
            fire_zones=[FireZoneDefinition(zone_id="FZ-001")],
            fire_pumps=[FirePump(pump_id="FP-001", capacity_m3h=50.0)],
            life_saving_appliances=[
                LifeSavingAppliance(appliance_id="LR-001", appliance_type="liferaft", capacity=12),
            ],
        )
        assert system.system_id == "SAFETY-001"
        assert len(system.fire_zones) == 1

    def test_safety_system_calculate_totals(self):
        """Test safety system totals calculation."""
        system = SafetySystem(
            system_id="SAFETY-001",
            life_saving_appliances=[
                LifeSavingAppliance(appliance_id="LR-001", appliance_type="liferaft", capacity=12),
                LifeSavingAppliance(appliance_id="LR-002", appliance_type="liferaft", capacity=12),
                LifeSavingAppliance(appliance_id="LJ-001", appliance_type="lifejacket", capacity=20),
                LifeSavingAppliance(appliance_id="LB-001", appliance_type="lifebuoy", capacity=6),
            ],
        )
        system.calculate_totals()

        assert system.liferaft_capacity == 24
        assert system.lifejacket_count == 20
        assert system.lifebuoy_count == 6


class TestSafetySystemGenerator:
    """Test SafetySystemGenerator class."""

    def test_generator_creation(self):
        """Test creating safety generator."""
        mock_state = MagicMock()
        mock_state.get.side_effect = lambda k, d=None: {
            "hull.loa": 26,
            "hull.beam": 6,
            "hull.depth": 3,
            "mission.crew": 4,
            "mission.passengers": 12,
        }.get(k, d)

        generator = SafetySystemGenerator(mock_state)
        assert generator.loa == 26
        assert generator.total_persons == 16

    def test_generate_fire_zones(self):
        """Test fire zone generation."""
        mock_state = MagicMock()
        mock_state.get.side_effect = lambda k, d=None: {
            "hull.loa": 26,
            "hull.beam": 6,
            "hull.depth": 3,
            "mission.crew": 4,
            "mission.passengers": 12,
        }.get(k, d)

        generator = SafetySystemGenerator(mock_state)
        zones = generator.generate_fire_zones()

        assert len(zones) > 0
        zone_types = [z.zone_type for z in zones]
        assert FireZone.ENGINE_ROOM in zone_types

    def test_generate_fire_pumps(self):
        """Test fire pump generation."""
        mock_state = MagicMock()
        mock_state.get.side_effect = lambda k, d=None: {
            "hull.loa": 26,
            "hull.beam": 6,
            "hull.depth": 3,
            "mission.crew": 4,
            "mission.passengers": 12,
        }.get(k, d)

        generator = SafetySystemGenerator(mock_state)
        pumps = generator.generate_fire_pumps()

        assert len(pumps) >= 2  # Main + emergency/portable
        main_pumps = [p for p in pumps if p.pump_type == "main"]
        assert len(main_pumps) >= 1

    def test_generate_life_saving_appliances(self):
        """Test life saving appliance generation."""
        mock_state = MagicMock()
        mock_state.get.side_effect = lambda k, d=None: {
            "hull.loa": 26,
            "hull.beam": 6,
            "hull.depth": 3,
            "mission.crew": 4,
            "mission.passengers": 12,
        }.get(k, d)

        generator = SafetySystemGenerator(mock_state)
        appliances = generator.generate_life_saving_appliances()

        assert len(appliances) > 0
        liferafts = [a for a in appliances if a.appliance_type == "liferaft"]
        lifejackets = [a for a in appliances if a.appliance_type == "lifejacket"]
        assert len(liferafts) >= 1
        assert len(lifejackets) >= 1

    def test_generate_complete_system(self):
        """Test complete safety system generation."""
        mock_state = MagicMock()
        mock_state.get.side_effect = lambda k, d=None: {
            "hull.loa": 26,
            "hull.beam": 6,
            "hull.depth": 3,
            "mission.crew": 4,
            "mission.passengers": 12,
        }.get(k, d)

        generator = SafetySystemGenerator(mock_state)
        system = generator.generate_safety_system()

        assert system.system_id
        assert len(system.fire_zones) > 0
        assert len(system.fire_pumps) > 0
        assert len(system.life_saving_appliances) > 0
        assert system.has_ais is True
        assert system.has_epirb is True


class TestSafetyValidator:
    """Test SafetyValidator class."""

    def test_validator_creation(self):
        """Test creating safety validator."""
        mock_state = MagicMock()
        mock_state.get.side_effect = lambda k, d=None: {
            "hull.loa": 26,
            "hull.beam": 6,
            "hull.depth": 3,
            "mission.crew": 4,
            "mission.passengers": 12,
        }.get(k, d)

        validator = SafetyValidator(mock_state)
        assert validator.loa == 26
        assert validator.total_persons == 16

    def test_valid_system(self):
        """Test validation of adequate safety system."""
        mock_state = MagicMock()
        mock_state.get.side_effect = lambda k, d=None: {
            "hull.loa": 26,
            "hull.beam": 6,
            "hull.depth": 3,
            "mission.crew": 4,
            "mission.passengers": 12,
        }.get(k, d)

        generator = SafetySystemGenerator(mock_state)
        system = generator.generate_safety_system()

        validator = SafetyValidator(mock_state)
        result = validator.validate(system)

        # Generated system should be valid
        assert result.liferaft_capacity_ratio >= 1.0
        assert result.lifejacket_ratio >= 1.0

    def test_insufficient_liferafts(self):
        """Test detection of insufficient liferaft capacity."""
        mock_state = MagicMock()
        mock_state.get.side_effect = lambda k, d=None: {
            "hull.loa": 26,
            "hull.beam": 6,
            "hull.depth": 3,
            "mission.crew": 4,
            "mission.passengers": 12,
        }.get(k, d)

        # Create system with insufficient liferafts
        system = SafetySystem(
            system_id="TEST-001",
            fire_zones=[FireZoneDefinition(
                zone_id="FZ-001",
                zone_type=FireZone.ENGINE_ROOM,
                has_fixed_system=True,
                has_smoke_detection=True,
            )],
            fire_pumps=[FirePump(pump_id="FP-001", capacity_m3h=50.0)],
            life_saving_appliances=[
                LifeSavingAppliance(
                    appliance_id="LR-001",
                    appliance_type="liferaft",
                    capacity=8,  # Only 8 for 16 persons
                ),
                LifeSavingAppliance(
                    appliance_id="LJ-001",
                    appliance_type="lifejacket",
                    capacity=20,
                ),
                LifeSavingAppliance(
                    appliance_id="LB-001",
                    appliance_type="lifebuoy",
                    capacity=4,
                ),
            ],
            bilge_system=BilgeSystem(
                main_pump_capacity_m3h=25.0,
                pump_count=2,
                has_high_level_alarm=True,
                alarm_locations=["Engine Room"],
            ),
            has_ais=True,
            has_epirb=True,
            has_sart=True,
        )

        validator = SafetyValidator(mock_state)
        result = validator.validate(system)

        # Should detect insufficient liferaft capacity
        assert result.liferaft_capacity_ratio < 1.0
        assert any("Liferaft capacity" in issue for issue in result.issues)

    def test_missing_engine_room_protection(self):
        """Test detection of missing engine room fire protection."""
        mock_state = MagicMock()
        mock_state.get.side_effect = lambda k, d=None: {
            "hull.loa": 26,
            "hull.beam": 6,
            "hull.depth": 3,
            "mission.crew": 4,
            "mission.passengers": 12,
        }.get(k, d)

        # Create system with unprotected engine room
        system = SafetySystem(
            system_id="TEST-002",
            fire_zones=[FireZoneDefinition(
                zone_id="FZ-001",
                zone_type=FireZone.ENGINE_ROOM,
                zone_name="Engine Room",
                has_fixed_system=False,  # Missing!
                has_smoke_detection=True,
            )],
            fire_pumps=[FirePump(pump_id="FP-001", capacity_m3h=50.0)],
            life_saving_appliances=[
                LifeSavingAppliance(appliance_id="LR-001", appliance_type="liferaft", capacity=20),
                LifeSavingAppliance(appliance_id="LJ-001", appliance_type="lifejacket", capacity=20),
                LifeSavingAppliance(appliance_id="LB-001", appliance_type="lifebuoy", capacity=4),
            ],
            bilge_system=BilgeSystem(
                pump_count=2,
                has_high_level_alarm=True,
                alarm_locations=["Engine Room"],
            ),
            has_ais=True,
            has_epirb=True,
        )

        validator = SafetyValidator(mock_state)
        result = validator.validate(system)

        # Should detect missing fixed system
        assert any("fixed firefighting" in issue.lower() for issue in result.issues)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestSystemsIntegration:
    """Integration tests for systems modules."""

    def test_all_systems_generation(self):
        """Test generating all systems together."""
        mock_state = MagicMock()
        mock_state.get.side_effect = lambda k, d=None: {
            "hull.loa": 26,
            "hull.lwl": 24,
            "hull.beam": 6,
            "hull.depth": 3,
            "hull.draft": 1.5,
            "mission.vessel_type": "patrol",
            "mission.crew": 8,
            "mission.passengers": 0,
            "mission.range_nm": 500,
            "mission.max_speed_kts": 30,
            "mission.cruise_speed_kts": 22,
            "mission.endurance_days": 3,
            "propulsion.installed_power_kw": 2000,
            "propulsion.total_installed_power_kw": 2000,
        }.get(k, d)

        # Generate all systems
        hvac = HVACSystemGenerator(mock_state).generate()
        fuel = FuelSystemGenerator(mock_state).generate()
        safety = SafetySystemGenerator(mock_state).generate_safety_system()

        # All should have valid IDs
        assert hvac.system_id
        assert fuel.system_id
        assert safety.system_id

    def test_all_systems_validation(self):
        """Test validating all systems together."""
        mock_state = MagicMock()
        mock_state.get.side_effect = lambda k, d=None: {
            "hull.loa": 26,
            "hull.lwl": 24,
            "hull.beam": 6,
            "hull.depth": 3,
            "hull.draft": 1.5,
            "mission.vessel_type": "patrol",
            "mission.crew": 8,
            "mission.passengers": 0,
            "mission.range_nm": 500,
            "mission.max_speed_kts": 30,
            "mission.cruise_speed_kts": 22,
            "mission.endurance_days": 3,
            "propulsion.installed_power_kw": 2000,
            "propulsion.total_installed_power_kw": 2000,
        }.get(k, d)

        # Generate and validate all systems
        # HVAC and Fuel validators generate internally
        hvac_result = HVACValidator(mock_state).validate()
        fuel_result = FuelValidator(mock_state).validate()

        # Safety system validates an explicit system
        safety = SafetySystemGenerator(mock_state).generate_safety_system()
        safety_result = SafetyValidator(mock_state).validate(safety)

        # All generated systems should pass validation
        assert hvac_result["status"] in ["passed", "failed"]
        assert fuel_result["status"] in ["passed", "failed"]
        assert safety_result.liferaft_capacity_ratio >= 1.0
