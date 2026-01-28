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


# =============================================================================
# GEOMETRY-BASED GM CALCULATION
# =============================================================================

def compute_gm_from_geometry(
    geometry: Any,
    draft: float,
    vcg: float,
    free_surface_correction: float = 0.0,
) -> Dict[str, Any]:
    """
    Compute GM from compiled HullGeometry.
    
    This is the bridge between the design language compiler output
    and the stability calculations. Novel forms work without new code.
    
    For multi-body vessels, delegates to multi_body_hydrostatics.
    For single hulls, computes KB and BM from geometry.
    
    Args:
        geometry: HullGeometry from compiler
        draft: Design draft in meters
        vcg: Vertical center of gravity in meters
        free_surface_correction: Free surface correction in meters
    
    Returns:
        Dict with:
            - gm_m: Metacentric height
            - kb_m: Height of center of buoyancy
            - bm_m: Metacentric radius
            - kg_m: Center of gravity (same as vcg input)
            - passes: True if GM >= GM_MIN
            - method: Calculation method used
    """
    # Check for multi-body
    bodies = getattr(geometry, 'bodies', None)
    if bodies and len(bodies) > 1:
        # Delegate to multi-body module
        try:
            from magnet.physics.multi_body_hydrostatics import compute_multi_body_gm
            return compute_multi_body_gm(bodies, geometry, draft, vcg)
        except ImportError:
            logger.warning("Multi-body hydrostatics not available, using single-hull method")
    
    # Single hull calculation
    kb = _compute_kb_from_geometry(geometry, draft)
    bm = _compute_bm_from_geometry(geometry, draft)
    
    # GM = KB + BM - KG - FSC
    km = kb + bm
    gm_solid = km - vcg
    gm = gm_solid - free_surface_correction
    
    # Check compliance
    passes = gm >= GM_MIN
    
    return {
        "gm_m": gm,
        "gm_solid_m": gm_solid,
        "km_m": km,
        "kb_m": kb,
        "bm_m": bm,
        "kg_m": vcg,
        "free_surface_correction_m": free_surface_correction,
        "passes": passes,
        "gm_margin_m": gm - GM_MIN,
        "method": "geometry_derived",
        "displacement_m3": abs(geometry.volume) if hasattr(geometry, 'volume') else 0,
    }


def _compute_kb_from_geometry(geometry: Any, draft: float) -> float:
    """
    Compute KB (center of buoyancy height) from geometry.
    
    Uses VCB if available, otherwise approximates from draft.
    """
    # Try to get VCB from geometry
    if hasattr(geometry, 'vcb') and geometry.vcb is not None:
        return abs(geometry.vcb)
    
    # Approximate: KB ≈ 0.53 * T for typical hull forms
    # This is geometry-based, not form-type based
    return draft * 0.53


def _compute_bm_from_geometry(geometry: Any, draft: float) -> float:
    """
    Compute BM (metacentric radius) from geometry.
    
    BM = I_waterplane / V_displaced
    
    Computes waterplane inertia from actual section geometry.
    """
    volume = abs(geometry.volume) if hasattr(geometry, 'volume') else 0
    
    if volume <= 0:
        return 0.0
    
    # Compute waterplane moment of inertia from sections
    if hasattr(geometry, 'sections') and geometry.sections:
        i_wp = _compute_waterplane_inertia(geometry.sections)
    else:
        # Fallback: estimate from beam
        beam = _estimate_beam_from_geometry(geometry)
        loa = _estimate_loa_from_geometry(geometry)
        # For rectangular waterplane: I = (L * B³) / 12
        i_wp = (loa * (beam ** 3)) / 12
    
    return i_wp / volume


def _compute_waterplane_inertia(sections: List[Any]) -> float:
    """
    Compute waterplane moment of inertia from section geometry.
    
    Integrates half-beam cubed along length using trapezoidal rule.
    """
    if len(sections) < 2:
        return 0.0
    
    # Sort sections by x position
    sorted_sections = sorted(sections, key=lambda s: s.x_position)
    
    i_wp = 0.0
    for i in range(len(sorted_sections) - 1):
        s1 = sorted_sections[i]
        s2 = sorted_sections[i + 1]
        
        dx = abs(s2.x_position - s1.x_position)
        if dx <= 0:
            continue
        
        # Get half-beam at waterline (y at z ≈ 0)
        b1 = _section_half_beam_at_waterline(s1)
        b2 = _section_half_beam_at_waterline(s2)
        
        # Transverse moment of inertia for strip
        # I = (2/3) * y³ * dx  (for symmetric section)
        i_strip = (2/3) * ((b1 ** 3 + b2 ** 3) / 2) * dx
        i_wp += i_strip
    
    return i_wp


def _section_half_beam_at_waterline(section: Any) -> float:
    """Get half-beam at waterline from section geometry."""
    if hasattr(section, 'half_beam') and section.half_beam:
        return section.half_beam
    
    if not hasattr(section, 'points') or not section.points:
        return 0.0
    
    # Find max Y at or near waterline (z ≈ 0)
    max_y = 0.0
    for pt in section.points:
        z = pt.position.z if hasattr(pt, 'position') else pt[1]
        y = pt.position.y if hasattr(pt, 'position') else pt[0]
        
        if abs(z) < 0.2:  # Near waterline
            max_y = max(max_y, abs(y))
    
    # If no points near waterline, use max Y
    if max_y == 0:
        for pt in section.points:
            y = pt.position.y if hasattr(pt, 'position') else pt[0]
            max_y = max(max_y, abs(y))
    
    return max_y


def _estimate_beam_from_geometry(geometry: Any) -> float:
    """Estimate overall beam from geometry."""
    if hasattr(geometry, 'beam') and geometry.beam:
        return geometry.beam
    
    if hasattr(geometry, 'sections') and geometry.sections:
        max_beam = 0.0
        for section in geometry.sections:
            half_beam = _section_half_beam_at_waterline(section)
            max_beam = max(max_beam, half_beam * 2)
        return max_beam if max_beam > 0 else 4.0
    
    return 4.0  # Default assumption


def _estimate_loa_from_geometry(geometry: Any) -> float:
    """Estimate LOA from geometry."""
    if hasattr(geometry, 'loa') and geometry.loa:
        return geometry.loa
    
    if hasattr(geometry, 'sections') and geometry.sections:
        x_positions = [s.x_position for s in geometry.sections]
        if x_positions:
            return max(x_positions) - min(x_positions)
    
    return 25.0  # Default assumption
