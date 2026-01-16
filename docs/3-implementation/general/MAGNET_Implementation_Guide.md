# MAGNET Implementation Guide v1.0

> **Purpose:** Step-by-step implementation roadmap for Cursor agent.  
> **Status:** Execution Plan  
> **Last Updated:** 2026-01-05  
> **Estimated Effort:** 10-15 working days

---

## Sacred Invariants (Enforce These Throughout)

> **Any hull form that requires a new language primitive is a failure of the language.**

1. **Kernel knows geometry, not design** — No "catamaran", "stepped hull", "patrol boat" in kernel code
2. **Agents coordinate on geometry only** — Never "features" (spray rails), always primitives (discontinuities)
3. **DERIVE is optional** — Agents can SET values directly; policies are conveniences, not requirements
4. **Enums classify physics, not design** — `physics_category` drives hydrostatic calculations, not style
5. **No second geometry engine** — Everything compiles to `HullSection`, `NURBSSurface`, `HullGeometry`

---

## How to Use This Document

This guide provides **concrete implementation steps** in sequence. Each phase has:

- **Goal:** What we're building
- **Files to Create/Modify:** Exact paths
- **Implementation:** Code structure or pseudocode
- **Test Criteria:** How to verify it works
- **Reference:** Which spec document has details

**Follow phases in order.** Each builds on the previous.

---

## Pre-Implementation Checklist

Before starting, verify:

```bash
# 1. Python environment works
python3 -c "import magnet; print('OK')"

# 2. Tests pass (ignore flaky API tests)
python3 -m pytest tests/unit/ -q --tb=no

# 3. Key files exist
ls magnet/hull_gen/geometry.py      # Canonical geometry
ls magnet/stability/intact_gm.py    # GM calculation
ls magnet/physics/resistance.py     # Resistance calculation
ls magnet/kernel/conductor.py       # Orchestrator
```

---

## Phase 0: Delete Enumeration (Day 1, Morning)

### Goal
Remove `HullFamily` enum that violates "no design knowledge in kernel" principle.

### Files to Modify

| File | Action |
|:-----|:-------|
| `magnet/kernel/priors/hull_families.py` | **DELETE ENTIRE FILE** |
| `magnet/kernel/synthesis.py` | Remove `HullFamily` imports and usage |
| Any file importing `HullFamily` | Remove or replace with geometry-based logic |

### Implementation

```bash
# Find all usages
grep -r "HullFamily" magnet/ --include="*.py" -l

# For each file found:
# - Remove import
# - Replace HullFamily.PATROL with geometry-based bounds
# - Replace FAMILY_PRIORS[family] with direct parameter specification
```

### Test Criteria

```bash
# MUST return zero results
grep -r "HullFamily" magnet/ --include="*.py"
grep -r "hull_families" magnet/ --include="*.py"

# Tests still pass
python3 -m pytest tests/unit/ -q
```

### Reference
- `MAGNET_Audit_Prompts.md` §1.3 (DELETE candidates)
- `MAGNET_Design_Language_Spec_v1.0.md` §0 (no enumerated designs)

---

## Phase 1: Design Language Parser (Days 1-2)

### Goal
Parse design programs into AST.

### Files to Create

```
magnet/kernel/stdlib/
├── __init__.py
├── parser.py          # Program text → AST
├── ast_nodes.py       # AST node definitions
└── lexer.py           # Tokenization (optional, can use regex)
```

### Implementation: `ast_nodes.py`

```python
# magnet/kernel/stdlib/ast_nodes.py
"""AST nodes for design language."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

@dataclass
class Statement:
    """Base class for all statements."""
    line_number: int = 0

@dataclass
class CreateStatement(Statement):
    """CREATE geometry.section name { ... }"""
    resource_type: str          # "geometry.section"
    resource_id: str            # "bow"
    properties: Dict[str, Any]  # { station: 0.0, ... }

@dataclass
class UpdateStatement(Statement):
    """UPDATE resource_id { ... }"""
    resource_id: str
    properties: Dict[str, Any]

@dataclass
class DeleteStatement(Statement):
    """DELETE resource_id"""
    resource_id: str

@dataclass
class LoftStatement(Statement):
    """LOFT surface_id FROM [section1, section2, ...]"""
    surface_id: str
    section_ids: List[str]
    options: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MirrorStatement(Statement):
    """MIRROR resource_id AS new_id"""
    source_id: str
    target_id: str

@dataclass
class AlignStatement(Statement):
    """ALIGN resource_id TO target AXIS axis"""
    resource_id: str
    target_id: str
    axis: str  # "x", "y", "z"

@dataclass
class ConstrainStatement(Statement):
    """CONSTRAIN path operator value"""
    path: str           # "hull.gm"
    operator: str       # ">=", "<=", "=="
    value: float
    priority: str = "hard"  # "hard" or "soft"

@dataclass
class SetStatement(Statement):
    """SET path = value"""
    path: str
    value: Any

@dataclass
class DeriveStatement(Statement):
    """DERIVE target FROM policy(inputs)"""
    target_path: str
    policy_name: str
    inputs: Dict[str, str]  # { "loa": "hull.loa", "ratio": "5.5" }

@dataclass
class Program:
    """Complete design program."""
    statements: List[Statement]
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### Implementation: `parser.py`

```python
# magnet/kernel/stdlib/parser.py
"""Parse design programs into AST."""

import re
import json
from typing import List, Dict, Any
from .ast_nodes import (
    Program, Statement, CreateStatement, UpdateStatement, 
    DeleteStatement, LoftStatement, MirrorStatement,
    AlignStatement, ConstrainStatement, DeriveStatement, SetStatement
)

class ParseError(Exception):
    """Raised when parsing fails."""
    def __init__(self, message: str, line: int = 0):
        self.line = line
        super().__init__(f"Line {line}: {message}")


def parse(program_text: str) -> Program:
    """
    Parse design program text into AST.
    
    Syntax:
        CREATE type id { json_properties }
        UPDATE id { json_properties }
        DELETE id
        LOFT id FROM [id1, id2, ...]
        MIRROR id AS new_id
        ALIGN id TO target AXIS axis
        CONSTRAIN path >= value
        DERIVE path FROM policy(inputs)
    """
    statements = []
    lines = program_text.strip().split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        line_num = i + 1
        
        # Skip empty lines and comments
        if not line or line.startswith('#') or line.startswith('//'):
            i += 1
            continue
        
        # Parse statement
        stmt = _parse_statement(line, line_num, lines, i)
        if stmt:
            statements.append(stmt)
        
        i += 1
    
    return Program(statements=statements)


