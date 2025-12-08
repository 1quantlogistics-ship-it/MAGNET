"""
structural/nesting.py - Plate nesting engine.

ALPHA OWNS THIS FILE.

Section 22: Plate Nesting.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Optional

from .plates import Plate


@dataclass
class NestSheet:
    """A single stock sheet with nested plates."""

    sheet_id: str = ""
    """Unique sheet identifier."""

    thickness_mm: float = 6.0
    """Sheet thickness (mm)."""

    length_mm: float = 6000.0
    """Sheet length (mm)."""

    width_mm: float = 2000.0
    """Sheet width (mm)."""

    plates: List[str] = field(default_factory=list)
    """List of plate IDs nested on this sheet."""

    plate_positions: List[Tuple[float, float, float, float]] = field(default_factory=list)
    """Plate positions: (x, y, length, width) in mm."""

    utilization_percent: float = 0.0
    """Sheet utilization percentage."""

    scrap_area_mm2: float = 0.0
    """Remaining scrap area (mm^2)."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sheet_id": self.sheet_id,
            "thickness_mm": self.thickness_mm,
            "length_mm": self.length_mm,
            "width_mm": self.width_mm,
            "plates": self.plates,
            "utilization_percent": round(self.utilization_percent, 1),
            "scrap_area_mm2": round(self.scrap_area_mm2, 0),
        }


