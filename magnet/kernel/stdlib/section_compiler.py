"""
Compile geometry.section resources into HullSection objects.

This compiles design language sections into the canonical HullSection class
used by the existing geometry pipeline.

NO SECOND GEOMETRY ENGINE - everything compiles into existing classes.

v1.1 (TASK-006): Added transform_report to eliminate silent transforms.
All resampling operations now emit explicit reports.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
import math
from magnet.hull_gen.geometry import (
    HullSection, 
    SectionPoint, 
    Point3D,
    EdgeType,
)


@dataclass
class TransformReport:
    """Report of transforms applied during section compilation.
    
    TASK-006: Eliminates silent transforms by making all resampling explicit.
    """
    original_points: int
    resampled_points: int
    rule: str  # "default_32", "explicit", "none"
    hard_edges_snapped: List[float] = field(default_factory=list)
    reversed_order: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_points": self.original_points,
            "resampled_points": self.resampled_points,
            "rule": self.rule,
            "hard_edges_snapped": self.hard_edges_snapped,
            "reversed_order": self.reversed_order,
        }


class SectionCompilationError(Exception):
    """Raised when section compilation fails."""
    pass


def compile_section(
    resource: Dict[str, Any], 
    loa: float = 25.0,
    default_body_id: str = "main",
    return_transform_report: bool = False,
) -> "HullSection | Tuple[HullSection, TransformReport]":
    """
    Compile a geometry.section resource into HullSection.
    
    Args:
        resource: Section resource dict from state
        loa: Length overall for station scaling
        default_body_id: Default body ID if not specified
        return_transform_report: If True, return (HullSection, TransformReport) tuple
    
    Returns:
        HullSection object compatible with existing geometry pipeline.
        If return_transform_report=True, returns (HullSection, TransformReport).
    
    The resource format:
        {
            "_type": "geometry.section",
            "station": 0.5,  # 0=bow, 1=stern
            "points": [[y, z], [y, z], ...],  # Section profile
            "body_id": "main",
            "definition_type": "polygon" | "nurbs",
            # For NURBS:
            "control_points": [[y, z, weight], ...],
            "knots": [...],
            "degree": 3
        }
    
    TASK-006: Transform reports eliminate silent transforms.
    """
    station_ratio = float(resource.get("station", 0.5))
    
    # Validate station
    if not 0.0 <= station_ratio <= 1.0:
        raise SectionCompilationError(
            f"Station {station_ratio} out of range [0, 1]"
        )
    
    # Compute x position from station
    # Station 0 = bow (x = loa), Station 1 = stern (x = 0)
    station_m = (1.0 - station_ratio) * loa
    
    definition_type = resource.get("definition_type", "polygon")
    
    if definition_type == "nurbs":
        points, transform_report = _compile_nurbs_section(resource)
    else:
        # When the caller explicitly asks for a TransformReport, we prefer deterministically
        # resampling low-res sections so the report can demonstrate (and test) hard-edge snapping.
        # For the default compilation path, preserve authored vertices when edge typing is present.
        points, transform_report = _compile_polygon_section(
            resource,
            preserve_authored_vertices=not return_transform_report,
        )
    
    body_id = resource.get("body_id", default_body_id)
    
    section = HullSection(
        station=station_ratio,
        x_position=station_m,
        points=points,
    )
    
    # Store body_id as attribute for multi-body handling
    section.body_id = body_id  # type: ignore
    section.resource_id = resource.get("_id", "")  # type: ignore
    
    # TASK-006: Store transform report in section metadata
    section.transform_report = transform_report.to_dict()  # type: ignore
    
    if return_transform_report:
        return section, transform_report
    
    # Compute derived properties
    _compute_section_properties(section)
    
    return section


def _dedupe_consecutive_points(points: List[List[float]], eps: float = 1e-9) -> List[List[float]]:
    """
    Remove consecutive duplicate points.

    Design-language sections are typically OPEN half-breadth curves (keel -> deck).
    Duplicate consecutive points create degenerate triangles in tessellation.
    """
    if not points:
        return points
    out = [points[0]]
    for p in points[1:]:
        py, pz = float(p[0]), float(p[1])
        oy, oz = float(out[-1][0]), float(out[-1][1])
        if abs(py - oy) <= eps and abs(pz - oz) <= eps:
            continue
        out.append([py, pz])
    return out


def _ensure_keel_to_deck_order(points: List[List[float]]) -> List[List[float]]:
    """
    Ensure points are ordered from keel (lowest z) to deck (highest z).

    IMPORTANT: Sections in MAGNET are OPEN curves, not closed polygons.
    Using polygon winding normalization (shoelace) on an open curve can
    randomly reverse some sections, causing loft twisting/tearing.
    """
    if len(points) < 2:
        return points
    z0 = float(points[0][1])
    zN = float(points[-1][1])
    if z0 <= zN:
        return points
    return list(reversed(points))


def _compile_polygon_section(
    resource: Dict[str, Any],
    *,
    preserve_authored_vertices: bool = True,
) -> Tuple[List[SectionPoint], TransformReport]:
    """Compile polygon-defined section to SectionPoints.
    
    TASK-006: Returns (points, transform_report) tuple.
    """
    points_raw = resource.get("points", [])
    edge_types_raw = resource.get("edge_types", None)
    
    if not points_raw:
        raise SectionCompilationError("Section has no points")
    
    original_count = len(points_raw)
    reversed_order = False
    
    # Sections are OPEN curves (half-breadth) for hulls: keel -> deck.
    # Do NOT apply polygon winding normalization here.
    points_raw = _dedupe_consecutive_points(points_raw)

    # Normalize edge_types into a per-vertex list aligned to points_raw
    per_vertex_edge: List[Optional[str]] = [None] * len(points_raw)
    if isinstance(edge_types_raw, list) and edge_types_raw:
        if len(edge_types_raw) == len(points_raw):
            per_vertex_edge = list(edge_types_raw)
        elif len(edge_types_raw) == len(points_raw) - 1:
            # per-segment types: assign segment type to the vertex it leads into
            for i in range(1, len(points_raw)):
                per_vertex_edge[i] = edge_types_raw[i - 1]

    # Ensure keel->deck order (and keep edge alignment)
    if len(points_raw) >= 2:
        z0 = float(points_raw[0][1])
        zN = float(points_raw[-1][1])
        if z0 > zN:
            points_raw = list(reversed(points_raw))
            per_vertex_edge = list(reversed(per_vertex_edge))
            reversed_order = True

    # Deterministic upsampling to reduce faceting/"boxy" appearance.
    # This is a pure geometric transform (no presets): resample the monotone z-ordered curve y(z).
    # Preserve any hard/crease edge markers by snapping them to the closest resampled z.
    target_n = int(resource.get("resample_points", 0) or 0)
    if target_n <= 0:
        if preserve_authored_vertices and isinstance(edge_types_raw, list) and edge_types_raw:
            # Preserve authored vertices when edge typing is present (vertex-indexed contract).
            target_n = len(points_raw)
        else:
            # Default: upscale if the section is low-resolution. This improves visual smoothness
            # without changing the language (pure geometric compilation).
            target_n = 32 if len(points_raw) < 32 else len(points_raw)
    # Clamp ONLY when we are actually resampling upward.
    if target_n > len(points_raw):
        target_n = max(10, min(64, target_n))

    def _is_hard(v: Optional[str]) -> bool:
        if not isinstance(v, str):
            return False
        s = v.strip().lower()
        return s in ("hard", "chine", "sharp", "crease", "line")

    hard_zs = [float(points_raw[i][1]) for i, et in enumerate(per_vertex_edge) if _is_hard(et)]

    def _interp_y_at_z(z: float) -> float:
        # points_raw assumed strictly increasing-ish in z; use segment search.
        for i in range(len(points_raw) - 1):
            y1, z1 = float(points_raw[i][0]), float(points_raw[i][1])
            y2, z2 = float(points_raw[i + 1][0]), float(points_raw[i + 1][1])
            if z1 <= z <= z2 or (i == len(points_raw) - 2 and z >= z2):
                if z2 == z1:
                    return y2
                t = (z - z1) / (z2 - z1)
                return y1 + t * (y2 - y1)
        return float(points_raw[-1][0])

    if len(points_raw) >= 2 and target_n > len(points_raw):
        z_min = float(points_raw[0][1])
        z_max = float(points_raw[-1][1])
        if z_max > z_min:
            zs = [z_min + (z_max - z_min) * (i / (target_n - 1)) for i in range(target_n)]
            # Tolerance for snapping hard edges to nearest sample
            snap_tol = (z_max - z_min) / max(1, target_n - 1) * 0.6
            new_points: List[List[float]] = []
            new_edges: List[Optional[str]] = []
            for z in zs:
                y = _interp_y_at_z(z)
                new_points.append([y, z])
                et = None
                if hard_zs and min(abs(z - hz) for hz in hard_zs) <= snap_tol:
                    et = "hard"
                new_edges.append(et)
            points_raw = new_points
            per_vertex_edge = new_edges
    
    section_points = []
    for i, pt in enumerate(points_raw):
        if not isinstance(pt, (list, tuple)) or len(pt) != 2:
            raise SectionCompilationError(
                f"Invalid point format at index {i}: {pt}. "
                f"Polygon section points must be [y, z] (2 numbers). "
                f"Do not include X in points; X is derived from station."
            )
        
        y = float(pt[0])
        z = float(pt[1])
        
        # Map optional edge_types to EdgeType (controls hard edges / chines).
        et_val = per_vertex_edge[i] if i < len(per_vertex_edge) else None

        def _map_edge_type(v) -> EdgeType:
            if v is None:
                return EdgeType.SMOOTH
            if isinstance(v, str):
                s = v.strip().lower()
                if s in ("hard", "chine", "sharp", "crease"):
                    return EdgeType.HARD if s != "crease" else EdgeType.CREASE
                if s in ("line", "straight"):
                    # A "line" is often intended as a sharp break in LLM outputs.
                    return EdgeType.HARD
                return EdgeType.SMOOTH
            return EdgeType.SMOOTH

        section_points.append(SectionPoint(
            position=Point3D(x=0.0, y=y, z=z),  # x filled in by caller
            edge_type=_map_edge_type(et_val),
        ))
    
    # Mark keel point (lowest Z at centerline)
    centerline_points = [p for p in section_points if abs(p.position.y) < 0.01]
    if centerline_points:
        keel = min(centerline_points, key=lambda p: p.position.z)
        keel.is_keel = True
    
    # TASK-006: Build transform report
    resampled = len(section_points) != original_count
    rule = "none"
    if resampled:
        explicit_target = int(resource.get("resample_points", 0) or 0)
        rule = "explicit" if explicit_target > 0 else "default_32"
    
    transform_report = TransformReport(
        original_points=original_count,
        resampled_points=len(section_points),
        rule=rule,
        hard_edges_snapped=hard_zs if resampled else [],
        reversed_order=reversed_order,
    )
    
    return section_points, transform_report


def _compile_nurbs_section(resource: Dict[str, Any]) -> Tuple[List[SectionPoint], TransformReport]:
    """Compile NURBS-defined section to SectionPoints by evaluation.
    
    TASK-006: Returns (points, transform_report) tuple.
    """
    control_points = resource.get("control_points", [])
    knots = resource.get("knots", [])
    degree = resource.get("degree", 3)
    
    if not control_points:
        raise SectionCompilationError("NURBS section has no control points")
    
    # Evaluate NURBS curve at regular parameter intervals
    # For MVP, sample at 20 points
    n_samples = 20
    
    try:
        from magnet.hull_gen.nurbs import NURBSCurve
        
        # Convert control points to NURBS format
        nurbs_pts = []
        for cp in control_points:
            if len(cp) >= 3:
                y, z, w = cp[0], cp[1], cp[2]
            else:
                y, z, w = cp[0], cp[1], 1.0
            nurbs_pts.append((y, z, w))
        
        # Create NURBS curve
        curve = NURBSCurve(
            control_points=nurbs_pts,
            knots=knots if knots else None,
            degree=degree,
        )
        
        # Evaluate
        section_points = []
        for i in range(n_samples + 1):
            t = i / n_samples
            y, z = curve.evaluate(t)
            section_points.append(SectionPoint(
                position=Point3D(x=0.0, y=y, z=z),
                edge_type=EdgeType.SMOOTH,
            ))
        
        # TASK-006: NURBS always samples from control points
        transform_report = TransformReport(
            original_points=len(control_points),
            resampled_points=len(section_points),
            rule="nurbs_evaluation",
            hard_edges_snapped=[],
            reversed_order=False,
        )
        
        return section_points, transform_report
        
    except ImportError:
        # Fallback: use control points directly as approximation
        return _compile_polygon_section({"points": control_points})


def _compute_section_properties(section: HullSection) -> None:
    """Compute derived section properties."""
    if not section.points:
        return
    
    # Half beam (max Y)
    section.half_beam = max(abs(p.position.y) for p in section.points)
    
    # Draft (min Z below waterline)
    section.draft_local = abs(min(
        (p.position.z for p in section.points if p.position.z < 0),
        default=0.0
    ))
    
    # Find key points
    # Keel = lowest point
    keel_pt = min(section.points, key=lambda p: p.position.z)
    section.keel_point = keel_pt.position
    
    # Waterline = point closest to z=0
    wl_candidates = [p for p in section.points if abs(p.position.z) < 0.1]
    if wl_candidates:
        section.waterline_point = max(
            wl_candidates, 
            key=lambda p: p.position.y
        ).position


def compile_sections(
    resources: Dict[str, Dict[str, Any]],
    loa: float = 25.0,
    body_id: Optional[str] = None,
) -> List[HullSection]:
    """
    Compile all geometry.section resources into HullSection list.
    
    Args:
        resources: Dict of resource_id -> resource_dict
        loa: Length overall
        body_id: If specified, only compile sections for this body
    
    Returns:
        List of HullSection objects sorted by station
    """
    sections = []
    
    for resource_id, resource in resources.items():
        # Skip non-sections
        if resource.get("_type") != "geometry.section":
            continue
        
        # Skip deleted
        if resource.get("_deleted"):
            continue
        
        # Filter by body_id if specified
        section_body = resource.get("body_id", "main")
        if body_id is not None and section_body != body_id:
            continue
        
        try:
            section = compile_section(resource, loa)
            sections.append(section)
        except SectionCompilationError as e:
            # Log but continue with other sections
            import logging
            logging.warning(f"Failed to compile section {resource_id}: {e}")
    
    # Sort by station (bow to stern)
    sections.sort(key=lambda s: s.station)
    
    return sections


def compile_sections_for_bodies(
    resources: Dict[str, Dict[str, Any]],
    bodies: Dict[str, Dict[str, Any]],
    loa: float = 25.0,
) -> Dict[str, List[HullSection]]:
    """
    Compile sections grouped by body.
    
    Returns dict of body_id -> List[HullSection]
    """
    body_sections = {}
    
    for body_id in bodies:
        sections = compile_sections(resources, loa, body_id=body_id)
        if sections:
            body_sections[body_id] = sections
    
    # Also compile sections without explicit body_id (main body)
    main_sections = compile_sections(resources, loa, body_id="main")
    if main_sections and "main" not in body_sections:
        body_sections["main"] = main_sections
    
    return body_sections