def _parse_statement(line: str, line_num: int, lines: List[str], idx: int) -> Statement:
    """Parse a single statement."""
    
    # CREATE geometry.section bow { ... }
    create_match = re.match(
        r'CREATE\s+(\S+)\s+(\w+)\s*(\{.*\})?', 
        line, 
        re.IGNORECASE
    )
    if create_match:
        resource_type = create_match.group(1)
        resource_id = create_match.group(2)
        props_str = create_match.group(3) or '{}'
        
        # Handle multi-line properties
        if props_str == '{' or not props_str.endswith('}'):
            props_str = _collect_multiline_json(lines, idx)
        
        properties = _parse_properties(props_str, line_num)
        return CreateStatement(
            resource_type=resource_type,
            resource_id=resource_id,
            properties=properties,
            line_number=line_num
        )
    
    # UPDATE bow { ... }
    update_match = re.match(r'UPDATE\s+(\w+)\s*(\{.*\})?', line, re.IGNORECASE)
    if update_match:
        resource_id = update_match.group(1)
        props_str = update_match.group(2) or '{}'
        if not props_str.endswith('}'):
            props_str = _collect_multiline_json(lines, idx)
        properties = _parse_properties(props_str, line_num)
        return UpdateStatement(
            resource_id=resource_id,
            properties=properties,
            line_number=line_num
        )
    
    # DELETE bow
    delete_match = re.match(r'DELETE\s+(\w+)', line, re.IGNORECASE)
    if delete_match:
        return DeleteStatement(
            resource_id=delete_match.group(1),
            line_number=line_num
        )
    
    # LOFT main_surface FROM [bow, mid, stern]
    loft_match = re.match(
        r'LOFT\s+(\w+)\s+FROM\s+\[([^\]]+)\]', 
        line, 
        re.IGNORECASE
    )
    if loft_match:
        surface_id = loft_match.group(1)
        sections = [s.strip() for s in loft_match.group(2).split(',')]
        return LoftStatement(
            surface_id=surface_id,
            section_ids=sections,
            line_number=line_num
        )
    
    # MIRROR port_rail AS stbd_rail
    mirror_match = re.match(
        r'MIRROR\s+(\w+)\s+AS\s+(\w+)', 
        line, 
        re.IGNORECASE
    )
    if mirror_match:
        return MirrorStatement(
            source_id=mirror_match.group(1),
            target_id=mirror_match.group(2),
            line_number=line_num
        )
    
    # ALIGN rail TO chine AXIS y
    align_match = re.match(
        r'ALIGN\s+(\w+)\s+TO\s+(\w+)\s+AXIS\s+(\w+)',
        line,
        re.IGNORECASE
    )
    if align_match:
        return AlignStatement(
            resource_id=align_match.group(1),
            target_id=align_match.group(2),
            axis=align_match.group(3).lower(),
            line_number=line_num
        )
    
    # CONSTRAIN hull.gm >= 0.5
    constrain_match = re.match(
        r'CONSTRAIN\s+(\S+)\s*(>=|<=|==|>|<)\s*(\S+)',
        line,
        re.IGNORECASE
    )
    if constrain_match:
        return ConstrainStatement(
            path=constrain_match.group(1),
            operator=constrain_match.group(2),
            value=float(constrain_match.group(3)),
            line_number=line_num
        )
    
    # SET hull.beam = 4.5
    set_match = re.match(
        r'SET\s+(\S+)\s*=\s*(.+)',
        line,
        re.IGNORECASE
    )
    if set_match:
        path = set_match.group(1)
        value_str = set_match.group(2).strip()
        # Parse value (number, string, or JSON)
        try:
            value = json.loads(value_str)
        except:
            try:
                value = float(value_str)
            except:
                value = value_str.strip('"\'')
        return SetStatement(
            path=path,
            value=value,
            line_number=line_num
        )
    
    # DERIVE hull.beam FROM lb_ratio(loa=hull.loa, ratio=5.5)
    # NOTE: No hull_type lookup — agent provides ratio directly
    derive_match = re.match(
        r'DERIVE\s+(\S+)\s+FROM\s+(\w+)\(([^)]*)\)',
        line,
        re.IGNORECASE
    )
    if derive_match:
        target = derive_match.group(1)
        policy = derive_match.group(2)
        inputs_str = derive_match.group(3)
        inputs = _parse_derive_inputs(inputs_str)
        return DeriveStatement(
            target_path=target,
            policy_name=policy,
            inputs=inputs,
            line_number=line_num
        )
    
    raise ParseError(f"Unrecognized statement: {line}", line_num)


def _parse_properties(props_str: str, line_num: int) -> Dict[str, Any]:
    """Parse JSON-like properties."""
    # Convert to valid JSON (allow unquoted keys)
    # station: 0.0 → "station": 0.0
    fixed = re.sub(r'(\w+)\s*:', r'"\1":', props_str)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        raise ParseError(f"Invalid properties: {e}", line_num)


def _parse_derive_inputs(inputs_str: str) -> Dict[str, str]:
    """Parse DERIVE inputs: loa=hull.loa, ratio=5.5"""
    inputs = {}
    for part in inputs_str.split(','):
        if '=' in part:
            key, value = part.split('=', 1)
            inputs[key.strip()] = value.strip()
    return inputs


def _collect_multiline_json(lines: List[str], start_idx: int) -> str:
    """Collect multi-line JSON block."""
    result = []
    depth = 0
    for i in range(start_idx, len(lines)):
        line = lines[i]
        result.append(line)
        depth += line.count('{') - line.count('}')
        if depth <= 0:
            break
    return ' '.join(result)
```

### Test Criteria

```python
# tests/unit/test_parser.py

def test_parse_create_section():
    program = parse("""
        CREATE geometry.section bow {
            station: 0.0,
            points: [[0, 0], [1, 0.5], [0, 1]]
        }
    """)
    assert len(program.statements) == 1
    assert isinstance(program.statements[0], CreateStatement)
    assert program.statements[0].resource_type == "geometry.section"
    assert program.statements[0].resource_id == "bow"

def test_parse_loft():
    program = parse("LOFT main_surface FROM [bow, mid, stern]")
    stmt = program.statements[0]
    assert isinstance(stmt, LoftStatement)
    assert stmt.section_ids == ["bow", "mid", "stern"]

def test_parse_constrain():
    program = parse("CONSTRAIN hull.gm >= 0.5")
    stmt = program.statements[0]
    assert stmt.path == "hull.gm"
    assert stmt.operator == ">="
    assert stmt.value == 0.5

def test_parse_set():
    program = parse("SET hull.beam = 4.5")
    stmt = program.statements[0]
    assert isinstance(stmt, SetStatement)
    assert stmt.path == "hull.beam"
    assert stmt.value == 4.5

def test_parse_set_string():
    program = parse('SET hull.bow_style = "wave_piercing"')
    stmt = program.statements[0]
    assert stmt.value == "wave_piercing"
