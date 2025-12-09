"""
production/coatings.py - Coating system definitions
ALPHA OWNS THIS FILE.

Section 33: Coatings & Corrosion Protection
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List
from enum import Enum


class CoatingZone(Enum):
    """Coating zone types."""
    UNDERWATER = "underwater"
    WATERLINE = "waterline"
    TOPSIDES = "topsides"
    DECK = "deck"
    SUPERSTRUCTURE = "superstructure"
    INTERIOR = "interior"
    TANKS = "tanks"


# Aluminum coating systems (7 zones)
ALUMINUM_COATING_SYSTEMS = {
    CoatingZone.UNDERWATER: {
        "name": "Underwater Hull",
        "primer": {"name": "Epoxy Primer", "dft_um": 75, "coats": 1},
        "intermediate": {"name": "Tie Coat", "dft_um": 50, "coats": 1},
        "antifouling": {"name": "SPC Antifouling", "dft_um": 150, "coats": 2},
        "total_dft_um": 275,
        "service_life_years": 3,
    },
    CoatingZone.WATERLINE: {
        "name": "Waterline Band",
        "primer": {"name": "Epoxy Primer", "dft_um": 75, "coats": 1},
        "intermediate": {"name": "High-Build Epoxy", "dft_um": 150, "coats": 2},
        "topcoat": {"name": "Linear Polyurethane", "dft_um": 50, "coats": 2},
        "total_dft_um": 275,
        "service_life_years": 5,
    },
    CoatingZone.TOPSIDES: {
        "name": "Topsides",
        "primer": {"name": "Epoxy Primer", "dft_um": 50, "coats": 1},
        "intermediate": {"name": "High-Build Epoxy", "dft_um": 100, "coats": 1},
        "topcoat": {"name": "Linear Polyurethane", "dft_um": 50, "coats": 2},
        "total_dft_um": 200,
        "service_life_years": 7,
    },
    CoatingZone.DECK: {
        "name": "Weather Deck",
        "primer": {"name": "Epoxy Primer", "dft_um": 50, "coats": 1},
        "intermediate": {"name": "Epoxy Anti-Slip", "dft_um": 200, "coats": 1},
        "topcoat": {"name": "Polyurethane", "dft_um": 50, "coats": 1},
        "total_dft_um": 300,
        "service_life_years": 5,
    },
    CoatingZone.SUPERSTRUCTURE: {
        "name": "Superstructure",
        "primer": {"name": "Epoxy Primer", "dft_um": 50, "coats": 1},
        "topcoat": {"name": "Linear Polyurethane", "dft_um": 50, "coats": 2},
        "total_dft_um": 100,
        "service_life_years": 7,
    },
    CoatingZone.INTERIOR: {
        "name": "Interior Spaces",
        "primer": {"name": "Epoxy Primer", "dft_um": 50, "coats": 1},
        "topcoat": {"name": "Epoxy", "dft_um": 75, "coats": 1},
        "total_dft_um": 125,
        "service_life_years": 10,
    },
    CoatingZone.TANKS: {
        "name": "Tanks",
        "primer": {"name": "Tank Primer", "dft_um": 75, "coats": 1},
        "lining": {"name": "Tank Lining Epoxy", "dft_um": 300, "coats": 2},
        "total_dft_um": 375,
        "service_life_years": 10,
    },
}


@dataclass
class CoatingArea:
    """Coating area specification."""

    area_id: str = ""
    zone: CoatingZone = CoatingZone.TOPSIDES
    area_m2: float = 0.0

    system: Dict[str, Any] = field(default_factory=dict)
    total_dft_um: float = 0.0

    @property
    def paint_volume_l(self) -> float:
        """Calculate paint volume required."""
        # Volume = Area * DFT / 1000 / solids_ratio
        solids_ratio = 0.5  # Typical 50% solids
        return self.area_m2 * self.total_dft_um / 1000 / solids_ratio

    def to_dict(self) -> Dict[str, Any]:
        return {
            "area_id": self.area_id,
            "zone": self.zone.value,
            "area_m2": round(self.area_m2, 1),
            "total_dft_um": self.total_dft_um,
            "paint_volume_l": round(self.paint_volume_l, 1),
        }


@dataclass
class Anode:
    """Cathodic protection anode."""

    anode_id: str = ""
    anode_type: str = "aluminum"  # aluminum, zinc
    weight_kg: float = 0.0
    location: str = ""

    @property
    def capacity_ah(self) -> float:
        """Anode capacity in amp-hours."""
        # Aluminum: 2700 Ah/kg, Zinc: 780 Ah/kg
        if self.anode_type == "aluminum":
            return self.weight_kg * 2700
        return self.weight_kg * 780

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anode_id": self.anode_id,
            "anode_type": self.anode_type,
            "weight_kg": self.weight_kg,
            "location": self.location,
            "capacity_ah": round(self.capacity_ah, 0),
        }


# Standard anode sizes
STANDARD_ANODE_SIZES_KG = [2.5, 5.0, 10.0, 15.0]


@dataclass
class CathodicProtection:
    """Cathodic protection system."""

    design_life_years: float = 3.0
    wetted_area_m2: float = 0.0
    current_density_ma_m2: float = 20.0  # For aluminum in seawater

    anodes: List[Anode] = field(default_factory=list)

    @classmethod
    def design_for_vessel(
        cls,
        wetted_area_m2: float,
        design_life_years: float = 3.0,
    ) -> 'CathodicProtection':
        """
        Design cathodic protection system.

        Rule: 0.3 kg/m²/year for aluminum in seawater
        """
        total_anode_weight = 0.3 * wetted_area_m2 * design_life_years

        # Select anode size (use 10kg standard)
        anode_size = 10.0
        num_anodes = max(4, int(total_anode_weight / anode_size) + 1)

        # Distribute anodes
        anodes = []
        locations = ["bow_keel", "stern_keel", "midship_p", "midship_s"]

        for i in range(num_anodes):
            loc_idx = i % len(locations)
            loc = f"{locations[loc_idx]}_{i // len(locations) + 1}"
            anodes.append(Anode(
                anode_id=f"AN-{i+1}",
                anode_type="aluminum",
                weight_kg=anode_size,
                location=loc,
            ))

        return cls(
            design_life_years=design_life_years,
            wetted_area_m2=wetted_area_m2,
            anodes=anodes,
        )

    @property
    def total_anode_weight_kg(self) -> float:
        return sum(a.weight_kg for a in self.anodes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "design_life_years": self.design_life_years,
            "wetted_area_m2": round(self.wetted_area_m2, 1),
            "anodes": [a.to_dict() for a in self.anodes],
            "total_anode_weight_kg": round(self.total_anode_weight_kg, 1),
            "num_anodes": len(self.anodes),
        }


@dataclass
class CoatingPlan:
    """Complete coating plan."""

    plan_id: str = ""

    areas: List[CoatingArea] = field(default_factory=list)
    cathodic_protection: CathodicProtection = field(default_factory=CathodicProtection)

    @property
    def total_area_m2(self) -> float:
        return sum(a.area_m2 for a in self.areas)

    @property
    def total_paint_volume_l(self) -> float:
        return sum(a.paint_volume_l for a in self.areas)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "areas": [a.to_dict() for a in self.areas],
            "cathodic_protection": self.cathodic_protection.to_dict(),
            "total_area_m2": round(self.total_area_m2, 1),
            "total_paint_volume_l": round(self.total_paint_volume_l, 1),
        }
