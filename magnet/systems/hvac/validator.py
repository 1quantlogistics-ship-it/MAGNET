"""
systems/hvac/validator.py - HVAC system validation.

BRAVO OWNS THIS FILE.

Module 28 v1.0 - HVAC Validator.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime

from .generator import HVACSystemGenerator

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class HVACValidator:
    """Validate HVAC system design."""

    VALIDATOR_ID = "hvac_system"
    VALIDATOR_NAME = "HVAC System Validator"

    # Minimum requirements
    MIN_AIR_CHANGES_ER = 20  # Engine room
    MIN_AIR_CHANGES_ACCOM = 4  # Accommodation

    def __init__(self, state: 'StateManager'):
        self.state = state
        self.findings: List[Dict[str, Any]] = []

    def validate(self) -> Dict[str, Any]:
        """Run HVAC validation."""
        self.findings = []
        started_at = datetime.utcnow()

        try:
            # Generate system
            generator = HVACSystemGenerator(self.state)
            system = generator.generate()

            # Check capacity
            self._check_cooling_capacity(system)

            # Check ventilation
            self._check_ventilation(system)

            # Check engine room
            self._check_engine_room_ventilation(system)

            # Store results
            self.state.set("hvac.total_cooling_kw", system.total_cooling_capacity_kw)
            self.state.set("hvac.total_power_kw", system.total_power_kw)
            self.state.set("hvac.zone_count", len(system.zones))

            status = "passed" if not self._has_errors() else "failed"

        except Exception as e:
            self.findings.append({
                "severity": "error",
                "message": f"HVAC validation error: {str(e)}",
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

    def _check_cooling_capacity(self, system) -> None:
        """Check total cooling capacity vs load."""
        total_load = sum(z.total_load_kw for z in system.zones
                        if z.zone_type.value != "engine_room")

        if system.total_cooling_capacity_kw < total_load:
            self.findings.append({
                "severity": "error",
                "message": f"Insufficient cooling capacity: {system.total_cooling_capacity_kw:.1f} kW < {total_load:.1f} kW load",
            })
        elif system.total_cooling_capacity_kw < total_load * 1.1:
            self.findings.append({
                "severity": "warning",
                "message": f"Low cooling margin: {system.total_cooling_capacity_kw:.1f} kW for {total_load:.1f} kW load",
            })

    def _check_ventilation(self, system) -> None:
        """Check ventilation rates."""
        for zone in system.zones:
            # Get fans for this zone
            zone_fans = [f for f in system.fans if f.zone_id == zone.zone_id]
            supply_airflow = sum(f.airflow_m3h for f in zone_fans if f.fan_type == "supply")

            if zone.volume_m3 > 0:
                actual_ach = supply_airflow / zone.volume_m3
                if actual_ach < zone.min_air_changes_per_hour * 0.9:
                    self.findings.append({
                        "severity": "warning",
                        "message": f"Zone {zone.zone_id}: Low air changes ({actual_ach:.1f} vs {zone.min_air_changes_per_hour} required)",
                    })

    def _check_engine_room_ventilation(self, system) -> None:
        """Check engine room meets minimum ventilation."""
        er_zones = [z for z in system.zones if z.zone_type.value == "engine_room"]

        for zone in er_zones:
            zone_fans = [f for f in system.fans if f.zone_id == zone.zone_id]
            supply_airflow = sum(f.airflow_m3h for f in zone_fans if f.fan_type == "supply")

            if zone.volume_m3 > 0:
                actual_ach = supply_airflow / zone.volume_m3
                if actual_ach < self.MIN_AIR_CHANGES_ER:
                    self.findings.append({
                        "severity": "error",
                        "message": f"Engine room ventilation insufficient: {actual_ach:.0f} ACH < {self.MIN_AIR_CHANGES_ER} required",
                    })

            # Check explosion-proof fans
            non_ex_fans = [f for f in zone_fans if not f.is_explosion_proof]
            if non_ex_fans:
                self.findings.append({
                    "severity": "error",
                    "message": f"Engine room has {len(non_ex_fans)} non-explosion-proof fans",
                })

    def _has_errors(self) -> bool:
        """Check if any error findings."""
        return any(f.get("severity") == "error" for f in self.findings)