```

```bash
# Run tests
python3 -m pytest tests/unit/test_parser.py -v
```

### Reference
- `MAGNET_Design_Language_Spec_v1.0.md` §2 (Syntax)

---

## Phase 2: Semantic Expander (Days 3-4)

### Goal
Expand AST into kernel Actions that modify state.

### Files to Create

```
magnet/kernel/stdlib/
├── expander.py        # AST → Actions
├── type_registry.py   # Resource type schemas
└── policies.py        # DERIVE policy implementations
```

### Implementation: `type_registry.py`

```python
# magnet/kernel/stdlib/type_registry.py
"""Kernel-owned type schemas for design language resources."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

@dataclass
class FieldSchema:
    """Schema for a single field."""
    name: str
    field_type: str  # "float", "str", "int", "list", "dict"
    required: bool = False
    default: Any = None
    description: str = ""

@dataclass
class TypeSchema:
    """Schema for a resource type."""
    type_name: str
    fields: List[FieldSchema]
    mirrorable: bool = False
    mirror_fields: List[str] = field(default_factory=list)
    alignable_axes: List[str] = field(default_factory=list)
    
    def validate(self, properties: Dict[str, Any]) -> List[str]:
        """Validate properties against schema. Returns list of errors."""
        errors = []
        
        # Check required fields
        for f in self.fields:
            if f.required and f.name not in properties:
                errors.append(f"Missing required field: {f.name}")
        
        # Check types (basic)
        for key, value in properties.items():
            field_schema = next((f for f in self.fields if f.name == key), None)
            if not field_schema:
                errors.append(f"Unknown field: {key}")
        
        return errors


# Canonical type registry
TYPE_REGISTRY: Dict[str, TypeSchema] = {
    "geometry.section": TypeSchema(
        type_name="geometry.section",
        fields=[
            FieldSchema("station", "float", required=True, description="Position along hull (0=bow, 1=stern)"),
            FieldSchema("body_id", "str", default="main", description="Which body this section belongs to"),
            # Polygon definition (default)
            FieldSchema("points", "list", description="Section profile points [[y, z], ...]"),
            # NURBS definition (alternative)
            FieldSchema("definition_type", "str", default="polygon", description="'polygon' or 'nurbs'"),
            FieldSchema("control_points", "list", description="NURBS control points [[y, z, weight], ...]"),
            FieldSchema("knots", "list", description="NURBS knot vector"),
            FieldSchema("degree", "int", default=3, description="NURBS curve degree"),
        ],
        mirrorable=False,  # Sections are symmetric by default
    ),
    
    "geometry.body": TypeSchema(
        type_name="geometry.body",
        fields=[
            FieldSchema("body_type", "str", required=False, default="hull", description="Freeform body type (any string)"),
            FieldSchema("physics_category", "str", required=False, default="surface_piercing", description="Physics behavior hint"),
            FieldSchema("offset_x_m", "float", default=0.0),
            FieldSchema("offset_y_m", "float", default=0.0),
            FieldSchema("offset_z_m", "float", default=0.0),
        ],
        mirrorable=True,
        mirror_fields=["offset_y_m"],
    ),
    
    "geometry.surface": TypeSchema(
        type_name="geometry.surface",
        fields=[
            FieldSchema("surface_type", "str", default="hull_shell"),
            FieldSchema("definition", "str", required=True, description="'lofted' or 'nurbs'"),
            FieldSchema("section_ids", "list", description="For lofted surfaces"),
            FieldSchema("control_points", "list", description="For NURBS surfaces"),
            FieldSchema("body_id", "str", default="main"),
        ],
    ),
    
    "geometry.discontinuity": TypeSchema(
        type_name="geometry.discontinuity",
        fields=[
            FieldSchema("discontinuity_type", "str", required=True, description="e.g., 'step', 'chine', 'spray_rail'"),
            FieldSchema("station_start", "float", required=True),
            FieldSchema("station_end", "float", required=True),
            FieldSchema("height_ratio", "float", default=0.5),
            FieldSchema("depth_m", "float", default=0.05),
        ],
        mirrorable=True,
        mirror_fields=[],  # Position is along centerline
    ),
    
    "geometry.attachment": TypeSchema(
        type_name="geometry.attachment",
        fields=[
            FieldSchema("parent_body_id", "str", required=True),
            FieldSchema("child_body_id", "str", required=True),
            FieldSchema("attachment_type", "str", default="rigid"),
            FieldSchema("offset_x_m", "float", default=0.0),
            FieldSchema("offset_y_m", "float", default=0.0),
            FieldSchema("offset_z_m", "float", default=0.0),
        ],
    ),
    
    # Flow path for ventilation, cooling, exhaust
    "geometry.flow_path": TypeSchema(
        type_name="geometry.flow_path",
        fields=[
            FieldSchema("medium", "str", required=True, description="Freeform: 'air', 'water', 'exhaust', or novel"),
            FieldSchema("inlet_point", "list", required=True, description="[x, y, z] inlet position"),
            FieldSchema("outlet_point", "list", required=True, description="[x, y, z] outlet position"),
            FieldSchema("cross_section_m2", "float", description="Flow area"),
            FieldSchema("body_id", "str", default="main"),
        ],
        mirrorable=True,
        mirror_fields=["inlet_point", "outlet_point"],  # Y-coords mirrored
    ),
    
    # Opening in surface (vents, hatches, intakes)
    "geometry.opening": TypeSchema(
        type_name="geometry.opening",
        fields=[
            FieldSchema("surface_id", "str", required=True, description="Which surface this opening is in"),
            FieldSchema("position", "list", required=True, description="[x, y, z] center position"),
            FieldSchema("dimensions", "list", required=True, description="[width, height] or [radius]"),
            FieldSchema("shape", "str", default="rectangular", description="Freeform: 'rectangular', 'circular', 'custom'"),
            FieldSchema("purpose", "str", description="Freeform description"),
        ],
        mirrorable=True,
        mirror_fields=["position"],
    ),
}


def get_schema(resource_type: str) -> Optional[TypeSchema]:
    """Get schema for resource type."""
    return TYPE_REGISTRY.get(resource_type)


def validate_resource(resource_type: str, properties: Dict[str, Any]) -> List[str]:
    """Validate resource properties against schema."""
    schema = get_schema(resource_type)
    if not schema:
        return [f"Unknown resource type: {resource_type}"]
    return schema.validate(properties)
```

### Implementation: `expander.py`

```python
# magnet/kernel/stdlib/expander.py
"""Expand AST statements into kernel Actions."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from .ast_nodes import (
    Program, Statement, CreateStatement, UpdateStatement,
    DeleteStatement, LoftStatement, MirrorStatement,
    AlignStatement, ConstrainStatement, DeriveStatement, SetStatement
)
from .type_registry import get_schema, validate_resource

@dataclass
class Action:
    """Single state modification action."""
    op: str              # "SET", "DELETE"
    path: str            # State path
    value: Any = None    # Value to set
    reason: str = ""     # Why this action was generated


class ExpansionError(Exception):
    """Raised when expansion fails."""
    pass


def expand(program: Program, current_state: Dict = None) -> List[Action]:
    """
    Expand design program AST into kernel Actions.
    
    This is the SEMANTIC layer - validates types, expands operations.
    """
    actions = []
    current_state = current_state or {}
    
    for stmt in program.statements:
        stmt_actions = _expand_statement(stmt, current_state)
        actions.extend(stmt_actions)
        
        # Update working state for subsequent statements
        for action in stmt_actions:
            if action.op == "SET":
                _set_nested(current_state, action.path, action.value)
    
    return actions


def _expand_statement(stmt: Statement, state: Dict) -> List[Action]:
    """Expand a single statement into Actions."""
    
    if isinstance(stmt, CreateStatement):
        return _expand_create(stmt)
    
    elif isinstance(stmt, UpdateStatement):
        return _expand_update(stmt, state)
    
    elif isinstance(stmt, DeleteStatement):
        return _expand_delete(stmt)
    
    elif isinstance(stmt, SetStatement):
        return _expand_set(stmt)
    
    elif isinstance(stmt, LoftStatement):
        return _expand_loft(stmt, state)
    
    elif isinstance(stmt, MirrorStatement):
        return _expand_mirror(stmt, state)
    
    elif isinstance(stmt, AlignStatement):
        return _expand_align(stmt, state)
    
    elif isinstance(stmt, ConstrainStatement):
        return _expand_constrain(stmt)
    
    elif isinstance(stmt, DeriveStatement):
        return _expand_derive(stmt, state)
    
    else:
        raise ExpansionError(f"Unknown statement type: {type(stmt)}")


def _expand_create(stmt: CreateStatement) -> List[Action]:
    """Expand CREATE into SET action."""
    # Validate against schema
    errors = validate_resource(stmt.resource_type, stmt.properties)
    if errors:
        raise ExpansionError(f"CREATE {stmt.resource_id}: {errors}")
    
    # Apply defaults from schema
    schema = get_schema(stmt.resource_type)
    properties = dict(stmt.properties)
    properties["_type"] = stmt.resource_type
    
    if schema:
        for field in schema.fields:
            if field.name not in properties and field.default is not None:
                properties[field.name] = field.default
    
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
        raise ExpansionError(f"UPDATE {stmt.resource_id}: resource does not exist")
    
    # Merge properties
    updated = dict(existing)
    updated.update(stmt.properties)
    
    return [Action(
        op="SET",
        path=path,
        value=updated,
        reason=f"UPDATE {stmt.resource_id}"
    )]


