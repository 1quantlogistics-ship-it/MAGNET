"""
analysis/__init__.py - Modules 34-35 Analysis exports
BRAVO OWNS THIS FILE.

Analysis Modules:
- Module 34: Noise & Vibration (Bravo)
- Module 35: Seakeeping Analysis (Bravo)
"""

# Section 34: Noise & Vibration
from .noise_vibration import (
    NoiseSource, SpaceNoiseLevel, IsolationMount, NoiseVibrationResults,
    IMO_NOISE_LIMITS, estimate_engine_swl, estimate_generator_swl
)
from .noise_vibration_analyzer import NoiseVibrationAnalyzer
from .noise_vibration_validator import NoiseVibrationValidator

# Section 35: Seakeeping
from .seakeeping import (
    SEA_STATES, NORDFORSK_CRITERIA,
    MotionResponse, OperabilityResult, SeakeepingResults
)
from .seakeeping_predictor import SeakeepingPredictor
from .seakeeping_validator import SeakeepingValidator


__all__ = [
    # Noise & Vibration (Section 34)
    'NoiseSource', 'SpaceNoiseLevel', 'IsolationMount', 'NoiseVibrationResults',
    'IMO_NOISE_LIMITS', 'estimate_engine_swl', 'estimate_generator_swl',
    'NoiseVibrationAnalyzer', 'NoiseVibrationValidator',
    # Seakeeping (Section 35)
    'SEA_STATES', 'NORDFORSK_CRITERIA',
    'MotionResponse', 'OperabilityResult', 'SeakeepingResults',
    'SeakeepingPredictor', 'SeakeepingValidator',
]
