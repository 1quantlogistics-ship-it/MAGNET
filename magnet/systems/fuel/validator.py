"""
systems/fuel/validator.py - Fuel system validation.

BRAVO OWNS THIS FILE.

Module 29 v1.1 - Fuel Validator.
"""

from typing import Any, Dict, List, TYPE_CHECKING
from datetime import datetime

from .generator import FuelSystemGenerator
from .schema import TankType

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class FuelValidator:
    """Validate fuel system design."""

    VALIDATOR_ID = "fuel_system"
    VALIDATOR_NAME = "Fuel System Validator"

    def __init__(self, state: 'StateManager'):
        self.state = state
        self.findings: List[Dict[str, Any]] = []

    def validate(self) -> Dict[str, Any]:
        """Run fuel system validation."""
        self.findings = []
        started_at = datetime.utcnow()

        try:
            # Generate system
            generator = FuelSystemGenerator(self.state)
            system = generator.generate()

            # Check fuel capacity vs range
            self._check_fuel_range(system)

            # Check day tank size
            self._check_day_tank(system)

            # Check fresh water capacity
            self._check_fresh_water(system)

            # Check pump redundancy
            self._check_pump_redundancy(system)

            # Check tank arrangement
            self._check_tank_arrangement(system)

            # Store results
            self.state.set("fuel.total_capacity_m3", system.total_fuel_capacity_m3)
            self.state.set("fuel.endurance_hours", system.endurance_hours)
            self.state.set("fuel.tank_count", len(system.tanks))

            status = "passed" if not self._has_errors() else "failed"

        except Exception as e:
            self.findings.append({
                "severity": "error",
                "message": f"Fuel validation error: {str(e)}",
            })
            status = "error"

        return {
            "validator_id": self.VALIDATOR_ID,
            "validator_name": self.VALIDATOR_NAME,
            "status": status,
            "findings": self.findings,
            "started_at": started_at.isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
        }

    def _check_fuel_range(self, system) -> None:
        """Check fuel capacity provides required range."""
        required_range = self.state.get("mission.range_nm", 500)
        speed = self.state.get("mission.max_speed_kts", 30)

        required_hours = required_range / speed

        if system.endurance_hours < required_hours:
            self.findings.append({
                "severity": "error",
                "message": f"Insufficient fuel endurance: {system.endurance_hours:.1f}h < {required_hours:.1f}h required for {required_range} nm range",
            })
        elif system.endurance_hours < required_hours * 1.1:
            self.findings.append({
                "severity": "warning",
                "message": f"Low fuel margin: {system.endurance_hours:.1f}h for {required_hours:.1f}h required",
            })

    def _check_day_tank(self, system) -> None:
        """Check day tank provides adequate service time."""
        day_tanks = system.get_tanks_by_type(TankType.FUEL_DAY)

        if not day_tanks:
            self.findings.append({
                "severity": "error",
                "message": "No fuel day tank provided",
            })
            return

        day_tank_m3 = sum(t.usable_capacity_m3 for t in day_tanks)
        consumption_m3h = system.fuel_consumption_rate_lph / 1000

        if consumption_m3h > 0:
            day_tank_hours = day_tank_m3 / consumption_m3h

            if day_tank_hours < 4:
                self.findings.append({
                    "severity": "warning",
                    "message": f"Day tank provides only {day_tank_hours:.1f}h service time (min 4h recommended)",
                })

    def _check_fresh_water(self, system) -> None:
        """Check fresh water capacity for endurance."""
        fw_tanks = system.get_tanks_by_type(TankType.FRESH_WATER)
        fw_capacity = sum(t.usable_capacity_m3 for t in fw_tanks)

        crew = self.state.get("mission.crew", 8)
        endurance_days = self.state.get("mission.endurance_days", 3)

        # 100L per person per day
        required_fw = crew * 0.1 * endurance_days

        if fw_capacity < required_fw:
            self.findings.append({
                "severity": "error",
                "message": f"Insufficient fresh water: {fw_capacity:.2f} m^3 < {required_fw:.2f} m^3 required",
            })

    def _check_pump_redundancy(self, system) -> None:
        """Check critical pumps have redundancy."""
        # Check for fuel supply pump
        fuel_supply_pumps = [p for p in system.pumps
                           if p.pump_type == "service" and p.fluid_type.value == "mgo"]

        if len(fuel_supply_pumps) < 1:
            self.findings.append({
                "severity": "error",
                "message": "No fuel supply pump provided",
            })

        # Check for bilge pump
        bilge_pumps = [p for p in system.pumps
                      if p.pump_type == "emergency" and "bilge" in p.pump_id.lower()]

        if len(bilge_pumps) < 1:
            self.findings.append({
                "severity": "error",
                "message": "No bilge pump provided (class requirement)",
            })

    def _check_tank_arrangement(self, system) -> None:
        """Check tank arrangement for safety."""
        fuel_tanks = [t for t in system.tanks
                     if t.tank_type in [TankType.FUEL_STORAGE, TankType.FUEL_SERVICE, TankType.FUEL_DAY]]

        # Check for fuel tanks below accommodation
        for tank in fuel_tanks:
            if tank.z_position > self.state.get("hull.depth", 3) * 0.7:
                self.findings.append({
                    "severity": "warning",
                    "message": f"Tank {tank.tank_id} positioned high in hull - verify not under accommodation",
                })

        # Check fuel tanks have cofferdam from engine room
        # (simplified check - in reality need spatial analysis)

    def _has_errors(self) -> bool:
        """Check if any error findings."""
        return any(f.get("severity") == "error" for f in self.findings)
