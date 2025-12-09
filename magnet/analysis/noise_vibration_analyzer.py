"""
analysis/noise_vibration_analyzer.py - Noise and vibration analysis
BRAVO OWNS THIS FILE.

Section 34: Noise & Vibration
"""

from typing import Dict, Any, List, TYPE_CHECKING
import math

from .noise_vibration import (
    NoiseSource, SpaceNoiseLevel, IsolationMount,
    NoiseVibrationResults, IMO_NOISE_LIMITS,
    estimate_engine_swl, estimate_generator_swl
)

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class NoiseVibrationAnalyzer:
    """Analyze noise and vibration."""

    def __init__(self, state: 'StateManager'):
        self.state = state

    def analyze(self) -> NoiseVibrationResults:
        """Perform noise/vibration analysis."""

        results = NoiseVibrationResults()
        results.sources = self._identify_sources()
        spaces = self._get_spaces()
        results.space_levels = self._predict_levels(results.sources, spaces)
        results.isolation_mounts = self._design_isolation()

        return results

    def _identify_sources(self) -> List[NoiseSource]:
        """Identify all noise sources."""
        sources = []

        num_engines = self.state.get("propulsion.num_engines", 2)
        installed_power = self.state.get("propulsion.installed_power_kw")
        if installed_power is None:
            installed_power = self.state.get("propulsion.total_installed_power_kw", 2000)
        engine_power = installed_power / max(1, num_engines)

        for i in range(num_engines):
            swl = estimate_engine_swl(engine_power)
            sources.append(NoiseSource(
                source_id=f"ME-{i+1}",
                source_type="main_engine",
                sound_power_level_dba=swl,
            ))

        num_gens = self.state.get("electrical.num_generators", 2)
        gen_power = self.state.get("electrical.total_generation_kw", 100) / max(1, num_gens)

        for i in range(num_gens):
            swl = estimate_generator_swl(gen_power)
            sources.append(NoiseSource(
                source_id=f"GEN-{i+1}",
                source_type="generator",
                sound_power_level_dba=swl,
            ))

        hvac_power = self.state.get("hvac.total_power_kw", 10)
        if hvac_power > 0:
            sources.append(NoiseSource(
                source_id="HVAC-1",
                source_type="hvac",
                sound_power_level_dba=70 + 5 * math.log10(max(1, hvac_power)),
            ))

        return sources

    def _get_spaces(self) -> List[Dict]:
        """Get accommodation spaces from outfitting."""
        outfitting = self.state.get("outfitting.system", {})
        spaces = outfitting.get("spaces", []) if isinstance(outfitting, dict) else []

        if not spaces:
            # Fallback default spaces if outfitting not available
            spaces = [
                {"space_id": "WH", "space_type": "wheelhouse"},
                {"space_id": "CC-1", "space_type": "crew_cabin"},
                {"space_id": "MESS", "space_type": "mess"},
            ]

        return spaces

    def _predict_levels(
        self,
        sources: List[NoiseSource],
        spaces: List[Dict],
    ) -> List[SpaceNoiseLevel]:
        """Predict noise levels in spaces."""
        levels = []

        # Calculate combined engine room sound power level
        engine_sources = [s for s in sources if "engine" in s.source_type]
        if engine_sources:
            er_swl = 10 * math.log10(sum(10 ** (s.sound_power_level_dba / 10)
                                          for s in engine_sources))
        else:
            er_swl = 100  # Default if no engines

        for space in spaces:
            space_type = space.get("space_type", "crew_cabin")
            space_id = space.get("space_id", "UNKNOWN")

            limit = IMO_NOISE_LIMITS.get(space_type, 65)

            # Predict level based on space type and distance attenuation
            if space_type == "engine_room":
                predicted = er_swl - 6
            elif space_type == "wheelhouse":
                # Distance ~15m, structure loss ~25 dB
                predicted = er_swl - 20 * math.log10(15) - 11 - 25
            elif space_type in ["crew_cabin", "officer_cabin"]:
                # Distance ~10m, structure loss ~30 dB
                predicted = er_swl - 20 * math.log10(10) - 11 - 30
            elif space_type == "passenger_saloon":
                # Distance ~12m, structure loss ~28 dB
                predicted = er_swl - 20 * math.log10(12) - 11 - 28
            else:
                # Default calculation
                predicted = er_swl - 20 * math.log10(10) - 11 - 25

            levels.append(SpaceNoiseLevel(
                space_id=space_id,
                space_type=space_type,
                predicted_level_dba=max(40, predicted),  # Minimum ambient
                limit_dba=limit,
            ))

        return levels

    def _design_isolation(self) -> List[Dict]:
        """Design isolation mounts for main equipment."""
        mounts = []

        # Engine isolation - assume high-speed diesel
        engine_rpm = 2000
        cylinders = 12
        firing_freq = engine_rpm * cylinders / 120

        mount = IsolationMount.design_for_isolation(firing_freq, 0.9)
        mounts.append({
            "equipment": "main_engines",
            "mount": mount.to_dict(),
        })

        return mounts
