"""
magnet/physics/stability_validator.py

T7.2: Stability validation wrapper.

This module exists to match the implementation guide's file layout while
reusing MAGNET's existing stability validators in `magnet/stability/validators.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from magnet.stability.validators import IntactGMValidator


@dataclass(frozen=True)
class StabilityValidationResult:
    passed: bool
    gm_m: Optional[float] = None
    findings: List[Dict[str, Any]] = field(default_factory=list)


def validate_stability(state_manager, context: Optional[Dict[str, Any]] = None) -> StabilityValidationResult:
    """
    Validate intact stability (GM) using the existing validator implementation.
    """
    res = IntactGMValidator().validate(state_manager, context or {})
    gm = state_manager.get("stability.gm_m")
    findings = []
    try:
        findings = [f.to_dict() for f in (getattr(res, "findings", []) or [])]
    except Exception:
        findings = []
    return StabilityValidationResult(
        passed=bool(getattr(res, "passed", False)),
        gm_m=float(gm) if gm is not None else None,
        findings=findings,
    )

