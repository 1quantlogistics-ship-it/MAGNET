"""
performance/__init__.py - Modules 39-40 Performance exports
BRAVO OWNS THIS FILE.

Performance Modules:
- Module 39: Performance Prediction (Bravo)
- Module 40: Operational Envelope (Bravo)
"""

# Section 39: Performance Prediction
from .resistance import ResistanceComponents, SpeedPowerPoint, PropulsiveEfficiency
from .predictor import PerformancePredictor
from .predictor_validator import PerformanceValidator

# Section 40: Operational Envelope
from .envelope import OperationalLimit, SpeedSeaStatePoint, OperationalEnvelope
from .envelope_generator import EnvelopeGenerator
from .envelope_validator import EnvelopeValidator


__all__ = [
    # Resistance & Prediction (Section 39)
    'ResistanceComponents', 'SpeedPowerPoint', 'PropulsiveEfficiency',
    'PerformancePredictor', 'PerformanceValidator',
    # Envelope (Section 40)
    'OperationalLimit', 'SpeedSeaStatePoint', 'OperationalEnvelope',
    'EnvelopeGenerator', 'EnvelopeValidator',
]