@dataclass
class NestingResult:
    """Complete nesting results."""

    sheets: List[NestSheet] = field(default_factory=list)
    """All nested sheets."""

    total_sheets: int = 0
    """Total number of sheets required."""

    total_plate_area_mm2: float = 0.0
    """Total plate area nested."""

    total_sheet_area_mm2: float = 0.0
    """Total sheet area used."""

    average_utilization_percent: float = 0.0
    """Average utilization across all sheets."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sheets": [s.to_dict() for s in self.sheets],
            "total_sheets": self.total_sheets,
            "total_plate_area_mm2": round(self.total_plate_area_mm2, 0),
            "total_sheet_area_mm2": round(self.total_sheet_area_mm2, 0),
            "average_utilization_percent": round(self.average_utilization_percent, 1),
        }


class NestingEngine:
    """
    Simple first-fit decreasing nesting engine.

    Phase 2 will add advanced algorithms (GA/SA).
    """

    # Stock sheet sizes (mm)
    STOCK_SHEETS: Dict[float, List[Tuple[int, int]]] = {
        4.0: [(6000, 2000), (4000, 2000)],
        5.0: [(6000, 2000), (4000, 2000)],
        6.0: [(6000, 2000), (4000, 2000)],
        8.0: [(6000, 2000), (4000, 2000)],
        10.0: [(6000, 1500), (3000, 1500)],
    }

    # Kerf width (mm) - cutting allowance
    KERF_MM = 3.0

    # Edge margin (mm)
    EDGE_MARGIN_MM = 25.0

    def __init__(self):
        self.sheets: List[NestSheet] = []

    def nest_plates(self, plates: List[Plate]) -> List[NestSheet]:
        """
        Nest plates onto stock sheets using first-fit decreasing.

        Groups plates by thickness, then nests each group.
        """
        self.sheets = []

        # Group by thickness
        by_thickness: Dict[float, List[Plate]] = {}
        for plate in plates:
            t = plate.thickness_mm
            if t not in by_thickness:
                by_thickness[t] = []
            by_thickness[t].append(plate)

        # Nest each thickness group
        for thickness, thickness_plates in by_thickness.items():
            self._nest_thickness_group(thickness, thickness_plates)

        return self.sheets

    def _nest_thickness_group(self, thickness: float, plates: List[Plate]) -> None:
        """Nest plates of same thickness."""
        # Get available stock for this thickness
        stock_options = self.STOCK_SHEETS.get(thickness, [(6000, 2000)])
        primary_stock = stock_options[0]

        # Sort plates by area (decreasing) - first-fit decreasing
        sorted_plates = sorted(
            plates,
            key=lambda p: p.extent.area_m2,
            reverse=True
        )

        # Active sheets for this thickness
        active_sheets: List[Tuple[NestSheet, List[Tuple[float, float, float, float]]]] = []

        for plate in sorted_plates:
            # Convert plate dimensions to mm
            plate_length = plate.extent.length_m * 1000 + self.KERF_MM
            plate_width = plate.extent.width_m * 1000 + self.KERF_MM

            # Try to fit in existing sheet
            placed = False
            for sheet, free_rects in active_sheets:
                pos = self._find_position(free_rects, plate_length, plate_width)
                if pos:
                    x, y = pos
                    sheet.plates.append(plate.plate_id)
                    sheet.plate_positions.append((x, y, plate_length, plate_width))
                    self._update_free_rects(free_rects, x, y, plate_length, plate_width)
                    placed = True
                    break

            # If not placed, create new sheet
            if not placed:
                sheet = NestSheet(
                    sheet_id=f"SHEET-{len(self.sheets) + len(active_sheets) + 1:03d}",
                    thickness_mm=thickness,
                    length_mm=float(primary_stock[0]),
                    width_mm=float(primary_stock[1]),
                )

                # Initial free rectangle (whole sheet minus margins)
                usable_length = primary_stock[0] - 2 * self.EDGE_MARGIN_MM
                usable_width = primary_stock[1] - 2 * self.EDGE_MARGIN_MM
                free_rects: List[Tuple[float, float, float, float]] = [
                    (self.EDGE_MARGIN_MM, self.EDGE_MARGIN_MM, usable_length, usable_width)
                ]

                # Place plate at origin
                pos = self._find_position(free_rects, plate_length, plate_width)
                if pos:
                    x, y = pos
                    sheet.plates.append(plate.plate_id)
                    sheet.plate_positions.append((x, y, plate_length, plate_width))
                    self._update_free_rects(free_rects, x, y, plate_length, plate_width)

                active_sheets.append((sheet, free_rects))

        # Calculate utilization and add to results
        for sheet, _ in active_sheets:
            self._calculate_utilization(sheet)
            self.sheets.append(sheet)

    def _find_position(
        self,
        free_rects: List[Tuple[float, float, float, float]],
        length: float,
        width: float,
    ) -> Optional[Tuple[float, float]]:
        """Find position for plate in free rectangles."""
        for rx, ry, rlen, rwid in free_rects:
            # Try normal orientation
            if length <= rlen and width <= rwid:
                return (rx, ry)
            # Try rotated
            if width <= rlen and length <= rwid:
                return (rx, ry)
        return None

    def _update_free_rects(
        self,
        free_rects: List[Tuple[float, float, float, float]],
        x: float, y: float,
        length: float, width: float,
    ) -> None:
        """Update free rectangles after placing plate (guillotine cut)."""
        new_rects: List[Tuple[float, float, float, float]] = []

        for rx, ry, rlen, rwid in free_rects:
            if rx == x and ry == y:
                # This is the rectangle we placed in
                # Split into right and top remainders

                # Right remainder
                if rlen > length:
                    new_rects.append((rx + length, ry, rlen - length, rwid))

                # Top remainder
                if rwid > width:
                    new_rects.append((rx, ry + width, length, rwid - width))
            else:
                new_rects.append((rx, ry, rlen, rwid))

        free_rects.clear()
        free_rects.extend(new_rects)

    def _calculate_utilization(self, sheet: NestSheet) -> None:
        """Calculate sheet utilization percentage."""
        sheet_area = sheet.length_mm * sheet.width_mm

        used_area = sum(
            pos[2] * pos[3] for pos in sheet.plate_positions
        )

        sheet.utilization_percent = (used_area / sheet_area) * 100
        sheet.scrap_area_mm2 = sheet_area - used_area

    def calculate_material_summary(self, sheets: List[NestSheet]) -> Dict[str, Any]:
        """Calculate material summary."""
        total_sheets = len(sheets)
        total_plate_area = sum(
            sum(pos[2] * pos[3] for pos in s.plate_positions)
            for s in sheets
        )
        total_sheet_area = sum(s.length_mm * s.width_mm for s in sheets)

        avg_util = sum(s.utilization_percent for s in sheets) / total_sheets if total_sheets > 0 else 0

        # Weight estimate
        weight_by_thickness: Dict[float, float] = {}
        for sheet in sheets:
            t = sheet.thickness_mm
            area_m2 = sum(pos[2] * pos[3] for pos in sheet.plate_positions) / 1e6
            weight = area_m2 * (t / 1000) * 2700  # kg
            weight_by_thickness[t] = weight_by_thickness.get(t, 0) + weight

        return {
            "total_sheets": total_sheets,
            "total_plate_area_m2": total_plate_area / 1e6,
            "total_sheet_area_m2": total_sheet_area / 1e6,
            "average_utilization_percent": round(avg_util, 1),
            "weight_by_thickness_kg": {k: round(v, 1) for k, v in weight_by_thickness.items()},
        }

    def get_nesting_result(self) -> NestingResult:
        """Get complete nesting result."""
        total_plate_area = sum(
            sum(pos[2] * pos[3] for pos in s.plate_positions)
            for s in self.sheets
        )
        total_sheet_area = sum(s.length_mm * s.width_mm for s in self.sheets)
        avg_util = (
            sum(s.utilization_percent for s in self.sheets) / len(self.sheets)
            if self.sheets else 0
        )

        return NestingResult(
            sheets=self.sheets,
            total_sheets=len(self.sheets),
            total_plate_area_mm2=total_plate_area,
            total_sheet_area_mm2=total_sheet_area,
            average_utilization_percent=avg_util,
        )
