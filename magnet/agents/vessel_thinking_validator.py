"""
magnet/agents/vessel_thinking_validator.py

Deterministic validation + (optional) server-side re-execution of VESSEL_THINKING_PASS checks.

v0 scope:
- Enforce coverage/proof completeness (DOFs ↔ checks ↔ proof).
- Re-execute a subset of checks that are computable from the thinking schema itself:
  - range, monotonic, varies (for schedule/scalar)
  - coverage (for track, interpreted conservatively)

This module is intentionally enum-free and domain-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from magnet.agents.vessel_thinking_schema import (
    BodyDOF,
    BindingEntry,
    CheckEntry,
    CoverageCheck,
    DOFEntry,
    MonotonicCheck,
    ObservationTarget,
    RangeCheck,
    ScalarDOF,
    ScheduleDOF,
    TrackDOF,
    VariesCheck,
    VesselThinkingPass,
)

from magnet.agents.geometry_observables import (
    VALID_OBSERVABLE_IDS,
    compute_observables_via_dry_run,
    compute_observable_series_from_geometry,
)


@dataclass
class ThinkingPassIssue:
    check_name: str
    message: str
    computed: Dict[str, Any]
    expected: Dict[str, Any]


EPS_STATION = 1e-9


@dataclass
class InsufficientData:
    required: int
    found: int
    station_range: Tuple[float, float]
    observable_id: str
    body_id: Optional[str] = None


def _normalize_station_range(rng: Any) -> Tuple[float, float]:
    try:
        lo = float(rng[0])
        hi = float(rng[1])
    except Exception:
        return (0.0, 1.0)
    if lo > hi:
        lo, hi = hi, lo
    lo = max(0.0, lo)
    hi = min(1.0, hi)
    return (lo, hi)


def _min_required_for_observable(oid: str) -> int:
    # v0.3 “sample size trap” guardrail.
    # - section_metric:* needs >=2 stations to make a span meaningful
    # - longitudinal_metric:keel_slope_deg_p95 uses adjacent pairs → needs >=3 stations
    # - longitudinal_metric:deadrise_drop_deg uses forward/aft 30% split → needs >=4 measurable stations
    if oid == "longitudinal_metric:keel_slope_deg_p95":
        return 3
    if oid == "longitudinal_metric:deadrise_drop_deg":
        return 4
    return 2


def _group_sections_by_body_station(sections: List[Any]) -> Dict[str, List[Any]]:
    out: Dict[str, List[Any]] = {}
    for s in sections or []:
        bid = str(getattr(s, "body_id", "main") or "main")
        out.setdefault(bid, []).append(s)
    for bid in list(out.keys()):
        out[bid] = sorted(out[bid], key=lambda sec: float(getattr(sec, "station", 0.0) or 0.0))
    return out


def _sections_in_station_range(secs: List[Any], rng: Tuple[float, float]) -> List[Any]:
    lo, hi = _normalize_station_range(rng)
    out: List[Any] = []
    for s in secs or []:
        try:
            st = float(getattr(s, "station", 0.0) or 0.0)
        except Exception:
            continue
        if (lo - EPS_STATION) <= st <= (hi + EPS_STATION):
            out.append(s)
    return out

def _median(values: Sequence[float]) -> Optional[float]:
    xs = sorted(float(x) for x in values)
    if not xs:
        return None
    m = len(xs) // 2
    if len(xs) % 2 == 1:
        return xs[m]
    return 0.5 * (xs[m - 1] + xs[m])


def _pctl(values: Sequence[float], p: float) -> Optional[float]:
    xs = sorted(float(x) for x in values)
    if not xs:
        return None
    if p <= 0:
        return xs[0]
    if p >= 100:
        return xs[-1]
    k = (len(xs) - 1) * (p / 100.0)
    i = int(k)
    j = min(i + 1, len(xs) - 1)
    t = k - i
    return (1 - t) * xs[i] + t * xs[j]


def _dofs_by_name(dofs: List[DOFEntry]) -> Dict[str, DOFEntry]:
    out: Dict[str, DOFEntry] = {}
    for d in dofs:
        # last-one-wins; caller should ensure unique names
        out[str(d.name)] = d
    return out


def _proof_by_check_name(thinking: VesselThinkingPass) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for p in thinking.closure_proof or []:
        out[str(p.check_name)] = p
    return out


def validate_coverage_and_proof(thinking: VesselThinkingPass) -> List[ThinkingPassIssue]:
    """
    Enforce the structural contract:
    - each non-defaulted DOF must have >= 1 check targeting it
    - every check must appear in closure_proof
    - closure_proof must not contain unknown checks
    """
    issues: List[ThinkingPassIssue] = []
    dofs = list(thinking.dof_schema or [])
    checks = list(thinking.verification_schema or [])
    proofs = _proof_by_check_name(thinking)

    checks_by_target: Dict[str, List[CheckEntry]] = {}
    for c in checks:
        checks_by_target.setdefault(str(getattr(c, "target", "")), []).append(c)

    for d in dofs:
        if bool(getattr(d, "defaulted", False)):
            continue
        dn = str(getattr(d, "name", ""))
        if not dn:
            continue
        if not checks_by_target.get(dn):
            issues.append(
                ThinkingPassIssue(
                    check_name=f"coverage:dof:{dn}",
                    message=f"Non-defaulted DOF '{dn}' has no verification checks targeting it.",
                    computed={"checks_found": 0},
                    expected={"checks_found": ">=1"},
                )
            )

    check_names = {str(getattr(c, "name", "")) for c in checks if str(getattr(c, "name", ""))}
    # each check needs proof
    for cn in sorted(check_names):
        if cn not in proofs:
            issues.append(
                ThinkingPassIssue(
                    check_name=cn,
                    message=f"Missing closure_proof entry for check '{cn}'.",
                    computed={"proof_present": False},
                    expected={"proof_present": True},
                )
            )

    # proofs must not include extras
    for pn in sorted(set(proofs.keys()) - check_names):
        issues.append(
            ThinkingPassIssue(
                check_name=pn,
                message=f"closure_proof references unknown check '{pn}'.",
                computed={"unknown_proof": pn},
                expected={"known_check_names": sorted(check_names)},
            )
        )

    return issues


def validate_verified_unverified_rules(thinking: VesselThinkingPass) -> List[ThinkingPassIssue]:
    """
    v0.1 rules:
    - DOFs are open. Observables are closed.
    - DOF without binding entry is UNVERIFIED and may not carry PASS/FAIL checks.
    """
    issues: List[ThinkingPassIssue] = []
    dofs = list(thinking.dof_schema or [])
    checks = list(thinking.verification_schema or [])

    binding_by_dof: Dict[str, BindingEntry] = {}
    for b in list(getattr(thinking, "binding_table", []) or []):
        if not isinstance(b, BindingEntry):
            continue
        binding_by_dof[str(b.dof_name)] = b

    # Identify check types that require VERIFIED
    verified_check_types = {"range", "monotonic", "varies"}

    for d in dofs:
        dn = str(getattr(d, "name", "") or "")
        if not dn:
            continue
        is_defaulted = bool(getattr(d, "defaulted", False))
        has_binding = dn in binding_by_dof

        # Gather checks targeting this DOF
        d_checks = [c for c in checks if str(getattr(c, "target", "")) == dn]
        needs_verified = any(str(getattr(c, "type", "")).lower() in verified_check_types for c in d_checks)

        if not has_binding and needs_verified:
            issues.append(
                ThinkingPassIssue(
                    check_name=f"binding_required:{dn}",
                    message=(
                        f"DOF '{dn}' has PASS/FAIL checks (range/monotonic/varies) but no binding_table entry. "
                        "UNVERIFIED DOFs may not claim verification."
                    ),
                    computed={"has_binding": False, "checks": [getattr(c, "name", "") for c in d_checks]},
                    expected={"has_binding": True},
                )
            )

        if not has_binding and (not is_defaulted) and d_checks:
            # If any checks exist at all for an unbound DOF, it's invalid in v0.1.
            issues.append(
                ThinkingPassIssue(
                    check_name=f"unverified_checks_forbidden:{dn}",
                    message=f"UNVERIFIED DOF '{dn}' may not include checks.",
                    computed={"checks_count": len(d_checks)},
                    expected={"checks_count": 0},
                )
            )

        if has_binding:
            # Validate binding table uses known observables
            binds_to = list(getattr(binding_by_dof[dn], "binds_to", []) or [])
            unknown = [x for x in binds_to if x not in VALID_OBSERVABLE_IDS]
            if unknown:
                issues.append(
                    ThinkingPassIssue(
                        check_name=f"unknown_observable:{dn}",
                        message=f"binding_table for DOF '{dn}' references unknown observables: {unknown}",
                        computed={"unknown": unknown},
                        expected={"valid_observables": sorted(VALID_OBSERVABLE_IDS)},
                    )
                )

    return issues


def validate_observation_targets_against_geometry(
    *,
    thinking: VesselThinkingPass,
    program_text: str,
    current_state: Dict[str, Any],
) -> Tuple[List[ThinkingPassIssue], Dict[str, Any]]:
    """
    v0.1: compute geometry-derived observables via dry-run compilation and validate
    observation targets (span_min).
    """
    issues: List[ThinkingPassIssue] = []
    computed: Dict[str, Any] = {"observables": {}}

    # Always compute whole-hull observables for baseline debugging (v0.2 behavior).
    series, err = compute_observables_via_dry_run(program_text=program_text, current_state=current_state)
    if err or not series:
        issues.append(
            ThinkingPassIssue(
                check_name="geometry_observables",
                message=f"Could not compute geometry observables (dry-run compile): {err or 'unknown'}",
                computed={"error": err},
                expected={"error": None},
            )
        )
        return issues, computed

    # Index by body_id + observable_id; also keep per observable aggregated spans.
    for key, s in series.items():
        computed["observables"][key] = {
            "span": s.span,
            "samples": len(s.values),
            "value": float(s.values[0]) if (s.observable_id.startswith("longitudinal_metric:") and len(s.values) == 1) else None,
        }

    computed["scoped_observables"] = {}

    # Only pay the cost of compiling geometry again if any station_range is non-default.
    need_scoped = False
    for be in list(getattr(thinking, "binding_table", []) or []):
        for ot in list(getattr(be, "observation_targets", []) or []):
            rng = _normalize_station_range(getattr(ot, "station_range", (0.0, 1.0)))
            if rng != (0.0, 1.0):
                need_scoped = True
                break
        if need_scoped:
            break

    scoped_by_body: Optional[Dict[str, List[Any]]] = None
    if need_scoped:
        try:
            from magnet.kernel.program_executor import execute_program

            res = execute_program(program_text=program_text, initial_state=current_state, dry_run=True, validate=False)
            geom = getattr(res, "geometry", None)
            secs = list(getattr(geom, "sections", []) or [])
            if getattr(res, "success", False) and secs:
                scoped_by_body = _group_sections_by_body_station(secs)
        except Exception:
            scoped_by_body = None

    # Evaluate all observation targets
    for be in list(getattr(thinking, "binding_table", []) or []):
        dn = str(getattr(be, "dof_name", "") or "")
        for ot in list(getattr(be, "observation_targets", []) or []):
            oid = str(getattr(ot, "observable_id", "") or "")
            if oid not in VALID_OBSERVABLE_IDS:
                issues.append(
                    ThinkingPassIssue(
                        check_name=f"unknown_observation_target:{dn}",
                        message=f"Observation target references unknown observable_id '{oid}'.",
                        computed={"observable_id": oid},
                        expected={"valid_observables": sorted(VALID_OBSERVABLE_IDS)},
                    )
                )
                continue

            rng = _normalize_station_range(getattr(ot, "station_range", (0.0, 1.0)))
            is_scoped = rng != (0.0, 1.0)
            thr_min = getattr(ot, "threshold_min", None)
            thr_max = getattr(ot, "threshold_max", None)

            # v0.3 scoped path: compute the observable only over sections in station_range.
            if is_scoped:
                if scoped_by_body is None:
                    issues.append(
                        ThinkingPassIssue(
                            check_name="geometry_observables_scoped",
                            message="Could not compute scoped observables (missing compiled geometry for station_range filtering).",
                            computed={"station_range": list(rng)},
                            expected={"compiled_geometry": True},
                        )
                    )
                    continue

                # Determine body candidates (per existing semantics).
                body_candidates: List[str] = []
                if getattr(ot, "body_id", None):
                    body_candidates = [str(getattr(ot, "body_id"))]
                else:
                    body_candidates = sorted(scoped_by_body.keys())

                best_span: Optional[float] = None
                best_val: Optional[float] = None
                best_bid: Optional[str] = None
                any_sufficient = False
                min_required = _min_required_for_observable(oid)

                for bid in body_candidates:
                    secs_all = scoped_by_body.get(bid) or []
                    secs_in = _sections_in_station_range(secs_all, rng)
                    if len(secs_in) < min_required:
                        continue
                    any_sufficient = True

                    # Compute series on a tiny geometry wrapper.
                    class _G:
                        def __init__(self, sections):
                            self.sections = sections

                    scoped_series = compute_observable_series_from_geometry(_G(secs_in))
                    s = scoped_series.get(f"{bid}:{oid}")
                    if s is None:
                        continue

                    # Record for debugging
                    computed["scoped_observables"][f"{bid}:{oid}:{rng[0]:.6f}-{rng[1]:.6f}"] = {
                        "span": s.span,
                        "samples": len(s.values),
                        "value": float(s.values[0]) if (oid.startswith("longitudinal_metric:") and len(s.values) == 1) else None,
                        "station_range": list(rng),
                    }

                    if oid.startswith("longitudinal_metric:"):
                        v = float(s.values[0]) if len(s.values) == 1 else None
                        if v is None:
                            continue
                        if best_val is None or v > best_val:
                            best_val = v
                            best_bid = bid
                    else:
                        sp = float(s.span) if isinstance(s.span, (int, float)) else None
                        if sp is None:
                            continue
                        if best_span is None or sp > best_span:
                            best_span = sp
                            best_bid = bid

                if not any_sufficient:
                    issues.append(
                        ThinkingPassIssue(
                            check_name=f"INSUFFICIENT_STATIONS:{dn}:{oid}",
                            message=(
                                f"INSUFFICIENT_STATIONS: station_range {list(rng)} contains fewer than {min_required} "
                                f"stations required to measure '{oid}'."
                            ),
                            computed={"found": max((len(_sections_in_station_range(scoped_by_body.get(b, []) or [], rng)) for b in body_candidates), default=0)},
                            expected={"required": min_required},
                        )
                    )
                    continue

                # Apply existing v0.2 semantics against the *scoped* best value/span.
                required = float(getattr(ot, "span_min", 0.0) or 0.0)
                if oid.startswith("longitudinal_metric:"):
                    if best_val is None:
                        issues.append(
                            ThinkingPassIssue(
                                check_name=f"observation_missing:{dn}:{oid}",
                                message=f"No measurable value for longitudinal observable '{oid}' in station_range {list(rng)}.",
                                computed={"station_range": list(rng), "best_body": best_bid},
                                expected={"value": "non-empty"},
                            )
                        )
                        continue
                    if best_val + 1e-12 < required:
                        issues.append(
                            ThinkingPassIssue(
                                check_name=f"threshold_min:{dn}:{oid}",
                                message=(
                                    f"Longitudinal observable '{oid}' below threshold in station_range {list(rng)}: "
                                    f"value={best_val:.6g} < min={required:.6g}"
                                ),
                                computed={"value": best_val, "station_range": list(rng), "best_body": best_bid},
                                expected={"min": required},
                            )
                        )
                    continue
                else:
                    # v0.4 bounds: apply threshold_min/max to a deterministic aggregate (mean of samples in range)
                    agg_mean = None
                    try:
                        # Prefer mean of section samples for magnitude commitments
                        # Recompute for the chosen best body if needed
                        if best_bid is not None:
                            class _G:
                                def __init__(self, sections):
                                    self.sections = sections
                            secs_all = scoped_by_body.get(best_bid) or []
                            secs_in = _sections_in_station_range(secs_all, rng)
                            scoped_series2 = compute_observable_series_from_geometry(_G(secs_in))
                            s2 = scoped_series2.get(f"{best_bid}:{oid}")
                            if s2 and s2.values:
                                agg_mean = float(sum(float(x) for x in s2.values) / len(s2.values))
                    except Exception:
                        agg_mean = None

                    if best_span is None:
                        issues.append(
                            ThinkingPassIssue(
                                check_name=f"observation_missing:{dn}:{oid}",
                                message=f"No measurable samples for observable '{oid}' in station_range {list(rng)}.",
                                computed={"station_range": list(rng), "best_body": best_bid},
                                expected={"span": "non-empty"},
                            )
                        )
                        continue
                    if isinstance(thr_min, (int, float)) and agg_mean is not None and agg_mean + 1e-12 < float(thr_min):
                        issues.append(
                            ThinkingPassIssue(
                                check_name=f"threshold_min:{dn}:{oid}",
                                message=f"Observable '{oid}' below threshold_min in station_range {list(rng)}: mean={agg_mean:.6g} < min={float(thr_min):.6g}",
                                computed={"mean": agg_mean, "station_range": list(rng), "best_body": best_bid},
                                expected={"threshold_min": float(thr_min)},
                            )
                        )
                    if isinstance(thr_max, (int, float)) and agg_mean is not None and agg_mean - 1e-12 > float(thr_max):
                        issues.append(
                            ThinkingPassIssue(
                                check_name=f"threshold_max:{dn}:{oid}",
                                message=f"Observable '{oid}' above threshold_max in station_range {list(rng)}: mean={agg_mean:.6g} > max={float(thr_max):.6g}",
                                computed={"mean": agg_mean, "station_range": list(rng), "best_body": best_bid},
                                expected={"threshold_max": float(thr_max)},
                            )
                        )
                    if best_span + 1e-12 < required:
                        issues.append(
                            ThinkingPassIssue(
                                check_name=f"span_min:{dn}:{oid}",
                                message=(
                                    f"Observable '{oid}' span too small in station_range {list(rng)}: "
                                    f"span={best_span:.6g} < span_min={required:.6g}"
                                ),
                                computed={"span": best_span, "station_range": list(rng), "best_body": best_bid},
                                expected={"span_min": required},
                            )
                        )
                    continue

            # Compute span(s) for specified body or across all bodies
            spans: List[float] = []
            vals: List[float] = []
            if getattr(ot, "body_id", None):
                bid = str(getattr(ot, "body_id"))
                k = f"{bid}:{oid}"
                v = computed["observables"].get(k, {}).get("span")
                vv = computed["observables"].get(k, {}).get("value")
                if isinstance(v, (int, float)):
                    spans.append(float(v))
                if isinstance(vv, (int, float)):
                    vals.append(float(vv))
            else:
                for k, v in computed["observables"].items():
                    if k.endswith(f":{oid}") and isinstance(v.get("span"), (int, float)):
                        spans.append(float(v["span"]))
                    if k.endswith(f":{oid}") and isinstance(v.get("value"), (int, float)):
                        vals.append(float(v["value"]))

            # Longitudinal metrics are validated as thresholds (v0.2): value >= span_min
            if oid.startswith("longitudinal_metric:"):
                if not vals:
                    issues.append(
                        ThinkingPassIssue(
                            check_name=f"observation_missing:{dn}:{oid}",
                            message=f"No measurable value for longitudinal observable '{oid}'.",
                            computed={"values": vals},
                            expected={"values": "non-empty"},
                        )
                    )
                    continue
                required = float(getattr(ot, "span_min", 0.0) or 0.0)
                best = max(vals)  # optimistic across bodies
                if best + 1e-12 < required:
                    issues.append(
                        ThinkingPassIssue(
                            check_name=f"threshold_min:{dn}:{oid}",
                            message=f"Longitudinal observable '{oid}' below threshold: value={best:.6g} < min={required:.6g}",
                            computed={"value": best},
                            expected={"min": required},
                        )
                    )
                # v0.4 bounds: apply threshold_min/max on the same scalar value
                if isinstance(thr_min, (int, float)) and best + 1e-12 < float(thr_min):
                    issues.append(
                        ThinkingPassIssue(
                            check_name=f"threshold_min:{dn}:{oid}",
                            message=f"Longitudinal observable '{oid}' below threshold_min: value={best:.6g} < min={float(thr_min):.6g}",
                            computed={"value": best},
                            expected={"threshold_min": float(thr_min)},
                        )
                    )
                if isinstance(thr_max, (int, float)) and best - 1e-12 > float(thr_max):
                    issues.append(
                        ThinkingPassIssue(
                            check_name=f"threshold_max:{dn}:{oid}",
                            message=f"Longitudinal observable '{oid}' above threshold_max: value={best:.6g} > max={float(thr_max):.6g}",
                            computed={"value": best},
                            expected={"threshold_max": float(thr_max)},
                        )
                    )
                continue

            if not spans:
                issues.append(
                    ThinkingPassIssue(
                        check_name=f"observation_missing:{dn}:{oid}",
                        message=f"No measurable samples for observable '{oid}' (body scope may be wrong or metric undefined).",
                        computed={"spans": spans},
                        expected={"spans": "non-empty"},
                    )
                )
                continue

            required = float(getattr(ot, "span_min", 0.0) or 0.0)
            best = max(spans)  # optimistic across bodies; v0.1 is a minimal guardrail
            if best + 1e-12 < required:
                issues.append(
                    ThinkingPassIssue(
                        check_name=f"span_min:{dn}:{oid}",
                        message=f"Observable '{oid}' span too small to support claimed variation: span={best:.6g} < span_min={required:.6g}",
                        computed={"span": best},
                        expected={"span_min": required},
                    )
                )

    return issues, computed


def reexecute_checks(thinking: VesselThinkingPass) -> Tuple[List[ThinkingPassIssue], Dict[str, Dict[str, Any]]]:
    """
    Re-execute computable checks and compare with the model-reported proof.

    Returns:
    - issues
    - computed_by_check_name (for patch instructions / observability)
    """
    issues: List[ThinkingPassIssue] = []
    computed_by_check: Dict[str, Dict[str, Any]] = {}

    dofs = _dofs_by_name(list(thinking.dof_schema or []))
    proofs = _proof_by_check_name(thinking)

    for c in (thinking.verification_schema or []):
        cn = str(getattr(c, "name", "") or "")
        if not cn:
            continue

        target = str(getattr(c, "target", "") or "")
        dof = dofs.get(target)
        proof = proofs.get(cn)
        proof_result = getattr(proof, "result", None) if proof is not None else None

        # Unexecutable checks (uniform/correspondence) are recorded-only in v0; do not fail.
        if isinstance(c, (CoverageCheck, RangeCheck, MonotonicCheck, VariesCheck)) is False:
            computed_by_check[cn] = {"skipped": True, "reason": "unexecutable_check_type_v0"}
            continue

        if dof is None:
            issues.append(
                ThinkingPassIssue(
                    check_name=cn,
                    message=f"Check '{cn}' targets missing DOF '{target}'.",
                    computed={"target_found": False},
                    expected={"target_found": True},
                )
            )
            continue

        ok = True
        computed: Dict[str, Any] = {}
        expected: Dict[str, Any] = {}

        # ---- range
        if isinstance(c, RangeCheck):
            expected = {"min": float(c.min), "max": float(c.max)}
            if isinstance(dof, ScalarDOF):
                v = float(dof.value)
                ok = (v >= float(c.min)) and (v <= float(c.max))
                computed = {"value": v}
            elif isinstance(dof, ScheduleDOF):
                vals = [float(p.value) for p in (dof.anchor_points or [])]
                if not vals:
                    ok = False
                    computed = {"values": [], "note": "no_anchor_points"}
                else:
                    mn = min(vals)
                    mx = max(vals)
                    ok = (mn >= float(c.min)) and (mx <= float(c.max))
                    computed = {"min_value": mn, "max_value": mx}
            else:
                ok = False
                computed = {"note": f"range_not_applicable_to_dof_type:{type(dof).__name__}"}

        # ---- monotonic
        if isinstance(c, MonotonicCheck):
            expected = {"direction": str(c.direction)}
            if isinstance(dof, ScheduleDOF):
                pts = list(dof.anchor_points or [])
                xs = [float(p.x) for p in pts]
                ys = [float(p.value) for p in pts]
                # assume increasing x; if not, sort by x
                pairs = sorted(zip(xs, ys), key=lambda t: t[0])
                ys2 = [y for _, y in pairs]
                inc = all(ys2[i + 1] >= ys2[i] - 1e-9 for i in range(len(ys2) - 1))
                dec = all(ys2[i + 1] <= ys2[i] + 1e-9 for i in range(len(ys2) - 1))
                if c.direction == "increasing":
                    ok = inc
                elif c.direction == "decreasing":
                    ok = dec
                else:
                    ok = inc or dec
                computed = {"monotonic_increasing": inc, "monotonic_decreasing": dec, "samples": len(ys2)}
            else:
                ok = False
                computed = {"note": "monotonic_requires_schedule"}

        # ---- varies (non-constant)
        if isinstance(c, VariesCheck):
            if isinstance(dof, ScheduleDOF):
                vals = [float(p.value) for p in (dof.anchor_points or [])]
                if len(vals) < 2:
                    ok = False
                    computed = {"values": vals, "note": "insufficient_samples"}
                else:
                    span = max(vals) - min(vals)
                    ok = span > 1e-6
                    computed = {"span": span, "min": min(vals), "max": max(vals)}
                expected = {"span": "> 0"}
            elif isinstance(dof, ScalarDOF):
                # scalar cannot "vary" by definition; this is a schema/design error
                ok = False
                computed = {"value": float(dof.value)}
                expected = {"note": "varies_check_not_applicable_to_scalar"}
            else:
                ok = False
                computed = {"note": f"varies_not_applicable_to_dof_type:{type(dof).__name__}"}

        # ---- coverage (track)
        if isinstance(c, CoverageCheck):
            expected = {"expected_stations": int(c.expected_stations)}
            if isinstance(dof, TrackDOF):
                # Interpret common shapes:
                # - {body_id: [stations...]}
                # - {body_id: {"stations": [...]} }
                stations_total = 0
                stations_unique: List[float] = []
                by_body: Dict[str, int] = {}
                for body_id, cov in (dof.body_coverage or {}).items():
                    st: List[float] = []
                    if isinstance(cov, list):
                        st = [float(x) for x in cov if isinstance(x, (int, float))]
                    elif isinstance(cov, dict) and isinstance(cov.get("stations"), list):
                        st = [float(x) for x in cov.get("stations") if isinstance(x, (int, float))]
                    stations_total += len(st)
                    by_body[str(body_id)] = len(st)
                    stations_unique.extend(st)
                uniq = sorted({round(float(x), 6) for x in stations_unique})
                ok = len(uniq) >= int(c.expected_stations)
                computed = {
                    "unique_stations": len(uniq),
                    "stations_total": stations_total,
                    "by_body_counts": by_body,
                }
            else:
                ok = False
                computed = {"note": "coverage_requires_track"}

        computed_by_check[cn] = dict(computed)

        # Compare to model's proof result if present
        if proof_result in ("PASS", "FAIL"):
            model_ok = proof_result == "PASS"
            if model_ok and not ok:
                issues.append(
                    ThinkingPassIssue(
                        check_name=cn,
                        message=f"Proof mismatch: model reported PASS for '{cn}', but server re-exec failed.",
                        computed={"server": computed, "model": {"result": proof_result}},
                        expected=expected,
                    )
                )
            if (not model_ok) and ok:
                issues.append(
                    ThinkingPassIssue(
                        check_name=cn,
                        message=f"Proof mismatch: model reported FAIL for '{cn}', but server re-exec passed.",
                        computed={"server": computed, "model": {"result": proof_result}},
                        expected=expected,
                    )
                )

        # If server re-exec fails, that's a failure regardless of model result.
        if not ok:
            issues.append(
                ThinkingPassIssue(
                    check_name=cn,
                    message=f"Check '{cn}' failed server-side re-execution.",
                    computed=computed,
                    expected=expected,
                )
            )

    return issues, computed_by_check


def build_targeted_patch_instruction(
    issues: List[ThinkingPassIssue],
    computed_by_check: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    failed = []
    for i in issues:
        if i.check_name.startswith("coverage:dof:"):
            continue
        failed.append(i.check_name)
    return {
        "failed_check_names": sorted(set(failed)),
        "computed": computed_by_check or {},
        "expected": {i.check_name: i.expected for i in issues},
        "instruction": (
            "Regenerate ONLY the affected DOFs and the minimal geometry edits needed to satisfy the failed checks. "
            "Do NOT restart from scratch. Preserve stable ids for existing resources."
        ),
    }

