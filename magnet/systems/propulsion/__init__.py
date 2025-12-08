"""
systems/propulsion/__init__.py - Propulsion system exports
ALPHA OWNS THIS FILE.

Section 26: Propulsion System
"""

from .enums import (
    EngineType,
    PropulsorType,
    GearboxType,
    ShaftMaterial,
    PropellerMaterial,
    FuelType,
)

from .engines import EngineSpecification, EngineLibrary

from .propulsors import PropellerSpecification, WaterjetSpecification

from .system import GearboxSpecification, ShaftLine, PropulsionSystem

from .generator import PropulsionSystemGenerator

from .validator import PropulsionValidator


__all__ = [
    # Enums
    "EngineType",
    "PropulsorType",
    "GearboxType",
    "ShaftMaterial",
    "PropellerMaterial",
    "FuelType",
    # Engines
    "EngineSpecification",
    "EngineLibrary",
    # Propulsors
    "PropellerSpecification",
    "WaterjetSpecification",
    # System
    "GearboxSpecification",
    "ShaftLine",
    "PropulsionSystem",
    # Generator
    "PropulsionSystemGenerator",
    # Validator
    "PropulsionValidator",
]
