"""
outfitting/furniture.py - Furniture and fixture definitions
ALPHA OWNS THIS FILE.

Section 31: Outfitting & Accommodation
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class FurnitureItem:
    """Furniture item specification."""

    item_id: str = ""
    item_type: str = ""
    name: str = ""

    length_mm: float = 0.0
    width_mm: float = 0.0
    height_mm: float = 0.0

    weight_kg: float = 0.0

    berth_capacity: int = 0
    seat_capacity: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "item_type": self.item_type,
            "name": self.name,
            "weight_kg": self.weight_kg,
            "berth_capacity": self.berth_capacity,
            "seat_capacity": self.seat_capacity,
        }


class FurnitureLibrary:
    """Standard furniture library."""

    ITEMS = {
        # Berths
        "single_berth": FurnitureItem(
            item_id="FURN-SB", item_type="single_berth",
            name="Single Berth", length_mm=2000, width_mm=800, height_mm=600,
            weight_kg=45, berth_capacity=1,
        ),
        "double_berth": FurnitureItem(
            item_id="FURN-DB", item_type="double_berth",
            name="Double Berth", length_mm=2000, width_mm=1400, height_mm=600,
            weight_kg=65, berth_capacity=2,
        ),
        "bunk_berth": FurnitureItem(
            item_id="FURN-BB", item_type="bunk_berth",
            name="Bunk Berth (2-tier)", length_mm=2000, width_mm=800, height_mm=1600,
            weight_kg=75, berth_capacity=2,
        ),

        # Seats
        "helm_seat": FurnitureItem(
            item_id="FURN-HS", item_type="helm_seat",
            name="Helm Seat (adjustable)", length_mm=600, width_mm=500, height_mm=1200,
            weight_kg=25, seat_capacity=1,
        ),
        "crew_seat": FurnitureItem(
            item_id="FURN-CS", item_type="crew_seat",
            name="Crew Seat", length_mm=500, width_mm=500, height_mm=900,
            weight_kg=15, seat_capacity=1,
        ),
        "passenger_seat": FurnitureItem(
            item_id="FURN-PS", item_type="passenger_seat",
            name="Passenger Seat", length_mm=500, width_mm=450, height_mm=900,
            weight_kg=12, seat_capacity=1,
        ),
        "shock_seat": FurnitureItem(
            item_id="FURN-SS", item_type="shock_seat",
            name="Shock Mitigating Seat", length_mm=600, width_mm=550, height_mm=1300,
            weight_kg=35, seat_capacity=1,
        ),

        # Tables
        "mess_table": FurnitureItem(
            item_id="FURN-MT", item_type="mess_table",
            name="Mess Table (6-person)", length_mm=1500, width_mm=800, height_mm=750,
            weight_kg=40,
        ),
        "nav_table": FurnitureItem(
            item_id="FURN-NT", item_type="nav_table",
            name="Navigation Table", length_mm=1200, width_mm=800, height_mm=900,
            weight_kg=35,
        ),

        # Storage
        "locker": FurnitureItem(
            item_id="FURN-LK", item_type="locker",
            name="Personal Locker", length_mm=600, width_mm=500, height_mm=1800,
            weight_kg=30,
        ),
        "wardrobe": FurnitureItem(
            item_id="FURN-WD", item_type="wardrobe",
            name="Wardrobe", length_mm=900, width_mm=600, height_mm=1900,
            weight_kg=45,
        ),
    }

    @classmethod
    def get(cls, item_type: str) -> Optional[FurnitureItem]:
        return cls.ITEMS.get(item_type)


@dataclass
class FixtureItem:
    """Fixture item specification."""

    item_id: str = ""
    item_type: str = ""
    name: str = ""

    power_kw: float = 0.0
    water_l_hr: float = 0.0
    drain_required: bool = False

    weight_kg: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "item_type": self.item_type,
            "name": self.name,
            "power_kw": self.power_kw,
            "water_l_hr": self.water_l_hr,
            "weight_kg": self.weight_kg,
        }


class FixtureLibrary:
    """Standard fixture library."""

    ITEMS = {
        # Sanitary
        "marine_toilet": FixtureItem(
            item_id="FIX-MT", item_type="marine_toilet",
            name="Marine Toilet", power_kw=0.05, water_l_hr=5,
            drain_required=True, weight_kg=25,
        ),
        "sink": FixtureItem(
            item_id="FIX-SK", item_type="sink",
            name="Sink (stainless)", power_kw=0, water_l_hr=10,
            drain_required=True, weight_kg=8,
        ),
        "shower": FixtureItem(
            item_id="FIX-SH", item_type="shower",
            name="Shower", power_kw=0, water_l_hr=30,
            drain_required=True, weight_kg=15,
        ),

        # Galley
        "stove_2": FixtureItem(
            item_id="FIX-S2", item_type="stove_2",
            name="2-Burner Stove (electric)", power_kw=3.0, water_l_hr=0,
            weight_kg=15,
        ),
        "stove_4": FixtureItem(
            item_id="FIX-S4", item_type="stove_4",
            name="4-Burner Stove (electric)", power_kw=6.0, water_l_hr=0,
            weight_kg=25,
        ),
        "fridge_100": FixtureItem(
            item_id="FIX-F1", item_type="fridge_100",
            name="Refrigerator 100L", power_kw=0.15, water_l_hr=0,
            weight_kg=35,
        ),
        "fridge_200": FixtureItem(
            item_id="FIX-F2", item_type="fridge_200",
            name="Refrigerator 200L", power_kw=0.25, water_l_hr=0,
            weight_kg=55,
        ),
        "microwave": FixtureItem(
            item_id="FIX-MW", item_type="microwave",
            name="Microwave Oven", power_kw=1.2, water_l_hr=0,
            weight_kg=15,
        ),

        # Laundry
        "washer": FixtureItem(
            item_id="FIX-WA", item_type="washer",
            name="Washing Machine", power_kw=2.0, water_l_hr=50,
            drain_required=True, weight_kg=70,
        ),
        "dryer": FixtureItem(
            item_id="FIX-DR", item_type="dryer",
            name="Dryer", power_kw=3.0, water_l_hr=0,
            weight_kg=50,
        ),

        # Water Heating
        "heater_40": FixtureItem(
            item_id="FIX-H4", item_type="heater_40",
            name="Water Heater 40L", power_kw=1.5, water_l_hr=0,
            weight_kg=25,
        ),
        "heater_80": FixtureItem(
            item_id="FIX-H8", item_type="heater_80",
            name="Water Heater 80L", power_kw=2.5, water_l_hr=0,
            weight_kg=40,
        ),
    }

    @classmethod
    def get(cls, item_type: str) -> Optional[FixtureItem]:
        return cls.ITEMS.get(item_type)