def _expand_delete(stmt: DeleteStatement) -> List[Action]:
    """Expand DELETE into tombstone action."""
    path = f"resources.{stmt.resource_id}"
    return [Action(
        op="SET",
        path=f"{path}._deleted",
        value=True,
        reason=f"DELETE {stmt.resource_id}"
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
    for section_id in stmt.section_ids:
        section_path = f"resources.{section_id}"
        if not _get_nested(state, section_path):
            raise ExpansionError(f"LOFT: section '{section_id}' does not exist")
    
    surface = {
        "_type": "geometry.surface",
        "definition": "lofted",
        "section_ids": stmt.section_ids,
        "surface_type": "hull_shell",
    }
    
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
    
    if not source:
        raise ExpansionError(f"MIRROR: source '{stmt.source_id}' does not exist")
    
    resource_type = source.get("_type", "")
    schema = get_schema(resource_type)
    
    if schema and not schema.mirrorable:
        raise ExpansionError(f"MIRROR: {resource_type} is not mirrorable")
    
    # Create mirrored copy
    mirrored = dict(source)
    mirrored["_mirrored_from"] = stmt.source_id
    
    # Mirror Y-axis fields
    if schema:
        for field_name in schema.mirror_fields:
            if field_name in mirrored:
                mirrored[field_name] = -mirrored[field_name]
    
    return [Action(
        op="SET",
        path=f"resources.{stmt.target_id}",
        value=mirrored,
        reason=f"MIRROR {stmt.source_id} as {stmt.target_id}"
    )]


def _expand_align(stmt: AlignStatement, state: Dict) -> List[Action]:
    """Expand ALIGN into position adjustment."""
    source_path = f"resources.{stmt.resource_id}"
    target_path = f"resources.{stmt.target_id}"
    
    source = _get_nested(state, source_path)
    target = _get_nested(state, target_path)
    
    if not source:
        raise ExpansionError(f"ALIGN: source '{stmt.resource_id}' does not exist")
    if not target:
        raise ExpansionError(f"ALIGN: target '{stmt.target_id}' does not exist")
    
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
        reason=f"ALIGN {stmt.resource_id} to {stmt.target_id} on {stmt.axis}"
    )]


def _expand_constrain(stmt: ConstrainStatement) -> List[Action]:
    """Expand CONSTRAIN into constraint registration."""
    constraint = {
        "path": stmt.path,
        "operator": stmt.operator,
        "value": stmt.value,
        "priority": stmt.priority,
    }
    
    return [Action(
        op="SET",
        path=f"constraints.{stmt.path.replace('.', '_')}",
        value=constraint,
        reason=f"CONSTRAIN {stmt.path} {stmt.operator} {stmt.value}"
    )]


def _expand_derive(stmt: DeriveStatement, state: Dict) -> List[Action]:
    """Expand DERIVE into computed value."""
    from .policies import execute_policy
    
    # Resolve inputs
    resolved_inputs = {}
    for key, value_or_path in stmt.inputs.items():
        # If it looks like a path, resolve it
        if '.' in value_or_path and not value_or_path.replace('.', '').replace('-', '').isdigit():
            resolved = _get_nested(state, value_or_path)
            if resolved is None:
                raise ExpansionError(f"DERIVE: input '{value_or_path}' not found in state")
            resolved_inputs[key] = resolved
        else:
            # Literal value
            try:
                resolved_inputs[key] = float(value_or_path)
            except ValueError:
                resolved_inputs[key] = value_or_path
    
    # Execute policy
    result = execute_policy(stmt.policy_name, resolved_inputs)
    
    return [Action(
        op="SET",
        path=stmt.target_path,
        value=result,
        reason=f"DERIVE {stmt.target_path} from {stmt.policy_name}"
    )]


# Helper functions
def _get_nested(d: Dict, path: str) -> Any:
    """Get nested value from dict using dot path."""
    keys = path.split('.')
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key)
        else:
            return None
    return d


def _set_nested(d: Dict, path: str, value: Any) -> None:
    """Set nested value in dict using dot path."""
    keys = path.split('.')
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value
```

### Implementation: `policies.py`

```python
# magnet/kernel/stdlib/policies.py
"""DERIVE policy implementations."""

from typing import Any, Dict

class PolicyError(Exception):
    """Raised when policy execution fails."""
    pass


POLICIES = {}


def register_policy(name: str):
    """Decorator to register a policy."""
    def decorator(func):
        POLICIES[name] = func
        return func
    return decorator


def execute_policy(name: str, inputs: Dict[str, Any]) -> Any:
    """Execute a named policy."""
    if name not in POLICIES:
        raise PolicyError(f"Unknown policy: {name}")
    return POLICIES[name](inputs)


# --- Built-in Policies ---

@register_policy("lb_ratio")
def lb_ratio_policy(inputs: Dict[str, Any]) -> float:
    """
    Derive beam from LOA and target L/B ratio.
    
    Inputs:
        loa: Length overall (m)
        ratio: Target L/B ratio
    
    Returns:
        beam (m)
    """
    loa = float(inputs.get("loa", 0))
    ratio = float(inputs.get("ratio", 5.0))
    
    if loa <= 0:
        raise PolicyError("LOA must be positive")
    if ratio <= 0:
        raise PolicyError("L/B ratio must be positive")
    
    return loa / ratio


@register_policy("displacement_from_dims")
def displacement_from_dims_policy(inputs: Dict[str, Any]) -> float:
    """
    Estimate displacement from principal dimensions.
    
    Inputs:
        loa: Length (m)
        beam: Beam (m)
        draft: Draft (m)
        cb: Block coefficient (default 0.5)
    
    Returns:
        displacement (m³)
    """
    loa = float(inputs.get("loa", 0))
    beam = float(inputs.get("beam", 0))
    draft = float(inputs.get("draft", 0))
    cb = float(inputs.get("cb", 0.5))
    
    return loa * beam * draft * cb


@register_policy("gm_from_beam")
def gm_from_beam_policy(inputs: Dict[str, Any]) -> float:
    """
    Estimate GM from beam (rough approximation).
    
    For initial stability estimation only.
    
    Inputs:
        beam: Beam (m)
        draft: Draft (m)
    
    Returns:
        estimated GM (m)
    """
    beam = float(inputs.get("beam", 0))
    draft = float(inputs.get("draft", 1.0))
    
    # Very rough: BM ≈ B²/(12*T), KB ≈ 0.53*T, KG ≈ 0.5*D
    # GM = KB + BM - KG
    bm_approx = (beam ** 2) / (12 * draft)
    kb_approx = 0.53 * draft
    kg_approx = 0.6 * draft  # Conservative estimate
    
    return kb_approx + bm_approx - kg_approx
```

### Test Criteria

```python
# tests/unit/test_expander.py

def test_expand_create():
    program = parse("CREATE geometry.section bow { station: 0.0, points: [[0,0],[1,1]] }")
    actions = expand(program)
    assert len(actions) == 1
    assert actions[0].op == "SET"
    assert actions[0].path == "resources.bow"
    assert actions[0].value["_type"] == "geometry.section"

def test_expand_loft():
    state = {
        "resources": {
            "bow": {"_type": "geometry.section"},
            "mid": {"_type": "geometry.section"},
            "stern": {"_type": "geometry.section"},
        }
    }
    program = parse("LOFT main_surface FROM [bow, mid, stern]")
    actions = expand(program, state)
    assert actions[0].value["definition"] == "lofted"
    assert actions[0].value["section_ids"] == ["bow", "mid", "stern"]

def test_expand_mirror():
    state = {
        "resources": {
            "port_hull": {"_type": "geometry.body", "offset_y_m": -3.0}
        }
    }
    program = parse("MIRROR port_hull AS stbd_hull")
    actions = expand(program, state)
    assert actions[0].value["offset_y_m"] == 3.0  # Mirrored
