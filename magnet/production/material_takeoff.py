"""
production/material_takeoff.py - Material quantity estimation.

BRAVO OWNS THIS FILE.

Module 11 v1.1 - Parametric material takeoff calculator.

v1.1 FIX: Uses structure.material and structure.frame_spacing_mm
          which exist in Module 01 v1.8 StructuralDesign.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .enums import MaterialCategory
from .models import MaterialItem, MaterialTakeoffResult, MATERIAL_DENSITIES

if TYPE_CHECKING:
    from ..core.state_manager import StateManager


class MaterialTakeoff:
    """
    Material quantity estimator (parametric early-stage).

    Calculates plate areas, profile lengths, and weights based on
    principal dimensions and structural parameters.
    """

    def __init__(self, scrap_factor: float = 1.15):
        """
        Initialize material takeoff calculator.

        Args:
            scrap_factor: Factor to account for waste/scrap (default 15%)
        """
        self.scrap_factor = scrap_factor
        self._item_counter = 0

    def calculate(self, state: "StateManager") -> MaterialTakeoffResult:
        """
        Calculate material takeoff from state.

        Args:
            state: StateManager with hull and structure data

        Returns:
            MaterialTakeoffResult with all material items and summary
        """
        result = MaterialTakeoffResult(scrap_factor=self.scrap_factor)
        self._item_counter = 0

        # Get principal dimensions
        lwl = state.get("hull.lwl", 0)
        beam = state.get("hull.beam", 0)
        depth = state.get("hull.depth", 0)

        if lwl <= 0 or beam <= 0 or depth <= 0:
            return result

        # Get structural parameters (v1.1: verified field names)
        material = state.get("structure.material", "aluminum_5083")
        bottom_t = state.get("structure.bottom_plate_thickness_mm", 6.0)
        side_t = state.get("structure.side_plate_thickness_mm", 5.0)
        deck_t = state.get("structure.deck_plate_thickness_mm", 4.0)
        frame_spacing_mm = state.get("structure.frame_spacing_mm", 500.0)

        # Get material density
        density = MATERIAL_DENSITIES.get(material, 2660.0)

        # === PLATE ITEMS ===

        # Bottom shell plating
        bottom_area = lwl * beam * 1.1  # 10% overlap factor
        result.items.append(self._create_plate_item(
            "Bottom Shell Plating",
            material,
            bottom_t,
            bottom_area,
            density,
        ))

        # Side shell plating (both sides)
        side_area = 2 * lwl * depth * 0.85  # Form factor
        result.items.append(self._create_plate_item(
            "Side Shell Plating",
            material,
            side_t,
            side_area,
            density,
        ))

        # Main deck plating
        deck_area = lwl * beam * 0.9  # Openings deduction
        result.items.append(self._create_plate_item(
            "Main Deck Plating",
            material,
            deck_t,
            deck_area,
            density,
        ))

        # Transom plating
        transom_area = beam * depth * 0.8
        result.items.append(self._create_plate_item(
            "Transom Plating",
            material,
            side_t,
            transom_area,
            density,
        ))

        # Bulkheads
        num_bulkheads = max(4, int(lwl / 5))
        bulkhead_area = num_bulkheads * beam * depth * 0.7
        result.items.append(self._create_plate_item(
            f"Bulkheads ({num_bulkheads})",
            material,
            side_t,
            bulkhead_area,
            density,
        ))

        # Inner bottom (double bottom)
        if lwl > 15:  # Only for larger vessels
            inner_bottom_area = lwl * beam * 0.6
            result.items.append(self._create_plate_item(
                "Inner Bottom Plating",
                material,
                bottom_t * 0.8,
                inner_bottom_area,
                density,
            ))

        # === PROFILE ITEMS ===

        frame_spacing_m = frame_spacing_mm / 1000.0

        # Longitudinal stiffeners
        num_longitudinals = int(beam / 0.3) * 2  # Both sides
        longitudinal_length = lwl * num_longitudinals
        result.items.append(self._create_profile_item(
            f"Longitudinal Stiffeners ({num_longitudinals})",
            material,
            longitudinal_length,
            3.5,  # kg/m typical for flat bar/angle
        ))

        # Transverse frames
        num_frames = int(lwl / frame_spacing_m) if frame_spacing_m > 0 else 20
        frame_length = (beam + 2 * depth) * num_frames
        result.items.append(self._create_profile_item(
            f"Transverse Frames ({num_frames})",
            material,
            frame_length,
            5.0,  # kg/m for frames
        ))

        # Deck beams
        deck_beam_length = beam * num_frames * 0.5
        result.items.append(self._create_profile_item(
            "Deck Beams",
            material,
            deck_beam_length,
            4.0,  # kg/m
        ))

        # Keel and girders
        keel_length = lwl * 3  # Keel + 2 girders
        result.items.append(self._create_profile_item(
            "Keel and Girders",
            material,
            keel_length,
            8.0,  # kg/m heavier section
        ))

        # Deck longitudinals
        deck_long_length = lwl * int(beam / 0.5)
        result.items.append(self._create_profile_item(
            "Deck Longitudinals",
            material,
            deck_long_length,
            3.0,  # kg/m
        ))

        # === TOTALS ===

        for item in result.items:
            if item.category == MaterialCategory.PLATE:
                result.plate_area_m2 += item.area_m2 or 0
                result.plate_weight_kg += item.weight_kg or 0
            elif item.category == MaterialCategory.PROFILE:
                result.profile_length_m += item.length_m or 0
                result.profile_weight_kg += item.weight_kg or 0

        # Apply scrap factor
        result.total_weight_kg = (
            result.plate_weight_kg + result.profile_weight_kg
        ) * self.scrap_factor

        return result

    def _create_plate_item(
        self,
        description: str,
        material: str,
        thickness_mm: float,
        area_m2: float,
        density_kg_m3: float,
    ) -> MaterialItem:
        """Create a plate material item."""
        self._item_counter += 1
        weight_kg = area_m2 * (thickness_mm / 1000.0) * density_kg_m3
        return MaterialItem(
            item_id=f"PLT-{self._item_counter:04d}",
            category=MaterialCategory.PLATE,
            material_type=material,
            description=description,
            thickness_mm=thickness_mm,
            area_m2=round(area_m2, 2),
            weight_kg=round(weight_kg, 1),
            unit="m2",
            quantity=area_m2,
        )

    def _create_profile_item(
        self,
        description: str,
        material: str,
        length_m: float,
        weight_per_m: float,
    ) -> MaterialItem:
        """Create a profile material item."""
        self._item_counter += 1
        return MaterialItem(
            item_id=f"PRF-{self._item_counter:04d}",
            category=MaterialCategory.PROFILE,
            material_type=material,
            description=description,
            length_m=round(length_m, 1),
            weight_kg=round(length_m * weight_per_m, 1),
            unit="m",
            quantity=length_m,
        )
