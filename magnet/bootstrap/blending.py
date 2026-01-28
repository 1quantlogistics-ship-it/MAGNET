"""
magnet/bootstrap/blending.py

T0.5: Hull Blending (manifold-aware).

This is the bootstrap-level blending utility. It must:
- avoid naive linear blending in high-dimensional spaces (use TA.5 ManifoldBlender)
- preserve coefficient coupling (Cb = Cp * Cm) per §0.9.1
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from magnet.bootstrap.hull_library import HullLibrary
from magnet.bootstrap.manifold_blending import ManifoldBlender


@dataclass(frozen=True)
class BlendResult:
    parameters: Dict[str, float]
    projected: bool


def blend_hulls(
    *,
    library: HullLibrary,
    hull_ids: Sequence[str],
    weights: Sequence[float],
    validator=None,
) -> BlendResult:
    """
    Blend hulls and return a parameter dict.

    - Blends in manifold latent space (PCA) and projects to validity if needed.
    - Fixes coefficient coupling after blending.
    """
    blender = ManifoldBlender(hull_library=library, validator=validator)
    params = blender.blend(hull_ids=list(hull_ids), weights=list(weights))

    fixed, changed = _fix_coefficient_coupling(params)
    return BlendResult(parameters=fixed, projected=changed)


def _fix_coefficient_coupling(params: Dict[str, float]) -> tuple[Dict[str, float], bool]:
    """
    Preserve coupling relationship Cb = Cp * Cm when all are present (case-insensitive).
    """
    out = dict(params)
    keys = {k.lower(): k for k in out.keys()}
    cp_k = keys.get("cp")
    cm_k = keys.get("cm")
    cb_k = keys.get("cb")
    if cp_k and cm_k:
        cp = float(out.get(cp_k, 0.0) or 0.0)
        cm = float(out.get(cm_k, 0.0) or 0.0)
        cb = cp * cm
        if cb_k:
            changed = abs(float(out.get(cb_k, 0.0) or 0.0) - cb) > 1e-12
            out[cb_k] = cb
            return out, changed
        # If no explicit Cb field, add canonical "cb".
        out["cb"] = cb
        return out, True
    return out, False

