"""
MAGNET Arrangement Validator (v1.1)

Arrangement validation with fixes.

Version 1.1 Fixes:
- Fixed FluidType import (CI#1)
- Added determinization to state writes (CI#8)
- Service profile support (CI#4)
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging

from .models import GeneralArrangement, FluidType, determinize_dict
from .generator import ArrangementGenerator, VesselServiceProfile

from ..validators.taxonomy import (
    ValidatorInterface, ValidatorDefinition, ValidationResult,
    ValidatorState, ValidationFinding, ResultSeverity
)

if TYPE_CHECKING:
    from ..core.state_manager import StateManager

logger = logging.getLogger(__name__)


class ArrangementValidator(ValidatorInterface):
    """
    Validates general arrangement against design rules.

    Version 1.1 Fixes:
    - Fixed FluidType import (CI#1)
    - Added determinization to state writes (CI#8)
    - Service profile support (CI#4)

    Reads:
        hull.lwl, hull.beam, hull.depth, hull.draft
        mission.range_nm, mission.crew_size, mission.vessel_type
        mission.endurance_days, mission.services_required
        propulsion.installed_power_kw

    Writes:
        arrangement.data - Complete arrangement data
        arrangement.compartment_count - Number of compartments
        arrangement.collision_bulkhead_m - Collision bulkhead position
        arrangement.tanks - Tank definitions for loading computer
        arrangement.compartments - Compartment definitions
        arrangement.tank_summary - Summary of tank capacities
    """

    def __init__(self, definition: ValidatorDefinition):
        super().__init__(definition)
        self._generator = ArrangementGenerator()

    def validate(
        self,
        state_manager: 'StateManager',
        context: Dict[str, Any]
    ) -> ValidationResult:
        """Generate and validate arrangement."""
        result = ValidationResult(
            validator_id=self.definition.validator_id,
            state=ValidatorState.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

        try:
            # Read inputs
            lwl = state_manager.get("hull.lwl")
            beam = state_manager.get("hull.beam")
            depth = state_manager.get("hull.depth")
            draft = state_manager.get("hull.draft")

            range_nm = state_manager.get("mission.range_nm") or 500
            crew_size = state_manager.get("mission.crew_size") or 6
            vessel_type = state_manager.get("mission.vessel_type") or "patrol"
            installed_power = (
                state_manager.get("propulsion.installed_power_kw") or
                state_manager.get("propulsion.total_installed_power_kw") or
                1000
            )
            endurance_days = state_manager.get("mission.endurance_days") or 3.0

            # Read service profile (v1.1)
            services_data = state_manager.get("mission.services_required")
            if services_data and isinstance(services_data, dict):
                services = VesselServiceProfile.from_dict(services_data)
            else:
                services = None  # Will be derived from vessel_type

            # Validate inputs
            if lwl is None or beam is None or depth is None:
                result.add_finding(ValidationFinding(
                    finding_id="arr-001",
                    severity=ResultSeverity.ERROR,
                    message="Missing hull dimensions for arrangement",
                ))
                result.state = ValidatorState.FAILED
                result.completed_at = datetime.now(timezone.utc)
                return result

            # Generate arrangement
            arrangement = self._generator.generate(
                lwl=lwl,
                beam=beam,
                depth=depth,
                draft=draft or depth * 0.5,
                vessel_type=vessel_type,
                crew_size=crew_size,
                range_nm=range_nm,
                installed_power_kw=installed_power,
                endurance_days=endurance_days,
                services=services,
            )

            # Validate collision bulkhead position
            collision_bhd = arrangement.get_collision_bulkhead()
            if collision_bhd:
                min_pos = lwl * 0.05
                max_pos = min(lwl * 0.08, lwl * 0.15)

                if collision_bhd.position_m < min_pos:
                    result.add_finding(ValidationFinding(
                        finding_id="arr-collision-fwd",
                        severity=ResultSeverity.WARNING,
                        message=f"Collision bulkhead at {collision_bhd.position_m:.2f}m "
                               f"is forward of minimum {min_pos:.2f}m",
                    ))

            # Validate fuel capacity
            # FIX v1.1: Correct FluidType import usage (CI#1)
            fuel_tanks = arrangement.get_tanks_by_type(FluidType.FUEL_MGO)
            total_fuel_m3 = sum(t.total_capacity_m3 for t in fuel_tanks)

            cruise_hours = range_nm / 10.0
            required_fuel_kg = installed_power * 0.7 * 0.21 * cruise_hours
            required_fuel_m3 = required_fuel_kg / 850 * 1.1

            if total_fuel_m3 < required_fuel_m3 * 0.9:  # 10% tolerance
                result.add_finding(ValidationFinding(
                    finding_id="arr-fuel-short",
                    severity=ResultSeverity.WARNING,
                    message=f"Fuel capacity {total_fuel_m3:.1f}m³ may be insufficient "
                           f"for {range_nm}nm range (need ~{required_fuel_m3:.1f}m³)",
                ))

            # Validate freshwater capacity if service required
            if services is None or services.freshwater:
                fw_tanks = arrangement.get_tanks_by_type(FluidType.FRESHWATER)
                total_fw_m3 = sum(t.total_capacity_m3 for t in fw_tanks)
                required_fw_m3 = crew_size * 0.1 * endurance_days

                if total_fw_m3 < required_fw_m3 * 0.8:  # 20% tolerance
                    result.add_finding(ValidationFinding(
                        finding_id="arr-fw-short",
                        severity=ResultSeverity.WARNING,
                        message=f"Freshwater capacity {total_fw_m3:.1f}m³ may be insufficient "
                               f"for {crew_size} crew, {endurance_days} days",
                    ))

            # Write results (with determinization - CI#8)
            source = "arrangement/generator"  # Hole #7 Fix: Proper source for provenance

            # FIX v1.1: Determinize all outputs
            arrangement_data = arrangement.to_dict()  # Already determinized
            state_manager.set("arrangement.data", arrangement_data, source)

            state_manager.set("arrangement.compartment_count", len(arrangement.compartments), source)

            if collision_bhd:
                state_manager.set("arrangement.collision_bulkhead_m", collision_bhd.position_m, source)

            # Tank list (with geometry for reconstruction - CI#3)
            tank_list = [t.to_dict() for t in arrangement.tanks]
            state_manager.set("arrangement.tanks", determinize_dict({"tanks": tank_list})["tanks"], source)

            # Compartment list
            compartment_list = [c.to_dict() for c in arrangement.compartments]
            state_manager.set(
                "arrangement.compartments",
                determinize_dict({"compartments": compartment_list})["compartments"],
                source
            )

            # Tank summary
            tank_summary = {
                "fuel_m3": sum(t.total_capacity_m3 for t in arrangement.get_tanks_by_type(FluidType.FUEL_MGO)),
                "fuel_mdo_m3": sum(t.total_capacity_m3 for t in arrangement.get_tanks_by_type(FluidType.FUEL_MDO)),
                "freshwater_m3": sum(t.total_capacity_m3 for t in arrangement.get_tanks_by_type(FluidType.FRESHWATER)),
                "lube_oil_m3": sum(t.total_capacity_m3 for t in arrangement.get_tanks_by_type(FluidType.LUBE_OIL)),
                "sewage_m3": sum(t.total_capacity_m3 for t in arrangement.get_tanks_by_type(FluidType.SEWAGE)),
                "ballast_m3": sum(t.total_capacity_m3 for t in arrangement.get_tanks_by_type(FluidType.SEAWATER)),
                "hydraulic_m3": sum(t.total_capacity_m3 for t in arrangement.get_tanks_by_type(FluidType.HYDRAULIC_OIL)),
                "total_tanks": len(arrangement.tanks),
            }
            state_manager.set("arrangement.tank_summary", determinize_dict(tank_summary), source)

            # Set result state
            if result.error_count > 0:
                result.state = ValidatorState.FAILED
            elif result.warning_count > 0:
                result.state = ValidatorState.WARNING
            else:
                result.state = ValidatorState.PASSED

            logger.debug(
                f"Arrangement validation complete: {len(arrangement.tanks)} tanks, "
                f"{len(arrangement.compartments)} compartments"
            )

        except Exception as e:
            result.state = ValidatorState.ERROR
            result.error_message = str(e)
            logger.error(f"Arrangement validation failed: {e}")

        result.completed_at = datetime.now(timezone.utc)
        return result
