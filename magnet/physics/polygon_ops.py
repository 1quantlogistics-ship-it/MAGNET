"""
magnet/physics/polygon_ops.py - Deterministic polygon operations for hydrostatics.

This module is intentionally:
- Pure (no state_manager access)
- Deterministic (no random, stable ordering rules)
- Numeric-robust (tolerances centralized)

Coordinate convention:
- Operates on 2D vertices in the (y, z) plane, where:
  - y: transverse (m, positive port)
  - z: vertical (m, positive up from baseline)
"""

from __future__ import annotations

from typing import List, Tuple

from magnet.core.constants import EPSILON_GEOMETRY

Vertex2 = Tuple[float, float]  # (y, z)


def _nearly_equal(a: float, b: float, eps: float = EPSILON_GEOMETRY) -> bool:
    return abs(a - b) <= eps


def _vertex_nearly_equal(p: Vertex2, q: Vertex2, eps: float = EPSILON_GEOMETRY) -> bool:
    return _nearly_equal(p[0], q[0], eps) and _nearly_equal(p[1], q[1], eps)


def normalize_polygon(vertices: List[Vertex2]) -> List[Vertex2]:
    """
    Normalize a polygon for deterministic downstream calculations:
    - Remove consecutive near-duplicate vertices
    - Ensure closure (first == last)
    - Ensure CCW winding (positive signed area)

    Note: This function does NOT attempt self-intersection repair.
    """
    if not vertices:
        return []

    # Drop consecutive duplicates
    cleaned: List[Vertex2] = []
    for v in vertices:
        if not cleaned or not _vertex_nearly_equal(cleaned[-1], v):
            cleaned.append((float(v[0]), float(v[1])))

    if len(cleaned) < 3:
        return []

    # Ensure closure
    if not _vertex_nearly_equal(cleaned[0], cleaned[-1]):
        cleaned.append(cleaned[0])

    # Ensure CCW
    a = signed_area(cleaned)
    if a < 0:
        # Reverse but preserve closure semantics
        body = list(reversed(cleaned[:-1]))
        body.append(body[0])
        cleaned = body

    return cleaned


def signed_area(vertices: List[Vertex2]) -> float:
    """Signed area using shoelace formula. Positive => CCW."""
    if len(vertices) < 3:
        return 0.0
    area2 = 0.0
    n = len(vertices)
    for i in range(n - 1):
        y1, z1 = vertices[i]
        y2, z2 = vertices[i + 1]
        area2 += (y1 * z2) - (y2 * z1)
    return 0.5 * area2


def clip_polygon_z_le(vertices: List[Vertex2], z_max: float) -> List[Vertex2]:
    """
    Clip polygon against the half-plane z <= z_max using Sutherland–Hodgman.

    Returns a normalized polygon (closed, CCW) or [] if fully above waterline.
    """
    poly = normalize_polygon(vertices)
    if not poly:
        return []

    def inside(v: Vertex2) -> bool:
        return v[1] <= z_max + EPSILON_GEOMETRY

    def intersect(p1: Vertex2, p2: Vertex2) -> Vertex2:
        y1, z1 = p1
        y2, z2 = p2
        dz = z2 - z1
        if abs(dz) <= EPSILON_GEOMETRY:
            # Segment parallel to clip line; return endpoint on boundary
            return (y2, z_max)
        t = (z_max - z1) / dz
        y = y1 + t * (y2 - y1)
        return (y, z_max)

    output: List[Vertex2] = poly[:-1]  # work on open list
    clipped: List[Vertex2] = []

    if not output:
        return []

    s = output[-1]
    for e in output:
        if inside(e):
            if inside(s):
                clipped.append(e)
            else:
                clipped.append(intersect(s, e))
                clipped.append(e)
        else:
            if inside(s):
                clipped.append(intersect(s, e))
        s = e

    return normalize_polygon(clipped)


def polygon_area_centroid(vertices: List[Vertex2]) -> Tuple[float, float, float]:
    """
    Compute area and centroid (cy, cz) for a simple polygon using Green's theorem.

    Returns:
      (area >= 0, cy, cz)
    """
    poly = normalize_polygon(vertices)
    if not poly:
        return (0.0, 0.0, 0.0)

    a2 = 0.0
    cy6 = 0.0
    cz6 = 0.0
    for i in range(len(poly) - 1):
        y1, z1 = poly[i]
        y2, z2 = poly[i + 1]
        cross = (y1 * z2) - (y2 * z1)
        a2 += cross
        cy6 += (y1 + y2) * cross
        cz6 += (z1 + z2) * cross

    if abs(a2) <= EPSILON_GEOMETRY:
        return (0.0, 0.0, 0.0)

    area = 0.5 * a2
    # poly is CCW => area should be positive; still guard.
    if area < 0:
        area = -area
        cy6 = -cy6
        cz6 = -cz6

    cy = cy6 / (6.0 * area)
    cz = cz6 / (6.0 * area)
    return (area, cy, cz)


def polygon_second_moments(vertices: List[Vertex2]) -> Tuple[float, float, float]:
    """
    Compute second moments for polygon about origin:
      Iy = ∫ y^2 dA
      Iz = ∫ z^2 dA
      Iyz = ∫ y z dA

    Notes:
    - These are planar moments in the (y,z) plane.
    - Hydrostatics waterplane moments are computed separately along x; this is
      provided for section-level diagnostics and potential future use.
    """
    poly = normalize_polygon(vertices)
    if not poly:
        return (0.0, 0.0, 0.0)

    iy = 0.0
    iz = 0.0
    iyz = 0.0

    for i in range(len(poly) - 1):
        y1, z1 = poly[i]
        y2, z2 = poly[i + 1]
        cross = (y1 * z2) - (y2 * z1)

        iy += (y1 * y1 + y1 * y2 + y2 * y2) * cross
        iz += (z1 * z1 + z1 * z2 + z2 * z2) * cross
        iyz += (y1 * z2 + 2.0 * y1 * z1 + 2.0 * y2 * z2 + y2 * z1) * cross

    iy = iy / 12.0
    iz = iz / 12.0
    iyz = iyz / 24.0

    # Ensure non-negative principal for CCW normalized polygons
    if iy < 0:
        iy = -iy
    if iz < 0:
        iz = -iz
    # iyz may be negative depending on symmetry; do not abs.
    return (iy, iz, iyz)

