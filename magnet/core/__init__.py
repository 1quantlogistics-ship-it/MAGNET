"""
MAGNET Core Module

Contains the foundation layer:
- Module 01: Unified Design State (dataclasses, DesignState, StateManager)
- Module 02: Phase State Machine (PhaseState, transitions, gate conditions)
"""

from magnet.core.enums import (
    PhaseState,
    DesignPhase,
    VesselType,
    HullType,
    PropulsionType,
    MaterialType,
    ClassificationSociety,
)

__all__ = [
    "PhaseState",
    "DesignPhase",
    "VesselType",
    "HullType",
    "PropulsionType",
    "MaterialType",
    "ClassificationSociety",
]
