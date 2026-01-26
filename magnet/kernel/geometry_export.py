"""
magnet/kernel/geometry_export.py

TA.4: Kernel Export Interface.

This module defines the kernel-side "geometry export" contract that other layers
(like rendering adapters) can consume without the kernel knowing anything about
rendering specifics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple

import numpy as np

from magnet.core.state_manager import StateManager
from magnet.hull_gen.geometry import HullGeometry, HullSection
from magnet.kernel.stdlib.compiler import compile_to_geometry


@dataclass(frozen=True)
class Section:
    section_id: str
    station: float
    body_id: str
    # points as (x,y,z)
    points: List[Tuple[float, float, float]] = field(default_factory=list)


@dataclass(frozen=True)
class Body:
    body_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Transform3D:
    """
    Pure transform (no coordinate-frame semantics).
    """

    matrix: np.ndarray  # shape (4,4)


class GeometryExport(Protocol):
    def get_sections(self) -> List[Section]: ...
    def get_bodies(self) -> List[Body]: ...
    def get_component_transforms(self) -> Dict[str, Transform3D]: ...


class StateGeometryExport:
    """
    Export geometry from the canonical StateManager.
    """

    def __init__(self, state_manager: StateManager):
        self._sm = state_manager
        self._geometry: Optional[HullGeometry] = None

    def _ensure_geometry(self) -> HullGeometry:
        if self._geometry is None:
            self._geometry = compile_to_geometry(self._sm.to_dict())
        return self._geometry

    def get_sections(self) -> List[Section]:
        geo = self._ensure_geometry()
        out: List[Section] = []
        for s in geo.sections:
            out.append(_export_section(s))
        return out

    def get_bodies(self) -> List[Body]:
        geo = self._ensure_geometry()
        body_ids = sorted(set(getattr(s, "body_id", "main") or "main" for s in geo.sections))
        return [Body(body_id=str(b), metadata={}) for b in body_ids]

    def get_component_transforms(self) -> Dict[str, Transform3D]:
        # Minimal implementation: if resources contain kinematics, export them here later.
        return {}


def _export_section(section: HullSection) -> Section:
    sid = str(getattr(section, "section_id", "") or getattr(section, "id", "") or "")
    station = float(getattr(section, "station", 0.0) or 0.0)
    body_id = str(getattr(section, "body_id", "main") or "main")
    pts: List[Tuple[float, float, float]] = []
    for p in getattr(section, "points", []) or []:
        pos = getattr(p, "position", None)
        if pos is None:
            continue
        pts.append((float(pos.x), float(pos.y), float(pos.z)))
    if not sid:
        sid = f"section_{station:.3f}_{body_id}"
    return Section(section_id=sid, station=station, body_id=body_id, points=pts)

