"""
MAGNET Loading Computer Validator (v1.1)

Loading computer validation with fixes.

Version 1.1 Fixes:
- Tank reconstruction uses geometry fields (CI#3)
- Draft uses design_displacement_mt (CI#6)
- lcf_m fallback handling (CI#7)
- Determinized outputs (CI#8)
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging

from .models import LoadingConditionType, DeadweightItem
from .calculator import LoadingCalculator
from ..arrangement.models import Tank, FluidType, FLUID_DENSITIES, determinize_dict

from ..validators.taxonomy import (
    ValidatorInterface, ValidatorDefinition, ValidationResult,
    ValidatorState, ValidationFinding, ResultSeverity
)

if TYPE_CHECKING:
    from ..core.state_manager import StateManager

logger = logging.getLogger(__name__)


class LoadingComputerValidator(ValidatorInterface):
    """
    Loading computer validator.

    Version 1.1 Fixes:
    - Tank reconstruction uses geometry fields (CI#3)
    - Draft uses design_displacement_mt (CI#6)
    - lcf_m fallback handling (CI#7)
    - Determinized outputs (CI#8)

    Reads:
        weight.lightship_mt, weight.lightship_lcg_m, weight.lightship_vcg_m
        hull.depth, hull.lwl, hull.draft, hull.tpc, hull.mct, hull.lcf_m
        hull.kb_m, hull.bm_m, hull.displacement_mt
        arrangement.tanks
        mission.crew_size

    Writes:
        loading.full_load_departure - Full load departure condition
        loading.full_load_arrival - Full load arrival condition
        loading.minimum_operating - Minimum operating condition
        loading.lightship - Lightship condition
        loading.all_conditions_pass - Whether all conditions pass criteria
        loading.worst_case_gm_m - Worst case GM across conditions
        loading.worst_case_condition - Name of worst case condition
        stability.kg_m - KG from worst loading condition
    """

    def __init__(self, definition: ValidatorDefinition):
        super().__init__(definition)
        self._calculator = LoadingCalculator()

    def validate(
        self,
        state_manager: 'StateManager',
        context: Dict[str, Any]
    ) -> ValidationResult:
        """Calculate loading conditions."""
        result = ValidationResult(
            validator_id=self.definition.validator_id,
            state=ValidatorState.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

        try:
            # Read weight data
            lightship_mt = state_manager.get("weight.lightship_mt")
            lightship_lcg = state_manager.get("weight.lightship_lcg_m")
            lightship_vcg = state_manager.get("weight.lightship_vcg_m")
            lightship_tcg = state_manager.get("weight.lightship_tcg_m") or 0.0

            # Read hull data
            depth = state_manager.get("hull.depth")
            lwl = state_manager.get("hull.lwl")
            draft = state_manager.get("hull.draft")

            # Read hydrostatics
            tpc = state_manager.get("hull.tpc") or 1.0
            mct = state_manager.get("hull.mct") or 10.0

            # FIX v1.1: lcf_m handling with fallback (CI#7)
            lcf = state_manager.get("hull.lcf_m")
            if lcf is None:
                # Fallback: estimate from LCF percentage or assume ~52% LWL
                lcf_percent = state_manager.get("hull.lcf_percent_lwl")
                if lcf_percent is not None and lwl:
                    lcf = lcf_percent * lwl / 100.0
                elif lwl:
                    lcf = lwl * 0.52
                else:
                    lcf = 10.0

            # FIX v1.1: Get design displacement for accurate draft calc (CI#6)
            design_displacement = state_manager.get("hull.displacement_mt")
            if design_displacement is None:
                # Fallback estimate
                if lwl and depth and draft:
                    beam = state_manager.get("hull.beam") or lwl * 0.25
                    cb = state_manager.get("hull.cb") or 0.5
                    design_displacement = lwl * beam * draft * cb * 1.025
                else:
                    design_displacement = 100.0  # Rough fallback

            # KM from KB + BM or direct
            km = state_manager.get("hull.km_m")
            if km is None:
                kb = state_manager.get("hull.kb_m") or 0.5
                bm = state_manager.get("hull.bm_m") or 2.0
                km = kb + bm

            # Read arrangement tanks
            tank_data = state_manager.get("arrangement.tanks") or []

            # Read mission data
            crew_size = state_manager.get("mission.crew_size") or 6

            # Validate inputs
            missing = []
            if lightship_mt is None:
                missing.append("weight.lightship_mt")
            if lightship_vcg is None:
                missing.append("weight.lightship_vcg_m")
            if depth is None:
                missing.append("hull.depth")
            if lwl is None:
                missing.append("hull.lwl")

            if missing:
                result.add_finding(ValidationFinding(
                    finding_id="load-001",
                    severity=ResultSeverity.ERROR,
                    message=f"Missing required inputs: {', '.join(missing)}",
                ))
                result.state = ValidatorState.FAILED
                result.completed_at = datetime.now(timezone.utc)
                return result

            # FIX v1.1: Reconstruct Tank objects with geometry (CI#3)
            tanks = []
            for td in tank_data:
                fluid_type = FluidType(td.get("fluid_type", "seawater"))

                # Use stored geometry (required fields in v1.1)
                length_m = td.get("length_m", 1.0)
                breadth_m = td.get("breadth_m", 1.0)
                height_m = td.get("height_m", 1.0)

                tank = Tank(
                    tank_id=td["tank_id"],
                    name=td.get("name", td["tank_id"]),
                    fluid_type=fluid_type,
                    length_m=length_m,
                    breadth_m=breadth_m,
                    height_m=height_m,
                    lcg_m=td.get("lcg_m", lwl * 0.5),
                    vcg_m=td.get("vcg_m", depth * 0.3),
                    tcg_m=td.get("tcg_m", 0.0),
                    capacity_m3=td.get("capacity_m3"),
                    fill_percent=td.get("current_fill_percent", 100) / 100,
                )
                tanks.append(tank)

            # Crew and stores estimates
            crew_weight = crew_size * 0.085  # ~85kg per person
            stores_weight = crew_size * 0.05  # ~50kg per person

            # Generate standard conditions
            conditions = self._calculator.create_standard_conditions(
                lightship_mt=lightship_mt,
                lightship_lcg_m=lightship_lcg or (lwl * 0.48),
                lightship_vcg_m=lightship_vcg,
                lightship_tcg_m=lightship_tcg,
                tanks=tanks,
                crew_weight_mt=crew_weight,
                stores_weight_mt=stores_weight,
                lcg_crew_m=lwl * 0.35,
                lcg_stores_m=lwl * 0.40,
                vcg_crew_m=depth * 0.9,
                vcg_stores_m=depth * 0.5,
                depth_m=depth,
                tpc=tpc,
                mct=mct,
                lcf_m=lcf,
                km_m=km,
                design_draft_m=draft or depth * 0.5,
                design_displacement_mt=design_displacement,
                lwl_m=lwl,
            )

            # Write results (with determinization - CI#8)
            agent = "loading/computer"
            all_pass = True
            worst_gm = float('inf')
            worst_condition = None

            for cond_name, cond_result in conditions.items():
                # FIX v1.1: Determinize output
                cond_dict = determinize_dict(cond_result.to_dict())
                state_manager.write(f"loading.{cond_name}", cond_dict,
                                   agent, f"Loading condition: {cond_result.condition_name}")

                # Track worst GM
                if cond_result.gm_fluid_m < worst_gm:
                    worst_gm = cond_result.gm_fluid_m
                    worst_condition = cond_name

                if not cond_result.passes_all_criteria:
                    all_pass = False
                    for error in cond_result.errors:
                        result.add_finding(ValidationFinding(
                            finding_id=f"load-{cond_name}-error",
                            severity=ResultSeverity.ERROR,
                            message=f"{cond_result.condition_name}: {error}",
                        ))

                for warning in cond_result.warnings:
                    result.add_finding(ValidationFinding(
                        finding_id=f"load-{cond_name}-warn",
                        severity=ResultSeverity.WARNING,
                        message=f"{cond_result.condition_name}: {warning}",
                    ))

            state_manager.write("loading.all_conditions_pass", all_pass,
                               agent, "All loading conditions pass criteria")

            state_manager.write("loading.worst_case_gm_m", worst_gm,
                               agent, "Worst case GM across conditions")

            state_manager.write("loading.worst_case_condition", worst_condition,
                               agent, "Condition with worst GM")

            # Update stability.kg_m for worst case (highest VCG)
            worst_vcg = max(c.vcg_m for c in conditions.values())
            state_manager.write("stability.kg_m", worst_vcg,
                               agent, "KG from worst loading condition")

            # Set result state
            if result.error_count > 0:
                result.state = ValidatorState.FAILED
            elif result.warning_count > 0:
                result.state = ValidatorState.WARNING
            else:
                result.state = ValidatorState.PASSED

            logger.debug(
                f"Loading computer complete: {len(conditions)} conditions, "
                f"worst GM={worst_gm:.3f}m ({worst_condition})"
            )

        except Exception as e:
            result.state = ValidatorState.ERROR
            result.error_message = str(e)
            logger.error(f"Loading computer failed: {e}")

        result.completed_at = datetime.now(timezone.utc)
        return result
