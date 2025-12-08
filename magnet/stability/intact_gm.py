"""
MAGNET Intact GM Calculator

Module 06 v1.2 - Production-Ready

Calculates metacentric height (GM) for intact stability assessment.

v1.2 Changes:
- KG sourcing priority: stability.kg_m (primary), weight.lightship_vcg_m (fallback)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import time
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# IMO minimum GM requirement (meters)
GM_MIN = 0.15


# =============================================================================
# INTACT GM RESULTS
# =============================================================================

@dataclass
class IntactGMResults:
    """
    Results from intact GM calculation.

    GM = KB + BM - KG - FSC

    Where:
    - KB = Height of center of buoyancy from keel
    - BM = Metacentric radius
    - KG = Height of center of gravity from keel
    - FSC = Free surface correction
    """
    # Metacentric height
    gm_m: float                 # GM with free surface correction
    gm_solid_m: float           # GM without free surface correction

    # Component values
    km_m: float                 # KM = KB + BM
    kb_m: float                 # Height of center of buoyancy
    bm_m: float                 # Metacentric radius
    kg_m: float                 # Height of center of gravity
    free_surface_correction_m: float

    # Compliance
    passes_criterion: bool      # GM ≥ 0.15m
    gm_margin_m: float          # GM - GM_MIN

    # Metadata
    kg_source: str = "unknown"  # Where KG came from
    calculation_time_ms: int = 0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "gm_m": round(self.gm_m, 3),
            "gm_solid_m": round(self.gm_solid_m, 3),
            "km_m": round(self.km_m, 3),
            "kb_m": round(self.kb_m, 3),
            "bm_m": round(self.bm_m, 3),
            "kg_m": round(self.kg_m, 3),
            "free_surface_correction_m": round(self.free_surface_correction_m, 4),
            "passes_criterion": self.passes_criterion,
            "gm_margin_m": round(self.gm_margin_m, 3),
            "kg_source": self.kg_source,
            "calculation_time_ms": self.calculation_time_ms,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntactGMResults":
        """Deserialize from dictionary."""
        return cls(
            gm_m=data.get("gm_m", 0.0),
            gm_solid_m=data.get("gm_solid_m", 0.0),
            km_m=data.get("km_m", 0.0),
            kb_m=data.get("kb_m", 0.0),
            bm_m=data.get("bm_m", 0.0),
            kg_m=data.get("kg_m", 0.0),
            free_surface_correction_m=data.get("free_surface_correction_m", 0.0),
            passes_criterion=data.get("passes_criterion", False),
            gm_margin_m=data.get("gm_margin_m", 0.0),
            kg_source=data.get("kg_source", "unknown"),
            calculation_time_ms=data.get("calculation_time_ms", 0),
            warnings=data.get("warnings", []),
        )


# =============================================================================
# INTACT GM CALCULATOR
# =============================================================================

class IntactGMCalculator:
    """
    Calculator for intact stability metacentric height.

    Implements the fundamental stability equation:
    GM = KB + BM - KG - FSC

    Accuracy: Exact (given accurate inputs)
    """

    def __init__(self, gm_min: float = GM_MIN):
        """
        Initialize calculator.

        Args:
            gm_min: Minimum GM for compliance (default: 0.15m per IMO)
        """
        self.gm_min = gm_min

    def calculate(
        self,
        kb_m: float,
        bm_m: float,
        kg_m: float,
        free_surface_correction_m: float = 0.0,
        kg_source: str = "input",
    ) -> IntactGMResults:
        """
        Calculate intact metacentric height.

        Args:
            kb_m: Height of center of buoyancy from keel (m)
            bm_m: Metacentric radius (m)
            kg_m: Height of center of gravity from keel (m)
            free_surface_correction_m: Free surface correction (m)
            kg_source: Source of KG value for traceability

        Returns:
            IntactGMResults with GM and compliance status

        Raises:
            ValueError: If inputs are invalid (negative values)
        """
        start_time = time.perf_counter()
        warnings: List[str] = []

        # Validate inputs
        if kb_m < 0:
            raise ValueError(f"KB must be non-negative: {kb_m}")
        if bm_m < 0:
            raise ValueError(f"BM must be non-negative: {bm_m}")
        if kg_m < 0:
            raise ValueError(f"KG must be non-negative: {kg_m}")
        if free_surface_correction_m < 0:
            raise ValueError(f"FSC must be non-negative: {free_surface_correction_m}")

        # Calculate KM
        km_m = kb_m + bm_m

        # Calculate GM (solid - without FSC)
        gm_solid_m = km_m - kg_m

        # Calculate GM (with FSC)
        gm_m = gm_solid_m - free_surface_correction_m

        # Check for stability warnings
        if gm_solid_m < 0:
            warnings.append(f"Negative solid GM: {gm_solid_m:.3f}m - vessel is initially unstable")

        if gm_m < 0:
            warnings.append(f"Negative GM (with FSC): {gm_m:.3f}m - vessel is unstable")
        elif gm_m < self.gm_min:
            warnings.append(f"GM {gm_m:.3f}m below minimum {self.gm_min}m")

        if kg_m > km_m:
            warnings.append(f"KG ({kg_m:.3f}m) exceeds KM ({km_m:.3f}m) - vessel is tender")

        if free_surface_correction_m > 0.5:
            warnings.append(f"Large free surface correction: {free_surface_correction_m:.3f}m")

        # Check compliance
        passes_criterion = gm_m >= self.gm_min
        gm_margin = gm_m - self.gm_min

        # Calculate elapsed time
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return IntactGMResults(
            gm_m=gm_m,
            gm_solid_m=gm_solid_m,
            km_m=km_m,
            kb_m=kb_m,
            bm_m=bm_m,
            kg_m=kg_m,
            free_surface_correction_m=free_surface_correction_m,
            passes_criterion=passes_criterion,
            gm_margin_m=gm_margin,
            kg_source=kg_source,
            calculation_time_ms=elapsed_ms,
            warnings=warnings,
        )

    def calculate_required_kg(
        self,
        kb_m: float,
        bm_m: float,
        free_surface_correction_m: float = 0.0,
        gm_target: Optional[float] = None,
    ) -> float:
        """
        Calculate maximum allowable KG for given GM target.

        Useful for weight estimation constraints.

        Args:
            kb_m: Height of center of buoyancy from keel (m)
            bm_m: Metacentric radius (m)
            free_surface_correction_m: Free surface correction (m)
            gm_target: Target GM (default: minimum)

        Returns:
            Maximum allowable KG (m)
        """
        if gm_target is None:
            gm_target = self.gm_min

        km_m = kb_m + bm_m
        max_kg = km_m - gm_target - free_surface_correction_m

        return max_kg
