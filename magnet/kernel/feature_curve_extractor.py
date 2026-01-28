"""
Feature curve extraction from compiled hull sections.

Extracts key geometric feature curves (stem, transom, sheer, chine, keel) 
during kernel compilation for use by character observables.

Contract:
- All curves are derived, never authored
- Curves are deterministic for a fixed set of sections
- If insufficient data, return empty list (downstream measurers return None)
- No dependency on WebGL/tessellation (kernel-only)
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from magnet.hull_gen.geometry import Point3D, HullSection


def extract_feature_curves(
    sections: List[HullSection],
    *,
    loa: Optional[float] = None,
) -> Dict[str, List[Point3D]]:
    """
    Extract all feature curves from compiled hull sections.
    
    Args:
        sections: Compiled hull sections (sorted by x_position)
        loa: Length overall (optional, for validation)
    
    Returns:
        Dict with keys: stem_profile, transom_outline, sheer_line, chine_line, keel_line
        Each value is a List[Point3D] (may be empty if insufficient data)
    """
    if not sections:
        return {
            "stem_profile": [],
            "transom_outline": [],
            "sheer_line": [],
            "chine_line": [],
            "keel_line": [],
        }
    
    # Sort sections by x_position (should already be sorted, but ensure)
    sorted_sections = sorted(sections, key=lambda s: float(s.x_position))
    
    return {
        "stem_profile": extract_stem_profile(sorted_sections),
        "transom_outline": extract_transom_outline(sorted_sections),
        "sheer_line": extract_sheer_line(sorted_sections),
        "chine_line": extract_chine_line(sorted_sections),
        "keel_line": extract_keel_line(sorted_sections),
    }


def extract_keel_line(sections: List[HullSection]) -> List[Point3D]:
    """
    Extract keel line: longitudinal curve of minimum z points.
    
    Returns: List[Point3D] with (x, 0, z) for each section
    """
    if len(sections) < 2:
        return []
    
    keel_points: List[Point3D] = []
    for section in sections:
        if not section.points:
            continue
        
        # Find minimum z point
        min_z = min(float(p.position.z) for p in section.points)
        x_m = float(section.x_position)
        
        keel_points.append(Point3D(x=x_m, y=0.0, z=min_z))
    
    return keel_points


def extract_sheer_line(sections: List[HullSection]) -> List[Point3D]:
    """
    Extract sheer line: longitudinal curve of maximum z points.
    
    Returns: List[Point3D] with (x, y, z) preserving outboard coordinate
    """
    if len(sections) < 2:
        return []
    
    sheer_points: List[Point3D] = []
    for section in sections:
        if not section.points:
            continue
        
        # Find maximum z point (preserve its y coordinate)
        max_pt = max(section.points, key=lambda p: float(p.position.z))
        x_m = float(section.x_position)
        
        sheer_points.append(Point3D(
            x=x_m,
            y=float(max_pt.position.y),
            z=float(max_pt.position.z),
        ))
    
    return sheer_points


def extract_chine_line(sections: List[HullSection]) -> List[Point3D]:
    """
    Extract chine line: longitudinal curve of chine-like anchor points.
    
    Uses knee detector (max slope change in dy/dz) to find chine.
    Preserves y coordinate for 3D chine planform.
    
    Returns: List[Point3D] with (x, y, z)
    """
    if len(sections) < 2:
        return []
    
    chine_points: List[Point3D] = []
    for section in sections:
        if not section.points or len(section.points) < 4:
            continue
        
        # Find chine-like point using knee detector
        chine_pt = _find_chine_anchor(section.points)
        if chine_pt is None:
            continue
        
        x_m = float(section.x_position)
        chine_points.append(Point3D(
            x=x_m,
            y=float(chine_pt.position.y),
            z=float(chine_pt.position.z),
        ))
    
    return chine_points


def extract_transom_outline(sections: List[HullSection]) -> List[Point3D]:
    """
    Extract transom outline: 3D perimeter of aft-most section.
    
    Returns: List[Point3D] with (x, y, z) at constant x (aft x_position)
    """
    if not sections:
        return []
    
    # Aft-most section
    aft_section = min(sections, key=lambda s: float(s.x_position))
    
    if not aft_section.points:
        return []
    
    x_aft = float(aft_section.x_position)
    
    # Build transom outline preserving y and z
    outline_points: List[Point3D] = []
    for pt in aft_section.points:
        outline_points.append(Point3D(
            x=x_aft,
            y=float(pt.position.y),
            z=float(pt.position.z),
        ))
    
    return outline_points


def extract_stem_profile(sections: List[HullSection]) -> List[Point3D]:
    """
    Extract stem profile: x-z curve at centerline (y=0) in bow region.
    
    For section-based geometry (no mesh), use forward-most section's 
    centerline projection as a proxy.
    
    Returns: List[Point3D] with (x, 0, z)
    """
    if not sections:
        return []
    
    # Forward-most section
    fwd_section = max(sections, key=lambda s: float(s.x_position))
    
    if not fwd_section.points:
        return []
    
    # Use forward section points as stem profile proxy
    # (sorted by z for a coherent profile)
    x_fwd = float(fwd_section.x_position)
    
    stem_points: List[Point3D] = []
    for pt in sorted(fwd_section.points, key=lambda p: float(p.position.z)):
        stem_points.append(Point3D(
            x=x_fwd,
            y=0.0,  # Centerline projection
            z=float(pt.position.z),
        ))
    
    return stem_points


def _find_chine_anchor(points: List[Any]) -> Optional[Any]:
    """
    Find chine anchor point using knee detection (max slope change dy/dz).
    
    The chine is the geometric discontinuity between bottom and topside.
    Returns the point with maximum second derivative in the z-profile.
    
    Returns: SectionPoint at chine, or None if < 4 points
    """
    if len(points) < 4:
        return None
    
    # Sort by z ascending (keel to sheer)
    sorted_pts = sorted(points, key=lambda p: float(p.position.z))
    
    # Compute slope changes
    max_slope_change = 0.0
    chine_candidate = None
    
    for i in range(1, len(sorted_pts) - 1):
        p0 = sorted_pts[i - 1].position
        p1 = sorted_pts[i].position
        p2 = sorted_pts[i + 1].position
        
        y0, z0 = float(p0.y), float(p0.z)
        y1, z1 = float(p1.y), float(p1.z)
        y2, z2 = float(p2.y), float(p2.z)
        
        # Slopes before and after
        dy1, dz1 = y1 - y0, z1 - z0
        dy2, dz2 = y2 - y1, z2 - z1
        
        len1 = math.hypot(dy1, dz1)
        len2 = math.hypot(dy2, dz2)
        
        if len1 < 1e-9 or len2 < 1e-9:
            continue
        
        # Angle change (proxy for curvature)
        dot = (dy1 * dy2 + dz1 * dz2) / (len1 * len2)
        dot = max(-1.0, min(1.0, dot))
        angle_change = math.acos(dot)
        
        # Require point to be outboard enough (not just keel noise)
        ys = [float(p.position.y) for p in sorted_pts]
        max_y = max(ys) if ys else 0.0
        if float(p1.y) < 0.25 * max_y:
            continue
        
        if angle_change > max_slope_change:
            max_slope_change = angle_change
            chine_candidate = sorted_pts[i]
    
    # Require meaningful slope change (> 15°)
    if max_slope_change < math.radians(15):
        return None
    
    return chine_candidate


def smooth_polyline_c1(points: List[Point3D], *, window: int = 5) -> List[Point3D]:
    """
    Apply C1-continuous smoothing to a polyline.
    
    Uses simple moving average (deterministic, no scipy dependency).
    Preserves endpoints.
    
    Args:
        points: Input polyline
        window: Smoothing window size (must be odd)
    
    Returns: Smoothed polyline
    """
    if len(points) < window:
        return points  # Too few points to smooth
    
    # Ensure odd window
    if window % 2 == 0:
        window += 1
    
    half_w = window // 2
    
    smoothed: List[Point3D] = []
    
    for i in range(len(points)):
        if i < half_w or i >= len(points) - half_w:
            # Preserve endpoints
            smoothed.append(points[i])
            continue
        
        # Moving average
        x_sum = sum(points[j].x for j in range(i - half_w, i + half_w + 1))
        y_sum = sum(points[j].y for j in range(i - half_w, i + half_w + 1))
        z_sum = sum(points[j].z for j in range(i - half_w, i + half_w + 1))
        
        smoothed.append(Point3D(
            x=x_sum / window,
            y=y_sum / window,
            z=z_sum / window,
        ))
    
    return smoothed
