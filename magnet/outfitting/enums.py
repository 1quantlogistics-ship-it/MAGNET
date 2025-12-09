"""
outfitting/enums.py - Outfitting enumerations
ALPHA OWNS THIS FILE.

Section 31: Outfitting & Accommodation
"""

from enum import Enum


class SpaceType(Enum):
    """Accommodation space types."""
    WHEELHOUSE = "wheelhouse"
    CREW_CABIN = "crew_cabin"
    OFFICER_CABIN = "officer_cabin"
    PASSENGER_CABIN = "passenger_cabin"
    PASSENGER_SALOON = "passenger_saloon"
    MESS = "mess"
    GALLEY = "galley"
    HEAD = "head"
    SHOWER = "shower"
    LOCKER = "locker"
    LAUNDRY = "laundry"
    STORE = "store"


class FurnitureType(Enum):
    """Furniture types."""
    SINGLE_BERTH = "single_berth"
    DOUBLE_BERTH = "double_berth"
    BUNK_BERTH = "bunk_berth"
    HELM_SEAT = "helm_seat"
    CREW_SEAT = "crew_seat"
    PASSENGER_SEAT = "passenger_seat"
    SHOCK_MITIGATING_SEAT = "shock_seat"
    MESS_TABLE = "mess_table"
    NAV_TABLE = "nav_table"
    LOCKER = "locker"
    WARDROBE = "wardrobe"


class FixtureType(Enum):
    """Fixture types."""
    MARINE_TOILET = "marine_toilet"
    SINK = "sink"
    SHOWER = "shower"
    STOVE_2_BURNER = "stove_2"
    STOVE_4_BURNER = "stove_4"
    REFRIGERATOR_100L = "fridge_100"
    REFRIGERATOR_200L = "fridge_200"
    MICROWAVE = "microwave"
    WASHER = "washer"
    DRYER = "dryer"
    WATER_HEATER_40L = "heater_40"
    WATER_HEATER_80L = "heater_80"


class DoorType(Enum):
    """Door types."""
    WATERTIGHT = "watertight"
    WEATHERTIGHT = "weathertight"
    FIRE_RATED = "fire_rated"
    STANDARD = "standard"
    SLIDING = "sliding"


class WindowType(Enum):
    """Window types."""
    FIXED = "fixed"
    OPENING = "opening"
    PORTLIGHT = "portlight"
