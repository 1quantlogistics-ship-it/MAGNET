"""
validators/fix_generator.py

Walking Trail Contract 8: SuggestedFix objects.

This is intentionally minimal, but structured:
- fixes are objects
- fixes link to findings
- fixes include causal chains + side effects
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import hashlib

from magnet.validators.taxonomy import ResultSeverity, ValidationFinding
from magnet.validators.causal_tracer import trace_upstream, estimate_side_effects_for_change


def _fix_id(finding_id: str, target_path: str, suggested_value: Any) -> str:
    content = f"{finding_id}:{target_path}:{suggested_value}"
    h = hashlib.sha256(content.encode("utf-8")).hexdigest()[:10]
    return f"fix_{h}"


def generate_fixes(
    *,
    findings: List[ValidationFinding],
    state_manager: Any,
) -> List[Dict[str, Any]]:
    """
    Generate suggested fixes from findings.

    Returns a list of SuggestedFix-compatible dicts.
    """
    fixes: List[Dict[str, Any]] = []

    for f in findings or []:
        if not isinstance(f, ValidationFinding):
            continue

        finding_id = f.finding_id
        p = f.parameter_path or ""
        msg = (f.message or "").lower()

        # 1) Adjustment hints (if present) become direct suggested fixes.
        if isinstance(f.adjustment, dict):
            adj = f.adjustment
            target_path = adj.get("path")
            direction = adj.get("direction")
            magnitude = adj.get("magnitude")
            if isinstance(target_path, str) and direction in ("increase", "decrease") and isinstance(magnitude, (int, float)):
                cur = state_manager.get(target_path) if hasattr(state_manager, "get") else None
                try:
                    cur_f = float(cur) if cur is not None else None
                except Exception:
                    cur_f = None
                if cur_f is not None:
                    suggested = cur_f * (1.0 + float(magnitude)) if direction == "increase" else cur_f * (1.0 - float(magnitude))
                else:
                    suggested = None

                fixes.append(
                    _build_fix(
                        finding_id=finding_id,
                        target_path=target_path,
                        current_value=cur_f,
                        suggested_value=suggested,
                        rationale=f.suggestion or "Suggested adjustment from validator",
                        from_parameter=p,
                        state_manager=state_manager,
                        confidence=0.75,
                    )
                )
                continue

        # 2) Negative GM / severe stability grade
        if (p in ("weight.estimated_gm_m", "stability.gm_m", "stability.gm_corrected_m") or "negative gm" in msg) and f.severity in (
            ResultSeverity.ERROR,
            ResultSeverity.WARNING,
        ):
            # Fix A: increase beam
            beam = state_manager.get("hull.beam") if hasattr(state_manager, "get") else None
            try:
                beam_f = float(beam) if beam is not None else None
            except Exception:
                beam_f = None
            if beam_f is not None and beam_f > 0:
                suggested_beam = beam_f * 1.10
                fixes.append(
                    _build_fix(
                        finding_id=finding_id,
                        target_path="hull.beam",
                        current_value=beam_f,
                        suggested_value=suggested_beam,
                        rationale="Increase beam to raise BM, improving GM.",
                        from_parameter=p or "stability.gm_m",
                        state_manager=state_manager,
                        confidence=0.85,
                    )
                )

            # Fix B: lower KG if available
            kg = state_manager.get("stability.kg_m") if hasattr(state_manager, "get") else None
            if kg is None and hasattr(state_manager, "get"):
                kg = state_manager.get("weight.lightship_vcg_m")
            try:
                kg_f = float(kg) if kg is not None else None
            except Exception:
                kg_f = None
            if kg_f is not None and kg_f > 0:
                suggested_kg = kg_f * 0.90
                fixes.append(
                    _build_fix(
                        finding_id=finding_id,
                        target_path="stability.kg_m",
                        current_value=kg_f,
                        suggested_value=suggested_kg,
                        rationale="Lower KG (move weight down / ballast) to improve GM.",
                        from_parameter=p or "stability.gm_m",
                        state_manager=state_manager,
                        confidence=0.75,
                    )
                )

    # De-duplicate fixes by (target_path, suggested_value)
    seen = set()
    unique: List[Dict[str, Any]] = []
    for fx in fixes:
        key = (fx.get("target_path"), fx.get("suggested_value"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(fx)

    return unique


def _build_fix(
    *,
    finding_id: str,
    target_path: str,
    current_value: Optional[float],
    suggested_value: Any,
    rationale: str,
    from_parameter: str,
    state_manager: Any,
    confidence: float,
) -> Dict[str, Any]:
    causal_chain = trace_upstream(from_parameter=from_parameter, state_manager=state_manager)
    side_effects = estimate_side_effects_for_change(
        target_path=target_path,
        current_value=current_value,
        suggested_value=suggested_value if isinstance(suggested_value, (int, float)) else None,
    )
    fid = _fix_id(finding_id, target_path, suggested_value)
    return {
        "fix_id": fid,
        "finding_id": finding_id,
        "target_path": target_path,
        "current_value": current_value,
        "suggested_value": suggested_value,
        "change_delta": (suggested_value - current_value) if isinstance(suggested_value, (int, float)) and isinstance(current_value, (int, float)) else None,
        "rationale": rationale,
        "causal_chain": causal_chain,
        "confidence": float(confidence),
        "side_effects": side_effects,
        "actions": [
            {"action": "accept", "label": "Accept Fix", "requires_confirmation": False},
            {"action": "modify", "label": "Modify Value", "requires_confirmation": False},
            {"action": "override", "label": "Override Warning", "requires_confirmation": True},
            {"action": "ignore", "label": "Ignore", "requires_confirmation": True},
        ],
    }

