"""
outfitting/__init__.py - Modules 31-32 Outfitting exports
ALPHA OWNS THIS FILE.

Section 31: Outfitting & Accommodation
Section 32: Deck Equipment
"""

# Enums
from .enums import (
    SpaceType,
    FurnitureType,
    FixtureType,
    DoorType,
    WindowType,
)

# Section 31: Accommodation
from .spaces import AccommodationSpace, SPACE_REQUIREMENTS
from .furniture import FurnitureItem, FurnitureLibrary, FixtureItem, FixtureLibrary
from .openings import Door, Window
from .system import OutfittingSystem
from .generator import OutfittingGenerator
from .validator import OutfittingValidator

# Section 32: Deck Equipment
from .deck_equipment import (
    Anchor,
    Chain,
    Windlass,
    MooringEquipment,
    Davit,
    DeckEquipmentSystem,
)
from .deck_equipment_generator import DeckEquipmentGenerator
from .deck_equipment_validator import DeckEquipmentValidator


__all__ = [
    # Enums
    "SpaceType",
    "FurnitureType",
    "FixtureType",
    "DoorType",
    "WindowType",
    # Spaces
    "AccommodationSpace",
    "SPACE_REQUIREMENTS",
    # Furniture & Fixtures
    "FurnitureItem",
    "FurnitureLibrary",
    "FixtureItem",
    "FixtureLibrary",
    # Openings
    "Door",
    "Window",
    # System
    "OutfittingSystem",
    "OutfittingGenerator",
    "OutfittingValidator",
    # Deck Equipment
    "Anchor",
    "Chain",
    "Windlass",
    "MooringEquipment",
    "Davit",
    "DeckEquipmentSystem",
    "DeckEquipmentGenerator",
    "DeckEquipmentValidator",
]