```

### Reference
- `MAGNET_Design_Language_Spec_v1.0.md` §4 (Type Registry)
- `MAGNET_Design_Language_Spec_v1.0.md` §7 (DERIVE Policies)

---

## Phase 3: Geometry Compiler (Days 5-6)

### Goal
Compile design language resources into canonical `HullGeometry`.

### Files to Create/Modify

```
magnet/kernel/stdlib/
├── compiler.py        # Resources → HullGeometry
└── section_compiler.py # geometry.section → HullSection
```

### Implementation: `section_compiler.py`

```python
# magnet/kernel/stdlib/section_compiler.py
"""Compile geometry.section resources into HullSection objects."""

from typing import Dict, List, Any
from magnet.hull_gen.geometry import HullSection, SectionPoint, Point3D

def compile_section(resource: Dict[str, Any], loa: float = 25.0) -> HullSection:
    """
    Compile a geometry.section resource into HullSection.
    
    Args:
        resource: Section resource from state
        loa: Length overall for station scaling
    
    Returns:
        HullSection object compatible with existing geometry pipeline
    """
    station_ratio = resource.get("station", 0.5)
    station_m = station_ratio * loa
    
    points_raw = resource.get("points", [])
    
    # Convert [[y, z], ...] to SectionPoint objects
    section_points = []
    for i, pt in enumerate(points_raw):
        if len(pt) >= 2:
            y, z = pt[0], pt[1]
            section_points.append(SectionPoint(
                y=float(y),
                z=float(z),
                index=i
            ))
    
    return HullSection(
        station=station_m,
        points=section_points,
        body_id=resource.get("body_id", "main")
    )


def compile_sections(
    resources: Dict[str, Dict], 
    loa: float = 25.0
) -> List[HullSection]:
    """
    Compile all geometry.section resources into HullSection list.
    
    Returns sections sorted by station.
    """
    sections = []
    
    for resource_id, resource in resources.items():
        if resource.get("_type") == "geometry.section":
            if not resource.get("_deleted"):
                section = compile_section(resource, loa)
                section.resource_id = resource_id  # Track origin
                sections.append(section)
    
    # Sort by station
    sections.sort(key=lambda s: s.station)
    
    return sections
```

### Implementation: `compiler.py`

```python
# magnet/kernel/stdlib/compiler.py
"""Compile design language state into HullGeometry."""

from typing import Dict, List, Any, Optional
from magnet.hull_gen.geometry import HullGeometry, HullSection
from .section_compiler import compile_sections

class CompilationError(Exception):
    """Raised when compilation fails."""
    pass


def compile_to_geometry(
    state: Dict[str, Any],
    loa: float = None,
) -> HullGeometry:
    """
    Compile design language state into HullGeometry.
    
    This is the bridge between design language and existing geometry pipeline.
    
    Args:
        state: Design state with resources
        loa: Length overall (extracted from state if not provided)
    
    Returns:
        HullGeometry object for tessellation/hydrostatics/export
    """
    resources = state.get("resources", {})
    
    # Get LOA from state or default
    if loa is None:
        loa = state.get("hull", {}).get("loa", 25.0)
    
    # Compile sections
    sections = compile_sections(resources, loa)
    
    if not sections:
        raise CompilationError("No sections defined - cannot create geometry")
    
    # Check for multi-body
    bodies = _extract_bodies(resources)
    
    if len(bodies) > 1:
        return _compile_multi_body(resources, sections, bodies, loa)
    else:
        return _compile_single_hull(sections, loa)


def _extract_bodies(resources: Dict) -> Dict[str, Dict]:
    """Extract geometry.body resources."""
    bodies = {}
    for rid, resource in resources.items():
        if resource.get("_type") == "geometry.body":
            if not resource.get("_deleted"):
                bodies[rid] = resource
    return bodies


def _compile_single_hull(
    sections: List[HullSection], 
    loa: float
) -> HullGeometry:
    """Compile single-body hull geometry."""
    from magnet.hull_gen.generator import HullGenerator
    
    # Create HullGeometry from sections
    geometry = HullGeometry(
        sections=sections,
        loa=loa,
        beam=_estimate_beam(sections),
        draft=_estimate_draft(sections),
    )
    
    return geometry


def _compile_multi_body(
    resources: Dict,
    sections: List[HullSection],
    bodies: Dict[str, Dict],
    loa: float,
) -> HullGeometry:
    """Compile multi-body hull geometry."""
    # Group sections by body_id
    body_sections: Dict[str, List[HullSection]] = {}
    
    for section in sections:
        body_id = getattr(section, 'body_id', 'main')
        if body_id not in body_sections:
            body_sections[body_id] = []
        body_sections[body_id].append(section)
    
    # Create geometry for each body
    body_geometries = {}
    
    for body_id, body_config in bodies.items():
        body_sects = body_sections.get(body_id, [])
        
        if body_sects:
            # Apply body offset to sections
            offset_y = body_config.get("offset_y_m", 0.0)
            offset_z = body_config.get("offset_z_m", 0.0)
            
            for sect in body_sects:
                for pt in sect.points:
                    pt.y += offset_y
                    pt.z += offset_z
            
            body_geometries[body_id] = {
                "sections": body_sects,
                "config": body_config,
            }
    
    # Create combined geometry
    all_sections = []
    for body_data in body_geometries.values():
        all_sections.extend(body_data["sections"])
    
    geometry = HullGeometry(
        sections=all_sections,
        loa=loa,
        beam=_estimate_beam(all_sections),
        draft=_estimate_draft(all_sections),
        bodies=bodies,  # Store body config for hydrostatics
    )
    
    return geometry


def _estimate_beam(sections: List[HullSection]) -> float:
    """Estimate beam from sections."""
    max_beam = 0.0
    for section in sections:
        for pt in section.points:
            max_beam = max(max_beam, abs(pt.y) * 2)
    return max_beam or 6.0


def _estimate_draft(sections: List[HullSection]) -> float:
    """Estimate draft from sections."""
    min_z = 0.0
    for section in sections:
        for pt in section.points:
            min_z = min(min_z, pt.z)
    return abs(min_z) or 1.5
```

### Test Criteria

```python
# tests/unit/test_compiler.py

def test_compile_single_hull():
    state = {
        "hull": {"loa": 25.0},
        "resources": {
            "bow": {
                "_type": "geometry.section",
                "station": 0.0,
                "points": [[0, 0], [2, -1], [0, -1.5]]
            },
            "mid": {
                "_type": "geometry.section", 
                "station": 0.5,
                "points": [[0, 0], [3, -0.5], [3, -1.5], [0, -2]]
            },
            "stern": {
                "_type": "geometry.section",
                "station": 1.0,
                "points": [[0, 0], [2.5, -0.5], [2.5, -1.2], [0, -1.5]]
            }
        }
    }
    
    geometry = compile_to_geometry(state)
    assert len(geometry.sections) == 3
    assert geometry.loa == 25.0

def test_compile_multi_body():
    state = {
        "hull": {"loa": 30.0},
        "resources": {
            "port_body": {
                "_type": "geometry.body",
                "offset_y_m": -4.0
            },
            "stbd_body": {
                "_type": "geometry.body", 
                "offset_y_m": 4.0
            },
            "port_bow": {
                "_type": "geometry.section",
                "station": 0.0,
                "body_id": "port_body",
                "points": [[0, 0], [1, -1]]
            },
            "stbd_bow": {
                "_type": "geometry.section",
                "station": 0.0,
                "body_id": "stbd_body",
                "points": [[0, 0], [1, -1]]
            }
        }
    }
    
    geometry = compile_to_geometry(state)
    assert len(geometry.bodies) == 2
