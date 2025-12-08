"""
hull_gen/nurbs.py - NURBS curve and surface representation.

ALPHA OWNS THIS FILE.

Module 17 v1.0 - Hull Geometry Representation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import math

from .geometry import Point3D


@dataclass
class NURBSCurve:
    """Non-Uniform Rational B-Spline curve."""

    degree: int = 3
    """Curve degree (typically 3 for cubic)."""

    control_points: List[Point3D] = field(default_factory=list)
    """Control points defining the curve."""

    weights: List[float] = field(default_factory=list)
    """Weights for rational curves (1.0 for non-rational)."""

    knot_vector: List[float] = field(default_factory=list)
    """Knot vector for basis functions."""

    def __post_init__(self):
        """Initialize weights if not provided."""
        if not self.weights and self.control_points:
            self.weights = [1.0] * len(self.control_points)

    @property
    def num_control_points(self) -> int:
        return len(self.control_points)

    def generate_uniform_knots(self) -> None:
        """Generate uniform clamped knot vector."""
        n = len(self.control_points)
        p = self.degree

        if n <= p:
            self.knot_vector = [0.0] * (n + p + 1)
            return

        self.knot_vector = []

        # Clamped start
        for _ in range(p + 1):
            self.knot_vector.append(0.0)

        # Internal knots
        num_internal = n - p - 1
        for i in range(num_internal):
            self.knot_vector.append((i + 1) / (num_internal + 1))

        # Clamped end
        for _ in range(p + 1):
            self.knot_vector.append(1.0)

    def evaluate(self, u: float) -> Point3D:
        """
        Evaluate curve at parameter u in [0, 1].

        Uses de Boor's algorithm.

        Args:
            u: Parameter value [0, 1]

        Returns:
            Point on curve at parameter u
        """
        if not self.control_points:
            return Point3D()

        if not self.knot_vector:
            self.generate_uniform_knots()

        # Clamp u
        u = max(0.0, min(1.0 - 1e-10, u))

        # Find knot span
        span = self._find_span(u)

        # Compute basis functions
        basis = self._basis_functions(span, u)

        # Compute weighted sum
        x, y, z, w_sum = 0.0, 0.0, 0.0, 0.0

        for i in range(self.degree + 1):
            idx = span - self.degree + i
            if 0 <= idx < len(self.control_points):
                pt = self.control_points[idx]
                w = self.weights[idx] if idx < len(self.weights) else 1.0
                bw = basis[i] * w

                x += pt.x * bw
                y += pt.y * bw
                z += pt.z * bw
                w_sum += bw

        if w_sum > 0:
            return Point3D(x / w_sum, y / w_sum, z / w_sum)
        return Point3D()

    def _find_span(self, u: float) -> int:
        """Find knot span index."""
        n = len(self.control_points) - 1

        if n < 0:
            return self.degree

        if u >= self.knot_vector[n + 1]:
            return n
        if u <= self.knot_vector[self.degree]:
            return self.degree

        low, high = self.degree, n + 1
        mid = (low + high) // 2

        while u < self.knot_vector[mid] or u >= self.knot_vector[mid + 1]:
            if u < self.knot_vector[mid]:
                high = mid
            else:
                low = mid
            mid = (low + high) // 2

        return mid

    def _basis_functions(self, span: int, u: float) -> List[float]:
        """Compute non-zero basis functions."""
        p = self.degree
        knots = self.knot_vector

        N = [0.0] * (p + 1)
        left = [0.0] * (p + 1)
        right = [0.0] * (p + 1)

        N[0] = 1.0

        for j in range(1, p + 1):
            left[j] = u - knots[span + 1 - j]
            right[j] = knots[span + j] - u
            saved = 0.0

            for r in range(j):
                denom = right[r + 1] + left[j - r]
                if denom != 0:
                    temp = N[r] / denom
                    N[r] = saved + right[r + 1] * temp
                    saved = left[j - r] * temp
                else:
                    N[r] = saved
                    saved = 0.0

            N[j] = saved

        return N

    def sample(self, num_points: int = 50) -> List[Point3D]:
        """
        Sample curve at uniform parameter intervals.

        Args:
            num_points: Number of sample points

        Returns:
            List of points along curve
        """
        points = []
        for i in range(num_points):
            u = i / (num_points - 1) if num_points > 1 else 0
            points.append(self.evaluate(u))
        return points

    def derivative(self, u: float) -> Point3D:
        """
        Compute first derivative at parameter u.

        Uses numerical differentiation.

        Args:
            u: Parameter value [0, 1]

        Returns:
            Tangent vector at parameter u
        """
        if not self.control_points or len(self.control_points) < 2:
            return Point3D()

        # Numerical derivative
        h = 0.001
        p0 = self.evaluate(max(0, u - h))
        p1 = self.evaluate(min(1, u + h))

        return Point3D(
            (p1.x - p0.x) / (2 * h),
            (p1.y - p0.y) / (2 * h),
            (p1.z - p0.z) / (2 * h),
        )

    def curvature(self, u: float) -> float:
        """
        Compute curvature at parameter u.

        Args:
            u: Parameter value [0, 1]

        Returns:
            Curvature value (1/radius)
        """
        h = 0.001
        p0 = self.evaluate(max(0, u - h))
        p1 = self.evaluate(u)
        p2 = self.evaluate(min(1, u + h))

        # First derivative approximation
        d1 = Point3D(
            (p2.x - p0.x) / (2 * h),
            (p2.y - p0.y) / (2 * h),
            (p2.z - p0.z) / (2 * h),
        )

        # Second derivative approximation
        d2 = Point3D(
            (p2.x - 2 * p1.x + p0.x) / (h * h),
            (p2.y - 2 * p1.y + p0.y) / (h * h),
            (p2.z - 2 * p1.z + p0.z) / (h * h),
        )

        # Curvature = |d1 x d2| / |d1|^3
        cross = d1.cross(d2)
        d1_mag = d1.length()

        if d1_mag < 1e-10:
            return 0.0

        return cross.length() / (d1_mag ** 3)

    def arc_length(self, num_segments: int = 100) -> float:
        """
        Compute approximate arc length of curve.

        Args:
            num_segments: Number of segments for approximation

        Returns:
            Approximate arc length
        """
        length = 0.0
        prev_pt = self.evaluate(0.0)

        for i in range(1, num_segments + 1):
            u = i / num_segments
            pt = self.evaluate(u)
            length += prev_pt.distance_to(pt)
            prev_pt = pt

        return length

    def to_dict(self) -> Dict[str, Any]:
        return {
            "degree": self.degree,
            "control_points": [p.to_dict() for p in self.control_points],
            "weights": self.weights,
            "knot_vector": self.knot_vector,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NURBSCurve':
        return cls(
            degree=data.get("degree", 3),
            control_points=[Point3D.from_dict(p) for p in data.get("control_points", [])],
            weights=data.get("weights", []),
            knot_vector=data.get("knot_vector", []),
        )


@dataclass
class NURBSSurface:
    """
    Non-Uniform Rational B-Spline surface.

    Used for representing smooth hull surfaces.
    """

    degree_u: int = 3
    """Degree in U direction (longitudinal)."""

    degree_v: int = 3
    """Degree in V direction (transverse)."""

    control_points: List[List[Point3D]] = field(default_factory=list)
    """2D grid of control points [u][v]."""

    weights: List[List[float]] = field(default_factory=list)
    """Weights grid."""

    knot_vector_u: List[float] = field(default_factory=list)
    knot_vector_v: List[float] = field(default_factory=list)

    @property
    def num_u(self) -> int:
        return len(self.control_points)

    @property
    def num_v(self) -> int:
        return len(self.control_points[0]) if self.control_points else 0

    def generate_uniform_knots(self) -> None:
        """Generate uniform clamped knot vectors."""
        self.knot_vector_u = self._uniform_knots(self.num_u, self.degree_u)
        self.knot_vector_v = self._uniform_knots(self.num_v, self.degree_v)

    def _uniform_knots(self, n: int, p: int) -> List[float]:
        """Generate uniform clamped knot vector."""
        if n <= p:
            return [0.0] * (p + 1) + [1.0] * (p + 1)

        knots = []

        for _ in range(p + 1):
            knots.append(0.0)

        num_internal = n - p - 1
        for i in range(num_internal):
            knots.append((i + 1) / (num_internal + 1))

        for _ in range(p + 1):
            knots.append(1.0)

        return knots

    def evaluate(self, u: float, v: float) -> Point3D:
        """
        Evaluate surface at parameters (u, v) in [0,1] x [0,1].

        Args:
            u: Longitudinal parameter [0, 1]
            v: Transverse parameter [0, 1]

        Returns:
            Point on surface at (u, v)
        """
        if not self.control_points:
            return Point3D()

        if not self.knot_vector_u:
            self.generate_uniform_knots()

        # Clamp parameters
        u = max(0.0, min(1.0 - 1e-10, u))
        v = max(0.0, min(1.0 - 1e-10, v))

        # Create temporary curves in U direction
        temp_points = []
        for i in range(self.num_u):
            # Evaluate V-direction curve at this U
            v_weights = self.weights[i] if self.weights and i < len(self.weights) else None
            v_curve = NURBSCurve(
                degree=self.degree_v,
                control_points=self.control_points[i],
                weights=v_weights if v_weights else [],
                knot_vector=self.knot_vector_v,
            )
            temp_points.append(v_curve.evaluate(v))

        # Evaluate U-direction curve
        u_curve = NURBSCurve(
            degree=self.degree_u,
            control_points=temp_points,
            knot_vector=self.knot_vector_u,
        )

        return u_curve.evaluate(u)

    def sample_grid(self, nu: int = 20, nv: int = 20) -> List[List[Point3D]]:
        """
        Sample surface on a grid.

        Args:
            nu: Number of samples in U direction
            nv: Number of samples in V direction

        Returns:
            2D grid of sample points
        """
        grid = []
        for i in range(nu):
            row = []
            u = i / (nu - 1) if nu > 1 else 0
            for j in range(nv):
                v = j / (nv - 1) if nv > 1 else 0
                row.append(self.evaluate(u, v))
            grid.append(row)
        return grid

    def normal(self, u: float, v: float) -> Point3D:
        """
        Compute surface normal at (u, v).

        Args:
            u: Longitudinal parameter [0, 1]
            v: Transverse parameter [0, 1]

        Returns:
            Unit normal vector
        """
        h = 0.001

        # Partial derivatives
        pu0 = self.evaluate(max(0, u - h), v)
        pu1 = self.evaluate(min(1, u + h), v)
        pv0 = self.evaluate(u, max(0, v - h))
        pv1 = self.evaluate(u, min(1, v + h))

        du = Point3D(
            (pu1.x - pu0.x) / (2 * h),
            (pu1.y - pu0.y) / (2 * h),
            (pu1.z - pu0.z) / (2 * h),
        )

        dv = Point3D(
            (pv1.x - pv0.x) / (2 * h),
            (pv1.y - pv0.y) / (2 * h),
            (pv1.z - pv0.z) / (2 * h),
        )

        # Cross product gives normal
        normal = du.cross(dv)
        return normal.normalize()

    def gaussian_curvature(self, u: float, v: float) -> float:
        """
        Compute Gaussian curvature at (u, v).

        Args:
            u: Longitudinal parameter [0, 1]
            v: Transverse parameter [0, 1]

        Returns:
            Gaussian curvature value
        """
        h = 0.01

        # Sample 3x3 grid
        pts = []
        for i in [-1, 0, 1]:
            row = []
            for j in [-1, 0, 1]:
                ui = max(0, min(1, u + i * h))
                vj = max(0, min(1, v + j * h))
                row.append(self.evaluate(ui, vj))
            pts.append(row)

        # First fundamental form coefficients (approximation)
        ru = (pts[2][1] - pts[0][1]) * (1 / (2 * h))
        rv = (pts[1][2] - pts[1][0]) * (1 / (2 * h))

        E = ru.dot(ru)
        F = ru.dot(rv)
        G = rv.dot(rv)

        # Second fundamental form
        n = ru.cross(rv).normalize()

        ruu = (pts[2][1] - pts[1][1] * 2 + pts[0][1]) * (1 / (h * h))
        rvv = (pts[1][2] - pts[1][1] * 2 + pts[1][0]) * (1 / (h * h))
        ruv = (pts[2][2] - pts[2][0] - pts[0][2] + pts[0][0]) * (1 / (4 * h * h))

        L = ruu.dot(n)
        M = ruv.dot(n)
        N = rvv.dot(n)

        # Gaussian curvature K = (LN - M^2) / (EG - F^2)
        denom = E * G - F * F
        if abs(denom) < 1e-10:
            return 0.0

        return (L * N - M * M) / denom

    def to_dict(self) -> Dict[str, Any]:
        return {
            "degree_u": self.degree_u,
            "degree_v": self.degree_v,
            "control_points": [
                [p.to_dict() for p in row]
                for row in self.control_points
            ],
            "weights": self.weights,
            "knot_vector_u": self.knot_vector_u,
            "knot_vector_v": self.knot_vector_v,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NURBSSurface':
        control_points = []
        for row in data.get("control_points", []):
            control_points.append([Point3D.from_dict(p) for p in row])

        return cls(
            degree_u=data.get("degree_u", 3),
            degree_v=data.get("degree_v", 3),
            control_points=control_points,
            weights=data.get("weights", []),
            knot_vector_u=data.get("knot_vector_u", []),
            knot_vector_v=data.get("knot_vector_v", []),
        )
