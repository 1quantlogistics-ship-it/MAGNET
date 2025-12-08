"""
systems/safety/validator.py - Safety system validation.

BRAVO OWNS THIS FILE.

Module 30 v1.0 - Safety System Validator.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, TYPE_CHECKING

from .schema import SafetySystem, FireZone

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


@dataclass
class SafetyValidationResult:
    """Result of safety system validation."""

    is_valid: bool = True
    """Overall validation status."""

    issues: List[str] = field(default_factory=list)
    """List of validation issues."""

    warnings: List[str] = field(default_factory=list)
    """List of warnings (non-critical)."""

    liferaft_capacity_ratio: float = 0.0
    """Liferaft capacity / total persons."""

    lifejacket_ratio: float = 0.0
    """Lifejacket count / total persons."""

    fire_pump_capacity_m3h: float = 0.0
    """Total fire pump capacity."""

    detector_coverage: float = 0.0
    """Detector coverage ratio."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "issues": self.issues,
            "warnings": self.warnings,
            "liferaft_capacity_ratio": round(self.liferaft_capacity_ratio, 2),
            "lifejacket_ratio": round(self.lifejacket_ratio, 2),
            "fire_pump_capacity_m3h": round(self.fire_pump_capacity_m3h, 1),
            "detector_coverage": round(self.detector_coverage, 2),
        }


