"""
magnet/physics/uncertainty.py

Phase 4 (Honest Output Contract) — shared uncertainty schema helpers.

This module defines a single schema shape to attach to physics outputs so that
clients can reason about extrapolation, model limits, and confidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


def _level_from_pct(value_pct: float) -> str:
    v = float(value_pct)
    if v <= 5.0:
        return "LOW"
    if v <= 15.0:
        return "MED"
    if v <= 30.0:
        return "HIGH"
    return "EXTREME"


@dataclass(frozen=True)
class Uncertainty:
    """
    Shared uncertainty schema (dict-serializable).

    - value_pct: ± percentage uncertainty estimate (e.g., 12.0 means ±12%)
    - level: LOW/MED/HIGH/EXTREME derived from value_pct
    - basis: short description of model + assumptions
    - validity_envelope: human-readable envelope of model validity
    - novelty_impact: notes about novel geometry/primitives not modeled
    """

    value_pct: float
    basis: str
    validity_envelope: str
    novelty_impact: str = ""
    level: str = "MED"
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value_pct": float(self.value_pct),
            "level": self.level,
            "basis": self.basis,
            "validity_envelope": self.validity_envelope,
            "novelty_impact": self.novelty_impact,
            "details": self.details or {},
        }


def make_uncertainty(
    *,
    value_pct: float,
    basis: str,
    validity_envelope: str,
    novelty_impact: str = "",
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    u = Uncertainty(
        value_pct=float(value_pct),
        basis=str(basis),
        validity_envelope=str(validity_envelope),
        novelty_impact=str(novelty_impact or ""),
        level=_level_from_pct(float(value_pct)),
        details=details or {},
    )
    return u.to_dict()


def novelty_impact_from_state_resources(resources: Any) -> str:
    """
    Derive a novelty-impact note from DesignState.resources.

    If universal primitives exist but the physics model does not yet incorporate them
    (e.g., openings not subtracted from volume), we must say so explicitly.
    """
    try:
        if not isinstance(resources, dict):
            return ""
        live = [
            r for r in resources.values()
            if isinstance(r, dict) and not r.get("_deleted")
        ]
        openings = [r for r in live if r.get("_type") == "geometry.opening"]
        flows = [r for r in live if r.get("_type") == "geometry.flow_path"]
        atts = [r for r in live if r.get("_type") == "geometry.attachment"]

        opening_count = len(openings)
        flow_count = len(flows)
        attach_count = len(atts)

        # Phase 3B: detect explicit (opt-in) buoyancy/void semantics.
        opening_sem_count = sum(
            1
            for r in openings
            if r.get("void_volume_m3") is not None or r.get("through_hull_length_m") is not None
        )
        flow_sem_count = sum(1 for r in flows if r.get("void_volume_m3") is not None)
        att_sem_count = sum(1 for r in atts if r.get("buoyancy_volume_m3") is not None)

        if opening_count or flow_count or attach_count:
            if opening_sem_count or flow_sem_count or att_sem_count:
                return (
                    f"Design includes universal primitives: opening={opening_count}, flow_path={flow_count}, attachment={attach_count}. "
                    f"Explicit volume semantics are provided for: opening={opening_sem_count}, flow_path={flow_sem_count}, attachment={att_sem_count}. "
                    f"Hydrostatics may apply explicit volume corrections, but waterplane inertias/BM are not fully adjusted yet; "
                    f"treat GM as advisory when primitives are present. "
                    f"Resistance/weight can incorporate primitives only when explicit drag/mass semantics are supplied (e.g., drag_area_m2, loss_coefficient, mass_kg)."
                )
            return (
                f"Design includes unmodeled primitives: "
                f"opening={opening_count}, flow_path={flow_count}, attachment={attach_count}. "
                f"Current physics outputs treat these as diagnostic-only and may ignore their effects "
                f"until Phase 3 semantics are implemented."
            )
        return ""
    except Exception:
        return ""

