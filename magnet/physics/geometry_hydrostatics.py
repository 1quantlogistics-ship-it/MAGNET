"""
magnet/physics/geometry_hydrostatics.py - Geometry-Based Hydrostatics

Computes hydrostatic properties directly from HullGeometry WITHOUT hull_type dispatch.

This fixes Issue 2.1: Downstream physics modules reading hull_type and returning
wrong values for novel geometry.

CRITICAL PRINCIPLE:
- body_count is a geometric fact, NOT a design classification
- body_count=2 could be: catamaran, proa, SWATH demihulls, or something unnamed
- We compute physics from geometry, not from what it's "called"

Reference: MAGNET_Critical_Corrections.md Part II Issue 2.1
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any, Literal

from magnet.hull_gen.geometry import HullGeometry, HullSection, SectionPoint

from magnet.physics.polygon_ops import (
    clip_polygon_z_le,
    polygon_area_centroid,
)


__all__ = [
    'HydrostaticsResult',
    'compute_hydrostatics_from_geometry',
    'GeometryHydrostaticsCalculator',  # For backward compatibility
]


# =============================================================================
# Calculator Stub (for backward compatibility with validators.py)
# =============================================================================

class GeometryHydrostaticsCalculator:
    """
    Stub for backward compatibility.
    
    TODO: This will be properly implemented when wiring to calculator registry.
    For now, use compute_hydrostatics_from_geometry() directly.
    """
    
    def calculate(self, *args, **kwargs) -> "HydrostaticsResult":
        """
        Backwards-compatible wrapper.

        Supported call patterns:
        - calculate(geometry=<HullGeometry>, draft=<float>, vcg=<float?>, seawater_density=<float?>)
        - calculate(<HullGeometry>, <draft>, <vcg?>, <seawater_density?>)
        """
        geometry: Optional[HullGeometry] = kwargs.get("geometry") or kwargs.get("hull_geometry") or kwargs.get("hull_geom")
        draft = kwargs.get("draft")
        vcg = kwargs.get("vcg")
        seawater_density = kwargs.get("seawater_density", 1025.0)

        if geometry is None and args:
            geometry = args[0]
        if draft is None and len(args) >= 2:
            draft = args[1]
        if vcg is None and len(args) >= 3:
            vcg = args[2]
        if len(args) >= 4 and "seawater_density" not in kwargs:
            seawater_density = args[3]

        if geometry is None or draft is None:
            raise ValueError("GeometryHydrostaticsCalculator.calculate requires (geometry, draft)")

        return compute_hydrostatics_from_geometry(
            geometry=geometry,
            draft=float(draft),
            vcg=float(vcg) if vcg is not None else None,
            seawater_density=float(seawater_density),
        )


# =============================================================================
# Result Dataclass
# =============================================================================

@dataclass
class HydrostaticsResult:
    """Hydrostatic properties computed from geometry."""
    
    # Buoyancy (required fields)
    displacement_m3: float  # Volume of displaced water
    displacement_kg: float  # Mass (assuming seawater density)
    lcb_m: float  # Longitudinal center of buoyancy from AP
    vcb_m: float  # Vertical center of buoyancy from baseline
    tcb_m: float  # Transverse center of buoyancy from centerline
    
    # Stability (required fields)
    kb_m: float  # Keel to center of buoyancy
    bm_transverse_m: float  # Metacentric radius (transverse)
    bm_longitudinal_m: float  # Metacentric radius (longitudinal)
    
    # Waterplane (required fields)
    waterplane_area_m2: float
    waterplane_inertia_transverse_m4: float  # Second moment about longitudinal axis
    waterplane_inertia_longitudinal_m4: float  # Second moment about transverse axis
    
    # Wetted surface (required field)
    wetted_surface_m2: float
    
    # Method info (required fields)
    method: str  # "single_body" | "multi_body_parallel_axis"
    body_count: int  # Number of hull bodies
    
    # Optional fields (must come after required)
    gm_transverse_m: Optional[float] = None  # Metacentric height (if VCG provided)
    gm_longitudinal_m: Optional[float] = None
    stable: bool = True  # TASK-023: False if GM is negative
    confidence: str = "high"  # "high" | "medium" | "low"
    warnings: List[str] = None  # Any computation warnings
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        
        # TASK-023: Check stability and add warnings
        if self.gm_transverse_m is not None:
            if self.gm_transverse_m < 0:
                self.stable = False
                self.warnings.append(
                    f"Hull is unstable (GM={self.gm_transverse_m:.2f}m). "
                    "Increase beam or reduce VCG."
                )
            elif self.gm_transverse_m < 0.5:
                self.warnings.append(
                    f"Hull has low stability (GM={self.gm_transverse_m:.2f}m). "
                    "Minimum recommended: 0.5m."
                )


# =============================================================================
# Main Entry Point
# =============================================================================

def compute_hydrostatics_from_geometry(
    geometry: HullGeometry,
    draft: float,
    vcg: Optional[float] = None,
    seawater_density: float = 1025.0,  # kg/m³
) -> HydrostaticsResult:
    """
    Compute hydrostatics directly from geometry.
    
    This is the PRIMARY hydrostatics calculator that DOES NOT depend on hull_type.
    
    Args:
        geometry: Hull geometry (single or multi-body)
        draft: Design waterline draft (m)
        vcg: Vertical center of gravity (m) - if provided, computes GM
        seawater_density: Water density (kg/m³)
    
    Returns:
        HydrostaticsResult with all properties
    
    Raises:
        ValueError: If geometry is invalid or incomplete
    """
    if not geometry.sections:
        raise ValueError("Geometry has no sections — cannot compute hydrostatics")

    # Phase 2: deterministic geometry↔physics coupling (Engineering Truth)
    # panelized => trapezoidal integration (piecewise-linear stations)
    # smooth    => Simpson (when eligible) with trapezoid fallback for irregular spacing
    surface_definition = None
    try:
        surface_definition = (getattr(geometry, "metadata", {}) or {}).get("surface_definition")
    except Exception:
        surface_definition = None
    integration_rule: Literal["auto", "trapezoid", "simpson"] = "simpson"
    if surface_definition == "panelized":
        integration_rule = "trapezoid"
    
    # Determine body count from geometry
    # NOTE: body_count is a GEOMETRIC FACT, not a design classification.
    # body_count=2 could be catamaran, proa, SWATH, or something novel.
    # We compute physics from geometry, not from what it's "called".
    body_ids = sorted(list(set(getattr(s, 'body_id', 'main') for s in geometry.sections)))
    body_count = len(body_ids) if body_ids else 1
    
    if body_count > 1:
        # Multi-body: Use parallel axis theorem
        return _compute_multi_body_hydrostatics(
            geometry, draft, vcg, seawater_density, body_count, integration_rule=integration_rule
        )
    else:
        # Single body: Standard integration.
        # NOTE: single-body geometry may still have a non-"main" body_id (e.g., demihull-only export).
        only_body = body_ids[0] if body_ids else "main"
        return _compute_single_body_hydrostatics(
            geometry, draft, vcg, seawater_density, body_id=str(only_body), integration_rule=integration_rule
        )


# =============================================================================
# Body Detection
# =============================================================================

def _count_bodies_in_geometry(geometry: HullGeometry) -> int:
    """
    Count distinct hull bodies in geometry.
    
    body_count is a GEOMETRIC FACT detected from body_id attributes on sections.
    """
    body_ids = set()
    for s in geometry.sections:
        # Default to 'main' if no body_id specified
        body_id = getattr(s, 'body_id', 'main')
        body_ids.add(body_id)
    
    return len(body_ids) if body_ids else 1


def _get_sections_for_body(geometry: HullGeometry, body_id: str) -> List[HullSection]:
    """Extract sections belonging to a specific body."""
    return [s for s in geometry.sections if getattr(s, 'body_id', 'main') == body_id]


# =============================================================================
# Single Body Hydrostatics
# =============================================================================

def _compute_single_body_hydrostatics(
    geometry: HullGeometry,
    draft: float,
    vcg: Optional[float],
    seawater_density: float,
    body_id: str = "main",
    sections: Optional[List[HullSection]] = None,
    integration_rule: Literal["auto", "trapezoid", "simpson"] = "simpson",
) -> HydrostaticsResult:
    """
    Compute hydrostatics for a single hull body using numerical integration.
    
    This works for ANY single-body geometry — conventional or novel.
    """
    if sections is None:
        sections = _get_sections_for_body(geometry, body_id)

    if not sections:
        return _empty_hydrostatics_result(body_id)

    # Ensure deterministic integration order
    sections = sorted(list(sections), key=lambda s: float(getattr(s, "x_position", 0.0) or 0.0))

    # Integrate volume and moments from sections
    displacement_m3, lcb_m, vcb_m, tcb_m = _integrate_displacement_and_centers(
        sections, draft, integration_rule=integration_rule
    )
    
    # Compute waterplane properties
    waterplane_area_m2, Ix_waterplane, Iy_waterplane = _integrate_waterplane_properties(
        sections, draft, integration_rule=integration_rule
    )
    
    # Compute wetted surface
    wetted_surface_m2 = _integrate_wetted_surface(sections, draft)
    
    # Metacentric radii
    bm_transverse = Ix_waterplane / displacement_m3 if displacement_m3 > 0 else 0.0
    bm_longitudinal = Iy_waterplane / displacement_m3 if displacement_m3 > 0 else 0.0
    
    # KB (keel to center of buoyancy)
    kb = vcb_m
    
    # GM (if VCG provided)
    gm_transverse = None
    gm_longitudinal = None
    if vcg is not None:
        gm_transverse = kb + bm_transverse - vcg
        gm_longitudinal = kb + bm_longitudinal - vcg

    result = HydrostaticsResult(
        displacement_m3=displacement_m3,
        displacement_kg=displacement_m3 * seawater_density,
        lcb_m=lcb_m,
        vcb_m=vcb_m,
        tcb_m=tcb_m,
        kb_m=kb,
        bm_transverse_m=bm_transverse,
        bm_longitudinal_m=bm_longitudinal,
        gm_transverse_m=gm_transverse,
        gm_longitudinal_m=gm_longitudinal,
        waterplane_area_m2=waterplane_area_m2,
        waterplane_inertia_transverse_m4=Ix_waterplane,
        waterplane_inertia_longitudinal_m4=Iy_waterplane,
        wetted_surface_m2=wetted_surface_m2,
        method="single_body",
        body_count=1,
        confidence="high",
    )

    # -------------------------------------------------------------------------
    # Truthfulness: station spacing risk warning (numerical integration honesty)
    # If station spacing variation RMS is high, trapezoid (and even simpson fallbacks)
    # can silently bias volume/moments.
    # -------------------------------------------------------------------------
    try:
        xs = [float(getattr(s, "x_position", 0.0) or 0.0) for s in sections]
        dxs = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
        dxs = [d for d in dxs if d > 0]
        if len(dxs) >= 2:
            mean_dx = sum(dxs) / len(dxs)
            if mean_dx > 0:
                import math as _math
                rms = _math.sqrt(sum(((d / mean_dx) - 1.0) ** 2 for d in dxs) / len(dxs))
                if rms > 0.2:
                    result.warnings.append(
                        f"IntegrationRiskWarning: station_spacing_variation_rms={rms:.3f} > 0.200. "
                        "Non-uniform station spacing can bias trapezoidal/strip integrations."
                    )
                    result.confidence = "medium"
    except Exception:
        pass

    # Phase 3B: primitive volume semantics (opt-in, explicit-only)
    _apply_primitive_volume_corrections(geometry, draft, seawater_density, result, body_id=body_id)

    return result


def _empty_hydrostatics_result(body_id: str) -> HydrostaticsResult:
    """Return empty result for a body with no sections."""
    return HydrostaticsResult(
        displacement_m3=0.0,
        displacement_kg=0.0,
        lcb_m=0.0,
        vcb_m=0.0,
        tcb_m=0.0,
        kb_m=0.0,
        bm_transverse_m=0.0,
        bm_longitudinal_m=0.0,
        waterplane_area_m2=0.0,
        waterplane_inertia_transverse_m4=0.0,
        waterplane_inertia_longitudinal_m4=0.0,
        wetted_surface_m2=0.0,
        method="none",
        body_count=0,
        confidence="low",
        warnings=[f"Body '{body_id}' has no sections."]
    )


# =============================================================================
# Multi-Body Hydrostatics (Parallel Axis Theorem)
# =============================================================================

def _compute_multi_body_hydrostatics(
    geometry: HullGeometry,
    draft: float,
    vcg: Optional[float],
    seawater_density: float,
    body_count: int,
    integration_rule: Literal["auto", "trapezoid", "simpson"] = "simpson",
) -> HydrostaticsResult:
    """
    Compute hydrostatics for multi-body vessel using parallel axis theorem.
    
    The parallel axis theorem works for ANY multi-body configuration:
    I_total = Σ (I_local + A_wp × d²)
    
    Reference: MAGNET_Critical_Corrections.md Part XIII Q5
    """
    body_ids = sorted(list(set(getattr(s, 'body_id', 'main') for s in geometry.sections)))
    
    # 1. Compute individual body hydrostatics
    body_results: Dict[str, HydrostaticsResult] = {}
    for bid in body_ids:
        body_results[bid] = _compute_single_body_hydrostatics(
            geometry, draft, None, seawater_density, body_id=bid, integration_rule=integration_rule
        )
    
    # 2. Combine displacement
    total_displacement_m3 = sum(r.displacement_m3 for r in body_results.values())
    
    if total_displacement_m3 <= 0:
        return _empty_hydrostatics_result("combined")
        
    # 3. Combine Centers of Buoyancy (weighted average)
    total_lcb = sum(r.lcb_m * r.displacement_m3 for r in body_results.values()) / total_displacement_m3
    total_vcb = sum(r.vcb_m * r.displacement_m3 for r in body_results.values()) / total_displacement_m3
    total_tcb = sum(r.tcb_m * r.displacement_m3 for r in body_results.values()) / total_displacement_m3
    
    # 4. Combine Waterplane Properties (Parallel Axis Theorem)
    total_wp_area = sum(r.waterplane_area_m2 for r in body_results.values())
    
    # Transverse Inertia (Roll): I_total = Σ (Ix_local + A_wp * dy²)
    # where dy is offset from combined transverse center of flotation (TCF)
    # For now assume TCF ≈ total_tcb for simplicity (often true for symmetric hulls)
    total_ix_wp = 0.0
    total_iy_wp = 0.0
    
    for r in body_results.values():
        dy = r.tcb_m - total_tcb
        dx = r.lcb_m - total_lcb
        
        total_ix_wp += r.waterplane_inertia_transverse_m4 + r.waterplane_area_m2 * (dy ** 2)
        total_iy_wp += r.waterplane_inertia_longitudinal_m4 + r.waterplane_area_m2 * (dx ** 2)
        
    # 5. Combined Metacentric Radii
    bm_transverse = total_ix_wp / total_displacement_m3
    bm_longitudinal = total_iy_wp / total_displacement_m3
    
    # 6. Combined GM
    gm_transverse = None
    gm_longitudinal = None
    if vcg is not None:
        gm_transverse = total_vcb + bm_transverse - vcg
        gm_longitudinal = total_vcb + bm_longitudinal - vcg
        
    result = HydrostaticsResult(
        displacement_m3=total_displacement_m3,
        displacement_kg=total_displacement_m3 * seawater_density,
        lcb_m=total_lcb,
        vcb_m=total_vcb,
        tcb_m=total_tcb,
        kb_m=total_vcb,
        bm_transverse_m=bm_transverse,
        bm_longitudinal_m=bm_longitudinal,
        gm_transverse_m=gm_transverse,
        gm_longitudinal_m=gm_longitudinal,
        waterplane_area_m2=total_wp_area,
        waterplane_inertia_transverse_m4=total_ix_wp,
        waterplane_inertia_longitudinal_m4=total_iy_wp,
        wetted_surface_m2=sum(r.wetted_surface_m2 for r in body_results.values()),
        method="multi_body_parallel_axis",
        body_count=body_count,
        confidence="high",
    )

    # Phase 3B: primitive volume semantics (opt-in, explicit-only)
    _apply_primitive_volume_corrections(geometry, draft, seawater_density, result, body_id=None)

    return result


def _apply_primitive_volume_corrections(
    geometry: HullGeometry,
    draft: float,
    seawater_density: float,
    result: HydrostaticsResult,
    body_id: Optional[str],
) -> None:
    """
    Phase 3B (staged): Apply *explicit* primitive buoyancy/void-volume corrections.

    This does NOT attempt full geometric boolean operations. It only applies corrections when the
    primitive declares an explicit volume (m^3) or declares enough parameters to compute one.

    Conventions:
    - baseline z=0, waterline at z=draft
    - positions are treated as global vessel coordinates
    """
    d = float(draft)

    # Nothing to do if no displacement
    if result.displacement_m3 <= 0:
        return

    delta_v = 0.0
    mx = 0.0
    my = 0.0
    mz = 0.0
    warnings: List[str] = []

    def _submerged_fraction(center_z: float, height_z: float) -> float:
        hz = float(height_z or 0.0)
        if hz <= 0:
            return 1.0 if center_z <= d else 0.0
        z_min = center_z - hz * 0.5
        z_max = center_z + hz * 0.5
        if z_min >= d:
            return 0.0
        if z_max <= d:
            return 1.0
        return max(0.0, min(1.0, (d - z_min) / hz))

    # --- Openings: subtract void volume (if explicitly modeled) ---
    for opening in list(getattr(geometry, "openings", []) or []):
        try:
            if body_id is not None and (opening.get("body_id") or "main") != body_id:
                continue

            pos = opening.get("position") or opening.get("center")  # tolerate aliases
            if not (isinstance(pos, list) and len(pos) >= 3):
                continue
            ox, oy, oz = float(pos[0]), float(pos[1]), float(pos[2])

            shape = str(opening.get("shape") or "rectangular").lower()
            dims = opening.get("dimensions") or []
            width = height = 0.0
            area = None
            if shape in ("circular", "circle"):
                r = float(dims[0]) if (isinstance(dims, list) and len(dims) >= 1) else 0.0
                area = 3.141592653589793 * (r ** 2) if r > 0 else None
                height = 2.0 * r
            else:
                if isinstance(dims, list) and len(dims) >= 2:
                    width = float(dims[0])
                    height = float(dims[1])
                    area = (width * height) if (width > 0 and height > 0) else None

            explicit_void = opening.get("void_volume_m3")
            if explicit_void is not None:
                void_v = float(explicit_void)
            else:
                thl = opening.get("through_hull_length_m")
                if thl is None or area is None:
                    # No explicit semantics; remain diagnostic-only.
                    continue
                void_v = float(area) * float(thl)

            if void_v <= 0:
                continue

            frac = _submerged_fraction(oz, height if height > 0 else 0.0)
            if frac <= 0:
                continue

            v = -abs(void_v) * frac
            delta_v += v
            mx += v * ox
            my += v * oy
            mz += v * oz
        except Exception:
            # best-effort; never crash hydrostatics
            continue

    # --- Attachments: add buoyant volume (if explicitly modeled) ---
    for att in list(getattr(geometry, "attachments", []) or []):
        try:
            explicit_v = att.get("buoyancy_volume_m3")
            if explicit_v is None:
                continue
            v_raw = float(explicit_v)
            if v_raw <= 0:
                continue

            center = att.get("buoyancy_center")
            if isinstance(center, list) and len(center) >= 3:
                ax, ay, az = float(center[0]), float(center[1]), float(center[2])
            else:
                ax = float(att.get("offset_x_m") or 0.0)
                ay = float(att.get("offset_y_m") or 0.0)
                az = float(att.get("offset_z_m") or 0.0)

            # If fully above WL, ignore. (No height model available; treat as point.)
            if az >= d:
                continue

            v = abs(v_raw)
            delta_v += v
            mx += v * ax
            my += v * ay
            mz += v * az
        except Exception:
            continue

    if abs(delta_v) <= 0.0:
        return

    v0 = float(result.displacement_m3)
    v1 = v0 + float(delta_v)
    if v1 <= 0:
        warnings.append("Primitive volume corrections would result in non-positive displacement; ignoring corrections.")
        result.warnings.extend(warnings)
        return

    # Recompute centers from combined moments.
    lcb0 = float(result.lcb_m)
    tcb0 = float(result.tcb_m)
    vcb0 = float(result.vcb_m)
    m0x = v0 * lcb0
    m0y = v0 * tcb0
    m0z = v0 * vcb0

    result.displacement_m3 = v1
    result.displacement_kg = v1 * float(seawater_density)
    result.lcb_m = (m0x + mx) / v1
    result.tcb_m = (m0y + my) / v1
    result.vcb_m = (m0z + mz) / v1
    result.kb_m = result.vcb_m  # KB == VCB under baseline convention

    # NOTE: BM is not recomputed here; full semantics would require waterplane inertia updates.
    # We keep BM as-is and add an explicit warning.
    result.confidence = "medium"
    warnings.append(
        "Applied Phase 3B primitive volume corrections (explicit-only). "
        "BM/waterplane inertias are not adjusted yet; treat GM as advisory when primitives are present."
    )
    result.warnings.extend(warnings)


# =============================================================================
# Numerical Integration Functions
# =============================================================================

def _integrate_displacement_and_centers(
    sections: List[HullSection],
    draft: float,
    *,
    integration_rule: Literal["auto", "trapezoid", "simpson"] = "auto",
) -> Tuple[float, float, float, float]:
    """
    Integrate displacement and centers of buoyancy.
    
    Returns:
        (volume, lcb, vcb, tcb)
    """
    if len(sections) < 2:
        return (0.0, 0.0, 0.0, 0.0)
    
    total_volume = 0.0
    volume_x_moment = 0.0
    volume_y_moment = 0.0
    volume_z_moment = 0.0
    
    # Evaluate per-section submerged area and centroid (y,z)
    xs: List[float] = []
    areas: List[float] = []
    ycs: List[float] = []
    zcs: List[float] = []

    for s in sections:
        a = _compute_section_area_below_waterline(s.points, draft)
        cy, cz = _compute_section_centroid(s.points, draft)
        xs.append(float(s.x_position))
        areas.append(float(a))
        ycs.append(float(cy))
        zcs.append(float(cz))

    # Phase 2 coupling: integration_rule selects Simpson vs trapezoid behavior.
    total_volume = _integrate_1d(xs, areas, rule=integration_rule)
    if total_volume <= 0:
        return (0.0, 0.0, 0.0, 0.0)

    x_moment = _integrate_1d(xs, [areas[i] * xs[i] for i in range(len(xs))], rule=integration_rule)
    y_moment = _integrate_1d(xs, [areas[i] * ycs[i] for i in range(len(xs))], rule=integration_rule)
    z_moment = _integrate_1d(xs, [areas[i] * zcs[i] for i in range(len(xs))], rule=integration_rule)

    volume_x_moment = x_moment
    volume_y_moment = y_moment
    volume_z_moment = z_moment
    
    if total_volume <= 0:
        return (0.0, 0.0, 0.0, 0.0)
    
    lcb = volume_x_moment / total_volume
    tcb = volume_y_moment / total_volume
    vcb = volume_z_moment / total_volume
    
    return (total_volume, lcb, vcb, tcb)


def _integrate_waterplane_properties(
    sections: List[HullSection],
    draft: float,
    *,
    integration_rule: Literal["auto", "trapezoid", "simpson"] = "auto",
) -> Tuple[float, float, float]:
    """
    Integrate waterplane area and second moments of area.
    
    Returns:
        (waterplane_area, Ix, Iy)
        where Ix = transverse inertia, Iy = longitudinal inertia
    """
    if len(sections) < 2:
        return (0.0, 0.0, 0.0)
    
    total_area = 0.0
    Ix_total = 0.0  # About longitudinal (x) axis
    Iy_total = 0.0  # About transverse (y) axis
    
    xs: List[float] = [float(s.x_position) for s in sections]
    beams: List[float] = [_compute_waterline_beam(s.points, draft) for s in sections]

    # Waterplane area = ∫ beam dx
    total_area = _integrate_1d(xs, beams, rule=integration_rule)

    # Transverse inertia about centerline (longitudinal axis): ∫ (B^3/12) dx
    Ix_total = _integrate_1d(xs, [(b ** 3) / 12.0 for b in beams], rule=integration_rule)

    # Longitudinal inertia about AP (compat with previous implementation):
    # Iy = ∫ x^2 * beam dx   (strip method, about x=0)
    Iy_total = _integrate_1d(xs, [(xs[i] ** 2) * beams[i] for i in range(len(xs))], rule=integration_rule)
    
    return (total_area, Ix_total, Iy_total)


def _integrate_wetted_surface(
    sections: List[HullSection],
    draft: float,
) -> float:
    """Integrate wetted surface area."""
    if len(sections) < 2:
        return 0.0
    
    total_surface = 0.0
    
    for i in range(len(sections) - 1):
        s1 = sections[i]
        s2 = sections[i + 1]
        
        perim1 = _compute_section_wetted_perimeter(s1.points, draft)
        perim2 = _compute_section_wetted_perimeter(s2.points, draft)
        dx = s2.x_position - s1.x_position
        total_surface += 0.5 * (perim1 + perim2) * dx
    
    return total_surface


# =============================================================================
# Section-Level Calculations
# =============================================================================

def _compute_section_area_below_waterline(
    points: List[SectionPoint],
    draft: float,
) -> float:
    """Compute full-section area below waterline at z=draft."""
    poly = _section_points_to_full_polygon_yz(points)
    if not poly:
        return 0.0
    clipped = clip_polygon_z_le(poly, z_max=draft)
    area, _, _ = polygon_area_centroid(clipped)
    return float(area)


def _compute_section_centroid(
    points: List[SectionPoint],
    draft: float,
) -> Tuple[float, float]:
    """Compute centroid (y,z) of the submerged full-section polygon."""
    poly = _section_points_to_full_polygon_yz(points)
    if not poly:
        return (0.0, 0.0)
    clipped = clip_polygon_z_le(poly, z_max=draft)
    area, cy, cz = polygon_area_centroid(clipped)
    if area <= 0:
        return (0.0, 0.0)
    return (float(cy), float(cz))


def _compute_waterline_beam(
    points: List[SectionPoint],
    draft: float,
) -> float:
    """Compute full beam at waterline z=draft from full-section polygon intersections."""
    poly = _section_points_to_full_polygon_yz(points)
    if not poly or len(poly) < 3:
        return 0.0

    # Work on open polygon for intersection scanning
    verts = poly
    # Beam must be relative to the section's OWN centerline (y=y0), not ship centerline (y=0),
    # so multi-body hulls (offset demihulls) compute correct local waterplanes.
    y0 = _infer_section_centerline_y(points)
    max_abs_dy = 0.0
    d = float(draft)
    for i in range(len(verts) - 1):
        y1, z1 = verts[i]
        y2, z2 = verts[i + 1]
        dz1 = z1 - d
        dz2 = z2 - d

        # Vertex exactly on waterline
        if abs(dz1) <= 1e-9:
            max_abs_dy = max(max_abs_dy, abs(y1 - y0))

        # Edge crosses waterline
        if dz1 == 0 and dz2 == 0:
            continue
        if dz1 * dz2 <= 0 and abs(z2 - z1) > 1e-12:
            t = (d - z1) / (z2 - z1)
            if 0.0 <= t <= 1.0:
                y = y1 + t * (y2 - y1)
                max_abs_dy = max(max_abs_dy, abs(y - y0))

    return float(2.0 * max_abs_dy)


def _compute_section_wetted_perimeter(
    points: List[SectionPoint],
    draft: float,
) -> float:
    """
    Wetted perimeter for a section curve (keel→deck on port side) at z=draft.

    Computes the submerged length of the port curve and doubles it (symmetry).
    """
    if len(points) < 2:
        return 0.0

    d = float(draft)
    perim_half = 0.0
    for i in range(len(points) - 1):
        p1 = getattr(points[i], "position", points[i])
        p2 = getattr(points[i + 1], "position", points[i + 1])
        z1 = p1.z
        z2 = p2.z
        y1 = p1.y
        y2 = p2.y

        below1 = z1 <= d
        below2 = z2 <= d

        if below1 and below2:
            dy = y2 - y1
            dz = z2 - z1
            perim_half += math.sqrt(dy * dy + dz * dz)
        elif below1 != below2:
            # Crossing: include only submerged portion up to intersection at z=d
            if abs(z2 - z1) > 1e-12:
                t = (d - z1) / (z2 - z1)
                t = max(0.0, min(1.0, t))
                yi = y1 + t * (y2 - y1)
                zi = d
                if below1:
                    dy = yi - y1
                    dz = zi - z1
                else:
                    dy = y2 - yi
                    dz = z2 - zi
                perim_half += math.sqrt(dy * dy + dz * dz)

    return float(2.0 * perim_half)


def _infer_section_centerline_y(points: List[SectionPoint]) -> float:
    """
    Infer section centerline y0.

    Matches WebGL tessellation heuristic: use the first point (keel) as the body's centerline reference.
    For monohulls this is typically 0. For offset demihulls this equals the body's offset_y_m after compilation.
    """
    try:
        if not points:
            return 0.0
        p0 = points[0]
        pos = getattr(p0, "position", p0)
        if hasattr(pos, "y"):
            return float(pos.y)
    except Exception:
        pass
    return 0.0


def _section_points_to_full_polygon_yz(points: List[SectionPoint]) -> List[Tuple[float, float]]:
    """
    Convert a section curve (typically half-section, keel→deck) into a closed full-section polygon.

    IMPORTANT (multi-body correctness):
    - Half-sections must be mirrored about the section's OWN centerline (y=y0), not always about y=0.
    - If a section already spans both sides about y0, we treat it as a full polygon and do not mirror.
    """
    if not points:
        return []

    y0 = _infer_section_centerline_y(points)

    curve: List[Tuple[float, float]] = []
    for p in points:
        pos = getattr(p, "position", p)
        # Support both SectionPoint(position=Point3D) and raw Point3D lists from older callers/tests.
        curve.append((float(pos.y), float(pos.z)))
    # Detect whether curve includes both sides around y0
    has_pos = False
    has_neg = False
    for (y, _z) in curve:
        dy = y - y0
        if dy > 1e-9:
            has_pos = True
        elif dy < -1e-9:
            has_neg = True

    if has_pos and has_neg:
        poly = curve[:]
    else:
        # Mirror about y=y0: reverse order and reflect across centerline.
        mirrored = [((2.0 * y0) - y, z) for (y, z) in reversed(curve)]

        # Avoid duplicating endpoints if they already lie on centerline
        poly = curve[:]
        if mirrored:
            if poly and mirrored and poly[-1] == mirrored[0]:
                poly.extend(mirrored[1:])
            else:
                poly.extend(mirrored)

    # Ensure closure
    if poly and poly[0] != poly[-1]:
        poly.append(poly[0])
    return poly


def _integrate_1d(
    xs: List[float],
    fs: List[float],
    *,
    rule: Literal["auto", "trapezoid", "simpson"] = "auto",
) -> float:
    """
    Deterministic 1D integration over x.
    - rule="trapezoid": force trapezoidal (piecewise-linear; matches panelized visuals)
    - rule="simpson": attempt composite Simpson where eligible; otherwise trapezoidal
    - rule="auto": legacy behavior (Simpson where eligible; otherwise trapezoidal)
    """
    n = min(len(xs), len(fs))
    if n < 2:
        return 0.0

    xs2 = xs[:n]
    fs2 = fs[:n]

    # Forced trapezoid path (panelized truthfulness)
    if rule == "trapezoid":
        pairs = list(zip(xs2, fs2))
        pairs.sort(key=lambda t: t[0])
        return sum(
            0.5 * (pairs[i][1] + pairs[i + 1][1]) * (pairs[i + 1][0] - pairs[i][0])
            for i in range(len(pairs) - 1)
            if (pairs[i + 1][0] - pairs[i][0]) > 0
        )

    # Detect approximate uniform spacing
    dxs = [xs2[i + 1] - xs2[i] for i in range(n - 1)]
    if any(dx <= 0 for dx in dxs):
        # Non-monotone or duplicates: trapezoid on sorted pairs
        pairs = sorted(zip(xs2, fs2), key=lambda t: t[0])
        return sum(0.5 * (pairs[i][1] + pairs[i + 1][1]) * (pairs[i + 1][0] - pairs[i][0]) for i in range(len(pairs) - 1))

    dx0 = dxs[0]
    uniform = all(abs(dx - dx0) <= 1e-6 * max(1.0, abs(dx0)) for dx in dxs)

    if not uniform or n < 3:
        return sum(0.5 * (fs2[i] + fs2[i + 1]) * (xs2[i + 1] - xs2[i]) for i in range(n - 1))

    # Composite Simpson requires odd n; if even, use Simpson on first n-1 then trap on last
    if n % 2 == 0:
        simpson_n = n - 1
        simpson = _integrate_1d(xs2[:simpson_n], fs2[:simpson_n], rule=rule)
        trap = 0.5 * (fs2[n - 2] + fs2[n - 1]) * (xs2[n - 1] - xs2[n - 2])
        return simpson + trap

    h = dx0
    s = fs2[0] + fs2[-1]
    s_odd = sum(fs2[i] for i in range(1, n - 1, 2))
    s_even = sum(fs2[i] for i in range(2, n - 1, 2))
    return (h / 3.0) * (s + 4.0 * s_odd + 2.0 * s_even)
