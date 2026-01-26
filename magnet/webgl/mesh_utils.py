"""
magnet/webgl/mesh_utils.py

Phase 1 (Geometry Stability): adapter layer for mesh utilities.

This module provides MAGNET-native interfaces to optional `trimesh` functionality,
ensuring no trimesh objects leak into DesignState/state payloads.

North Star compliance:
- Inputs/outputs are MAGNET-native (lists, floats, bools, numpy arrays when available)
- No `trimesh.Trimesh` objects are returned or stored
- Graceful fallback when trimesh is unavailable or disabled
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from typing import Optional, Tuple, Any

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Optional dependency gate
# -----------------------------------------------------------------------------

_DISABLE_TRIMESH = str(os.getenv("MAGNET_DISABLE_TRIMESH", "")).strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)

_TRIMESH_AVAILABLE = False
_trimesh: Any = None
try:
    if not _DISABLE_TRIMESH:
        import trimesh as _trimesh  # type: ignore

        _TRIMESH_AVAILABLE = True
except Exception:
    _TRIMESH_AVAILABLE = False
    _trimesh = None

if _DISABLE_TRIMESH:
    logger.info("MAGNET_DISABLE_TRIMESH enabled; trimesh adapter disabled")
elif not _TRIMESH_AVAILABLE:
    logger.info("trimesh not available; using fallback mesh utilities")


def _as_vertices_np(vertices: Any) -> Optional["Any"]:
    """
    Convert MAGNET mesh vertex storage into an (N, 3) numpy array.

    Accepts:
    - list[float] length 3N  (MeshData.vertices in webgl schema)
    - array-like (N, 3)
    """
    if vertices is None:
        return None
    try:
        import numpy as np
    except Exception:
        return None

    v = np.asarray(vertices, dtype=float)
    if v.size == 0:
        return np.zeros((0, 3), dtype=float)
    if v.ndim == 1:
        if (v.size % 3) != 0:
            raise ValueError("vertices must be flat array of length 3N or (N,3)")
        v = v.reshape((-1, 3))
    if v.ndim != 2 or v.shape[1] != 3:
        raise ValueError("vertices must be shaped (N,3)")
    return v


def _as_faces_np(indices: Any) -> Optional["Any"]:
    """
    Convert MAGNET mesh index storage into an (F, 3) numpy array.

    Accepts:
    - list[int] length 3F (MeshData.indices)
    - array-like (F, 3)
    """
    if indices is None:
        return None
    try:
        import numpy as np
    except Exception:
        return None

    f = np.asarray(indices, dtype=int)
    if f.size == 0:
        return np.zeros((0, 3), dtype=int)
    if f.ndim == 1:
        if (f.size % 3) != 0:
            raise ValueError("indices must be flat array of length 3F or (F,3)")
        f = f.reshape((-1, 3))
    if f.ndim != 2 or f.shape[1] != 3:
        raise ValueError("indices must be shaped (F,3)")
    return f


@dataclass(frozen=True)
class MeshValidationResult:
    is_watertight: bool
    volume_m3: float
    surface_area_m2: float
    euler_number: int
    component_count: int
    has_degenerate_faces: bool
    error_message: Optional[str] = None


def compute_mesh_volume(
    vertices: Any,
    indices: Any,
    *,
    attempt_repair: bool = False,
) -> float:
    """
    Compute mesh volume in cubic meters (always >= 0).

    This function NEVER returns trimesh objects; it returns a float.
    """
    if vertices is None or indices is None:
        return 0.0

    v = _as_vertices_np(vertices)
    f = _as_faces_np(indices)
    if v is None or f is None:
        # No numpy available: best-effort pure-python fallback.
        return float(_fallback_volume_py(vertices, indices))

    if v.shape[0] < 3 or f.shape[0] < 1:
        return 0.0

    if _TRIMESH_AVAILABLE:
        return float(_trimesh_volume(v, f, attempt_repair=attempt_repair))

    return float(_fallback_volume_np(v, f))


def validate_mesh(vertices: Any, indices: Any) -> MeshValidationResult:
    """
    Comprehensive mesh validation.

    If trimesh is unavailable/disabled, returns a partial result with a warning.
    """
    try:
        import numpy as np
    except Exception:
        return MeshValidationResult(
            is_watertight=False,
            volume_m3=float(_fallback_volume_py(vertices, indices)),
            surface_area_m2=0.0,
            euler_number=0,
            component_count=0,
            has_degenerate_faces=False,
            error_message="numpy not available for mesh validation",
        )

    v = _as_vertices_np(vertices)
    if v is None:
        v = np.zeros((0, 3), dtype=float)
    f = _as_faces_np(indices)
    if f is None:
        f = np.zeros((0, 3), dtype=int)

    if v.shape[0] < 3 or f.shape[0] < 1:
        return MeshValidationResult(
            is_watertight=False,
            volume_m3=0.0,
            surface_area_m2=0.0,
            euler_number=0,
            component_count=0,
            has_degenerate_faces=False,
            error_message="empty_mesh",
        )

    if not _TRIMESH_AVAILABLE:
        return MeshValidationResult(
            is_watertight=False,
            volume_m3=float(_fallback_volume_np(v, f)),
            surface_area_m2=0.0,
            euler_number=0,
            component_count=1,
            has_degenerate_faces=False,
            error_message="trimesh not available for full validation",
        )

    tm = _trimesh.Trimesh(vertices=v, faces=f, process=False)
    try:
        comps = tm.split(only_watertight=False)
        comp_count = len(comps)
    except Exception:
        comp_count = 1
    try:
        deg = getattr(tm, "degenerate_faces", None)
        has_deg = bool(deg is not None and len(deg) > 0)
    except Exception:
        has_deg = False

    return MeshValidationResult(
        is_watertight=bool(getattr(tm, "is_watertight", False)),
        volume_m3=abs(float(getattr(tm, "volume", 0.0) or 0.0)),
        surface_area_m2=float(getattr(tm, "area", 0.0) or 0.0),
        euler_number=int(getattr(tm, "euler_number", 0) or 0),
        component_count=int(comp_count),
        has_degenerate_faces=bool(has_deg),
        error_message=None,
    )


def repair_mesh(vertices: Any, indices: Any) -> Tuple[Any, Any]:
    """
    Best-effort mesh repair.

    Returns MAGNET-native numpy arrays when available; otherwise returns inputs.
    """
    if not _TRIMESH_AVAILABLE:
        return vertices, indices

    v = _as_vertices_np(vertices)
    f = _as_faces_np(indices)
    if v is None or f is None or v.shape[0] < 3 or f.shape[0] < 1:
        return vertices, indices

    tm = _trimesh.Trimesh(vertices=v, faces=f, process=False)
    try:
        _trimesh.repair.fix_normals(tm)
        _trimesh.repair.fix_inversion(tm)
        _trimesh.repair.fill_holes(tm)
    except Exception:
        # Return the best available (do not raise inside adapter).
        pass

    # Return MAGNET-native arrays, not trimesh object.
    return (tm.vertices.copy(), tm.faces.copy())


# -----------------------------------------------------------------------------
# Internals
# -----------------------------------------------------------------------------

def _trimesh_volume(vertices_np: "Any", faces_np: "Any", *, attempt_repair: bool) -> float:
    tm = _trimesh.Trimesh(vertices=vertices_np, faces=faces_np, process=False)
    if attempt_repair and not bool(getattr(tm, "is_watertight", False)):
        try:
            _trimesh.repair.fix_normals(tm)
            _trimesh.repair.fill_holes(tm)
        except Exception:
            pass
    return abs(float(getattr(tm, "volume", 0.0) or 0.0))


def _fallback_volume_np(vertices_np: "Any", faces_np: "Any") -> float:
    """
    Vectorized-ish tetrahedra sum in numpy.
    """
    import numpy as np

    if faces_np.ndim != 2 or faces_np.shape[1] != 3:
        faces_np = faces_np.reshape((-1, 3))

    valid = (faces_np >= 0) & (faces_np < vertices_np.shape[0])
    mask = valid.all(axis=1)
    if not bool(np.any(mask)):
        return 0.0

    f = faces_np[mask]
    p0 = vertices_np[f[:, 0], :]
    p1 = vertices_np[f[:, 1], :]
    p2 = vertices_np[f[:, 2], :]
    cross = np.cross(p1 - p0, p2 - p0)
    vol = np.einsum("ij,ij->i", p0, cross) / 6.0
    return abs(float(np.sum(vol)))


def _fallback_volume_py(vertices: Any, indices: Any) -> float:
    """
    Pure-python fallback volume for environments without numpy.

    Accepts:
    - vertices as flat list length 3N or list of 3-lists
    - indices as flat list length 3F or list of 3-lists
    """
    if vertices is None or indices is None:
        return 0.0

    # Normalize vertices to list[(x,y,z)]
    if isinstance(vertices, (list, tuple)) and vertices and isinstance(vertices[0], (int, float)):
        if (len(vertices) % 3) != 0:
            return 0.0
        verts = [
            (float(vertices[i]), float(vertices[i + 1]), float(vertices[i + 2]))
            for i in range(0, len(vertices), 3)
        ]
    else:
        try:
            verts = [(float(v[0]), float(v[1]), float(v[2])) for v in vertices]
        except Exception:
            return 0.0

    # Normalize faces to list[(i0,i1,i2)]
    if isinstance(indices, (list, tuple)) and indices and isinstance(indices[0], (int, float)):
        if (len(indices) % 3) != 0:
            return 0.0
        faces = [
            (int(indices[i]), int(indices[i + 1]), int(indices[i + 2]))
            for i in range(0, len(indices), 3)
        ]
    else:
        try:
            faces = [(int(f[0]), int(f[1]), int(f[2])) for f in indices]
        except Exception:
            return 0.0

    total = 0.0
    n = len(verts)
    for (i0, i1, i2) in faces:
        if i0 < 0 or i1 < 0 or i2 < 0 or i0 >= n or i1 >= n or i2 >= n:
            continue
        x0, y0, z0 = verts[i0]
        x1, y1, z1 = verts[i1]
        x2, y2, z2 = verts[i2]

        ax, ay, az = (x1 - x0), (y1 - y0), (z1 - z0)
        bx, by, bz = (x2 - x0), (y2 - y0), (z2 - z0)

        cx = ay * bz - az * by
        cy = az * bx - ax * bz
        cz = ax * by - ay * bx

        total += (x0 * cx + y0 * cy + z0 * cz) / 6.0

    return abs(float(total))

