"""
outfitting/deck_equipment.py - Deck equipment definitions
ALPHA OWNS THIS FILE.

Section 32: Deck Equipment
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List
import math


@dataclass
class Anchor:
    """Anchor specification."""

    anchor_id: str = ""
    anchor_type: str = "pool"  # pool, danforth, bruce, plow

    weight_kg: float = 0.0
    holding_power_ratio: float = 4.0  # Holding power / weight

    @classmethod
    def size_for_vessel(cls, loa: float, displacement_mt: float = None) -> 'Anchor':
        """
        Size anchor using Lloyd's rule.

        Rule: W_anchor = 2.5 * LOA (kg) for aluminum HSC
        """
        weight = 2.5 * loa

        # Adjust for displacement if provided
        if displacement_mt:
            disp_factor = min(1.5, max(0.8, displacement_mt / (loa * 3)))
            weight *= disp_factor

        return cls(
            anchor_id="ANC-1",
            anchor_type="pool",
            weight_kg=round(weight, 0),
            holding_power_ratio=4.0,
        )

    @property
    def holding_power_kg(self) -> float:
        return self.weight_kg * self.holding_power_ratio

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "anchor_type": self.anchor_type,
            "weight_kg": self.weight_kg,
            "holding_power_kg": self.holding_power_kg,
        }


@dataclass
class Chain:
    """Anchor chain specification."""

    chain_id: str = ""
    chain_type: str = "stud_link"

    diameter_mm: float = 0.0
    length_m: float = 0.0
    grade: str = "U2"

    @classmethod
    def size_for_anchor(cls, anchor_weight_kg: float, max_depth_m: float = 50) -> 'Chain':
        """
        Size chain based on anchor weight.

        Diameter: d = 0.35 * sqrt(W_anchor)
        Length: L = 6 * max_depth
        """
        diameter = 0.35 * math.sqrt(anchor_weight_kg)
        length = 6 * max_depth_m

        return cls(
            chain_id="CHN-1",
            chain_type="stud_link",
            diameter_mm=round(diameter, 0),
            length_m=length,
            grade="U2",
        )

    @property
    def weight_per_m_kg(self) -> float:
        """Chain weight per meter: 0.0218 * d^2 (kg/m)."""
        return 0.0218 * (self.diameter_mm ** 2)

    @property
    def total_weight_kg(self) -> float:
        return self.weight_per_m_kg * self.length_m

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "chain_type": self.chain_type,
            "diameter_mm": self.diameter_mm,
            "length_m": self.length_m,
            "grade": self.grade,
            "weight_per_m_kg": round(self.weight_per_m_kg, 2),
            "total_weight_kg": round(self.total_weight_kg, 1),
        }


@dataclass
class Windlass:
    """Windlass specification."""

    windlass_id: str = ""
    windlass_type: str = "vertical"  # vertical, horizontal

    rated_pull_kg: float = 0.0
    power_kw: float = 0.0
    chain_diameter_mm: float = 0.0

    @classmethod
    def size_for_anchor(cls, anchor_weight_kg: float, chain_diameter_mm: float, chain_30m_weight_kg: float) -> 'Windlass':
        """
        Size windlass for anchor system.

        Pull = 3 * (anchor_weight + 30m_chain_weight)
        Power = Pull * 0.001 (approx)
        """
        pull = 3 * (anchor_weight_kg + chain_30m_weight_kg)
        power = pull * 0.001

        return cls(
            windlass_id="WL-1",
            windlass_type="vertical",
            rated_pull_kg=round(pull, 0),
            power_kw=round(power, 1),
            chain_diameter_mm=chain_diameter_mm,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "windlass_id": self.windlass_id,
            "windlass_type": self.windlass_type,
            "rated_pull_kg": self.rated_pull_kg,
            "power_kw": self.power_kw,
            "chain_diameter_mm": self.chain_diameter_mm,
        }


@dataclass
class MooringEquipment:
    """Mooring equipment specification."""

    bollards: List[Dict[str, Any]] = field(default_factory=list)
    cleats: List[Dict[str, Any]] = field(default_factory=list)
    lines: List[Dict[str, Any]] = field(default_factory=list)
    fenders: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def generate_for_vessel(cls, loa: float, displacement_mt: float) -> 'MooringEquipment':
        """Generate mooring equipment for vessel."""
        # Bollard SWL based on displacement
        bollard_swl = max(5, displacement_mt * 0.2)

        # 6 bollards: bow_p/s, midship_p/s, stern_p/s
        bollards = [
            {"location": "bow_p", "swl_mt": bollard_swl},
            {"location": "bow_s", "swl_mt": bollard_swl},
            {"location": "midship_p", "swl_mt": bollard_swl},
            {"location": "midship_s", "swl_mt": bollard_swl},
            {"location": "stern_p", "swl_mt": bollard_swl},
            {"location": "stern_s", "swl_mt": bollard_swl},
        ]

        # Lines based on LOA
        line_diameter = max(16, loa * 0.6)
        line_length = max(30, loa * 1.5)
        lines = [
            {"type": "head_line", "diameter_mm": line_diameter, "length_m": line_length},
            {"type": "stern_line", "diameter_mm": line_diameter, "length_m": line_length},
            {"type": "breast_line", "diameter_mm": line_diameter, "length_m": line_length * 0.5},
            {"type": "spring_line", "diameter_mm": line_diameter, "length_m": line_length},
        ]

        # Fenders based on LOA
        fender_diameter = max(200, loa * 8)
        fender_length = max(400, loa * 16)
        num_fenders = max(4, int(loa / 5))
        fenders = [
            {"diameter_mm": fender_diameter, "length_mm": fender_length}
            for _ in range(num_fenders)
        ]

        return cls(
            bollards=bollards,
            lines=lines,
            fenders=fenders,
        )

    @property
    def total_weight_kg(self) -> float:
        """Estimate total mooring equipment weight."""
        bollard_weight = len(self.bollards) * 25
        line_weight = sum(
            0.001 * (l["diameter_mm"] ** 2) * l["length_m"]
            for l in self.lines
        )
        fender_weight = len(self.fenders) * 15
        return bollard_weight + line_weight + fender_weight

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bollards": self.bollards,
            "lines": self.lines,
            "fenders": self.fenders,
            "total_weight_kg": round(self.total_weight_kg, 0),
        }


@dataclass
class Davit:
    """Davit specification."""

    davit_id: str = ""
    davit_type: str = "rescue_boat"  # rescue_boat, stores, general

    swl_kg: float = 0.0
    reach_m: float = 0.0
    hoisting_speed_m_min: float = 0.0

    weight_kg: float = 0.0

    @classmethod
    def for_rescue_boat(cls, boat_weight_kg: float = 300) -> 'Davit':
        """Create davit for rescue boat."""
        swl = boat_weight_kg * 1.5  # 50% margin
        return cls(
            davit_id="DVT-RB",
            davit_type="rescue_boat",
            swl_kg=swl,
            reach_m=2.5,
            hoisting_speed_m_min=15,
            weight_kg=150,
        )

    @classmethod
    def for_stores(cls, stores_swl_kg: float = 500) -> 'Davit':
        """Create davit for stores handling."""
        return cls(
            davit_id="DVT-ST",
            davit_type="stores",
            swl_kg=stores_swl_kg,
            reach_m=3.0,
            hoisting_speed_m_min=10,
            weight_kg=200,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "davit_id": self.davit_id,
            "davit_type": self.davit_type,
            "swl_kg": self.swl_kg,
            "reach_m": self.reach_m,
            "hoisting_speed_m_min": self.hoisting_speed_m_min,
            "weight_kg": self.weight_kg,
        }


@dataclass
class DeckEquipmentSystem:
    """Complete deck equipment system."""

    system_id: str = ""

    anchor: Anchor = field(default_factory=Anchor)
    chain: Chain = field(default_factory=Chain)
    windlass: Windlass = field(default_factory=Windlass)
    mooring: MooringEquipment = field(default_factory=MooringEquipment)
    davits: List[Davit] = field(default_factory=list)

    @property
    def total_weight_kg(self) -> float:
        """Total deck equipment weight."""
        anchor_weight = self.anchor.weight_kg
        chain_weight = self.chain.total_weight_kg
        windlass_weight = 50  # Estimated windlass weight
        mooring_weight = self.mooring.total_weight_kg
        davit_weight = sum(d.weight_kg for d in self.davits)

        return anchor_weight + chain_weight + windlass_weight + mooring_weight + davit_weight

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_id": self.system_id,
            "anchor": self.anchor.to_dict(),
            "chain": self.chain.to_dict(),
            "windlass": self.windlass.to_dict(),
            "mooring": self.mooring.to_dict(),
            "davits": [d.to_dict() for d in self.davits],
            "total_weight_kg": round(self.total_weight_kg, 0),
        }
