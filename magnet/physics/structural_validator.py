"""
magnet/physics/structural_validator.py

T7.3: Structural validation (lightweight).

This is a *physics-layer* check that surfaces structural issues without
introducing any hull-form enums. It reuses existing structural tooling:
- `magnet.structural.feasibility` (advisory proportions checks)
- `magnet.structural.scantlings` (DNV-GL HSLC-style plate thickness formulas)

NOTE:
This module intentionally does NOT gate novelty by default; it returns
structured warnings and recommended thicknesses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from magnet.structural.feasibility import assess_structural_feasibility
from magnet.structural.scantlings import ScantlingCalculator
from magnet.structural.enums import StructuralZone


@dataclass(frozen=True)
class StructuralValidationResult:
    passed: bool
    warnings: List[str] = field(default_factory=list)
    recommended_bottom_plating_mm: Optional[float] = None


def validate_structure(state_manager, *, span_mm: float = 500.0) -> StructuralValidationResult:
    """
    Run a minimal structural check.

    - Proportion-based feasibility warnings (never blocks)
    - Representative bottom scantling recommendation at midship baseline
    """
    loa = float(state_manager.get("hull.loa") or 0.0)
    lwl = float(state_manager.get("hull.lwl") or 0.0)
    beam = float(state_manager.get("hull.beam") or 0.0)
    draft = float(state_manager.get("hull.draft") or 0.0)
    depth = float(state_manager.get("hull.depth") or 0.0)

    body_count = state_manager.get("hull.body_count") or state_manager.get("hull.num_hulls") or 1
    try:
        body_count = int(body_count)
    except Exception:
        body_count = 1
    body_count = max(1, int(body_count))

    hull_spacing = state_manager.get("hull.hull_spacing_m")
    try:
        hull_spacing = float(hull_spacing) if hull_spacing is not None else None
    except Exception:
        hull_spacing = None

    warnings: List[str] = []

    if loa > 0 and beam > 0 and draft > 0:
        assess = assess_structural_feasibility(
            loa=float(loa),
            beam=float(beam),
            draft=float(draft),
            depth=float(depth) if depth > 0 else None,
            body_count=body_count,
            hull_spacing=hull_spacing,
        )
        for w in assess.warnings:
            warnings.append(str(w.message))

    # Scantlings (requires some hull fields; displacement is best-effort)
    recommended = None
    try:
        calc = ScantlingCalculator(state_manager)
        p = calc.calculate_design_pressure(
            StructuralZone.BOTTOM,
            x_position=0.5 * float(calc.lwl),
            z_position=0.0,
        )
        recommended = float(
            calc.calculate_plate_thickness(
                StructuralZone.BOTTOM,
                span_mm=float(span_mm),
                pressure_kpa=float(p.combined_pressure_kpa),
                aspect_ratio=2.0,
            )
        )
    except Exception:
        recommended = None

    # Never hard-fail here; surface warnings and recommendation.
    return StructuralValidationResult(
        passed=True,
        warnings=warnings,
        recommended_bottom_plating_mm=recommended,
    )

