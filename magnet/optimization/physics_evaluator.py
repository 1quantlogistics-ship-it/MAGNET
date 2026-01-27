"""
magnet/optimization/physics_evaluator.py

TM.3A: PhysicsEvaluator interface (wrap existing physics stack).

This module provides a thin adapter to evaluate objective scalars from:
- a HullGeometry (preferred when available)
- or a serialized design-state-like dict containing geometry resources (compile first)

This keeps the multi-fidelity optimizer decoupled from MAGNET internals while
still using the canonical physics implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from magnet.hull_gen.geometry import HullGeometry
from magnet.kernel.stdlib.compiler import compile_to_geometry
from magnet.physics.geometry_hydrostatics import compute_hydrostatics_from_geometry


@dataclass(frozen=True)
class PhysicsObjectiveResult:
    objective: str
    value: float
    confidence: float = 1.0
    notes: str = ""


class PhysicsEvaluator:
    """
    Evaluate objective scalars using existing MAGNET physics modules.
    """

    def __init__(self, *, seawater_density: float = 1025.0) -> None:
        self._rho = float(seawater_density)

    def evaluate(self, design: Dict[str, Any] | HullGeometry, objective: str) -> float:
        """
        Evaluate `objective` for the given design.

        Supported objectives (initial set):
        - "displacement_mt"
        - "waterplane_area_m2"
        - "wetted_surface_m2"
        - "gm_transverse_m" (requires vcg in state, else raises)
        """
        geom = self._coerce_geometry(design)

        # Draft convention: use design-state hull.draft if present; else default to 1.0m
        draft = self._extract_draft(design) if not isinstance(design, HullGeometry) else 1.0
        vcg = self._extract_vcg(design) if not isinstance(design, HullGeometry) else None

        hs = compute_hydrostatics_from_geometry(
            geometry=geom,
            draft=float(draft),
            vcg=float(vcg) if vcg is not None else None,
            seawater_density=self._rho,
        )

        obj = str(objective)
        if obj == "displacement_mt":
            return float(hs.displacement_kg) / 1000.0
        if obj == "waterplane_area_m2":
            return float(hs.waterplane_area_m2)
        if obj == "wetted_surface_m2":
            return float(hs.wetted_surface_m2)
        if obj == "gm_transverse_m":
            if hs.gm_transverse_m is None:
                raise ValueError("gm_transverse_m requested but vcg not provided")
            return float(hs.gm_transverse_m)

        raise KeyError(f"Unsupported objective: {objective!r}")

    def _coerce_geometry(self, design: Dict[str, Any] | HullGeometry) -> HullGeometry:
        if isinstance(design, HullGeometry):
            return design

        if not isinstance(design, dict):
            raise TypeError("design must be HullGeometry or dict state")

        # Expect state-like dict: {"hull": {...}, "geometry_intent": {...}, "resources": {...}}
        state = dict(design)
        if "geometry_intent" not in state:
            # Default intent to smooth for evaluator purposes; production code should be explicit.
            state["geometry_intent"] = {"surface_definition": "smooth"}
        if "resources" not in state:
            state["resources"] = {}

        return compile_to_geometry(state)

    def _extract_draft(self, design: Dict[str, Any] | HullGeometry) -> float:
        if isinstance(design, HullGeometry):
            return 1.0
        try:
            # support both nested and dotted
            hull = design.get("hull") if isinstance(design.get("hull"), dict) else {}
            d = hull.get("draft") if isinstance(hull, dict) else None
            if d is None:
                d = design.get("hull.draft")
            if d is None:
                return 1.0
            return float(d)
        except Exception:
            return 1.0

    def _extract_vcg(self, design: Dict[str, Any] | HullGeometry) -> Optional[float]:
        if isinstance(design, HullGeometry):
            return None
        try:
            hull = design.get("hull") if isinstance(design.get("hull"), dict) else {}
            v = hull.get("vcg") if isinstance(hull, dict) else None
            if v is None:
                v = design.get("hull.vcg")
            return float(v) if v is not None else None
        except Exception:
            return None

