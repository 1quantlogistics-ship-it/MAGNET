# MAGNET Physics Gaps and Solutions v1.0

> **Document Purpose:** Identifies physics/validation gaps for novel forms and proposes concrete solutions.  
> **Status:** Implementation Specification  
> **Last Updated:** 2026-01-05  
> **Version:** 1.0

---

## Executive Summary

> **Any hull form that requires a new language primitive is a failure of the language.**

> **Agent Coordination Rule:** Agents never coordinate on "features" — they coordinate on **geometry and constraints only**.

**The Problem:** MAGNET's documents claim "unchanged downstream pipeline" for physics validation, but this is false. The existing physics engines were designed for conventional monohulls. Multi-body vessels and novel forms require:

1. New multi-body hydrostatics (parallel axis theorem for BM)
2. Form coefficient derivation from arbitrary geometry
3. Resistance method selection with honest uncertainty
4. Physics-category-driven calculations

**The Solution:** This document specifies exactly what code needs to be written, with implementations. These are **physics extensions**, not new primitives. Novel forms must work without kernel changes.

---

## Table of Contents

- [Gap 1: Multi-Body Hydrostatics](#gap-1-multi-body-hydrostatics)
- [Gap 1.5: Multi-Body GZ Curve](#gap-15-multi-body-gz-curve-large-angle-stability)
- [Gap 2: Form Coefficient Derivation](#gap-2-form-coefficient-derivation)
- [Gap 3: Resistance Method Selection](#gap-3-resistance-method-selection)
- [Gap 4: Multi-Body Form Parameters](#gap-4-multi-body-form-parameters)
- [Gap 5: Physics Category Implementation](#gap-5-physics-category-implementation)
- [Gap 6: Novelty Detection](#gap-6-novelty-detection)
- [Implementation Priority](#implementation-priority)
- [Honest Physics Validation Contract](#honest-physics-validation-contract)
- [Appendix A: Required Helper Functions](#appendix-a-required-helper-functions)

---

## Gap 1: Multi-Body Hydrostatics

### The Problem

Current `stability/intact_gm.py` assumes single hull:

```python
# Current (BROKEN for multi-body):
def compute_gm(geometry: HullGeometry, draft: float, vcg: float) -> float:
    displacement = compute_displacement(geometry, draft)
    kb = compute_kb(geometry, draft)
    bm = compute_bm(geometry, draft)  # ❌ Assumes single waterplane
    return kb + bm - vcg
```

For catamaran with hull spacing S, the transverse moment of inertia is:

```
I_total = 2 × I_single + 2 × A_waterplane × (S/2)²
          ^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
          Local inertia  PARALLEL AXIS THEOREM (dominates!)
```

**Without parallel axis theorem, catamaran BM is WRONG by ~10x.**

### The Solution

```python
# magnet/physics/multi_body_hydrostatics.py

from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np

@dataclass
class BodyHydrostatics:
    """Hydrostatics for a single body."""
    body_id: str
    displacement_m3: float
    waterplane_area_m2: float
    waterplane_inertia_xx: float  # About body's own centroid
    waterplane_inertia_yy: float
    lcb_m: float  # Longitudinal center of buoyancy
    vcb_m: float  # Vertical center of buoyancy
    tcb_m: float  # Transverse center (usually 0 for symmetric)
    offset_y_m: float  # Body's lateral offset from centerline


@dataclass
class CombinedHydrostatics:
    """Hydrostatics for multi-body vessel."""
    total_displacement_m3: float
    combined_lcb_m: float
    combined_vcb_m: float
    combined_tcb_m: float
    
    # Waterplane properties (combined)
    total_waterplane_area_m2: float
    combined_inertia_xx: float  # Roll (includes parallel axis)
    combined_inertia_yy: float  # Pitch
    
    # Stability
    kb_m: float
    bm_transverse_m: float
    bm_longitudinal_m: float
    
    # Per-body breakdown
    body_contributions: Dict[str, BodyHydrostatics]
    
    # Confidence
    method: str
    confidence: float


def compute_multi_body_hydrostatics(
    bodies: Dict[str, 'BodyConfig'],
    geometry: 'HullGeometry',
    draft_m: float,
) -> CombinedHydrostatics:
    """
    Compute hydrostatics for multi-body vessel using parallel axis theorem.
    
    CRITICAL: For transverse stability (roll), the moment of inertia must include
    the parallel axis contribution: I_combined = Σ(I_local + A × d²)
    
    This is what makes catamarans stable — the A × d² term dominates.
    """
    body_hydro: Dict[str, BodyHydrostatics] = {}
    
    # Step 1: Compute hydrostatics for each body individually
    for body_id, body in bodies.items():
        body_geom = extract_body_geometry(geometry, body_id)
        
        displacement = compute_body_displacement(body_geom, draft_m)
        wp_area = compute_body_waterplane_area(body_geom, draft_m)
        wp_ixx = compute_body_waterplane_inertia_xx(body_geom, draft_m)  # Local
        wp_iyy = compute_body_waterplane_inertia_yy(body_geom, draft_m)
        lcb = compute_body_lcb(body_geom, draft_m)
        vcb = compute_body_vcb(body_geom, draft_m)
        
        body_hydro[body_id] = BodyHydrostatics(
            body_id=body_id,
            displacement_m3=displacement,
            waterplane_area_m2=wp_area,
            waterplane_inertia_xx=wp_ixx,
            waterplane_inertia_yy=wp_iyy,
            lcb_m=lcb,
            vcb_m=vcb,
            tcb_m=0.0,  # Assume symmetric body
            offset_y_m=body.offset_y_m,
        )
    
    # Step 2: Combine displacements (simple sum)
    total_disp = sum(bh.displacement_m3 for bh in body_hydro.values())
    
    if total_disp <= 0:
        raise ValueError("Total displacement must be positive")
    
    # Step 3: Combine centers (weighted average)
    combined_lcb = sum(
        bh.displacement_m3 * bh.lcb_m for bh in body_hydro.values()
    ) / total_disp
    
    combined_vcb = sum(
        bh.displacement_m3 * bh.vcb_m for bh in body_hydro.values()
    ) / total_disp
    
    combined_tcb = sum(
        bh.displacement_m3 * bh.offset_y_m for bh in body_hydro.values()
    ) / total_disp
    
    # Step 4: Combine waterplane area (simple sum)
    total_wp_area = sum(bh.waterplane_area_m2 for bh in body_hydro.values())
    
    # Step 5: Combine moment of inertia with PARALLEL AXIS THEOREM
    # I_combined = Σ(I_local + A × d²)
    # where d = distance from body centroid to combined centroid
    
    combined_ixx = 0.0  # For roll (transverse)
    combined_iyy = 0.0  # For pitch (longitudinal)
    
    for bh in body_hydro.values():
        # Distance from this body's waterplane centroid to combined centroid
        d_transverse = bh.offset_y_m - combined_tcb
        d_longitudinal = bh.lcb_m - combined_lcb
        
        # Parallel axis theorem: I_total = I_local + A × d²
        combined_ixx += bh.waterplane_inertia_xx + bh.waterplane_area_m2 * d_transverse**2
        combined_iyy += bh.waterplane_inertia_yy + bh.waterplane_area_m2 * d_longitudinal**2
    
    # Step 6: Compute BM
    # BM = I / V (moment of inertia / displaced volume)
    bm_transverse = combined_ixx / total_disp
    bm_longitudinal = combined_iyy / total_disp
    
    # Step 7: KB is weighted average of body VCBs
    kb = combined_vcb
    
    return CombinedHydrostatics(
        total_displacement_m3=total_disp,
        combined_lcb_m=combined_lcb,
        combined_vcb_m=combined_vcb,
        combined_tcb_m=combined_tcb,
        total_waterplane_area_m2=total_wp_area,
        combined_inertia_xx=combined_ixx,
        combined_inertia_yy=combined_iyy,
        kb_m=kb,
        bm_transverse_m=bm_transverse,
        bm_longitudinal_m=bm_longitudinal,
        body_contributions=body_hydro,
        method="parallel_axis_theorem",
        confidence=0.95,  # Geometry-based, high confidence
    )


def compute_multi_body_gm(
    bodies: Dict[str, 'BodyConfig'],
    geometry: 'HullGeometry',
    draft_m: float,
    vcg_m: float,
) -> Dict[str, float]:
    """
    Compute GM for multi-body vessel.
    
    GM = KB + BM - KG
    
    Returns dict with transverse and longitudinal GM.
    """
    hydro = compute_multi_body_hydrostatics(bodies, geometry, draft_m)
    
    gm_transverse = hydro.kb_m + hydro.bm_transverse_m - vcg_m
    gm_longitudinal = hydro.kb_m + hydro.bm_longitudinal_m - vcg_m
    
    return {
        "gm_transverse_m": gm_transverse,
        "gm_longitudinal_m": gm_longitudinal,
        "kb_m": hydro.kb_m,
        "bm_transverse_m": hydro.bm_transverse_m,
        "bm_longitudinal_m": hydro.bm_longitudinal_m,
        "method": "multi_body_parallel_axis",
        "confidence": 0.95,
    }
```

### Files to Modify

| File | Change |
|:-----|:-------|
| `magnet/physics/multi_body_hydrostatics.py` | **NEW FILE** — implementation above |
| `magnet/stability/intact_gm.py` | Add dispatch to multi-body when `len(bodies) > 1` |
| `magnet/kernel/validator.py` | Use multi-body hydrostatics for multi-body designs |

### Effort: 3-4 days

---

## Gap 1.5: Multi-Body GZ Curve (Large Angle Stability)

### The Problem

Gap 1 covers small-angle stability (GM). But regulatory compliance and capsize analysis require GZ curves at large heel angles.

For multi-body vessels, this is non-trivial:
- At large heel, one hull may emerge from water entirely
- The righting arm is highly nonlinear
- Multiple equilibria may exist at certain angles

### The Solution

```python
# magnet/physics/multi_body_gz_curve.py

from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np

@dataclass
class GZCurvePoint:
    """Single point on GZ curve."""
    heel_angle_deg: float
    gz_m: float
    
    # Additional data
    displacement_m3: float    # May change as hulls emerge
    waterline_height_m: float # Equilibrium waterline
    bodies_submerged: List[str]  # Which bodies still in water
    
    # Confidence
    converged: bool
    iterations: int


@dataclass
class MultiBodyGZCurve:
    """Complete GZ curve for multi-body vessel."""
    points: List[GZCurvePoint]
    
    # Key metrics
    gz_max_m: float
    angle_at_gz_max_deg: float
    range_of_positive_stability_deg: float
    angle_of_vanishing_stability_deg: float
    
    # Warnings
    warnings: List[str]
    
    # Methodology
    method: str
    confidence: float


def compute_multi_body_gz_curve(
    bodies: Dict[str, 'BodyConfig'],
    geometry: 'HullGeometry',
    displacement_tonnes: float,
    vcg_m: float,
    tcg_m: float,
    heel_angles_deg: List[float] = None,
) -> MultiBodyGZCurve:
    """
    Compute GZ curve for multi-body vessel.
    
    Algorithm at each heel angle:
    1. Rotate all bodies around longitudinal axis by heel angle
    2. Find equilibrium waterline (displaced volume = weight)
    3. Compute centers: TCB (transverse center of buoyancy)
    4. Compute righting arm: GZ = (TCB - TCG) × cos(heel) + (VCB - VCG) × sin(heel)
    
    WARNING: Computationally expensive. May have convergence issues at large angles.
    """
    if heel_angles_deg is None:
        heel_angles_deg = list(range(0, 91, 5))  # 0° to 90° in 5° steps
    
    target_volume_m3 = displacement_tonnes * 1.025  # Seawater density
    
    points = []
    warnings = []
    
    for heel_deg in heel_angles_deg:
        heel_rad = np.radians(heel_deg)
        
        # Rotate geometry around X-axis (longitudinal)
        rotated_geometry = rotate_geometry_around_x(geometry, heel_rad)
        
        # Find equilibrium waterline (iterative)
        waterline, converged, iterations = find_equilibrium_waterline(
            bodies, rotated_geometry, target_volume_m3, max_iterations=50
        )
        
        if not converged:
            warnings.append(f"Waterline did not converge at {heel_deg}°")
        
        # Compute displaced volume and centers at this waterline
        total_volume = 0.0
        moment_y = 0.0  # For TCB
        moment_z = 0.0  # For VCB
        bodies_submerged = []
        
        for body_id, body in bodies.items():
            body_geom = extract_body_geometry(rotated_geometry, body_id)
            vol = compute_body_volume_below_wl(body_geom, waterline)
            
            if vol > 0.001:  # Body contributes
                bodies_submerged.append(body_id)
                cb_y, cb_z = compute_body_cb_position(body_geom, waterline)
                
                total_volume += vol
                moment_y += vol * cb_y
                moment_z += vol * cb_z
        
        # Combined centers
        tcb = moment_y / total_volume if total_volume > 0 else 0
        vcb = moment_z / total_volume if total_volume > 0 else 0
        
        # GZ = horizontal distance between B and G
        # In heeled reference frame:
        # GZ = (TCB - TCG) × cos(heel) + (VCB - VCG) × sin(heel)
        gz = (tcb - tcg_m) * np.cos(heel_rad) + (vcb - vcg_m) * np.sin(heel_rad)
        
        points.append(GZCurvePoint(
            heel_angle_deg=heel_deg,
            gz_m=gz,
            displacement_m3=total_volume,
            waterline_height_m=waterline,
            bodies_submerged=bodies_submerged,
            converged=converged,
            iterations=iterations,
        ))
        
        # Check for hull emergence
        if len(bodies_submerged) < len(bodies):
            emerged = set(bodies.keys()) - set(bodies_submerged)
            warnings.append(f"Bodies emerged at {heel_deg}°: {emerged}")
    
    # Compute key metrics
    gz_values = [p.gz_m for p in points]
    angles = [p.heel_angle_deg for p in points]
    
    gz_max = max(gz_values)
    angle_at_max = angles[gz_values.index(gz_max)]
    
    # Find angle of vanishing stability (GZ crosses zero from positive)
    avs = 90.0  # Default to max if never crosses
    for i in range(1, len(points)):
        if points[i-1].gz_m > 0 and points[i].gz_m <= 0:
            # Linear interpolation
            avs = angles[i-1] + (angles[i] - angles[i-1]) * points[i-1].gz_m / (points[i-1].gz_m - points[i].gz_m)
            break
    
    # Range of positive stability
    range_positive = avs
    
    return MultiBodyGZCurve(
        points=points,
        gz_max_m=gz_max,
        angle_at_gz_max_deg=angle_at_max,
        range_of_positive_stability_deg=range_positive,
        angle_of_vanishing_stability_deg=avs,
        warnings=warnings,
        method="iterative_equilibrium",
        confidence=0.85 if all(p.converged for p in points) else 0.6,
    )


def find_equilibrium_waterline(
    bodies: Dict[str, 'BodyConfig'],
    geometry: 'HullGeometry',
    target_volume_m3: float,
    max_iterations: int = 50,
    tolerance: float = 0.001,
) -> Tuple[float, bool, int]:
    """
    Find waterline height that gives target displaced volume.
    
    Uses bisection method for robustness.
    """
    # Initial bounds (assume reasonable draft range)
    wl_low = -10.0   # Deep
    wl_high = 10.0   # High
    
    for iteration in range(max_iterations):
        wl_mid = (wl_low + wl_high) / 2
        
        # Compute total displaced volume at this waterline
        total_vol = sum(
            compute_body_volume_below_wl(
                extract_body_geometry(geometry, body_id), wl_mid
            )
            for body_id in bodies.keys()
        )
        
        error = total_vol - target_volume_m3
        
        if abs(error) < tolerance * target_volume_m3:
            return wl_mid, True, iteration + 1
        
        if error > 0:  # Too much volume, raise waterline
            wl_low = wl_mid
        else:  # Too little volume, lower waterline
            wl_high = wl_mid
    
    return (wl_low + wl_high) / 2, False, max_iterations
```

### Files to Create

| File | Change |
|:-----|:-------|
| `magnet/physics/multi_body_gz_curve.py` | **NEW FILE** — implementation above |

### Effort: 3-4 days (complex iterative algorithm)

---

## Gap 2: Form Coefficient Derivation

### The Problem

Resistance methods (Holtrop-Mennen, Savitsky) require form coefficients:

| Coefficient | Definition | Problem for Novel Forms |
|:------------|:-----------|:------------------------|
| Cp | Prismatic coefficient | Requires volume integration along length |
| Cwp | Waterplane coefficient | Requires area integration |
| Cm | Midship coefficient | What's "midship" for asymmetric form? |
| LCB% | LCB as % of LWL | Requires LWL definition |

**Current code assumes these are INPUT parameters, not derived from geometry.**

### The Solution

```python
# magnet/physics/form_coefficients.py

from dataclasses import dataclass
from typing import Optional
import numpy as np

@dataclass
class FormCoefficients:
    """Form coefficients derived from geometry."""
    
    # Volume-based
    cb: float           # Block coefficient = V / (L × B × T)
    cp: float           # Prismatic coefficient = V / (Am × L)
    cm: float           # Midship coefficient = Am / (B × T)
    cvp: float          # Vertical prismatic = V / (Awp × T)
    
    # Area-based
    cwp: float          # Waterplane coefficient = Awp / (L × B)
    
    # Position-based
    lcb_percent: float  # LCB as % of LWL from FP
    lcf_percent: float  # LCF as % of LWL from FP
    
    # Raw values used
    volume_m3: float
    waterplane_area_m2: float
    midship_area_m2: float
    lwl_m: float
    beam_m: float       # Maximum beam at waterline
    draft_m: float
    
    # Confidence
    confidence: float
    notes: List[str]


def derive_form_coefficients(
    geometry: 'HullGeometry',
    draft_m: float,
    body_id: Optional[str] = None,
) -> FormCoefficients:
    """
    Numerically derive form coefficients from arbitrary geometry.
    
    This replaces the assumption that form coefficients are known inputs.
    """
    notes = []
    
    # Get sections for this body (or all if single-body)
    sections = get_sections_for_body(geometry, body_id)
    
    if len(sections) < 3:
        notes.append("WARNING: < 3 sections, coefficients may be inaccurate")
    
    # Step 1: Compute displaced volume by integrating section areas
    volume, lcb = integrate_displaced_volume(sections, draft_m)
    
    # Step 2: Find LWL (length at waterline)
    lwl = compute_lwl(sections, draft_m)
    
    # Step 3: Find maximum beam at waterline
    beam = compute_max_beam_at_waterline(sections, draft_m)
    
    # Step 4: Compute waterplane area
    awp = integrate_waterplane_area(sections, draft_m)
    
    # Step 5: Find midship section (maximum area)
    am, midship_station = find_midship_section(sections, draft_m)
    
    # Step 6: Compute coefficients
    cb = volume / (lwl * beam * draft_m) if (lwl * beam * draft_m) > 0 else 0
    cp = volume / (am * lwl) if (am * lwl) > 0 else 0
    cm = am / (beam * draft_m) if (beam * draft_m) > 0 else 0
    cwp = awp / (lwl * beam) if (lwl * beam) > 0 else 0
    cvp = volume / (awp * draft_m) if (awp * draft_m) > 0 else 0
    
    # LCB as percentage from FP
    lcb_percent = (lcb / lwl) * 100 if lwl > 0 else 50.0
    
    # LCF (longitudinal center of floatation)
    lcf = compute_lcf(sections, draft_m)
    lcf_percent = (lcf / lwl) * 100 if lwl > 0 else 50.0
    
    # Confidence based on section count and coefficient reasonableness
    confidence = 0.9
    if len(sections) < 5:
        confidence -= 0.2
        notes.append("Low section count reduces accuracy")
    if cb < 0.3 or cb > 0.9:
        confidence -= 0.1
        notes.append(f"Unusual Cb={cb:.3f}, verify geometry")
    if cp < 0.5 or cp > 0.9:
        confidence -= 0.1
        notes.append(f"Unusual Cp={cp:.3f}, verify geometry")
    
    return FormCoefficients(
        cb=cb,
        cp=cp,
        cm=cm,
        cvp=cvp,
        cwp=cwp,
        lcb_percent=lcb_percent,
        lcf_percent=lcf_percent,
        volume_m3=volume,
        waterplane_area_m2=awp,
        midship_area_m2=am,
        lwl_m=lwl,
        beam_m=beam,
        draft_m=draft_m,
        confidence=max(0.5, confidence),
        notes=notes,
    )


def integrate_displaced_volume(
    sections: List['HullSection'],
    draft_m: float,
) -> tuple[float, float]:
    """
    Integrate section areas to get displaced volume and LCB.
    
    Uses trapezoidal rule on section areas below waterline.
    """
    stations = []
    areas = []
    
    for section in sorted(sections, key=lambda s: s.station):
        area = compute_section_area_below_wl(section, draft_m)
        stations.append(section.station)
        areas.append(area)
    
    # Trapezoidal integration
    volume = np.trapz(areas, stations)
    
    # LCB = ∫(x × A(x) dx) / V
    if volume > 0:
        moments = [s * a for s, a in zip(stations, areas)]
        lcb = np.trapz(moments, stations) / volume
    else:
        lcb = stations[len(stations) // 2] if stations else 0
    
    return volume, lcb


def compute_section_area_below_wl(
    section: 'HullSection',
    draft_m: float,
) -> float:
    """
    Compute area of section below waterline.
    
    Handles both point-based sections and NURBS curves.
    
    Algorithm:
    1. Find intersection of section curve with waterline (z = draft_m)
    2. Integrate enclosed area below waterline
    """
    waterline_z = draft_m
    
    # Check section type
    if hasattr(section, 'control_points') and section.control_points is not None:
        # NURBS-defined section
        return _nurbs_section_area_below_wl(section, waterline_z)
    elif hasattr(section, 'points') and section.points is not None:
        # Point-based section
        return _polygon_area_below_wl(section.points, waterline_z)
    else:
        # Parametric section (half-breadths)
        return _parametric_section_area_below_wl(section, waterline_z)


def _polygon_area_below_wl(
    points: List[Tuple[float, float]],
    waterline_z: float,
) -> float:
    """
    Compute area of polygon below waterline.
    
    Uses shoelace formula on clipped polygon.
    Points are (y, z) pairs in section plane.
    """
    # Clip polygon to waterline
    clipped_points = []
    
    n = len(points)
    for i in range(n):
        p1 = points[i]
        p2 = points[(i + 1) % n]
        
        y1, z1 = p1
        y2, z2 = p2
        
        # Is p1 below waterline?
        p1_below = z1 <= waterline_z
        p2_below = z2 <= waterline_z
        
        if p1_below:
            clipped_points.append(p1)
        
        # Check for intersection with waterline
        if p1_below != p2_below:
            # Linear interpolation to find intersection
            if z2 != z1:
                t = (waterline_z - z1) / (z2 - z1)
                y_intersect = y1 + t * (y2 - y1)
                clipped_points.append((y_intersect, waterline_z))
    
    if len(clipped_points) < 3:
        return 0.0
    
    # Shoelace formula for area
    area = 0.0
    n = len(clipped_points)
    for i in range(n):
        y1, z1 = clipped_points[i]
        y2, z2 = clipped_points[(i + 1) % n]
        area += y1 * z2 - y2 * z1
    
    return abs(area) / 2.0


def _nurbs_section_area_below_wl(
    section: 'HullSection',
    waterline_z: float,
    num_samples: int = 50,
) -> float:
    """
    Compute area below waterline for NURBS-defined section.
    
    Algorithm:
    1. Sample NURBS curve at many points
    2. Find intersection with waterline
    3. Integrate area below waterline
    """
    from magnet.hull_gen.nurbs import NURBSCurve  # Assuming this exists
    
    # Create NURBS curve from section control points
    curve = NURBSCurve(
        control_points=section.control_points,
        degree=section.degree if hasattr(section, 'degree') else 3,
        knots=section.knots if hasattr(section, 'knots') else None,
    )
    
    # Sample curve
    t_values = np.linspace(0, 1, num_samples)
    points = [curve.evaluate(t) for t in t_values]
    
    # Convert to (y, z) list
    point_list = [(p[1], p[2]) for p in points]  # Assuming (x, y, z) output
    
    # Use polygon method on sampled points
    return _polygon_area_below_wl(point_list, waterline_z)


def _parametric_section_area_below_wl(
    section: 'HullSection',
    waterline_z: float,
) -> float:
    """
    Compute area for parametric section (defined by half-breadths at heights).
    
    HullSection has:
    - station: x position along hull
    - heights: list of z values
    - half_breadths: list of y values at each height
    """
    # Build points from half-breadths
    heights = section.heights if hasattr(section, 'heights') else []
    half_breadths = section.half_breadths if hasattr(section, 'half_breadths') else []
    
    if not heights or not half_breadths:
        return 0.0
    
    # Create polygon from half-breadths (port side + mirror)
    points = []
    
    # Starboard side (positive y)
    for h, hb in zip(heights, half_breadths):
        points.append((hb, h))
    
    # Port side (negative y) - reverse order
    for h, hb in reversed(list(zip(heights, half_breadths))):
        points.append((-hb, h))
    
    return _polygon_area_below_wl(points, waterline_z)
```

### Files to Create/Modify

| File | Change |
|:-----|:-------|
| `magnet/physics/form_coefficients.py` | **NEW FILE** — implementation above |
| `magnet/physics/resistance.py` | Call `derive_form_coefficients()` instead of expecting inputs |

### Effort: 3-5 days

---

## Gap 3: Resistance Method Selection

### The Problem

Different hull forms require different resistance prediction methods:

| Form | Method | Validity Range |
|:-----|:-------|:---------------|
| Displacement monohull | Holtrop-Mennen | Fn < 0.55, 3 < L/B < 15 |
| Planing monohull | Savitsky | Fn > 1.0, prismatic planing hull |
| Catamaran | Insel-Molland (1992) | Fn < 0.9, slender demihulls |
| SWATH | Custom | Submerged body drag |
| Novel form | **NONE** | Return uncertainty |

**Current code picks one method without checking validity.**

### The Solution

```python
# magnet/physics/resistance_selector.py

from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import Enum

class ResistanceMethod(Enum):
    HOLTROP_MENNEN = "holtrop_mennen"
    SAVITSKY = "savitsky"
    INSEL_MOLLAND = "insel_molland"
    SWATH_EMPIRICAL = "swath_empirical"
    CRUDE_ESTIMATE = "crude_estimate"  # Fallback with high uncertainty
    UNKNOWN = "unknown"


@dataclass
class ResistanceResult:
    """Resistance prediction with honest uncertainty."""
    
    resistance_kn: Optional[float]
    power_kw: Optional[float]
    
    method_used: ResistanceMethod
    method_confidence: float  # 0-1
    
    validity_check: Dict[str, bool]
    validity_notes: List[str]
    
    # Uncertainty bounds
    resistance_low_kn: Optional[float]   # 10th percentile
    resistance_high_kn: Optional[float]  # 90th percentile
    
    recommendation: str


@dataclass
class MethodValidity:
    """Validity check for a resistance method."""
    method: ResistanceMethod
    is_valid: bool
    confidence: float
    reason: str


def select_resistance_method(
    form_coefficients: 'FormCoefficients',
    froude_number: float,
    body_count: int,
    physics_categories: List[str],
) -> MethodValidity:
    """
    Select appropriate resistance method based on form and regime.
    
    Returns the best method with confidence, or UNKNOWN if no method applies.
    """
    
    validities = []
    
    # Check Holtrop-Mennen validity
    hm_valid = True
    hm_reasons = []
    
    if froude_number > 0.55:
        hm_valid = False
        hm_reasons.append(f"Fn={froude_number:.2f} > 0.55 limit")
    
    if body_count > 1:
        hm_valid = False
        hm_reasons.append(f"Multi-body ({body_count}) not supported")
    
    lb_ratio = form_coefficients.lwl_m / form_coefficients.beam_m
    if lb_ratio < 3.0 or lb_ratio > 15.0:
        hm_valid = False
        hm_reasons.append(f"L/B={lb_ratio:.1f} outside 3-15 range")
    
    if form_coefficients.cp < 0.55 or form_coefficients.cp > 0.85:
        hm_valid = False
        hm_reasons.append(f"Cp={form_coefficients.cp:.2f} outside 0.55-0.85 range")
    
    validities.append(MethodValidity(
        method=ResistanceMethod.HOLTROP_MENNEN,
        is_valid=hm_valid,
        confidence=0.85 if hm_valid else 0.0,
        reason="; ".join(hm_reasons) if hm_reasons else "Within validity envelope",
    ))
    
    # Check Savitsky validity
    sav_valid = True
    sav_reasons = []
    
    if froude_number < 1.0:
        sav_valid = False
        sav_reasons.append(f"Fn={froude_number:.2f} < 1.0 (not planing)")
    
    if body_count > 1:
        sav_valid = False
        sav_reasons.append("Multi-body not supported")
    
    # Savitsky requires prismatic planing form (high deadrise at transom)
    # This is hard to verify from form coefficients alone
    
    validities.append(MethodValidity(
        method=ResistanceMethod.SAVITSKY,
        is_valid=sav_valid,
        confidence=0.75 if sav_valid else 0.0,
        reason="; ".join(sav_reasons) if sav_reasons else "Planing regime",
    ))
    
    # Check Insel-Molland (catamaran) validity
    im_valid = True
    im_reasons = []
    
    if body_count != 2:
        im_valid = False
        im_reasons.append(f"Requires 2 bodies, got {body_count}")
    
    if froude_number > 0.9:
        im_valid = False
        im_reasons.append(f"Fn={froude_number:.2f} > 0.9 limit")
    
    # Slenderness check (demihulls should be slender)
    if lb_ratio < 7.0:
        im_valid = False
        im_reasons.append(f"Demihull L/B={lb_ratio:.1f} < 7 (not slender)")
    
    validities.append(MethodValidity(
        method=ResistanceMethod.INSEL_MOLLAND,
        is_valid=im_valid,
        confidence=0.80 if im_valid else 0.0,
        reason="; ".join(im_reasons) if im_reasons else "Catamaran regime",
    ))
    
    # Check SWATH validity
    swath_valid = all(pc == "submerged" for pc in physics_categories)
    validities.append(MethodValidity(
        method=ResistanceMethod.SWATH_EMPIRICAL,
        is_valid=swath_valid and body_count >= 2,
        confidence=0.70 if swath_valid else 0.0,
        reason="Submerged body resistance" if swath_valid else "Not fully submerged",
    ))
    
    # Select best valid method
    valid_methods = [v for v in validities if v.is_valid]
    
    if valid_methods:
        best = max(valid_methods, key=lambda v: v.confidence)
        return best
    else:
        # No valid method — return UNKNOWN with all reasons
        all_reasons = [f"{v.method.value}: {v.reason}" for v in validities]
        return MethodValidity(
            method=ResistanceMethod.UNKNOWN,
            is_valid=False,
            confidence=0.0,
            reason="No validated method. " + "; ".join(all_reasons),
        )


def compute_resistance_with_uncertainty(
    geometry: 'HullGeometry',
    bodies: Dict[str, 'BodyConfig'],
    speed_kts: float,
    draft_m: float,
) -> ResistanceResult:
    """
    Compute resistance with honest uncertainty quantification.
    
    If no method is valid, returns None for resistance with recommendation.
    """
    # Derive form coefficients from geometry
    form_coeff = derive_form_coefficients(geometry, draft_m)
    
    # Compute Froude number
    fn = compute_froude_number(speed_kts, form_coeff.lwl_m)
    
    # Get physics categories
    physics_cats = [b.physics_category for b in bodies.values()]
    
    # Select method
    method_validity = select_resistance_method(
        form_coeff, fn, len(bodies), physics_cats
    )
    
    validity_check = {
        "froude_in_range": fn <= 0.55 or fn >= 1.0,
        "form_coefficients_valid": form_coeff.confidence > 0.7,
        "method_available": method_validity.is_valid,
    }
    
    if not method_validity.is_valid:
        # Return CRUDE ESTIMATE with huge uncertainty (±100%)
        # Gives engineers something to work with, while being honest about uncertainty
        rough_rt, rough_power = crude_resistance_estimate(geometry, form_coeff, speed_kts, draft_m)
        
        return ResistanceResult(
            resistance_kn=rough_rt,
            power_kw=rough_power,
            method_used=ResistanceMethod.CRUDE_ESTIMATE,
            method_confidence=0.2,  # Very low confidence
            validity_check=validity_check,
            validity_notes=[method_validity.reason, "Using crude wetted surface estimate"],
            resistance_low_kn=rough_rt * 0.5 if rough_rt else None,   # Could be half
            resistance_high_kn=rough_rt * 2.0 if rough_rt else None,  # Could be double
            recommendation="No validated method. Estimate shown with ±100% uncertainty. CFD/model test required.",
        )
    
    # Compute resistance using selected method
    if method_validity.method == ResistanceMethod.HOLTROP_MENNEN:
        rt, power = holtrop_mennen_resistance(geometry, form_coeff, speed_kts, draft_m)
        uncertainty = 0.15  # ±15% typical
    
    elif method_validity.method == ResistanceMethod.SAVITSKY:
        rt, power = savitsky_resistance(geometry, form_coeff, speed_kts, draft_m)
        uncertainty = 0.20  # ±20% for planing
    
    elif method_validity.method == ResistanceMethod.INSEL_MOLLAND:
        rt, power = insel_molland_resistance(geometry, bodies, form_coeff, speed_kts, draft_m)
        uncertainty = 0.18  # ±18% for catamarans
    
    elif method_validity.method == ResistanceMethod.SWATH_EMPIRICAL:
        rt, power = swath_resistance(geometry, bodies, form_coeff, speed_kts, draft_m)
        uncertainty = 0.25  # Higher uncertainty
    
    else:
        # NO VALID METHOD: Return crude estimate with huge uncertainty
        rt, power = crude_resistance_estimate(geometry, form_coeff, speed_kts, draft_m)
        uncertainty = 1.0  # ±100% uncertainty
    
    return ResistanceResult(
        resistance_kn=rt,
        power_kw=power,
        method_used=method_validity.method,
        method_confidence=method_validity.confidence,
        validity_check=validity_check,
        validity_notes=[method_validity.reason],
        resistance_low_kn=rt * (1 - uncertainty) if rt else None,
        resistance_high_kn=rt * (1 + uncertainty) if rt else None,
        recommendation=f"Method: {method_validity.method.value}, confidence: {method_validity.confidence:.0%}",
    )
```

### Insel-Molland Implementation with Interference Factor

The key to catamaran resistance is the **interference factor τ**:

```
R_catamaran = 2 × R_demihull × τ
```

Where τ accounts for wave interference between hulls.

```python
# magnet/physics/insel_molland.py

from typing import Tuple, Dict
import numpy as np

def insel_molland_resistance(
    geometry: 'HullGeometry',
    bodies: Dict[str, 'BodyConfig'],
    form_coeff: 'FormCoefficients',
    speed_kts: float,
    draft_m: float,
) -> Tuple[float, float]:
    """
    Catamaran resistance using Insel-Molland (1992) method.
    
    R_catamaran = 2 × R_demihull × τ
    
    where τ is the interference factor based on:
    - Hull separation / length ratio (S/L)
    - Froude number
    - Demihull slenderness (L/B)
    
    Reference: Insel & Molland (1992), "An Investigation into the Resistance 
    Components of High Speed Displacement Catamarans"
    """
    # Get hull spacing (distance between demihull centerlines)
    offsets = [b.offset_y_m for b in bodies.values()]
    hull_spacing = abs(max(offsets) - min(offsets))
    
    # Demihull L/B
    lwl = form_coeff.lwl_m
    demihull_beam = form_coeff.beam_m / 2  # Approximate demihull beam
    lb_demihull = lwl / demihull_beam if demihull_beam > 0 else 10.0
    
    # S/L ratio (separation / length)
    sl_ratio = hull_spacing / lwl if lwl > 0 else 0.2
    
    # Froude number
    speed_ms = speed_kts * 0.5144
    fn = speed_ms / np.sqrt(9.81 * lwl)
    
    # Compute single demihull resistance (using Holtrop for displacement regime)
    # Note: Create synthetic form coefficients for demihull
    demihull_form = FormCoefficients(
        cb=form_coeff.cb,
        cp=form_coeff.cp,
        cm=form_coeff.cm,
        cvp=form_coeff.cvp,
        cwp=form_coeff.cwp,
        lcb_percent=form_coeff.lcb_percent,
        lcf_percent=form_coeff.lcf_percent,
        volume_m3=form_coeff.volume_m3 / 2,  # Half for demihull
        waterplane_area_m2=form_coeff.waterplane_area_m2 / 2,
        midship_area_m2=form_coeff.midship_area_m2 / 2,
        lwl_m=lwl,
        beam_m=demihull_beam,
        draft_m=draft_m,
        confidence=form_coeff.confidence,
        notes=form_coeff.notes + ["Demihull approximation"],
    )
    
    # Single demihull resistance (simplified Holtrop or ITTC friction)
    r_demihull = compute_demihull_resistance(demihull_form, speed_kts, draft_m)
    
    # INTERFERENCE FACTOR (this is the key!)
    tau = compute_interference_factor(sl_ratio, fn, lb_demihull)
    
    # Total catamaran resistance
    r_total = 2 * r_demihull * tau
    
    # Power estimate
    power_kw = r_total * speed_ms / 1000 / 0.65  # Assume 65% propulsive efficiency
    
    return r_total, power_kw


def compute_interference_factor(sl_ratio: float, fn: float, lb: float) -> float:
    """
    Compute catamaran interference factor τ.
    
    Based on Insel-Molland regression data for NPL round-bilge series.
    
    τ > 1.0 means interference INCREASES resistance (unfavorable)
    τ < 1.0 means interference DECREASES resistance (favorable, rare)
    τ ≈ 1.0 means negligible interference
    
    Key parameters:
    - S/L: Higher separation → τ → 1.0
    - Fn: Interference peaks near Fn ≈ 0.3-0.5
    - L/B: Slender hulls have less interference
    """
    # Base interference from S/L (wider spacing = less interference)
    if sl_ratio >= 0.4:
        tau_sl = 1.0  # Wide enough, no interference
    elif sl_ratio >= 0.2:
        tau_sl = 1.0 + 0.25 * (0.4 - sl_ratio) / 0.2  # Linear ramp
    else:
        tau_sl = 1.25 + 0.5 * (0.2 - sl_ratio) / 0.2  # Strong interference
    
    # Froude number effect (interference peaks in hump region)
    if fn < 0.2:
        tau_fn = 1.0  # Low speed, no wave interference
    elif fn < 0.35:
        tau_fn = 1.0 + 0.2 * (fn - 0.2) / 0.15  # Building up
    elif fn < 0.5:
        tau_fn = 1.2 - 0.15 * (fn - 0.35) / 0.15  # Peak and decline
    else:
        tau_fn = 1.05  # High Fn, some residual interference
    
    # L/B effect (slender hulls have less interference)
    if lb > 12:
        tau_lb = 0.95  # Very slender, favorable interference possible
    elif lb > 8:
        tau_lb = 1.0
    else:
        tau_lb = 1.0 + 0.1 * (8 - lb) / 4  # Beamier hulls, more interference
    
    # Combined interference factor
    # Note: This is simplified; full Insel-Molland uses regression tables
    tau = tau_sl * tau_fn * tau_lb
    
    # Clamp to reasonable range
    return max(0.9, min(1.5, tau))


def compute_demihull_resistance(
    form_coeff: 'FormCoefficients',
    speed_kts: float,
    draft_m: float,
) -> float:
    """
    Compute single demihull resistance.
    
    Uses simplified approach: friction + form factor + wave drag.
    """
    speed_ms = speed_kts * 0.5144
    
    # Wetted surface (approximation)
    lwl = form_coeff.lwl_m
    beam = form_coeff.beam_m
    draft = draft_m
    wetted_surface = lwl * (2 * draft + beam) * 0.8  # Simplified
    
    # Reynolds number
    nu = 1.19e-6  # Kinematic viscosity seawater
    rn = speed_ms * lwl / nu
    
    # ITTC friction coefficient
    cf = 0.075 / (np.log10(rn) - 2) ** 2 if rn > 1e5 else 0.01
    
    # Form factor (simplified)
    k = 0.1 + 0.4 * form_coeff.cb  # Higher Cb = more form drag
    
    # Wave resistance coefficient (simplified, Fn-based)
    fn = speed_ms / np.sqrt(9.81 * lwl)
    if fn < 0.2:
        cw = 0.0001
    elif fn < 0.4:
        cw = 0.001 * ((fn - 0.2) / 0.2) ** 2
    else:
        cw = 0.001 + 0.002 * (fn - 0.4)
    
    # Total resistance coefficient
    ct = cf * (1 + k) + cw
    
    # Resistance in kN
    rho = 1025  # kg/m³ seawater
    resistance_n = 0.5 * rho * speed_ms ** 2 * wetted_surface * ct
    resistance_kn = resistance_n / 1000
    
    return resistance_kn


def crude_resistance_estimate(
    geometry: 'HullGeometry',
    form_coeff: 'FormCoefficients',
    speed_kts: float,
    draft_m: float,
) -> Tuple[float, float]:
    """
    Crude resistance estimate for forms where no validated method exists.
    
    Uses basic friction + wave drag formula.
    This is VERY approximate (±100% uncertainty).
    """
    speed_ms = speed_kts * 0.5144
    
    # Estimate wetted surface from form coefficients
    lwl = form_coeff.lwl_m
    beam = form_coeff.beam_m
    draft = draft_m
    
    # Denny-Mumford approximation for wetted surface
    wetted_surface = 1.7 * lwl * draft + form_coeff.volume_m3 / draft
    
    # Reynolds number
    nu = 1.19e-6
    rn = speed_ms * lwl / nu if lwl > 0 else 1e6
    
    # ITTC friction
    cf = 0.075 / (np.log10(max(rn, 1e5)) - 2) ** 2
    
    # Conservative form factor
    k = 0.2
    
    # Conservative wave resistance
    fn = speed_ms / np.sqrt(9.81 * lwl) if lwl > 0 else 0.3
    cw = 0.002 * fn ** 2
    
    # Total
    ct = cf * (1 + k) + cw
    
    # Resistance
    rho = 1025
    resistance_n = 0.5 * rho * speed_ms ** 2 * wetted_surface * ct
    resistance_kn = resistance_n / 1000
    
    # Power (very conservative 50% efficiency for unknown form)
    power_kw = resistance_kn * speed_ms / 0.50
    
    return resistance_kn, power_kw
```

### Files to Create/Modify

| File | Change |
|:-----|:-------|
| `magnet/physics/resistance_selector.py` | **NEW FILE** — method selection with validity |
| `magnet/physics/insel_molland.py` | **NEW FILE** — catamaran with interference factor |
| `magnet/physics/crude_estimate.py` | **NEW FILE** — fallback for novel forms |
| `magnet/physics/resistance.py` | Refactor to use selector |

### Effort: 5-7 days

---

## Gap 4: Multi-Body Form Parameters

### The Problem

What is "beam" for a catamaran? A trimaran?

```
Catamaran:
  Overall beam (hull to hull) = 9m
  Demihull beam = 1.5m
  Which goes into L/B?

Trimaran:
  Overall beam (outrigger to outrigger) = 15m
  Main hull beam = 3m
  Which one?
```

**This affects ALL form-based calculations.**

### The Solution

Define explicit conventions:

```python
# magnet/physics/multi_body_form.py

from dataclasses import dataclass
from typing import Dict, List
from enum import Enum


class BeamDefinition(Enum):
    """How to define beam for multi-body vessel."""
    OVERALL = "overall"           # Extreme breadth (outrigger to outrigger)
    MAIN_HULL = "main_hull"       # Main/center hull beam
    SINGLE_BODY = "single_body"   # Individual body beam (for resistance)
    EFFECTIVE = "effective"       # √(Σ beam² / n) — RMS


@dataclass
class MultiBodyFormParameters:
    """Form parameters for multi-body vessel with explicit conventions."""
    
    # Length (always overall)
    loa_m: float
    lwl_m: float
    
    # Beam with multiple definitions
    beam_overall_m: float      # Extreme breadth
    beam_main_hull_m: float    # Main hull only
    beam_demihull_m: float     # Single demihull (for catamaran)
    beam_effective_m: float    # For resistance calculations
    
    # Draft
    draft_m: float
    
    # Spacing
    hull_spacing_m: float      # Centerline to centerline
    tunnel_width_m: float      # Clear distance between hulls
    
    # Derived ratios
    lb_overall: float          # LOA / beam_overall
    lb_demihull: float         # LOA / beam_demihull (for resistance)
    slenderness: float         # LWL / beam_demihull^(1/3)
    
    # Multi-body specific
    body_count: int
    configuration: str         # "catamaran", "trimaran", "asymmetric", "custom"


def compute_multi_body_form_parameters(
    bodies: Dict[str, 'BodyConfig'],
    geometry: 'HullGeometry',
    draft_m: float,
) -> MultiBodyFormParameters:
    """
    Compute form parameters for multi-body vessel with explicit conventions.
    
    Convention for L/B in resistance:
    - Catamaran: Use demihull L/B (what goes into Insel-Molland)
    - Trimaran: Use main hull L/B
    - General: Use effective beam
    """
    # Compute per-body dimensions
    body_dims = {}
    for body_id, body in bodies.items():
        body_geom = extract_body_geometry(geometry, body_id)
        body_dims[body_id] = {
            "lwl": compute_body_lwl(body_geom, draft_m),
            "beam": compute_body_beam_at_wl(body_geom, draft_m),
            "offset_y": body.offset_y_m,
        }
    
    # Overall dimensions
    loa = compute_overall_loa(geometry)
    lwl = max(bd["lwl"] for bd in body_dims.values())
    
    # Beam definitions
    all_offsets = [bd["offset_y"] for bd in body_dims.values()]
    all_beams = [bd["beam"] for bd in body_dims.values()]
    
    beam_overall = max(all_offsets) - min(all_offsets) + max(all_beams)
    
    # Find main hull (center or largest)
    main_hull_id = min(body_dims.keys(), key=lambda k: abs(body_dims[k]["offset_y"]))
    beam_main = body_dims[main_hull_id]["beam"]
    
    # Demihull beam (for catamaran)
    if len(bodies) == 2:
        beam_demihull = sum(all_beams) / 2
    else:
        beam_demihull = beam_main
    
    # Effective beam (RMS)
    beam_effective = (sum(b**2 for b in all_beams) / len(all_beams)) ** 0.5
    
    # Spacing
    if len(all_offsets) >= 2:
        sorted_offsets = sorted(all_offsets)
        hull_spacing = sorted_offsets[-1] - sorted_offsets[0]
        # Find two closest bodies for tunnel width
        if len(sorted_offsets) >= 2:
            gaps = [sorted_offsets[i+1] - sorted_offsets[i] for i in range(len(sorted_offsets)-1)]
            tunnel_width = min(gaps) - beam_demihull
        else:
            tunnel_width = hull_spacing - beam_demihull
    else:
        hull_spacing = 0
        tunnel_width = 0
    
    # Determine configuration (generic label, NOT design type)
    # We use body count, not design names like "catamaran" or "trimaran"
    config = f"multi_body_{len(bodies)}" if len(bodies) > 1 else "single_body"
    
    return MultiBodyFormParameters(
        loa_m=loa,
        lwl_m=lwl,
        beam_overall_m=beam_overall,
        beam_main_hull_m=beam_main,
        beam_demihull_m=beam_demihull,
        beam_effective_m=beam_effective,
        draft_m=draft_m,
        hull_spacing_m=hull_spacing,
        tunnel_width_m=tunnel_width,
        lb_overall=lwl / beam_overall if beam_overall > 0 else 0,
        lb_demihull=lwl / beam_demihull if beam_demihull > 0 else 0,
        slenderness=lwl / (beam_demihull ** (1/3)) if beam_demihull > 0 else 0,
        body_count=len(bodies),
        configuration=config,
    )
```

### Files to Create

| File | Change |
|:-----|:-------|
| `magnet/physics/multi_body_form.py` | **NEW FILE** — implementation above |

### Effort: 1-2 days

---

## Gap 5: Physics Category Implementation

### The Problem

`physics_category` is defined but doesn't drive physics calculations:

```python
# Current: All bodies treated the same
for body in bodies:
    vol += compute_volume(body)  # No category differentiation
```

**Should be:**
- `submerged`: Added mass, wave radiation damping, no waterplane
- `surface_piercing`: Normal hydrostatics, waterplane contribution
- `above_water`: Weight only, no buoyancy

### The Solution

```python
# magnet/physics/category_physics.py

from dataclasses import dataclass
from typing import Optional

@dataclass
class CategoryPhysicsContribution:
    """Physics contribution based on body category."""
    
    # Buoyancy
    contributes_buoyancy: bool
    buoyancy_m3: float
    
    # Waterplane (stability)
    contributes_waterplane: bool
    waterplane_area_m2: float
    waterplane_inertia_m4: float
    
    # Added mass (seakeeping)
    added_mass_coefficient: float  # For surge/sway/heave
    
    # Wave damping
    wave_damping_coefficient: float
    
    # Air resistance
    contributes_windage: bool
    projected_area_m2: float


class PhysicsBehavior(Enum):
    """Inferred physics behavior from geometry."""
    FULLY_SUBMERGED = "fully_submerged"
    SURFACE_PIERCING = "surface_piercing"
    ABOVE_WATER = "above_water"
    PARTIALLY_SUBMERGED = "partially_submerged"


def infer_physics_behavior(
    body_geometry: 'HullGeometry',
    waterline_z: float,
) -> PhysicsBehavior:
    """
    GEOMETRY-DRIVEN: Infer physics behavior from actual geometry position.
    
    This makes physics_category a HINT that the kernel VERIFIES against geometry,
    rather than blindly trusting the agent's category string.
    """
    volume_below = compute_body_volume_below_wl(body_geometry, waterline_z)
    volume_total = compute_body_volume(body_geometry)
    
    if volume_total <= 0:
        return PhysicsBehavior.ABOVE_WATER
    
    submergence_ratio = volume_below / volume_total
    
    if submergence_ratio > 0.99:
        return PhysicsBehavior.FULLY_SUBMERGED
    elif submergence_ratio > 0.01:
        if submergence_ratio > 0.5:
            return PhysicsBehavior.SURFACE_PIERCING
        else:
            return PhysicsBehavior.PARTIALLY_SUBMERGED
    else:
        return PhysicsBehavior.ABOVE_WATER


def compute_category_contribution(
    body_config: 'BodyConfig',
    body_geometry: 'HullGeometry',
    draft_m: float,
    waterline_z: float = 0.0,
) -> CategoryPhysicsContribution:
    """
    Compute physics contribution by DERIVING behavior from geometry.
    
    The agent's physics_category is a HINT, but we VERIFY against actual geometry.
    This prevents garbage-in-garbage-out when agents hallucinate categories.
    """
    # DERIVE actual behavior from geometry (don't trust agent category blindly)
    actual_behavior = infer_physics_behavior(body_geometry, waterline_z)
    
    # Log if agent's hint differs from geometry (useful for debugging)
    agent_hint = body_config.physics_category.lower()
    # (In production: log discrepancy if agent_hint doesn't match actual_behavior)
    
    # Compute based on ACTUAL geometry position
    volume_below = compute_body_volume_below_wl(body_geometry, draft_m)
    volume_total = compute_body_volume(body_geometry)
    submergence_ratio = volume_below / volume_total if volume_total > 0 else 0
    
    if actual_behavior == PhysicsBehavior.FULLY_SUBMERGED:
        return CategoryPhysicsContribution(
            contributes_buoyancy=True,
            buoyancy_m3=volume_total,  # Entire volume contributes
            contributes_waterplane=False,
            waterplane_area_m2=0.0,
            waterplane_inertia_m4=0.0,
            added_mass_coefficient=0.9,
            wave_damping_coefficient=0.1,
            contributes_windage=False,
            projected_area_m2=0.0,
        )
    
    elif actual_behavior == PhysicsBehavior.SURFACE_PIERCING:
        wp_area = compute_body_waterplane_area(body_geometry, draft_m)
        wp_inertia = compute_body_waterplane_inertia(body_geometry, draft_m)
        
        return CategoryPhysicsContribution(
            contributes_buoyancy=True,
            buoyancy_m3=volume_below,
            contributes_waterplane=True,
            waterplane_area_m2=wp_area,
            waterplane_inertia_m4=wp_inertia,
            added_mass_coefficient=0.5,
            wave_damping_coefficient=0.3,
            contributes_windage=True,
            projected_area_m2=compute_above_water_projection(body_geometry, draft_m),
        )
    
    elif actual_behavior == PhysicsBehavior.ABOVE_WATER:
        return CategoryPhysicsContribution(
            contributes_buoyancy=False,
            buoyancy_m3=0.0,
            contributes_waterplane=False,
            waterplane_area_m2=0.0,
            waterplane_inertia_m4=0.0,
            added_mass_coefficient=0.0,
            wave_damping_coefficient=0.0,
            contributes_windage=True,
            projected_area_m2=compute_body_frontal_area(body_geometry),
        )
    
    else:  # PARTIALLY_SUBMERGED
        wp_area = compute_body_waterplane_area(body_geometry, draft_m) if submergence_ratio > 0.1 else 0
        wp_inertia = compute_body_waterplane_inertia(body_geometry, draft_m) if submergence_ratio > 0.1 else 0
        
        return CategoryPhysicsContribution(
            contributes_buoyancy=True,
            buoyancy_m3=volume_below,
            contributes_waterplane=submergence_ratio > 0.1,
            waterplane_area_m2=wp_area,
            waterplane_inertia_m4=wp_inertia,
            added_mass_coefficient=0.7 * submergence_ratio,
            wave_damping_coefficient=0.2 * (1 - submergence_ratio),
            contributes_windage=submergence_ratio < 0.9,
            projected_area_m2=compute_above_water_projection(body_geometry, draft_m),
        )
```

### Files to Create/Modify

| File | Change |
|:-----|:-------|
| `magnet/physics/category_physics.py` | **NEW FILE** — implementation above |
| `magnet/physics/multi_body_hydrostatics.py` | Use category contributions |
| `magnet/stability/intact_gm.py` | Use category contributions |

### Effort: 2-3 days

---

## Gap 6: Novelty Detection

### The Problem

How does the kernel know when a form is "too novel" for empirical methods?

### The Solution

```python
# magnet/physics/novelty_detector.py

from dataclasses import dataclass
from typing import List, Dict

# CONFIGURABLE WEIGHTS: Calibrate against model test validation studies
# These defaults are based on engineering judgment
NOVELTY_WEIGHTS = {
    "geometry": 0.4,       # Form coefficient deviations from validated range
    "configuration": 0.35, # Body arrangement novelty
    "regime": 0.25,        # Operating regime (Froude number, physics category)
}
# TODO: Calibrate weights against model test database when available


@dataclass
class NoveltyAssessment:
    """Assessment of how novel a form is relative to validated methods."""
    
    novelty_score: float  # 0.0 = conventional, 1.0 = completely novel
    
    # Breakdown
    geometry_novelty: float      # Based on form coefficients
    configuration_novelty: float # Based on body arrangement
    regime_novelty: float        # Based on Froude number / physics category
    
    # Specific flags
    outside_holtrop_envelope: bool
    outside_savitsky_envelope: bool
    outside_any_envelope: bool
    
    # Recommendations
    trusted_methods: List[str]
    untrusted_methods: List[str]
    recommendation: str


def assess_novelty(
    form_coefficients: 'FormCoefficients',
    multi_body_form: 'MultiBodyFormParameters',
    froude_number: float,
    physics_categories: List[str],
) -> NoveltyAssessment:
    """
    Assess how novel a design is relative to empirical method databases.
    
    Empirical methods were calibrated on specific hull forms:
    - Holtrop-Mennen: BSRA Series 60 (conventional displacement)
    - Savitsky: Prismatic planing hulls
    - Insel-Molland: Slender catamaran demihulls
    
    Designs outside these envelopes get high novelty scores.
    """
    
    # Geometry novelty (form coefficients outside typical ranges)
    geometry_issues = []
    
    if form_coefficients.cb < 0.35 or form_coefficients.cb > 0.85:
        geometry_issues.append(f"Cb={form_coefficients.cb:.2f} unusual")
    
    if form_coefficients.cp < 0.55 or form_coefficients.cp > 0.85:
        geometry_issues.append(f"Cp={form_coefficients.cp:.2f} unusual")
    
    if form_coefficients.cwp < 0.65 or form_coefficients.cwp > 0.95:
        geometry_issues.append(f"Cwp={form_coefficients.cwp:.2f} unusual")
    
    geometry_novelty = min(1.0, len(geometry_issues) * 0.25)
    
    # Configuration novelty
    config_issues = []
    
    if multi_body_form.body_count > 3:
        config_issues.append(f"{multi_body_form.body_count} bodies (no empirical data)")
    
    if multi_body_form.body_count == 2 and multi_body_form.lb_demihull < 7:
        config_issues.append("Non-slender catamaran demihulls")
    
    if "submerged" in physics_categories and "surface_piercing" in physics_categories:
        config_issues.append("Mixed submerged/surface-piercing (SWATH-like)")
    
    configuration_novelty = min(1.0, len(config_issues) * 0.35)
    
    # Regime novelty
    regime_issues = []
    
    if 0.4 < froude_number < 1.0:
        regime_issues.append(f"Fn={froude_number:.2f} in hump region")
    
    if froude_number > 2.0:
        regime_issues.append(f"Fn={froude_number:.2f} very high speed")
    
    regime_novelty = min(1.0, len(regime_issues) * 0.4)
    
    # Combined score (weighted)
    # NOTE: Weights are configurable and should be calibrated against model test database
    # Default weights based on engineering judgment — adjust per validation studies
    novelty_score = (
        NOVELTY_WEIGHTS["geometry"] * geometry_novelty +
        NOVELTY_WEIGHTS["configuration"] * configuration_novelty +
        NOVELTY_WEIGHTS["regime"] * regime_novelty
    )
    
    # Envelope checks
    outside_holtrop = (
        froude_number > 0.55 or
        multi_body_form.body_count > 1 or
        multi_body_form.lb_overall < 3 or
        multi_body_form.lb_overall > 15 or
        form_coefficients.cp < 0.55 or
        form_coefficients.cp > 0.85
    )
    
    outside_savitsky = (
        froude_number < 1.0 or
        multi_body_form.body_count > 1
    )
    
    # Determine trusted methods
    trusted = []
    untrusted = []
    
    if not outside_holtrop:
        trusted.append("Holtrop-Mennen")
    else:
        untrusted.append("Holtrop-Mennen")
    
    if not outside_savitsky:
        trusted.append("Savitsky")
    else:
        untrusted.append("Savitsky")
    
    if multi_body_form.body_count == 2 and froude_number < 0.9 and multi_body_form.lb_demihull >= 7:
        trusted.append("Insel-Molland (catamaran)")
    else:
        untrusted.append("Insel-Molland")
    
    # Recommendation
    if novelty_score < 0.3:
        recommendation = "Conventional form — empirical methods reliable"
    elif novelty_score < 0.6:
        recommendation = "Moderately novel — empirical results have increased uncertainty (±25%)"
    elif novelty_score < 0.8:
        recommendation = "Novel form — recommend model test or CFD validation"
    else:
        recommendation = "Highly novel — no validated method, CFD/model test required"
    
    return NoveltyAssessment(
        novelty_score=novelty_score,
        geometry_novelty=geometry_novelty,
        configuration_novelty=configuration_novelty,
        regime_novelty=regime_novelty,
        outside_holtrop_envelope=outside_holtrop,
        outside_savitsky_envelope=outside_savitsky,
        outside_any_envelope=outside_holtrop and outside_savitsky,
        trusted_methods=trusted,
        untrusted_methods=untrusted,
        recommendation=recommendation,
    )
```

### Files to Create

| File | Change |
|:-----|:-------|
| `magnet/physics/novelty_detector.py` | **NEW FILE** — implementation above |

### Effort: 2 days

---

## Implementation Priority

| Priority | Gap | What | Effort | Why First |
|:---------|:----|:-----|:-------|:----------|
| **P0** | Gap 1 | Multi-body hydrostatics (BM/GM) | 3-4 days | Catamarans are WRONG without this |
| **P0** | Gap 4 | Multi-body form parameters | 1-2 days | Needed for all physics |
| **P0** | Gap 6 | Novelty detection | 2 days | Honest uncertainty |
| **P1** | Gap 1.5 | Multi-body GZ curve | 3-4 days | Regulatory compliance |
| **P1** | Gap 2 | Form coefficient derivation | 3-5 days | Resistance needs this |
| **P1** | Gap 3 | Resistance method selection + Insel-Molland | 5-7 days | Catamaran resistance with interference |
| **P1** | Gap 5 | Physics category (geometry-derived) | 2-3 days | SWATH, mixed forms |

**Total: 19-27 days**

---

## Honest Physics Validation Contract

### What ALWAYS Works (Geometry-Based)

These are computed from raw geometry with no form assumptions:

| Calculation | Method | Confidence |
|:------------|:-------|:-----------|
| Displacement | Volume integral below WL | 99% |
| LCB, VCB | Centroid of displaced volume | 99% |
| Waterplane area | Surface integral at WL | 99% |
| BM (single hull) | I_wp / V | 98% |
| BM (multi-body) | Parallel axis theorem | 95% |
| GM | KB + BM - KG | 95% |

### What Requires Form Classification (Empirical)

These methods return garbage for novel forms:

| Calculation | Method | Valid For | Invalid For |
|:------------|:-------|:----------|:------------|
| Resistance | Holtrop-Mennen | Displacement mono, Fn<0.55 | Multi-body, high Fn, unusual Cp |
| Resistance | Savitsky | Planing mono, Fn>1.0 | Non-planing, multi-body |
| Resistance | Insel-Molland | Catamaran, Fn<0.9 | Non-catamaran, high Fn |
| Seakeeping | Strip theory | Slender ships | Wide bodies, SWATH |

### What Doesn't Exist Yet

For these, the kernel returns: **"No validated method available"**

- Trimaran resistance with interference
- SWATH resistance (needs custom implementation)
- Hydrofoil lift and drag
- Surface effect ship
- Novel configuration stability (coupling effects)
- Planing catamaran resistance
- Asymmetric multi-body

---

## Correction to Other Documents

### Design Language Spec

**Remove/modify these claims:**

| Line | Current Claim | Correction |
|:-----|:--------------|:-----------|
| 166 | "EXISTING DOWNSTREAM PIPELINE (unchanged)" | "DOWNSTREAM PIPELINE (modified for multi-body)" |
| 187 | "Feed to existing pipeline" | "Feed to pipeline (multi-body requires new code)" |
| 3285 | "unchanged" | "requires multi-body extensions" |

### Unified Implementation Plan

**Add physics gap acknowledgment in architecture section.**

### Failure Modes Document

**Already covers some of this in "Empirical Methods Break" — cross-reference this document.**

---

## Appendix A: Required Helper Functions

All implementations above reference these helper functions. They must be implemented:

### Geometry Extraction

```python
def extract_body_geometry(geometry: 'HullGeometry', body_id: str) -> 'HullGeometry':
    """Extract geometry for a single body from multi-body vessel."""
    ...

def get_sections_for_body(geometry: 'HullGeometry', body_id: Optional[str]) -> List['HullSection']:
    """Get sections belonging to a specific body."""
    ...

def rotate_geometry_around_x(geometry: 'HullGeometry', angle_rad: float) -> 'HullGeometry':
    """Rotate geometry around longitudinal (X) axis for heeled calculations."""
    ...
```

### Volume/Area Computations

```python
def compute_body_volume(body_geometry: 'HullGeometry') -> float:
    """Compute total volume of a body."""
    ...

def compute_body_volume_below_wl(body_geometry: 'HullGeometry', waterline_z: float) -> float:
    """Compute volume of body below specified waterline."""
    ...

def compute_body_waterplane_area(body_geometry: 'HullGeometry', waterline_z: float) -> float:
    """Compute waterplane area at specified waterline."""
    ...

def compute_body_waterplane_inertia(body_geometry: 'HullGeometry', waterline_z: float) -> float:
    """Compute waterplane moment of inertia about centerline."""
    ...

def compute_body_waterplane_inertia_xx(body_geometry: 'HullGeometry', draft_m: float) -> float:
    """Compute transverse (roll) waterplane inertia."""
    ...

def compute_body_waterplane_inertia_yy(body_geometry: 'HullGeometry', draft_m: float) -> float:
    """Compute longitudinal (pitch) waterplane inertia."""
    ...
```

### Center Computations

```python
def compute_body_lcb(body_geometry: 'HullGeometry', draft_m: float) -> float:
    """Compute longitudinal center of buoyancy."""
    ...

def compute_body_vcb(body_geometry: 'HullGeometry', draft_m: float) -> float:
    """Compute vertical center of buoyancy."""
    ...

def compute_body_cb_position(body_geometry: 'HullGeometry', waterline_z: float) -> Tuple[float, float]:
    """Compute center of buoyancy position (y, z) in section plane."""
    ...

def compute_lcf(sections: List['HullSection'], draft_m: float) -> float:
    """Compute longitudinal center of floatation."""
    ...
```

### Dimension Computations

```python
def compute_overall_loa(geometry: 'HullGeometry') -> float:
    """Compute overall length of vessel."""
    ...

def compute_body_lwl(body_geometry: 'HullGeometry', draft_m: float) -> float:
    """Compute waterline length for a body."""
    ...

def compute_lwl(sections: List['HullSection'], draft_m: float) -> float:
    """Compute waterline length from sections."""
    ...

def compute_body_beam_at_wl(body_geometry: 'HullGeometry', draft_m: float) -> float:
    """Compute maximum beam at waterline for a body."""
    ...

def compute_max_beam_at_waterline(sections: List['HullSection'], draft_m: float) -> float:
    """Compute maximum beam at waterline from sections."""
    ...

def compute_body_frontal_area(body_geometry: 'HullGeometry') -> float:
    """Compute frontal projected area (for windage)."""
    ...

def compute_above_water_projection(body_geometry: 'HullGeometry', draft_m: float) -> float:
    """Compute above-water projected area."""
    ...
```

### Section Integration

```python
def integrate_waterplane_area(sections: List['HullSection'], draft_m: float) -> float:
    """Integrate waterplane area from sections."""
    ...

def find_midship_section(
    sections: List['HullSection'], 
    draft_m: float
) -> Tuple[float, float]:
    """Find midship section (maximum area) and return (area, station)."""
    ...
```

### Froude Number

```python
def compute_froude_number(speed_kts: float, lwl_m: float) -> float:
    """Compute Froude number from speed and waterline length."""
    speed_ms = speed_kts * 0.5144
    return speed_ms / (9.81 * lwl_m) ** 0.5 if lwl_m > 0 else 0
```

### Notes

- Most of these exist in `magnet/hull_gen/geometry.py` or `magnet/analysis/hydrostatics.py`
- Some need extension for multi-body support
- Waterplane operations need waterline intersection logic

---

## Version History

| Version | Date | Changes |
|:--------|:-----|:--------|
| 1.0 | 2026-01-05 | Initial specification identifying 6 physics gaps with solutions |
| 1.1 | 2026-01-05 | **Critical fixes:** Geometry-derived physics behavior (not enum), GZ curve for multi-body, Insel-Molland interference factor, crude estimate for unknown forms, NURBS section area integration, configurable novelty weights, helper function appendix |
| 1.2 | 2026-01-05 | **ENUM REMOVAL**: Replaced `config = "catamaran"/"trimaran"` labeling with generic `config = f"multi_body_{n}"` to prevent design terminology from creeping into physics code |

---

## Related Documents

| Document | Purpose |
|:---------|:--------|
| `MAGNET_Design_Language_Spec_v1.0.md` | Language that generates geometry requiring physics validation |
| `MAGNET_Implementation_Spec.md` | API contracts showing physics validation responses |
| `MAGNET_Failure_Modes_And_Mitigations.md` | Failure mode analysis (empirical methods breaking) |
| `MAGNET_Implementation_Guide.md` | **START HERE:** Step-by-step implementation roadmap with code |