class SafetyValidator:
    """Validate safety systems per SOLAS requirements."""

    # SOLAS requirements
    LIFERAFT_CAPACITY_MIN = 1.0  # 100% of persons
    LIFEJACKET_RATIO_MIN = 1.0   # 100% of persons
    LIFEBUOY_MIN = 4             # Minimum lifebuoys

    # Fire detection coverage (detectors per 100 m²)
    DETECTOR_DENSITY_MIN = 1.0

    def __init__(self, state: 'StateManager'):
        self.state = state

        # Get vessel parameters
        self.loa = state.get("hull.loa", 26)
        self.beam = state.get("hull.beam", 6)
        self.depth = state.get("hull.depth", 3)
        self.crew = state.get("mission.crew", 4)
        self.passengers = state.get("mission.passengers", 12)
        self.total_persons = self.crew + self.passengers

    def validate(self, system: SafetySystem) -> SafetyValidationResult:
        """Validate complete safety system."""
        result = SafetyValidationResult()

        # Run all validation checks
        self._check_liferaft_capacity(system, result)
        self._check_lifejacket_count(system, result)
        self._check_lifebuoy_count(system, result)
        self._check_fire_pumps(system, result)
        self._check_fire_detection(system, result)
        self._check_engine_room_protection(system, result)
        self._check_bilge_system(system, result)
        self._check_navigation_safety(system, result)

        # Set overall validity
        result.is_valid = len(result.issues) == 0

        return result

    def _check_liferaft_capacity(
        self,
        system: SafetySystem,
        result: SafetyValidationResult,
    ) -> None:
        """Check liferaft capacity per SOLAS III."""
        # Calculate total liferaft capacity
        liferafts = [a for a in system.life_saving_appliances
                     if a.appliance_type == "liferaft"]
        total_capacity = sum(r.capacity for r in liferafts)

        ratio = total_capacity / self.total_persons if self.total_persons > 0 else 0
        result.liferaft_capacity_ratio = ratio

        if ratio < self.LIFERAFT_CAPACITY_MIN:
            result.issues.append(
                f"Liferaft capacity {total_capacity} insufficient for "
                f"{self.total_persons} persons (need {self.LIFERAFT_CAPACITY_MIN * 100:.0f}%)"
            )

        # Check distribution (should be on both sides)
        if len(liferafts) < 2:
            result.warnings.append(
                "Liferafts should be distributed on both sides of vessel"
            )

    def _check_lifejacket_count(
        self,
        system: SafetySystem,
        result: SafetyValidationResult,
    ) -> None:
        """Check lifejacket count per SOLAS III."""
        lifejackets = [a for a in system.life_saving_appliances
                       if a.appliance_type == "lifejacket"]
        total_jackets = sum(j.capacity for j in lifejackets)

        ratio = total_jackets / self.total_persons if self.total_persons > 0 else 0
        result.lifejacket_ratio = ratio

        if ratio < self.LIFEJACKET_RATIO_MIN:
            result.issues.append(
                f"Lifejacket count {total_jackets} insufficient for "
                f"{self.total_persons} persons (need 100%)"
            )

    def _check_lifebuoy_count(
        self,
        system: SafetySystem,
        result: SafetyValidationResult,
    ) -> None:
        """Check lifebuoy count per SOLAS III."""
        lifebuoys = [a for a in system.life_saving_appliances
                     if a.appliance_type == "lifebuoy"]
        total_buoys = sum(b.capacity for b in lifebuoys)

        if total_buoys < self.LIFEBUOY_MIN:
            result.issues.append(
                f"Lifebuoy count {total_buoys} below minimum {self.LIFEBUOY_MIN}"
            )

    def _check_fire_pumps(
        self,
        system: SafetySystem,
        result: SafetyValidationResult,
    ) -> None:
        """Check fire pump capacity per SOLAS II-2."""
        # Required capacity: Q = 0.15 * sqrt(L * (B + D))
        q_required = 0.15 * (self.loa * (self.beam + self.depth)) ** 0.5
        q_required = max(25.0, q_required)

        # Sum main pump capacities
        main_pumps = [p for p in system.fire_pumps if not p.is_portable]
        total_capacity = sum(p.capacity_m3h for p in main_pumps)
        result.fire_pump_capacity_m3h = total_capacity

        if total_capacity < q_required:
            result.issues.append(
                f"Fire pump capacity {total_capacity:.1f} m³/h below "
                f"required {q_required:.1f} m³/h"
            )

        # Check for emergency pump if required
        if self.loa > 20:
            emergency_pumps = [p for p in system.fire_pumps if p.is_emergency]
            if len(emergency_pumps) == 0:
                result.issues.append(
                    "Emergency fire pump required for vessels > 20m LOA"
                )

    def _check_fire_detection(
        self,
        system: SafetySystem,
        result: SafetyValidationResult,
    ) -> None:
        """Check fire detection coverage."""
        total_area = sum(z.floor_area_m2 for z in system.fire_zones)
        total_detectors = sum(z.detector_count for z in system.fire_zones)

        # Calculate coverage (detectors per 100 m²)
        coverage = (total_detectors / total_area * 100) if total_area > 0 else 0
        result.detector_coverage = coverage

        if coverage < self.DETECTOR_DENSITY_MIN:
            result.warnings.append(
                f"Fire detector density {coverage:.2f} per 100m² below "
                f"recommended {self.DETECTOR_DENSITY_MIN}"
            )

        # Check all zones have detection
        for zone in system.fire_zones:
            if not zone.has_smoke_detection and not zone.has_heat_detection:
                result.issues.append(
                    f"Fire zone '{zone.zone_name}' has no detection"
                )

    def _check_engine_room_protection(
        self,
        system: SafetySystem,
        result: SafetyValidationResult,
    ) -> None:
        """Check engine room fire protection per SOLAS II-2."""
        er_zones = [z for z in system.fire_zones
                    if z.zone_type == FireZone.ENGINE_ROOM]

        if len(er_zones) == 0:
            result.issues.append("Engine room fire zone not defined")
            return

        for er in er_zones:
            # Must have fixed firefighting system
            if not er.has_fixed_system:
                result.issues.append(
                    f"Engine room '{er.zone_name}' requires fixed "
                    "firefighting system (CO2, water mist, etc.)"
                )

            # Must have A-60 boundaries
            if not er.has_a60_boundaries:
                result.warnings.append(
                    f"Engine room '{er.zone_name}' should have A-60 boundaries"
                )

            # Must have heat detection (in addition to smoke)
            if not er.has_heat_detection:
                result.warnings.append(
                    f"Engine room '{er.zone_name}' should have heat detection"
                )

    def _check_bilge_system(
        self,
        system: SafetySystem,
        result: SafetyValidationResult,
    ) -> None:
        """Check bilge system per SOLAS II-1."""
        bilge = system.bilge_system

        # Check pump count
        min_pumps = 2 if self.loa < 30 else 3
        if bilge.pump_count < min_pumps:
            result.issues.append(
                f"Bilge pump count {bilge.pump_count} below "
                f"minimum {min_pumps} for {self.loa:.0f}m vessel"
            )

        # Check high level alarms
        if not bilge.has_high_level_alarm:
            result.issues.append("Bilge high level alarm required")

        # Check engine room has alarm
        if "Engine Room" not in bilge.alarm_locations:
            result.warnings.append(
                "Engine room should have bilge level alarm"
            )

    def _check_navigation_safety(
        self,
        system: SafetySystem,
        result: SafetyValidationResult,
    ) -> None:
        """Check navigation safety equipment."""
        if not system.has_ais:
            result.issues.append("AIS required for commercial vessels")

        if not system.has_epirb:
            result.issues.append("EPIRB required")

        if not system.has_sart:
            result.warnings.append("SART recommended for SAR operations")

        # Check EPIRB in life saving appliances
        epirbs = [a for a in system.life_saving_appliances
                  if a.appliance_type == "EPIRB"]
        if len(epirbs) == 0:
            result.warnings.append("EPIRB should be listed in life saving appliances")
