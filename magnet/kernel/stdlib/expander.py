"""
Expand AST statements into kernel Actions.

The kernel knows geometry, not design.
Agents propose geometric primitives, the kernel validates physics.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
import copy
import math

from .ast_nodes import (
    Program, Statement, CreateStatement, UpdateStatement,
    DeleteStatement, LoftStatement, MirrorStatement,
    AlignStatement, ConstrainStatement, DeriveStatement, SetStatement,
    AdjustStatement, TargetStatement,
)
from .type_registry import get_schema, validate_resource, TYPE_REGISTRY


@dataclass
class Action:
    """Single state modification action."""
    op: str              # "SET", "DELETE"
    path: str            # State path
    value: Any = None    # Value to set
    reason: str = ""     # Why this action was generated (provenance)


@dataclass
class Constraint:
    """Constraint to be checked after compilation."""
    path: str
    operator: str  # ">=", "<=", "==", ">", "<"
    value: float
    priority: str  # "hard" or "soft"
    source_line: int = 0


@dataclass
class ExpansionResult:
    """Result of expanding a program."""
    actions: List[Action] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ExpansionError(Exception):
    """Raised when expansion fails."""
    def __init__(self, message: str, line: int = 0):
        self.line = line
        super().__init__(f"Line {line}: {message}" if line else message)


def expand(program: Program, current_state: Dict = None) -> ExpansionResult:
    """
    Expand design program AST into kernel Actions.
    
    This is the SEMANTIC layer - validates types, expands operations,
    collects constraints.
    """
    result = ExpansionResult()
    current_state = current_state or {}
    working_state = copy.deepcopy(current_state)
    
    # Ensure resources dict exists
    if "resources" not in working_state:
        working_state["resources"] = {}
    
    for stmt in program.statements:
        try:
            stmt_actions, stmt_constraints = _expand_statement(stmt, working_state)
            result.actions.extend(stmt_actions)
            result.constraints.extend(stmt_constraints)
            
            # Update working state for subsequent statements
            for action in stmt_actions:
                if action.op == "SET":
                    _set_nested(working_state, action.path, action.value)
        
        except ExpansionError as e:
            result.errors.append(str(e))
        except Exception as e:
            result.errors.append(f"Line {stmt.line_number}: {e}")
    
    return result


def _expand_statement(stmt: Statement, state: Dict) -> tuple:
    """Expand a single statement into (Actions, Constraints)."""
    
    if isinstance(stmt, CreateStatement):
        return _expand_create(stmt), []
    
    elif isinstance(stmt, UpdateStatement):
        return _expand_update(stmt, state), []
    
    elif isinstance(stmt, DeleteStatement):
        return _expand_delete(stmt, state), []
    
    elif isinstance(stmt, SetStatement):
        return _expand_set(stmt), []
    
    elif isinstance(stmt, LoftStatement):
        return _expand_loft(stmt, state), []
    
    elif isinstance(stmt, MirrorStatement):
        return _expand_mirror(stmt, state), []
    
    elif isinstance(stmt, AlignStatement):
        return _expand_align(stmt, state), []
    
    elif isinstance(stmt, ConstrainStatement):
        return [], [_expand_constrain(stmt)]
    
    elif isinstance(stmt, DeriveStatement):
        return _expand_derive(stmt, state), []

    elif isinstance(stmt, AdjustStatement):
        return _expand_adjust(stmt, state), []

    elif isinstance(stmt, TargetStatement):
        return _expand_target(stmt, state), []
    
    else:
        raise ExpansionError(f"Unknown statement type: {type(stmt).__name__}")


def _section_ids_in_body(state: Dict, body_id: str) -> List[str]:
    resources = state.get("resources", {}) or {}
    out: List[tuple] = []
    for rid, r in resources.items():
        if not isinstance(r, dict) or r.get("_deleted"):
            continue
        if r.get("_type") != "geometry.section":
            continue
        if str(r.get("body_id") or "main") != str(body_id):
            continue
        try:
            st = float(r.get("station"))
        except Exception:
            st = 0.0
        out.append((st, str(rid)))
    out.sort(key=lambda t: t[0])
    return [rid for _st, rid in out]


def _identity_snapshot(state: Dict, body_id: str) -> Dict[str, Any]:
    ids = _section_ids_in_body(state, body_id)
    resources = state.get("resources", {}) or {}
    stations = []
    for rid in ids:
        r = resources.get(rid) or {}
        try:
            stations.append(float(r.get("station")))
        except Exception:
            stations.append(None)
    return {"section_ids": ids, "stations": stations}


def _assert_identity_continuity(before: Dict[str, Any], after: Dict[str, Any], line: int) -> None:
    if before.get("section_ids") != after.get("section_ids"):
        raise ExpansionError(
            f"EDIT identity continuity violated: section IDs changed (before={before.get('section_ids')}, after={after.get('section_ids')})",
            line,
        )
    if len(before.get("section_ids") or []) != len(after.get("section_ids") or []):
        raise ExpansionError(
            "EDIT identity continuity violated: section count changed",
            line,
        )
    if before.get("stations") != after.get("stations"):
        raise ExpansionError(
            "EDIT identity continuity violated: station ordering/values changed",
            line,
        )


def _validate_section_points(points: Any, *, line: int) -> None:
    """
    Post-transform geometry validity checks (Phase 1 minimal):
    - point count unchanged (enforced by caller)
    - y >= 0
    - z strictly increasing
    - no collapsed segments (dz > 1e-9)
    """
    if not isinstance(points, list) or len(points) < 2:
        raise ExpansionError("Invalid section points: expected list of at least 2 points", line)
    prev_z = None
    for p in points:
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            raise ExpansionError("Invalid section point: expected [y,z]", line)
        y, z = p[0], p[1]
        if not isinstance(y, (int, float)) or not isinstance(z, (int, float)):
            raise ExpansionError("Invalid section point: y/z must be numeric", line)
        if y < -1e-9:
            raise ExpansionError("Invalid section point: y must be non-negative", line)
        if prev_z is not None:
            if z <= prev_z + 1e-9:
                raise ExpansionError("Invalid section points: z must be strictly increasing", line)
        prev_z = z


def _get_anchor_cache(state: Dict) -> Dict[str, Any]:
    meta = state.get("metadata")
    if not isinstance(meta, dict):
        return {}
    cache = meta.get("anchor_witness_cache")
    if not isinstance(cache, dict):
        return {}
    return cache


def _set_anchor_cache(state: Dict, cache: Dict[str, Any]) -> None:
    meta = state.get("metadata")
    if not isinstance(meta, dict):
        meta = {}
        state["metadata"] = meta
    meta["anchor_witness_cache"] = cache


def _anchor_cache_key(*, body_id: str, section_id: str, observable_id: str) -> str:
    return f"{body_id}:{section_id}:{observable_id}"


def _expand_adjust(stmt: AdjustStatement, state: Dict) -> List[Action]:
    from magnet.kernel.geometry_observables import (
        get_observable_spec,
        _sections_for_scope,
        measure_section_metric_deadrise_deg_at_chine,
        measure_section_metric_max_half_beam_m,
        measure_section_metric_sheer_z_m,
    )

    spec = get_observable_spec(stmt.observable_id)
    if spec is None:
        raise ExpansionError(f"Unknown observable_id: {stmt.observable_id}", stmt.line_number)
    if not spec.controllable:
        raise ExpansionError(f"Observable is not controllable in Phase 1: {stmt.observable_id}", stmt.line_number)
    if str(spec.unit or "") != str(stmt.unit or ""):
        raise ExpansionError(f"Unit mismatch for {stmt.observable_id}: expected {spec.unit}, got {stmt.unit}", stmt.line_number)
    if spec.max_delta and abs(float(stmt.delta)) > float(spec.max_delta) + 1e-9:
        raise ExpansionError(f"Delta too large for {stmt.observable_id}: |{stmt.delta}| > {spec.max_delta}", stmt.line_number)

    scope = stmt.scope or {}
    body_id = str(scope.get("body_id") or "main")
    station_range = scope.get("station_range")
    station = scope.get("station")

    before = _identity_snapshot(state, body_id)

    resources = state.get("resources", {}) or {}
    targets = _sections_for_scope(
        resources=resources,
        body_id=body_id,
        station_range=station_range,
        station=station,
    )
    if not targets:
        raise ExpansionError("ADJUST scope selects no sections", stmt.line_number)

    cache = _get_anchor_cache(state)
    receipt = {
        "op": "ADJUST",
        "observable_id": stmt.observable_id,
        "scope": dict(scope),
        "requested_delta": float(stmt.delta),
        "unit": str(stmt.unit),
        "affected_sections": [rid for rid, _r in targets],
        "achieved": [],
        "committed": True,
        "diagnostics": {
            "sections_affected": len(targets),
            "points_before": {},
            "points_after": {},
            "validation_errors": [],
        },
    }

    actions: List[Action] = []
    for sec_id, sec in targets:
        if not isinstance(sec, dict):
            continue
        pts = list(sec.get("points") or [])
        n_before = len(pts)
        if n_before < 2:
            raise ExpansionError(f"Section {sec_id} has insufficient points", stmt.line_number)
        
        # Capture before state for diagnostics
        receipt["diagnostics"]["points_before"][sec_id] = {
            "count": n_before,
            "points": [[float(y), float(z)] for y, z in pts],
        }

        key = _anchor_cache_key(body_id=body_id, section_id=sec_id, observable_id=stmt.observable_id)
        witness_index = None
        if key in cache and isinstance(cache.get(key), dict):
            wi = cache[key].get("witness_index")
            if isinstance(wi, int) and 0 <= wi < n_before:
                witness_index = int(wi)

        # Apply DIRECT mapping
        if stmt.observable_id == "section_metric:max_half_beam_m":
            meas = measure_section_metric_max_half_beam_m(sec)
            if meas is None or not getattr(meas, "is_valid", False):
                msg = getattr(getattr(meas, "violation", None), "message", None) if meas is not None else None
                raise ExpansionError(
                    f"Cannot measure max_half_beam_m on {sec_id}" + (f" ({msg})" if msg else ""),
                    stmt.line_number,
                )
            current = float(meas.value)
            target_val = max(0.0, current + float(stmt.delta))
            if current <= 1e-12:
                scale = 1.0
            else:
                scale = target_val / current
            new_pts = []
            for y, z in pts:
                new_pts.append([max(0.0, float(y) * float(scale)), float(z)])
            _validate_section_points(new_pts, line=stmt.line_number)
            if len(new_pts) != n_before:
                raise ExpansionError("Point count changed (illegal in EDIT mode)", stmt.line_number)
            sec["points"] = new_pts
            # Update cache witness (max-y index is stable after scaling)
            cache[key] = {"witness_index": int(meas.witness_index) if meas.witness_index is not None else None}
            receipt["achieved"].append({"section_id": sec_id, "before": current, "after": target_val, "witness_index": meas.witness_index})

        elif stmt.observable_id == "section_metric:sheer_z_m":
            # v1 spec: distributed move on top-3 points by z with linear falloff weights
            # Points affected: top 3 points by z-index per section
            # Weight: [1.0, 0.6, 0.3] from top
            # Constraints:
            # - maintain min 5mm between adjacent points
            # - preserve z-monotonicity in topside region
            pts_f = [(float(y), float(z)) for (y, z) in pts]
            if len(pts_f) < 3:
                raise ExpansionError(f"Section {sec_id} has insufficient points for sheer_z_m", stmt.line_number)

            idx_sorted = sorted(range(len(pts_f)), key=lambda i: pts_f[i][1], reverse=True)
            top3 = idx_sorted[:3]
            weights = [1.0, 0.6, 0.3]
            dz = float(stmt.delta)

            # Measure "current" as top point z (for receipt)
            current = float(pts_f[top3[0]][1])

            new_pts = []
            for i, (y, z) in enumerate(pts_f):
                if i in top3:
                    w = weights[top3.index(i)]
                    new_pts.append([float(y), float(z) + dz * float(w)])
                else:
                    new_pts.append([float(y), float(z)])

            _validate_section_points(new_pts, line=stmt.line_number)

            # Constraint: min 5mm between adjacent points
            for i in range(len(new_pts) - 1):
                y1, z1 = new_pts[i]
                y2, z2 = new_pts[i + 1]
                dist = math.hypot(float(y2) - float(y1), float(z2) - float(z1))
                if dist < 0.005:
                    raise ExpansionError(f"sheer_z_m would collapse segment at point {i} (<5mm)", stmt.line_number)

            # Constraint: preserve z-monotonicity in topside region (top3 remain strictly decreasing)
            top_zs = [float(new_pts[i][1]) for i in top3]
            if not (top_zs[0] > top_zs[1] > top_zs[2]):
                raise ExpansionError("sheer_z_m violated topside z-monotonicity (top3)", stmt.line_number)

            sec["points"] = new_pts
            # Cache top point index as witness
            cache[key] = {"witness_index": int(top3[0])}
            receipt["achieved"].append({"section_id": sec_id, "before": current, "after": float(current + dz), "witness_index": int(top3[0])})

        elif stmt.observable_id == "section_metric:deadrise_deg_at_chine":
            meas = measure_section_metric_deadrise_deg_at_chine(sec, witness_index=witness_index)
            if meas is None or not getattr(meas, "is_valid", False) or meas.witness_index is None:
                msg = getattr(getattr(meas, "violation", None), "message", None) if meas is not None else None
                raise ExpansionError(
                    f"Cannot measure deadrise at chine on {sec_id}" + (f" ({msg})" if msg else ""),
                    stmt.line_number,
                )
            ci = int(meas.witness_index)
            current = float(meas.value)
            target_beta = max(0.0, current + float(stmt.delta))

            # v1 spec:
            # - Points affected: keel to chine (indices keel..chine)
            # - Method: adjust bottom region about keel so beta matches target (keep y fixed; update z)
            # - Constraint: chine point y preserved
            # - Constraint: no segment inversion / collapse
            pts_yz = [(float(y), float(z)) for (y, z) in pts]
            keel_i = min(range(len(pts_yz)), key=lambda i: pts_yz[i][1])
            ky, kz = pts_yz[keel_i]
            cy, cz = pts_yz[ci]
            dy_ch = abs(cy - ky)
            if dy_ch <= 1e-6:
                raise ExpansionError(f"Cannot adjust deadrise: chine dy too small on {sec_id}", stmt.line_number)

            sign = 1.0 if cz >= kz else -1.0
            slope = math.tan(math.radians(float(target_beta)))

            lo = min(keel_i, ci)
            hi = max(keel_i, ci)
            new_pts = []
            for i, (y, z) in enumerate(pts_yz):
                if lo <= i <= hi:
                    dy = abs(float(y) - float(ky))
                    new_z = float(kz) + float(sign) * float(slope) * float(dy)
                    new_pts.append([float(y), float(new_z)])
                else:
                    new_pts.append([float(y), float(z)])

            _validate_section_points(new_pts, line=stmt.line_number)

            # Basic inversion/collapse guard in bottom region
            for i in range(lo, hi):
                y1, z1 = new_pts[i]
                y2, z2 = new_pts[i + 1]
                dist = math.hypot(float(y2) - float(y1), float(z2) - float(z1))
                if dist < 0.005:
                    raise ExpansionError(f"deadrise adjustment would collapse segment at point {i} (<5mm)", stmt.line_number)

            sec["points"] = new_pts
            cache[key] = {"witness_index": ci}
            receipt["achieved"].append({"section_id": sec_id, "before": current, "after": target_beta, "witness_index": ci})

        else:
            raise ExpansionError(f"No DIRECT control mapping for {stmt.observable_id}", stmt.line_number)

        # Capture after state for diagnostics
        new_pts_diag = sec.get("points", [])
        receipt["diagnostics"]["points_after"][sec_id] = {
            "count": len(new_pts_diag),
            "points": [[float(y), float(z)] for y, z in new_pts_diag],
        }
        
        # Validate geometry doesn't collapse
        try:
            pts_array = sec.get("points", [])
            if len(pts_array) < 3:
                raise ValueError("Section has < 3 points after ADJUST")
            # Check for collapsed segments (adjacent points too close)
            for i in range(len(pts_array) - 1):
                y1, z1 = pts_array[i]
                y2, z2 = pts_array[i + 1]
                dist = math.hypot(float(y2) - float(y1), float(z2) - float(z1))
                if dist < 1e-6:
                    raise ValueError(f"Collapsed segment at point {i}")
        except Exception as e:
            receipt["diagnostics"]["validation_errors"].append({
                "section_id": sec_id,
                "error": str(e),
            })
        
        # Persist section resource update
        actions.append(
            Action(op="SET", path=f"resources.{sec_id}", value=dict(sec), reason=f"ADJUST {stmt.observable_id} ({sec_id})")
        )

    _set_anchor_cache(state, cache)

    after = _identity_snapshot(state, body_id)
    _assert_identity_continuity(before, after, stmt.line_number)

    # Atomic receipt (stored in state metadata)
    actions.append(Action(op="SET", path="metadata.last_edit_receipt", value=receipt, reason="ADJUST receipt"))
    actions.append(Action(op="SET", path="metadata.anchor_witness_cache", value=cache, reason="ADJUST witness cache"))

    return actions


def _expand_target(stmt: TargetStatement, state: Dict) -> List[Action]:
    # Phase 1: TARGET implemented only for controllable section metrics by converting to ADJUST (measure->delta)
    from magnet.kernel.geometry_observables import get_observable_spec

    spec = get_observable_spec(stmt.observable_id)
    if spec is None:
        raise ExpansionError(f"Unknown observable_id: {stmt.observable_id}", stmt.line_number)
    if not spec.controllable:
        raise ExpansionError(f"Observable is not controllable in Phase 1: {stmt.observable_id}", stmt.line_number)
    if str(spec.unit or "") != str(stmt.unit or ""):
        raise ExpansionError(f"Unit mismatch for {stmt.observable_id}: expected {spec.unit}, got {stmt.unit}", stmt.line_number)

    # Convert to ADJUST by measuring at the first selected section and applying per-section (DIRECT)
    # This keeps behavior deterministic but simple for v0.
    # Note: in Phase 2, TARGET becomes its own compiled/optimized operator with convergence checks.
    from magnet.kernel.geometry_observables import (
        _sections_for_scope,
        measure_section_metric_deadrise_deg_at_chine,
        measure_section_metric_max_half_beam_m,
        measure_section_metric_sheer_z_m,
    )

    scope = stmt.scope or {}
    body_id = str(scope.get("body_id") or "main")
    station_range = scope.get("station_range")
    station = scope.get("station")

    resources = state.get("resources", {}) or {}
    targets = _sections_for_scope(
        resources=resources,
        body_id=body_id,
        station_range=station_range,
        station=station,
    )
    if not targets:
        raise ExpansionError("TARGET scope selects no sections", stmt.line_number)

    # Measure on first selected section to compute delta, then run ADJUST path.
    sec_id0, sec0 = targets[0]
    cache = _get_anchor_cache(state)
    key0 = _anchor_cache_key(body_id=body_id, section_id=sec_id0, observable_id=stmt.observable_id)
    witness_index0 = None
    if key0 in cache and isinstance(cache.get(key0), dict):
        wi = cache[key0].get("witness_index")
        if isinstance(wi, int) and 0 <= wi < len((sec0 or {}).get("points") or []):
            witness_index0 = int(wi)

    meas0 = None
    if stmt.observable_id == "section_metric:max_half_beam_m":
        meas0 = measure_section_metric_max_half_beam_m(sec0)
    elif stmt.observable_id == "section_metric:sheer_z_m":
        meas0 = measure_section_metric_sheer_z_m(sec0, witness_index=witness_index0)
    elif stmt.observable_id == "section_metric:deadrise_deg_at_chine":
        meas0 = measure_section_metric_deadrise_deg_at_chine(sec0, witness_index=witness_index0)
    else:
        raise ExpansionError(f"No TARGET mapping for {stmt.observable_id} in Phase 1", stmt.line_number)

    if meas0 is None:
        raise ExpansionError(f"Cannot measure {stmt.observable_id} to compute TARGET delta", stmt.line_number)
    if hasattr(meas0, "is_valid") and not meas0.is_valid:
        msg = getattr(getattr(meas0, "violation", None), "message", None)
        raise ExpansionError(
            f"Cannot measure {stmt.observable_id} to compute TARGET delta" + (f" ({msg})" if msg else ""),
            stmt.line_number,
        )

    delta = float(stmt.value) - float(meas0.value)
    return _expand_adjust(
        AdjustStatement(
            observable_id=stmt.observable_id,
            scope=dict(scope),
            delta=delta,
            unit=str(stmt.unit),
            line_number=stmt.line_number,
        ),
        state,
    )


def _expand_create(stmt: CreateStatement) -> List[Action]:
    """Expand CREATE into SET action."""
    # Validate against schema
    # Normalize schema aliases before validating and persisting
    from .type_registry import _normalize_properties
    normalized_props = _normalize_properties(stmt.resource_type, stmt.properties)
    errors = validate_resource(stmt.resource_type, normalized_props)
    if errors:
        raise ExpansionError(
            f"CREATE {stmt.resource_id}: {'; '.join(errors)}",
            stmt.line_number
        )
    
    # Build properties with defaults
    properties = dict(normalized_props)
    properties["_type"] = stmt.resource_type
    properties["_id"] = stmt.resource_id
    
    # Apply defaults from schema
    schema = get_schema(stmt.resource_type)
    if schema:
        properties = schema.apply_defaults(properties)
    
    path = f"resources.{stmt.resource_id}"
    return [Action(
        op="SET",
        path=path,
        value=properties,
        reason=f"CREATE {stmt.resource_type} {stmt.resource_id}"
    )]


def _expand_update(stmt: UpdateStatement, state: Dict) -> List[Action]:
    """Expand UPDATE into SET action(s)."""
    path = f"resources.{stmt.resource_id}"
    existing = _get_nested(state, path)
    
    if not existing:
        raise ExpansionError(
            f"UPDATE {stmt.resource_id}: resource does not exist",
            stmt.line_number
        )
    
    # Merge properties
    updated = dict(existing)
    updated.update(stmt.properties)

    # Validate updates too (critical control-plane invariant).
    # Without this, CREATE is validated but UPDATE can silently corrupt the grammar
    # (e.g., geometry.section.points emitted as [x,y,z] triples).
    resource_type = updated.get("_type") or existing.get("_type") or ""
    if resource_type:
        from .type_registry import _normalize_properties
        normalized_props = _normalize_properties(resource_type, updated)
        errors = validate_resource(resource_type, normalized_props)
        if errors:
            raise ExpansionError(
                f"UPDATE {stmt.resource_id}: {'; '.join(errors)}",
                stmt.line_number,
            )
        updated = dict(normalized_props)
    
    return [Action(
        op="SET",
        path=path,
        value=updated,
        reason=f"UPDATE {stmt.resource_id}"
    )]


def _expand_delete(stmt: DeleteStatement, state: Dict) -> List[Action]:
    """
    Expand DELETE into tombstone action.

    Referential integrity rule:
    - A geometry.body MUST NOT be deleted while any non-deleted resources still reference it
      (sections, surfaces, discontinuities, attachments).
    """
    rid = stmt.resource_id
    path = f"resources.{rid}"
    existing = _get_nested(state, path)

    # If deleting a body, ensure nothing still references it (otherwise compilation silently drops it).
    if isinstance(existing, dict) and existing.get("_type") == "geometry.body":
        resources = state.get("resources", {}) or {}
        refs = []
        for other_id, r in resources.items():
            if not isinstance(r, dict) or r.get("_deleted"):
                continue
            rtype = r.get("_type")
            if rtype in ("geometry.section", "geometry.surface", "geometry.discontinuity"):
                if r.get("body_id") == rid:
                    refs.append(other_id)
            if rtype == "geometry.attachment":
                if r.get("parent_body_id") == rid or r.get("child_body_id") == rid:
                    refs.append(other_id)
        if refs:
            raise ExpansionError(
                f"DELETE {rid}: body is still referenced by resources: {sorted(refs)[:5]} (and others)"
                if len(refs) > 5
                else f"DELETE {rid}: body is still referenced by resources: {sorted(refs)}",
                stmt.line_number,
            )

    return [Action(
        op="SET",
        path=f"{path}._deleted",
        value=True,
        reason=f"DELETE {rid}"
    )]


def _expand_set(stmt: SetStatement) -> List[Action]:
    """Expand SET into direct value assignment."""
    return [Action(
        op="SET",
        path=stmt.path,
        value=stmt.value,
        reason=f"SET {stmt.path} = {stmt.value}"
    )]


def _expand_loft(stmt: LoftStatement, state: Dict) -> List[Action]:
    """Expand LOFT into surface creation."""
    # Verify all sections exist
    missing = []
    for section_id in stmt.section_ids:
        section_path = f"resources.{section_id}"
        section = _get_nested(state, section_path)
        if not section or section.get("_deleted"):
            missing.append(section_id)
    
    if missing:
        raise ExpansionError(
            f"LOFT: sections do not exist: {missing}",
            stmt.line_number
        )
    
    # Determine body_id from first section
    first_section = _get_nested(state, f"resources.{stmt.section_ids[0]}")
    body_id = first_section.get("body_id", "main")
    
    surface = {
        "_type": "geometry.surface",
        "_id": stmt.surface_id,
        "definition": "lofted",
        # Truthfulness intent default: callers may override via stmt.options.
        # (e.g., LOFT hull_shell FROM [...] surface_definition="panelized")
        "surface_definition": "smooth",
        "section_ids": list(stmt.section_ids),
        "surface_type": "hull_shell",
        "body_id": body_id,
    }
    surface.update(stmt.options)
    
    return [Action(
        op="SET",
        path=f"resources.{stmt.surface_id}",
        value=surface,
        reason=f"LOFT {stmt.surface_id} from {stmt.section_ids}"
    )]


def _expand_mirror(stmt: MirrorStatement, state: Dict) -> List[Action]:
    """Expand MIRROR into mirrored resource creation."""
    source_path = f"resources.{stmt.source_id}"
    source = _get_nested(state, source_path)
    
    if not source or source.get("_deleted"):
        raise ExpansionError(
            f"MIRROR: source '{stmt.source_id}' does not exist",
            stmt.line_number
        )
    
    resource_type = source.get("_type", "")
    schema = get_schema(resource_type)
    
    if schema and not schema.mirrorable:
        raise ExpansionError(
            f"MIRROR: {resource_type} is not mirrorable",
            stmt.line_number
        )
    
    # Create mirrored copy
    mirrored = dict(source)
    mirrored["_id"] = stmt.target_id
    mirrored["_mirrored_from"] = stmt.source_id
    
    # Mirror Y-axis fields
    mirror_fields = schema.mirror_fields if schema else ["offset_y_m"]
    for field_name in mirror_fields:
        if field_name in mirrored:
            value = mirrored[field_name]
            if isinstance(value, (int, float)):
                mirrored[field_name] = -value
            elif isinstance(value, list) and len(value) >= 2:
                # Mirror Y coordinate (index 1)
                mirrored[field_name] = list(value)
                mirrored[field_name][1] = -value[1]
    
    return [Action(
        op="SET",
        path=f"resources.{stmt.target_id}",
        value=mirrored,
        reason=f"MIRROR {stmt.source_id} as {stmt.target_id}"
    )]


def _expand_align(stmt: AlignStatement, state: Dict) -> List[Action]:
    """Expand ALIGN into position adjustment."""
    source_path = f"resources.{stmt.resource_id}"
    source = _get_nested(state, source_path)
    
    if not source or source.get("_deleted"):
        raise ExpansionError(
            f"ALIGN: resource '{stmt.resource_id}' does not exist",
            stmt.line_number
        )
    
    target_path = f"resources.{stmt.target_id}"
    target = _get_nested(state, target_path)
    
    if not target or target.get("_deleted"):
        raise ExpansionError(
            f"ALIGN: target '{stmt.target_id}' does not exist",
            stmt.line_number
        )
    
    # Get target position on axis
    axis_field = f"offset_{stmt.axis}_m"
    target_value = target.get(axis_field, 0.0)
    
    # Update source
    updated = dict(source)
    updated[axis_field] = target_value
    
    return [Action(
        op="SET",
        path=source_path,
        value=updated,
        reason=f"ALIGN {stmt.resource_id} to {stmt.target_id} on {stmt.axis} axis"
    )]


def _expand_constrain(stmt: ConstrainStatement) -> Constraint:
    """Convert CONSTRAIN statement to Constraint object."""
    return Constraint(
        path=stmt.path,
        operator=stmt.operator,
        value=stmt.value,
        priority=stmt.priority,
        source_line=stmt.line_number
    )


def _expand_derive(stmt: DeriveStatement, state: Dict) -> List[Action]:
    """Expand DERIVE by invoking policy."""
    from .policies import invoke_policy
    
    # Resolve input paths to values
    resolved_inputs = {}
    for key, value_or_path in stmt.inputs.items():
        # Check if it's a path reference or a literal
        if value_or_path.startswith(("hull.", "resources.", "mission.")):
            resolved = _get_nested(state, value_or_path)
            if resolved is None:
                raise ExpansionError(
                    f"DERIVE: input '{value_or_path}' not found",
                    stmt.line_number
                )
            resolved_inputs[key] = resolved
        else:
            # Literal value - try to parse as number
            try:
                resolved_inputs[key] = float(value_or_path)
            except ValueError:
                resolved_inputs[key] = value_or_path
    
    # Invoke policy
    try:
        result = invoke_policy(stmt.policy_name, resolved_inputs)
    except Exception as e:
        raise ExpansionError(
            f"DERIVE policy '{stmt.policy_name}' failed: {e}",
            stmt.line_number
        )
    
    return [Action(
        op="SET",
        path=stmt.target_path,
        value=result,
        reason=f"DERIVE {stmt.target_path} from {stmt.policy_name}({stmt.inputs})"
    )]


# =============================================================================
# Helper functions
# =============================================================================

def _get_nested(obj: Dict, path: str) -> Any:
    """Get nested value from dict using dot notation."""
    parts = path.split('.')
    current = obj
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
        if current is None:
            return None
    return current


def _set_nested(obj: Dict, path: str, value: Any) -> None:
    """Set nested value in dict using dot notation."""
    parts = path.split('.')
    current = obj
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