```

### Reference
- `MAGNET_Design_Language_Spec_v1.0.md` §0.1 (Canonical Geometry Model)
- `MAGNET_Design_Language_Spec_v1.0.md` §15.5 (Section Compiler)

---

## Phase 4: Multi-Body Hydrostatics (Days 7-8)

### Goal
Implement parallel axis theorem for multi-body BM/GM.

### Files to Create

```
magnet/physics/
└── multi_body_hydrostatics.py
```

### Implementation Order

1. **`infer_physics_behavior()`** — Derive physics from geometry position (not string matching)
2. **`compute_multi_body_hydrostatics()`** — Parallel axis theorem for BM
3. **`compute_multi_body_gm()`** — Wraps hydrostatics with KG

### Implementation

Use code from `MAGNET_Physics_Gaps_And_Solutions.md` §Gap 1:

- `compute_multi_body_hydrostatics()`
- `compute_multi_body_gm()`
- Parallel axis theorem for I_combined

### Files to Modify

| File | Change |
|:-----|:-------|
| `magnet/stability/intact_gm.py` | Add dispatch to multi-body when bodies > 1 |

```python
# In intact_gm.py, modify calculate_gm():

def calculate_gm(state: StateManager) -> IntactGMResults:
    # ... existing code ...
    
    # Check for multi-body
    bodies = state.get("resources", {})
    body_count = sum(1 for r in bodies.values() 
                     if r.get("_type") == "geometry.body" 
                     and not r.get("_deleted"))
    
    if body_count > 1:
        from magnet.physics.multi_body_hydrostatics import compute_multi_body_gm
        return compute_multi_body_gm(bodies, geometry, draft, vcg)
    
    # ... existing single-hull code ...
```

### Test Criteria

```python
# tests/unit/test_multi_body_hydrostatics.py

def test_catamaran_bm_parallel_axis():
    """
    Verify parallel axis theorem for catamaran BM.
    
    Two identical rectangular pontoons:
    BM = (2 * I_local + 2 * A * d²) / V
    """
    L, B, T = 20.0, 2.0, 1.0
    spacing = 8.0
    
    # Analytical
    I_local = (L * B**3) / 12
    A = L * B
    d = spacing / 2
    V = 2 * L * B * T
    BM_analytical = (2 * I_local + 2 * A * d**2) / V
    
    # Our implementation
    bodies = {
        "port": {"offset_y_m": -spacing/2, "physics_category": "surface_piercing"},
        "stbd": {"offset_y_m": spacing/2, "physics_category": "surface_piercing"},
    }
    # ... create box geometry ...
    
    result = compute_multi_body_hydrostatics(bodies, geometry, T)
    
    assert abs(result.bm_transverse_m - BM_analytical) < 0.1
```

### Reference
- `MAGNET_Physics_Gaps_And_Solutions.md` §Gap 1 (complete implementation)

---

## Phase 5: Program Executor Integration (Days 9-10)

### Goal
Wire parser → expander → compiler → validation into single endpoint.

### Files to Create

```
magnet/kernel/
└── program_executor.py

magnet/deployment/
└── program_endpoint.py
```

### Implementation: `program_executor.py`

```python
# magnet/kernel/program_executor.py
"""Execute design programs end-to-end."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from magnet.kernel.stdlib.parser import parse, ParseError
from magnet.kernel.stdlib.expander import expand, ExpansionError, Action
from magnet.kernel.stdlib.compiler import compile_to_geometry, CompilationError
from magnet.core.state_manager import StateManager

@dataclass
class ExecutionResult:
    """Result of program execution."""
    success: bool
    actions: List[Action]
    geometry: Optional[Any]
    validation: Dict[str, Any]
    errors: List[str]


def execute_program(
    program_text: str,
    state_manager: StateManager,
    dry_run: bool = False,
) -> ExecutionResult:
    """
    Execute a design program.
    
    Pipeline:
    1. Parse program text → AST
    2. Expand AST → Actions
    3. Apply actions to state (unless dry_run)
    4. Compile state → HullGeometry
    5. Run validation
    
    Args:
        program_text: Design program source
        state_manager: Current design state
        dry_run: If True, don't commit actions
    
    Returns:
        ExecutionResult with geometry and validation
    """
    errors = []
    actions = []
    geometry = None
    validation = {}
    
    # 1. Parse
    try:
        ast = parse(program_text)
    except ParseError as e:
        return ExecutionResult(
            success=False,
            actions=[],
            geometry=None,
            validation={},
            errors=[f"Parse error: {e}"]
        )
    
    # 2. Expand
    try:
        current_state = state_manager.to_dict()
        actions = expand(ast, current_state)
    except ExpansionError as e:
        return ExecutionResult(
            success=False,
            actions=[],
            geometry=None,
            validation={},
            errors=[f"Expansion error: {e}"]
        )
    
    # 3. Apply actions
    if not dry_run:
        for action in actions:
            if action.op == "SET":
                state_manager.set(action.path, action.value)
    
    # 4. Compile
    try:
        state_dict = state_manager.to_dict() if not dry_run else _apply_actions_temp(current_state, actions)
        geometry = compile_to_geometry(state_dict)
    except CompilationError as e:
        errors.append(f"Compilation error: {e}")
    
    # 5. Validate
    if geometry:
        validation = _run_validation(geometry, state_manager)
    
    return ExecutionResult(
        success=len(errors) == 0,
        actions=actions,
        geometry=geometry,
        validation=validation,
        errors=errors
    )


def _apply_actions_temp(state: Dict, actions: List[Action]) -> Dict:
    """Apply actions to a copy of state (for dry_run)."""
    import copy
    temp = copy.deepcopy(state)
    for action in actions:
        if action.op == "SET":
            _set_nested(temp, action.path, action.value)
    return temp


def _set_nested(d: Dict, path: str, value: Any):
    keys = path.split('.')
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value


def _run_validation(geometry, state_manager) -> Dict[str, Any]:
    """Run physics validation on geometry."""
    from magnet.stability.intact_gm import calculate_gm
    from magnet.physics.resistance import calculate_resistance
    
    results = {
        "hydrostatics": {},
        "resistance": {},
        "constraints": [],
    }
    
    try:
        gm_result = calculate_gm(state_manager)
        results["hydrostatics"] = {
            "gm_m": gm_result.gm_m,
            "passes": gm_result.passes_criterion,
        }
    except Exception as e:
        results["hydrostatics"]["error"] = str(e)
    
    try:
        resistance_result = calculate_resistance(state_manager)
        results["resistance"] = {
            "total_kn": resistance_result.total_kn,
            "method_valid": resistance_result.method_valid,
        }
    except Exception as e:
        results["resistance"]["error"] = str(e)
    
    # Check constraints
    constraints = state_manager.get("constraints", {})
    for cid, constraint in constraints.items():
        path = constraint.get("path")
        operator = constraint.get("operator")
        target = constraint.get("value")
        actual = state_manager.get(path)
        
        if actual is not None:
            passed = _check_constraint(actual, operator, target)
            results["constraints"].append({
                "path": path,
                "target": target,
                "actual": actual,
                "passed": passed,
            })
    
    return results


def _check_constraint(actual, operator, target) -> bool:
    if operator == ">=":
        return actual >= target
    elif operator == "<=":
        return actual <= target
    elif operator == "==":
        return abs(actual - target) < 0.001
    return False
```

### Implementation: `program_endpoint.py`

```python
# magnet/deployment/program_endpoint.py
"""FastAPI endpoint for design program execution."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from magnet.kernel.program_executor import execute_program, ExecutionResult
from magnet.core.state_manager import StateManager

router = APIRouter(prefix="/program", tags=["program"])


class ProgramRequest(BaseModel):
    """Request to execute a design program."""
    program: str
    design_id: Optional[str] = None
    dry_run: bool = False


