"""
analysis/noise_vibration_validator.py - Noise/vibration validator
BRAVO OWNS THIS FILE.

Section 34: Noise & Vibration
"""

from typing import Dict, Any, TYPE_CHECKING

from .noise_vibration_analyzer import NoiseVibrationAnalyzer

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class NoiseVibrationValidator:
    """Validator for noise/vibration - v1.1."""

    validator_id = "analysis/noise_vibration"
    phase = "analysis"
    priority = 340

    reads = [
        "propulsion.num_engines",
        "propulsion.installed_power_kw",
        "electrical.num_generators",
        "electrical.total_generation_kw",
        "hvac.total_power_kw",
        "outfitting.system",
    ]

    writes = [
        "analysis.noise_vibration",
        "analysis.noise_compliant",
        "analysis.max_noise_level_dba",
        "analysis.spaces_exceeding_limits",
    ]

    def validate(self, state: 'StateManager') -> Dict[str, Any]:
        analyzer = NoiseVibrationAnalyzer(state)
        results = analyzer.analyze()

        state.set("analysis.noise_vibration", results.to_dict())
        state.set("analysis.noise_compliant", results.compliant)
        state.set("analysis.max_noise_level_dba", results.max_level_dba)
        state.set("analysis.spaces_exceeding_limits", results.spaces_exceeding)

        warnings = []
        if not results.compliant:
            warnings.append(f"{results.spaces_exceeding} spaces exceed IMO noise limits")

        return {
            "valid": True,
            "errors": [],
            "warnings": warnings,
            "summary": {
                "compliant": results.compliant,
                "max_level_dba": results.max_level_dba,
                "spaces_exceeding": results.spaces_exceeding,
            },
        }
