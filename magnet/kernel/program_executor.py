"""
Execute design programs end-to-end.

Pipeline:
1. Parse program text → AST
2. Expand AST → Actions
3. Apply actions to state
4. Compile state → HullGeometry
5. Run validation → Quantified feedback

The kernel validates physics, not design intent.
Novel forms work without new code.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
import logging
import copy

from magnet.kernel.stdlib.parser import parse, ParseError
from magnet.kernel.stdlib.ast_nodes import AskStatement
from magnet.kernel.stdlib.expander import (
    expand, 
    ExpansionError, 
    ExpansionResult,
    Action,
    Constraint,
)
from magnet.kernel.stdlib.compiler import compile_to_geometry, CompilationError

logger = logging.getLogger(__name__)


class LockedParameterError(Exception):
    """Raised when attempting to modify a locked parameter (TASK-008)."""
    pass


@dataclass
class ValidationResult:
    """Physics validation result with quantified feedback."""
    passes: bool
    metric_name: str
    value: float
    required: Optional[float] = None
    unit: str = ""
    confidence: float = 1.0
    method: str = ""
    recommendation: Optional[str] = None


@dataclass
class ExecutionResult:
    """Result of program execution."""
    success: bool
    actions: List[Action] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    geometry: Optional[Any] = None
    validation: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    # TASK-016: explicit clarification support (ASK op)
    needs_clarification: bool = False
    clarification: Optional[Dict[str, Any]] = None


def execute_program(
    program_text: str,
    state_manager: Any = None,
    initial_state: Dict[str, Any] = None,
    dry_run: bool = False,
    validate: bool = True,
) -> ExecutionResult:
    """
    Execute a design program.
    
    Pipeline:
    1. Parse program text → AST
    2. Expand AST → Actions
    3. Apply actions to state (unless dry_run)
    4. Compile state → HullGeometry
    5. Run validation (unless disabled)
    
    Args:
        program_text: Design program source code
        state_manager: StateManager instance (optional)
        initial_state: Initial state dict (used if state_manager not provided)
        dry_run: If True, don't commit actions to state_manager
        validate: If True, run physics validation
    
    Returns:
        ExecutionResult with geometry and validation
    """
    result = ExecutionResult(success=False)
    
    # Get initial state
    if state_manager is not None:
        current_state = state_manager.to_dict() if hasattr(state_manager, 'to_dict') else {}
    else:
        current_state = initial_state or {}
    
    # Ensure resources dict exists
    if "resources" not in current_state:
        current_state["resources"] = {}
    
    # 1. Parse
    try:
        ast = parse(program_text)
    except ParseError as e:
        result.errors.append(f"Parse error: {e}")
        return result

    # TASK-016: Intercept ASK and return structured clarification request (no side effects)
    for stmt in getattr(ast, "statements", []) or []:
        if isinstance(stmt, AskStatement):
            result.success = False
            result.needs_clarification = True
            result.clarification = {
                "question": stmt.question,
                "options": stmt.options,
                "line_number": stmt.line_number,
            }
            return result
    
    logger.debug(f"Parsed {len(ast.statements)} statements")
    
    # 2. Expand
    try:
        expansion = expand(ast, current_state)
        result.actions = expansion.actions
        result.constraints = expansion.constraints
        
        if expansion.errors:
            result.errors.extend(expansion.errors)
            return result
            
    except ExpansionError as e:
        result.errors.append(f"Expansion error: {e}")
        return result
    
    logger.debug(f"Expanded to {len(result.actions)} actions")
    
    # TASK-008: Check lock enforcement BEFORE applying any actions
    if state_manager is not None and hasattr(state_manager, "is_locked"):
        for action in result.actions:
            if action.op == "SET" and state_manager.is_locked(action.path):
                result.errors.append(f"Cannot modify locked parameter: {action.path}")
                return result
    
    # 3. Apply actions to WORKING STATE ONLY (atomic execution)
    # We only commit to state_manager after ALL steps succeed
    working_state = copy.deepcopy(current_state)
    
    for action in result.actions:
        if action.op == "SET":
            _set_nested(working_state, action.path, action.value)
    
    # 4. Compile (still using working state - no commit yet)
    try:
        result.geometry = compile_to_geometry(working_state)
    except CompilationError as e:
        result.errors.append(f"Compilation error: {e}")
        # DO NOT commit - working_state is discarded
        return result
    except Exception as e:
        # Never allow KeyError(...) to degrade into a useless "0" message.
        result.errors.append(f"Unexpected compilation error ({type(e).__name__}): {e!r}")
        # DO NOT commit - working_state is discarded
        return result
    
    logger.debug("Compiled geometry successfully")
    
    # 5. Validate
    if validate and result.geometry:
        result.validation = _run_validation(
            result.geometry, 
            working_state,
            result.constraints,
        )
    
    # Check constraint violations
    constraint_violations = result.validation.get("constraint_violations", [])
    if constraint_violations:
        for cv in constraint_violations:
            if cv.get("priority") == "hard":
                result.warnings.append(f"Constraint violated: {cv}")
    
    # 6. ONLY NOW commit to state_manager if:
    #    - not dry_run
    #    - no errors occurred
    #    - all steps succeeded
    result.success = len(result.errors) == 0
    
    if result.success and not dry_run and state_manager is not None:
        def _apply_set(sm: Any, path: str, value: Any, source: str) -> None:
            """
            Apply a SET to the provided state manager.

            - Real StateManager requires `source` (provenance).
            - Test mocks may only accept (path, value).
            """
            if not hasattr(sm, "set"):
                return
            try:
                # Preferred: keyword `source` (real StateManager)
                sm.set(path, value, source=source)
            except TypeError:
                # Fallback: positional (path, value, source)
                try:
                    sm.set(path, value, source)
                except TypeError:
                    # Test mock fallback: (path, value)
                    sm.set(path, value)

        # Best-effort transactional commit if supported
        txn_id = None
        try:
            if hasattr(state_manager, "begin_transaction") and hasattr(state_manager, "rollback_transaction"):
                txn_id = state_manager.begin_transaction()

            for action in result.actions:
                if action.op == "SET":
                    # TASK-008: Check lock enforcement before mutation
                    if hasattr(state_manager, "is_locked") and state_manager.is_locked(action.path):
                        raise LockedParameterError(f"Cannot modify locked parameter: {action.path}")
                    _apply_set(state_manager, action.path, action.value, action.reason or "program_executor")

            if txn_id and hasattr(state_manager, "commit"):
                state_manager.commit()
            logger.debug(f"Committed {len(result.actions)} actions to state_manager")

        except Exception as e:
            if txn_id:
                try:
                    state_manager.rollback_transaction(txn_id)
                except Exception:
                    pass
            result.success = False
            result.errors.append(str(e))
    
    return result


def execute_program_json(
    program_json: Dict[str, Any],
    state_manager: Any = None,
    initial_state: Dict[str, Any] = None,
    dry_run: bool = False,
) -> ExecutionResult:
    """
    Execute a design program from JSON format.
    
    JSON format:
    {
        "operations": [
            {"op": "CREATE", "type": "geometry.section", "id": "bow", "params": {...}},
            {"op": "SET", "path": "hull.beam", "value": 4.5},
            ...
        ]
    }
    """
    # Convert JSON operations to text format
    lines = []
    for op in program_json.get("operations", []):
        line = _json_op_to_text(op)
        if line:
            lines.append(line)
    
    program_text = "\n".join(lines)
    return execute_program(
        program_text,
        state_manager=state_manager,
        initial_state=initial_state,
        dry_run=dry_run,
    )


def _json_op_to_text(op: Dict[str, Any]) -> Optional[str]:
    """Convert JSON operation to text format."""
    op_type = op.get("op", "").upper()
    
    if op_type == "CREATE":
        resource_type = op.get("type", "")
        resource_id = op.get("id", "")
        params = op.get("params", {})
        import json
        return f"CREATE {resource_type} {resource_id} {json.dumps(params)}"
    
    elif op_type == "UPDATE":
        resource_id = op.get("id", "")
        params = op.get("params", {})
        import json
        return f"UPDATE {resource_id} {json.dumps(params)}"
    
    elif op_type == "DELETE":
        resource_id = op.get("id", "")
        return f"DELETE {resource_id}"
    
    elif op_type == "SET":
        path = op.get("path", "")
        value = op.get("value")
        import json
        return f"SET {path} = {json.dumps(value)}"
    
    elif op_type == "LOFT":
        surface_id = op.get("id", "")
        sections = op.get("sections", [])
        return f"LOFT {surface_id} FROM [{', '.join(sections)}]"
    
    elif op_type == "MIRROR":
        source = op.get("source", "")
        target = op.get("target", "")
        return f"MIRROR {source} AS {target}"
    
    elif op_type == "CONSTRAIN":
        path = op.get("path", "")
        operator = op.get("operator", ">=")
        value = op.get("value", 0)
        return f"CONSTRAIN {path} {operator} {value}"
    
    return None


def _run_validation(
    geometry: Any,
    state: Dict[str, Any],
    constraints: List[Constraint],
) -> Dict[str, Any]:
    """
    Run physics validation on geometry.
    
    Returns quantified feedback, not just pass/fail.
    """
    results: Dict[str, Any] = {
        "hydrostatics": {},
        "resistance": {},
        "constraints": [],
        "constraint_violations": [],
    }
    
    # Get hull parameters
    hull = state.get("hull", {})
    draft = hull.get("draft", 1.5)
    vcg = hull.get("vcg", 1.0)
    speed_kts = hull.get("design_speed_kts", 20.0)
    
    # Check for multi-body
    resources = state.get("resources", {})
    body_count = sum(
        1 for r in resources.values()
        if r.get("_type") == "geometry.body" and not r.get("_deleted")
    )
    
    # Hydrostatics
    try:
        if body_count > 1:
            # Multi-body hydrostatics
            hydro = _compute_multi_body_hydrostatics(geometry, state, draft, vcg)
        else:
            # Single hull hydrostatics
            hydro = _compute_single_hull_hydrostatics(geometry, draft, vcg)
        
        results["hydrostatics"] = hydro
        
    except Exception as e:
        logger.warning(f"Hydrostatics calculation failed: {e}")
        results["hydrostatics"]["error"] = str(e)
    
    # Resistance (if available)
    try:
        resistance = _compute_resistance(geometry, state, speed_kts)
        results["resistance"] = resistance
    except Exception as e:
        logger.debug(f"Resistance calculation not available: {e}")
        results["resistance"]["error"] = str(e)
    
    # Check constraints
    for constraint in constraints:
        violation = _check_constraint(constraint, results, state)
        results["constraints"].append({
            "path": constraint.path,
            "operator": constraint.operator,
            "required": constraint.value,
            "actual": violation.get("actual"),
            "passes": violation.get("passes", False),
        })
        if not violation.get("passes", True):
            results["constraint_violations"].append({
                "path": constraint.path,
                "required": constraint.value,
                "actual": violation.get("actual"),
                "priority": constraint.priority,
            })
    
    return results


def _compute_single_hull_hydrostatics(
    geometry: Any,
    draft: float,
    vcg: float,
) -> Dict[str, Any]:
    """Compute hydrostatics for single hull."""
    # Use existing stability calculations
    try:
        from magnet.stability.intact_gm import compute_gm_from_geometry
        
        gm_result = compute_gm_from_geometry(geometry, draft, vcg)
        
        return {
            "displacement_m3": geometry.volume,
            "gm_m": gm_result.get("gm_m", 0),
            "bm_transverse_m": gm_result.get("bm_m", 0),
            "kb_m": gm_result.get("kb_m", 0),
            "lcb_m": geometry.lcb,
            "vcb_m": geometry.vcb,
            "method": "single_hull",
            "passes": gm_result.get("gm_m", 0) > 0,
        }
    except ImportError:
        # Fallback: basic calculations
        return _basic_hydrostatics(geometry, draft)


def _compute_multi_body_hydrostatics(
    geometry: Any,
    state: Dict[str, Any],
    draft: float,
    vcg: float,
) -> Dict[str, Any]:
    """Compute hydrostatics for multi-body vessel using parallel axis theorem."""
    try:
        from magnet.physics.multi_body_hydrostatics import compute_multi_body_gm
        
        bodies = getattr(geometry, 'bodies', None) or state.get("resources", {})
        body_configs = {
            k: v for k, v in bodies.items()
            if isinstance(v, dict) and v.get("_type") == "geometry.body"
        }
        
        result = compute_multi_body_gm(body_configs, geometry, draft, vcg)
        return {
            **result,
            "method": "parallel_axis_theorem",
        }
        
    except ImportError:
        # Fallback to basic calculation
        logger.warning("Multi-body hydrostatics module not found, using basic calculation")
        return _basic_hydrostatics(geometry, draft)


def _basic_hydrostatics(geometry: Any, draft: float) -> Dict[str, Any]:
    """Basic hydrostatics without full stability module."""
    return {
        "displacement_m3": geometry.volume if hasattr(geometry, 'volume') else 0,
        "gm_m": None,
        "method": "basic",
        "warning": "Full hydrostatics calculation not available",
    }


def _compute_resistance(
    geometry: Any,
    state: Dict[str, Any],
    speed_kts: float,
) -> Dict[str, Any]:
    """
    Compute resistance estimate.
    
    Uses the existing resistance module which validates physics,
    not design intent. Novel hull forms work without new code.
    """
    try:
        from magnet.physics.resistance import calculate_resistance
        
        hull = state.get("hull", {})
        lwl = hull.get("lwl", hull.get("loa", 20.0))
        beam = hull.get("beam", 4.0)
        draft = hull.get("draft", 1.5)
        
        # Get volume from geometry
        volume = abs(geometry.volume) if hasattr(geometry, 'volume') else 100
        
        # Estimate displacement in tonnes
        displacement_mt = volume * 1.025  # Seawater density
        
        # Estimate wetted surface (approximation)
        # S ≈ 1.7 * L * T + V / T  (Holtrop approximation)
        wetted_surface = 1.7 * lwl * draft + volume / draft
        
        result = calculate_resistance(
            lwl=lwl,
            beam=beam,
            draft=draft,
            displacement_mt=displacement_mt,
            wetted_surface=wetted_surface,
            speed_kts=speed_kts,
        )
        
        # Convert to standardized output
        return {
            "resistance_kn": getattr(result, 'total_resistance_kn', None) or result.get('total_resistance_kn') if isinstance(result, dict) else None,
            "method": "holtrop_mennen",
            "confidence": 0.8 if volume > 50 else 0.5,
            "speed_kts": speed_kts,
        }
        
    except ImportError as e:
        return {"error": f"Resistance module not available: {e}"}
    except Exception as e:
        return {"error": str(e), "method": "failed"}


def _check_constraint(
    constraint: Constraint,
    validation_results: Dict[str, Any],
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """Check if constraint is satisfied."""
    # Get actual value
    actual = _get_constraint_value(constraint.path, validation_results, state)
    
    if actual is None:
        return {"passes": False, "actual": None, "error": "Value not found"}
    
    # Check operator
    passes = False
    if constraint.operator == ">=":
        passes = actual >= constraint.value
    elif constraint.operator == "<=":
        passes = actual <= constraint.value
    elif constraint.operator == "==":
        passes = abs(actual - constraint.value) < 0.001
    elif constraint.operator == ">":
        passes = actual > constraint.value
    elif constraint.operator == "<":
        passes = actual < constraint.value
    
    return {"passes": passes, "actual": actual}


def _get_constraint_value(
    path: str,
    validation_results: Dict[str, Any],
    state: Dict[str, Any],
) -> Optional[float]:
    """Get value for constraint path."""
    # Check validation results first
    if path.startswith("hull.gm") or path == "stability.gm":
        return validation_results.get("hydrostatics", {}).get("gm_m")
    
    if path.startswith("hull.displacement"):
        return validation_results.get("hydrostatics", {}).get("displacement_m3")
    
    # Check state
    return _get_nested(state, path)


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


