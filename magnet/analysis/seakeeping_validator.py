"""
analysis/seakeeping_validator.py - Seakeeping validator
BRAVO OWNS THIS FILE.

Section 35: Seakeeping Analysis - v1.1
"""

from typing import Dict, Any, TYPE_CHECKING

from .seakeeping_predictor import SeakeepingPredictor

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class SeakeepingValidator:
    """Validator for seakeeping - v1.1."""

    validator_id = "analysis/seakeeping"
    phase = "analysis"
    priority = 350

    reads = [
        "hull.lwl",
        "hull.beam",
        "hull.draft",
        "stability.gm_transverse_m",
        "mission.cruise_speed_kts",
    ]

    writes = [
        "analysis.seakeeping",
        "analysis.operability_index",
        "analysis.limiting_criterion",
        "analysis.max_sea_state",
    ]

    def validate(self, state: 'StateManager') -> Dict[str, Any]:
        predictor = SeakeepingPredictor(state)

        missing = predictor._verify_inputs()
        if missing:
            return {
                "valid": False,
                "errors": [f"Missing required fields: {', '.join(missing)}"],
                "warnings": [],
            }

        results = predictor.analyze()

        state.set("analysis.seakeeping", results.to_dict())
        state.set("analysis.operability_index", results.operability_index)
        state.set("analysis.limiting_criterion", results.limiting_criterion)
        state.set("analysis.max_sea_state", results.max_operational_ss)

        warnings = []
        if results.operability_index < 80:
            warnings.append(f"Low operability index: {results.operability_index:.0f}%")
        if results.max_operational_ss < 3:
            warnings.append(f"Limited to Sea State {results.max_operational_ss}")

        return {
            "valid": True,
            "errors": [],
            "warnings": warnings,
            "summary": {
                "max_operational_ss": results.max_operational_ss,
                "operability_index": results.operability_index,
                "limiting_criterion": results.limiting_criterion,
            },
        }