class ProgramResponse(BaseModel):
    """Response from program execution."""
    success: bool
    actions: List[Dict[str, Any]]
    validation: Dict[str, Any]
    errors: List[str]


@router.post("/execute", response_model=ProgramResponse)
async def execute_design_program(request: ProgramRequest):
    """
    Execute a design program.
    
    The program is parsed, expanded to actions, applied to state,
    compiled to geometry, and validated.
    """
    # Get or create state manager
    # (In production, resolve from design_id)
    state_manager = StateManager()
    
    result = execute_program(
        request.program,
        state_manager,
        dry_run=request.dry_run
    )
    
    return ProgramResponse(
        success=result.success,
        actions=[{"op": a.op, "path": a.path, "reason": a.reason} for a in result.actions],
        validation=result.validation,
        errors=result.errors
    )


@router.post("/validate")
async def validate_program(request: ProgramRequest):
    """Validate a program without committing (dry run)."""
    request.dry_run = True
    return await execute_design_program(request)
```

### Wire into main API

```python
# In magnet/deployment/api.py, add:

from magnet.deployment.program_endpoint import router as program_router

app.include_router(program_router)
```

### Test Criteria

```bash
# Start server
uvicorn magnet.deployment.api:app --reload

# Test endpoint
curl -X POST http://localhost:8000/program/execute \
  -H "Content-Type: application/json" \
  -d '{
    "program": "CREATE geometry.section bow { station: 0.0, points: [[0,0],[2,-1]] }\nCREATE geometry.section stern { station: 1.0, points: [[0,0],[2,-1]] }\nLOFT main FROM [bow, stern]",
    "dry_run": true
  }'
```

### Reference
- `MAGNET_Implementation_Spec.md` §2 (API Contract)

---

## Phase 6: Agent Integration (Days 11-12)

### Goal
Connect LLM agents to generate design programs.

### Files to Create

```
magnet/agents/
├── geometry_proposer.py   # Proposes geometry programs
├── intent_decomposer.py   # Translates user intent
└── prompts/
    ├── geometry_proposer.py
    └── intent_decomposer.py
```

### Implementation

Use prompts from `MAGNET_Implementation_Spec.md` §1.3:

- Intent Decomposer system prompt
- Geometry Proposer system prompt
- Output schema validation

### Test Criteria

```python
# tests/integration/test_agent_pipeline.py

def test_agent_generates_valid_program():
    """Agent generates parseable, expandable program."""
    from magnet.agents.geometry_proposer import GeometryProposer
    
    proposer = GeometryProposer()
    
    # Agent generates program
    program = proposer.propose({
        "request": "Create a 25m patrol boat",
        "constraints": ["hull.gm >= 0.5"]
    })
    
    # Program parses
    ast = parse(program)
    assert len(ast.statements) > 0
    
    # Program expands
    actions = expand(ast)
    assert len(actions) > 0
```

### Reference
- `MAGNET_Implementation_Spec.md` §1 (Agent Prompt Specification)

---

## Phase 7: Invariant Tests (Day 13)

### Goal
Add automated tests that prevent enumeration from returning.

### Files to Create

```
tests/invariants/
├── test_no_enumeration.py
└── test_acid_compositional.py
```

### Implementation: `test_no_enumeration.py`

```python
# tests/invariants/test_no_enumeration.py
"""Invariant tests: No enumeration in kernel."""

import subprocess
import pytest

FORBIDDEN_DESIGN_TYPES = [
    "patrol_boat", "workboat", "ferry", "yacht",
    "tanker", "container_ship", "fishing_vessel",
]

FORBIDDEN_HULL_CONFIGS = [
    "catamaran", "trimaran", "monohull", "swath", "proa",
]

KERNEL_PATHS = [
    "magnet/kernel/",
    "magnet/physics/",
    "magnet/stability/",
]


def test_no_design_types_in_kernel():
    """Kernel code must not contain design type strings."""
    for term in FORBIDDEN_DESIGN_TYPES:
        for path in KERNEL_PATHS:
            result = subprocess.run(
                ["grep", "-r", term, path, "--include=*.py"],
                capture_output=True,
                text=True
            )
            assert result.returncode != 0, \
                f"Found forbidden term '{term}' in {path}:\n{result.stdout}"


def test_no_hull_config_dispatch_in_kernel():
    """Kernel must not dispatch on hull configuration names."""
    for term in FORBIDDEN_HULL_CONFIGS:
        for path in KERNEL_PATHS:
            result = subprocess.run(
                ["grep", "-r", f'== "{term}"', path, "--include=*.py"],
                capture_output=True,
                text=True
            )
            assert result.returncode != 0, \
                f"Found dispatch on '{term}' in {path}:\n{result.stdout}"


def test_no_hull_family_enum():
    """HullFamily enum must not exist."""
    result = subprocess.run(
        ["grep", "-r", "HullFamily", "magnet/", "--include=*.py"],
        capture_output=True,
        text=True
    )
    assert result.returncode != 0, \
        f"HullFamily still exists:\n{result.stdout}"
```

### Implementation: `test_acid_compositional.py`

```python
# tests/invariants/test_acid_compositional.py
"""Acid tests: Novel geometry without new code."""

import pytest
from magnet.kernel.stdlib.parser import parse
from magnet.kernel.stdlib.expander import expand
from magnet.kernel.stdlib.compiler import compile_to_geometry
from magnet.kernel.program_executor import execute_program
from magnet.core.state_manager import StateManager


def test_novel_configuration_works():
    """
    ACID TEST: Create a configuration no one has named.
    
    This MUST work without adding code.
    """
    program = """
    # 4-body configuration with novel body types
    CREATE geometry.body main_hull {
        body_type: "asymmetric_displacement",
        physics_category: "surface_piercing",
        offset_y_m: 0
    }
    CREATE geometry.body left_outrigger {
        body_type: "stability_float",
        physics_category: "surface_piercing",
        offset_y_m: -5.0
    }
    CREATE geometry.body right_outrigger {
        body_type: "stability_float",
        physics_category: "surface_piercing",
        offset_y_m: 5.0
    }
    CREATE geometry.body bow_foil {
        body_type: "hydrofoil_strut",
        physics_category: "partially_submerged",
        offset_x_m: 10.0
    }
    """
    
    state_manager = StateManager()
    result = execute_program(program, state_manager)
    
    # Must succeed
    assert result.success, f"Failed: {result.errors}"
    
    # Novel body types accepted
    resources = state_manager.get("resources", {})
    assert resources["main_hull"]["body_type"] == "asymmetric_displacement"
    assert resources["bow_foil"]["body_type"] == "hydrofoil_strut"


def test_stepped_hull_from_primitives():
    """
    ACID TEST: Create stepped hull without "stepped" type.
    
    Uses only geometry.discontinuity primitive.
    """
    program = """
    CREATE geometry.section bow { station: 0.0, points: [[0,0],[2,-1],[0,-1.5]] }
    CREATE geometry.section mid { station: 0.5, points: [[0,0],[3,-0.5],[3,-1.5],[0,-2]] }
    CREATE geometry.section stern { station: 1.0, points: [[0,0],[2.5,-0.5],[2.5,-1.2],[0,-1.5]] }
    
    LOFT main_surface FROM [bow, mid, stern]
    
    CREATE geometry.discontinuity step_1 {
        discontinuity_type: "surface_break",
        station_start: 0.4,
        station_end: 0.6,
        depth_m: 0.15
    }
    
    CREATE geometry.discontinuity step_2 {
        discontinuity_type: "surface_break",
        station_start: 0.7,
        station_end: 0.85,
        depth_m: 0.10
    }
    """
    
    state_manager = StateManager()
    result = execute_program(program, state_manager)
    
    assert result.success, f"Failed: {result.errors}"
    
    # No "stepped_hull" string anywhere
    state_str = str(state_manager.to_dict())
    assert "stepped_hull" not in state_str.lower()
    assert "step" not in [r.get("_type", "") for r in state_manager.get("resources", {}).values()]


