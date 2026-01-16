"""
Expand AST statements into kernel Actions.

The kernel knows geometry, not design.
Agents propose geometric primitives, the kernel validates physics.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
import copy

from .ast_nodes import (
    Program, Statement, CreateStatement, UpdateStatement,
    DeleteStatement, LoftStatement, MirrorStatement,
    AlignStatement, ConstrainStatement, DeriveStatement, SetStatement
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
    
    else:
        raise ExpansionError(f"Unknown statement type: {type(stmt).__name__}")


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


