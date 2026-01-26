"""
Kernel Planarity Validator (Engineering Truth)

Hard-gate for panelized hulls: quad warp factor must remain within tolerance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from magnet.hull_gen.geometry import Point3D, HullSection
from magnet.kernel.stdlib.compiler import compile_to_geometry
from magnet.validators.taxonomy import (
    ValidatorInterface,
    ValidatorDefinition,
    ValidationResult,
    create_passed_result,
)


class PlanarityGateError(RuntimeError):
    """Raised when panel planarity violates the hard gate in panelized mode."""

    def __init__(self, message: str, *, max_warp: float, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.max_warp = float(max_warp)
        self.details = details or {}


def _vec(a: Point3D, b: Point3D) -> Tuple[float, float, float]:
    return (float(b.x - a.x), float(b.y - a.y), float(b.z - a.z))


def _cross(u: Tuple[float, float, float], v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    )


def _dot(u: Tuple[float, float, float], v: Tuple[float, float, float]) -> float:
    return u[0] * v[0] + u[1] * v[1] + u[2] * v[2]


def _norm(u: Tuple[float, float, float]) -> float:
    return math.sqrt(_dot(u, u))


def _warp_factor(p0: Point3D, p1: Point3D, p2: Point3D, p3: Point3D) -> float:
    """
    Normalized warp factor for quad (p0,p1,p2,p3).

    Plane defined by (p0,p1,p2); measure distance of p3 to that plane.
    Normalize by the longer diagonal length.
    """
    u = _vec(p0, p1)
    v = _vec(p0, p2)
    n = _cross(u, v)
    nn = _norm(n)
    if nn <= 0:
        return 0.0
    nh = (n[0] / nn, n[1] / nn, n[2] / nn)
    d = abs(_dot(nh, _vec(p0, p3)))
    diag0 = _norm(_vec(p0, p2))
    diag1 = _norm(_vec(p1, p3))
    denom = max(diag0, diag1, 1e-12)
    return float(d / denom)


# Backwards-compatible alias (used by some callers/tests)
def _compute_quad_warp_factor(p0: Point3D, p1: Point3D, p2: Point3D, p3: Point3D) -> float:
    return _warp_factor(p0, p1, p2, p3)


def _group_sections_by_body(sections: List[HullSection]) -> Dict[str, List[HullSection]]:
    out: Dict[str, List[HullSection]] = {}
    for s in sections:
        bid = str(getattr(s, "body_id", "main"))
        out.setdefault(bid, []).append(s)
    for bid in list(out.keys()):
        out[bid] = sorted(out[bid], key=lambda sec: float(sec.x_position))
    return out


class PlanarityValidator(ValidatorInterface):
    """
    Panel planarity hard gate.

    Only applies when surface_definition == "panelized".
    """

    WARP_GATE_MAX = 0.02

    def __init__(self, definition: ValidatorDefinition):
        super().__init__(definition)

    def validate(self, state_manager: "StateManager", context: Dict[str, Any]) -> ValidationResult:
        state = state_manager.to_dict()
        resources = state.get("resources") or {}
        has_sections = any(
            isinstance(r, dict)
            and r.get("_type") == "geometry.section"
            and not r.get("_deleted")
            for r in (resources.values() if isinstance(resources, dict) else [])
        )
        if not has_sections:
            return create_passed_result(self.definition.validator_id, "No geometry.section resources; planarity skipped")

        loa = None
        try:
            loa = (state.get("hull") or {}).get("loa") or (state.get("hull") or {}).get("lwl")
        except Exception:
            loa = None

        hull_geom = compile_to_geometry(state, loa=float(loa) if loa else None)
        surface_definition = (getattr(hull_geom, "metadata", {}) or {}).get("surface_definition")

        if surface_definition != "panelized":
            return create_passed_result(
                self.definition.validator_id,
                f"surface_definition={surface_definition!r}; planarity gate not applicable",
            )

        by_body = _group_sections_by_body(list(hull_geom.sections or []))
        max_warp = 0.0
        worst: Optional[Dict[str, Any]] = None

        for body_id, secs in by_body.items():
            if len(secs) < 2:
                continue
            # Topology contract: all sections must have the same vertex count after harmonization.
            counts = sorted({len(s.points or []) for s in secs})
            if len(counts) > 1:
                raise PlanarityGateError(
                    f"Panelized topology mismatch in body '{body_id}': section point counts {counts}",
                    max_warp=1.0,
                    details={"body_id": body_id, "counts": counts},
                )

            npts = counts[0] if counts else 0
            if npts < 4:
                continue

            for si in range(len(secs) - 1):
                a = secs[si].points or []
                b = secs[si + 1].points or []
                for i in range(npts - 1):
                    p0 = a[i].position
                    p1 = a[i + 1].position
                    p2 = b[i + 1].position
                    p3 = b[i].position
                    w = _warp_factor(p0, p1, p2, p3)
                    if w > max_warp:
                        max_warp = w
                        worst = {
                            "body_id": body_id,
                            "section_pair": [si, si + 1],
                            "vertex_span": [i, i + 1],
                            "warp_factor": w,
                        }

        if max_warp > self.WARP_GATE_MAX:
            raise PlanarityGateError(
                f"Planarity gate violated: warp_factor_max={max_warp:.4f} > {self.WARP_GATE_MAX:.4f}",
                max_warp=max_warp,
                details=worst or {},
            )

        return create_passed_result(
            self.definition.validator_id,
            f"Planarity OK (panelized): warp_factor_max={max_warp:.4f} ≤ {self.WARP_GATE_MAX:.4f}",
        )