def test_dual_body_vessel_from_primitives():
    """
    ACID TEST: Create dual-body vessel without "catamaran" type.
    """
    program = """
    CREATE geometry.body port_hull {
        body_type: "slender_displacement",
        offset_y_m: -4.0
    }
    CREATE geometry.body stbd_hull {
        body_type: "slender_displacement",
        offset_y_m: 4.0
    }
    
    CREATE geometry.section port_bow {
        station: 0.0,
        body_id: "port_hull",
        points: [[0,0],[1,-0.5],[1,-1.5],[0,-2]]
    }
    CREATE geometry.section port_stern {
        station: 1.0,
        body_id: "port_hull",
        points: [[0,0],[1,-0.5],[1,-1.2],[0,-1.5]]
    }
    
    MIRROR port_hull AS stbd_hull
    """
    
    state_manager = StateManager()
    result = execute_program(program, state_manager)
    
    assert result.success, f"Failed: {result.errors}"
    
    # No "catamaran" string anywhere
    state_str = str(state_manager.to_dict())
    assert "catamaran" not in state_str.lower()
```

### Reference
- `MAGNET_Implementation_Spec.md` §3.3 (Invariant Tests)
- `MAGNET_Implementation_Spec.md` §3.5 (Acid Tests)

---

## Phase 8: Documentation & Cleanup (Days 14-15)

### Goal
Update docs, run full test suite, prepare for production.

### Tasks

1. **Run full test suite**
   ```bash
   python3 -m pytest tests/ -v --tb=short
   ```

2. **Run invariant tests**
   ```bash
   python3 -m pytest tests/invariants/ -v
   ```

3. **Update README**
   - Add design language examples
   - Document new endpoints

4. **Verify no regression**
   - Existing hull generation still works
   - Existing validation still works

5. **Performance check**
   - Parser: < 10ms for typical program
   - Expander: < 50ms
   - Compilation: < 100ms
   - Validation: < 1s

---

## Quick Reference: File Locations

| Component | Path | Phase |
|:----------|:-----|:------|
| Parser | `magnet/kernel/stdlib/parser.py` | 1 |
| AST Nodes | `magnet/kernel/stdlib/ast_nodes.py` | 1 |
| Type Registry | `magnet/kernel/stdlib/type_registry.py` | 2 |
| Expander | `magnet/kernel/stdlib/expander.py` | 2 |
| Policies | `magnet/kernel/stdlib/policies.py` | 2 |
| Section Compiler | `magnet/kernel/stdlib/section_compiler.py` | 3 |
| Geometry Compiler | `magnet/kernel/stdlib/compiler.py` | 3 |
| Multi-Body Hydro | `magnet/physics/multi_body_hydrostatics.py` | 4 |
| Program Executor | `magnet/kernel/program_executor.py` | 5 |
| Program Endpoint | `magnet/deployment/program_endpoint.py` | 5 |
| Agents | `magnet/agents/geometry_proposer.py` | 6 |
| Invariant Tests | `tests/invariants/` | 7 |

---

## Quick Reference: Primitive Types

| Type | Purpose | Key Fields |
|:-----|:--------|:-----------|
| `geometry.section` | Cross-section profile | `station`, `points` or `control_points` (NURBS) |
| `geometry.body` | Hull body | `body_type` (freeform), `offset_y_m`, `physics_category` |
| `geometry.surface` | Lofted/NURBS surface | `definition` ("lofted"/"nurbs"), `section_ids` |
| `geometry.discontinuity` | Steps, chines, rails | `discontinuity_type` (freeform), `station_start/end` |
| `geometry.flow_path` | Ventilation, cooling | `medium` (freeform), `inlet_point`, `outlet_point` |
| `geometry.opening` | Vents, hatches, intakes | `surface_id`, `position`, `dimensions` |
| `geometry.attachment` | Body connections | `parent_body_id`, `child_body_id` |

---

## Quick Reference: Statements

| Statement | Syntax | Purpose |
|:----------|:-------|:--------|
| `CREATE` | `CREATE type id { props }` | Create new resource |
| `UPDATE` | `UPDATE id { props }` | Modify existing resource |
| `DELETE` | `DELETE id` | Tombstone resource |
| `SET` | `SET path = value` | Set state value directly |
| `LOFT` | `LOFT id FROM [s1, s2]` | Create surface from sections |
| `MIRROR` | `MIRROR id AS new_id` | Mirror resource across Y axis |
| `ALIGN` | `ALIGN id TO target AXIS x` | Align position |
| `CONSTRAIN` | `CONSTRAIN path >= value` | Add constraint |
| `DERIVE` | `DERIVE path FROM policy(...)` | Compute value from policy |

---

## Success Criteria

### Milestone 1 (Day 5): Single Hull from Program
```bash
# This works:
python3 -c "
from magnet.kernel.program_executor import execute_program
from magnet.core.state_manager import StateManager

program = '''
CREATE geometry.section bow { station: 0.0, points: [[0,0],[2,-1]] }
CREATE geometry.section stern { station: 1.0, points: [[0,0],[2,-1]] }
LOFT main FROM [bow, stern]
'''

sm = StateManager()
result = execute_program(program, sm)
print('Success:', result.success)
print('Sections:', len(result.geometry.sections))
"
```

### Milestone 2 (Day 10): Multi-Body with Validation
```bash
# Catamaran validates correctly with parallel axis theorem:
python3 -c "
from magnet.kernel.program_executor import execute_program
from magnet.core.state_manager import StateManager

program = '''
CREATE geometry.body port { offset_y_m: -4.0, physics_category: \"surface_piercing\" }
CREATE geometry.body stbd { offset_y_m: 4.0, physics_category: \"surface_piercing\" }
CREATE geometry.section port_bow { station: 0.0, body_id: \"port\", points: [[0,0],[1,-1],[1,-1.5],[0,-2]] }
CREATE geometry.section port_stern { station: 1.0, body_id: \"port\", points: [[0,0],[1,-0.5],[1,-1.2],[0,-1.5]] }
MIRROR port AS stbd
'''

sm = StateManager()
result = execute_program(program, sm)

hydro = result.validation.get('hydrostatics', {})
print('GM:', hydro.get('gm_m'))
print('BM transverse:', hydro.get('bm_transverse_m'))
print('Method:', hydro.get('method'))

# VERIFY parallel axis theorem applied:
# BM should be large (>10m) due to hull spacing of 8m
# BM = (2*I_local + 2*A*d²) / V, where d = 4m
assert hydro.get('bm_transverse_m', 0) > 5.0, 'BM too small - parallel axis not applied?'
assert hydro.get('method') == 'parallel_axis_theorem', 'Wrong method used'
print('✓ Parallel axis theorem verified')
"
```

### Milestone 3 (Day 15): All Tests Pass
```bash
python3 -m pytest tests/ -v
# Expected: 3000+ tests pass, 0 fail
```

---

## Related Documents

| Document | Use For |
|:---------|:--------|
| `MAGNET_Design_Language_Spec_v1.0.md` | Syntax, semantics, type schemas |
| `MAGNET_Implementation_Spec.md` | Agent prompts, API contracts, tests |
| `MAGNET_Physics_Gaps_And_Solutions.md` | Multi-body hydrostatics code |
| `MAGNET_Failure_Modes_And_Mitigations.md` | Error handling strategies |
| `MAGNET_Hard_Questions_Answers.md` | Verification, costs, timeline |

