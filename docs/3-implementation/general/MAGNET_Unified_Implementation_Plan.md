# MAGNET Multi-Agent Design OS — Unified Implementation Plan

## Executive Summary

**What MAGNET Is:**

```
MAGNET is not: AI that designs boats autonomously
MAGNET is: An engineer creativity amplifier
```

```
┌─────────────────────────────────────────────────────────────────┐
│                         ENGINEER                                │
│     (infinite creativity, domain knowledge, quality judgment)   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
                    "Make the bow finer"
                    "Try a stepped configuration"
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT SWARM                                │
│          (translates intent → geometry primitives)              │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         KERNEL                                  │
│              (validates physics, returns quantified feedback)   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
                    "GM = 0.6m, need 0.8m. Increase beam ~15cm"
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         ENGINEER                                │
│                   (judges, refines, iterates)                   │
└─────────────────────────────────────────────────────────────────┘
```

**Goal:** Build an environment where:
- **Engineers** express creative intent, judge quality, decide convergence
- **Agents** translate intent to geometry primitives (not decisions)
- **Kernel** validates physics instantly with quantified feedback
- **Iteration** is as fast as the engineer can think

**The Core Equation:**
```
ENGINEER PRODUCTIVITY = creative expression × instant feedback × no artificial limits
```

**Core Principles (aligned with MAGNET_Design_Language_Spec_v1.0.md):**
| Principle | Meaning |
|:----------|:--------|
| **Engineer is in the loop** | Engineers express intent, judge quality, decide when to stop |
| **Kernel knows geometry, not design** | No "stepped hull" or "catamaran" types — only geometric primitives |
| **No second geometry engine** | Language compiles INTO existing `HullSection`, `NURBSSurface`, `HullGeometry` |
| **Infinite composition** | Novel designs emerge from primitive combinations, not style catalogs |
| **Agents propose geometry** | Agents output `CREATE geometry.body`, not `STYLE = "aggressive"` |
| **Quantified feedback** | Engineers get numbers ("GM = 0.6, need 0.8"), not just pass/fail |
| **Primitives are complete** | **Any hull form that requires a new language primitive is a failure of the language** |
| **Agents coordinate on geometry** | Agents never debate "features" — they debate geometry and constraints only |

**Current State (from audits):**
| Component | Readiness | Score |
|-----------|-----------|-------|
| Kernel (Validator, Executor) | Ready | 8/10 |
| Explainability (ExplainRecord, Query) | Ready | 8/10 |
| NURBS/Section Infrastructure | **Ready** | **8/10** |
| Feedback Loop | Partial | 6/10 |
| Design Language | Not Implemented | 0/10 |
| Type Registry (kernel-owned) | Not Implemented | 0/10 |
| Agent Infrastructure | Partial | 3/10 |
| Swarm Coordination | Not Implemented | 1/10 |

**Timeline:** 4 weeks (20 working days)

**Reference:** See `MAGNET_Design_Language_Spec_v1.0.md` for complete language specification.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ENGINEER                                        │
│              "I want a fast catamaran that's stable in rough seas"          │
│                    (creative intent, domain knowledge)                       │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            INTENT DECOMPOSER                                │
│                    User text → DesignProblem                                │
│            (extracts constraints, preferences, requirements)                │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AGENT SWARM                                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │    Hull     │ │  Stability  │ │ Resistance  │ │Manufacturing│           │
│  │   Agent     │ │   Agent     │ │   Agent     │ │   Agent     │           │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘           │
│         │               │               │               │                   │
│         │  AGENTS OUTPUT GEOMETRIC PRIMITIVES:                              │
│         │  • CREATE geometry.body { body_type: "hull", offset_y_m: 3.0 }   │
│         │  • CREATE geometry.section { station: 0.5, ... }                 │
│         │  • LOFT [sections] INTO surface                                  │
│         │  • CONSTRAIN stability.gm_m >= 2.0                               │
│         │                                                                   │
│         │  NOT: STYLE = "catamaran" (enumerated)                           │
│         │                                                                   │
│         ▼               ▼               ▼               ▼                   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │   Critic    │ │   Critic    │ │   Critic    │ │   Critic    │           │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘           │
│         └───────────────┴───────────────┴───────────────┘                   │
│                                  │                                          │
│                                  ▼                                          │
│                         CONFLICT RESOLUTION                                 │
│                                  │                                          │
│                                  ▼                                          │
│                    MERGED DESIGN LANGUAGE PROGRAM                           │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
══════════════════════════════════│═══════════════ DEPLOYMENT BOUNDARY ═══════
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SEMANTIC EXPANDER                                   │
│  • Parse program to AST                                                    │
│  • Type-check against kernel schemas                                       │
│  • Expand operations via kernel/stdlib functions:                          │
│    - CREATE → resources.create_resource()                                  │
│    - LOFT → geometry.loft_sections_to_surface()                            │
│    - ALIGN → geometry.align_resource()                                     │
│  • Emit Actions with SemanticTrace                                         │
│  • geometry.section → HullSection (canonical)                              │
│  • geometry.surface → NURBSSurface (canonical)                             │
│                                                                            │
│  NO SECOND GEOMETRY ENGINE — compiles INTO existing classes                │
│                      → ActionPlan                                          │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
══════════════════════════════════│═══════════════ KERNEL BOUNDARY ═══════════
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              KERNEL                                         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │    VALIDATOR    │ →  │    EXECUTOR     │ →  │  POST-COMMIT    │         │
│  │   (Firewall)    │    │  (State Mutate) │    │   (Physics)     │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│                                  │                                          │
│                                  ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │              EXISTING DOWNSTREAM PIPELINE (unchanged)                │  │
│  │                                                                      │  │
│  │  HullGeometry                                                        │  │
│  │      ├──▶ HullGeometryPipeline.tessellate() → WebGL mesh             │  │
│  │      ├──▶ compute_hydrostatics() → displacement, GM, LCB             │  │
│  │      └──▶ STLExporter / IGESExporter → files                         │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
              [PASS]                      [FAIL + QUANTIFIED FEEDBACK]
                │                               │
                │                               ▼
                │                         "GM = 0.6m, need 0.8m"
                │                         "Increase beam by ~15cm"
                │                               │
                ▼                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ENGINEER                                        │
│                   (reviews results, judges quality, iterates)                │
│                                                                             │
│  ENGINEER decides:                                                          │
│  • "That's good enough" → DONE                                              │
│  • "Try wider beam" → another iteration                                     │
│  • "Show me tradeoffs" → compare alternatives                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Design Language Foundation (Days 1-5)

### Goal
Enable agents to express designs using **compositional geometric primitives**, not enumerated styles.

**Key Principle:** No style registry. Agents compose geometry directly.

### Task 1.1: Type Registry (Kernel-Owned)
**File:** `kernel/stdlib/type_registry.py`

**CRITICAL:** The kernel owns all type schemas. Agents read from here; they do NOT define types.

```python
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple

@dataclass(frozen=True)
class FieldSchema:
    """Schema for a single field."""
    name: str
    field_type: str  # "float", "int", "str", "bool", "enum", "array"
    required: bool = True
    default: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    enum_values: Optional[Tuple[str, ...]] = None
    description: str = ""

@dataclass(frozen=True)
class TypeSchema:
    """Schema for a resource type."""
    type_name: str
    fields: Tuple[FieldSchema, ...]
    mirrorable: bool = False
    mirror_fields: Tuple[str, ...] = ()
    mirror_behavior: str = "create_copy"  # "create_copy", "error", "no_op"
    alignable_axes: Tuple[str, ...] = ()
    description: str = ""

# ═══════════════════════════════════════════════════════════════════════════
# GEOMETRIC PRIMITIVES — What agents actually speak
# ═══════════════════════════════════════════════════════════════════════════
#
# CRITICAL: Enums are PHYSICS CATEGORIES, not design semantics.
# body_type, surface_type, medium are FREEFORM STRINGS for novelty.
# Novel types like "hydrofoil_strut" are VALID if physics passes.
# ═══════════════════════════════════════════════════════════════════════════

TYPE_SCHEMAS: Dict[str, TypeSchema] = {
    
    # Multi-body support (catamarans, trimarans, novel configurations)
    "geometry.body": TypeSchema(
        type_name="geometry.body",
        fields=(
            # FREEFORM STRING — agents can invent novel body types
            FieldSchema("body_type", "str", default="hull",
                       description="Body identifier (freeform: hull, pontoon, hydrofoil_strut, novel)"),
            # Physics category for hydrostatics — THIS is what the kernel validates
            FieldSchema("physics_category", "enum",
                       enum_values=("submerged", "surface_piercing", "above_water"),
                       description="Physics category determines hydrostatic treatment"),
            FieldSchema("parent_body_id", "str", required=False),
            FieldSchema("offset_x_m", "float", default=0.0),
            FieldSchema("offset_y_m", "float", default=0.0),
            FieldSchema("offset_z_m", "float", default=0.0),
            FieldSchema("surface_id", "str", required=False),
        ),
        mirrorable=True,
        mirror_fields=("offset_y_m",),
        description="A distinct solid volume — novel types allowed",
    ),
    
    # Section definition for lofting
    "geometry.section": TypeSchema(
        type_name="geometry.section",
        fields=(
            FieldSchema("station", "float", min_value=0.0, max_value=1.0),
            FieldSchema("x_position_m", "float"),
            # definition_type remains enum — these are mathematical categories
            FieldSchema("definition_type", "enum",
                       enum_values=("parametric", "points", "nurbs_curve")),
            FieldSchema("half_beam_m", "float", required=False),
            FieldSchema("draft_m", "float", required=False),
            FieldSchema("deadrise_deg", "float", required=False),
            FieldSchema("fullness", "float", required=False, min_value=0.0, max_value=1.0),
            FieldSchema("points", "array", required=False),
            FieldSchema("nurbs_control_points", "array", required=False),
        ),
        mirrorable=False,
        description="Cross-section for surface lofting",
    ),
    
    # Surface definition (NURBS or lofted)
    "geometry.surface": TypeSchema(
        type_name="geometry.surface",
        fields=(
            # FREEFORM STRING — agents can invent novel surface types
            FieldSchema("surface_type", "str", default="hull_shell",
                       description="Surface identifier (freeform: hull_shell, deck, foil_surface, novel)"),
            # Physics category for structural/hydrostatic treatment
            FieldSchema("physics_category", "enum",
                       enum_values=("watertight", "non_watertight", "structural"),
                       description="Physics category determines hydrostatic treatment"),
            # definition_type remains enum — these are mathematical categories
            FieldSchema("definition_type", "enum",
                       enum_values=("nurbs", "lofted", "ruled", "developable")),
            FieldSchema("body_id", "str", required=False),
            FieldSchema("section_ids", "array", required=False),
            FieldSchema("loft_tension", "float", required=False, default=0.5),
            FieldSchema("nurbs_control_points", "array", required=False),
        ),
        mirrorable=False,
        description="Parametric surface — novel types allowed",
    ),
    
    # Discontinuities (what designers call "steps", but kernel sees as geometry)
    "geometry.discontinuity": TypeSchema(
        type_name="geometry.discontinuity",
        fields=(
            FieldSchema("surface_id", "str"),
            FieldSchema("station", "float", min_value=0.0, max_value=1.0),
            FieldSchema("depth_m", "float", min_value=0.0),
            # FREEFORM STRING — agents can invent novel profiles
            FieldSchema("profile", "str", default="transverse",
                       description="Profile shape (transverse, diagonal, curved, or novel)"),
    ),
        mirrorable=False,
        description="Surface discontinuity (break in continuity)",
    ),
    
    # Flow paths (for ventilation, cooling, novel fluids)
    "geometry.flow_path": TypeSchema(
        type_name="geometry.flow_path",
        fields=(
            FieldSchema("inlet_surface", "str"),
            FieldSchema("inlet_point", "str"),
            FieldSchema("outlet_surface", "str"),
            FieldSchema("outlet_point", "str"),
            FieldSchema("cross_section_area_m2", "float", min_value=0.0001),
            # FREEFORM STRING — agents can specify novel fluids
            FieldSchema("medium", "str", default="air",
                       description="What flows through (air, water, coolant, or novel)"),
        ),
        mirrorable=True,
        description="Path for fluid flow — novel media allowed",
    ),
    
    # Openings in surfaces
    "geometry.opening": TypeSchema(
        type_name="geometry.opening",
        fields=(
            FieldSchema("surface_id", "str"),
            FieldSchema("center_u", "float", min_value=0.0, max_value=1.0),
            FieldSchema("center_v", "float", min_value=0.0, max_value=1.0),
            # FREEFORM STRING — agents can define novel shapes
            FieldSchema("shape", "str", default="rectangle",
                       description="Opening shape (circle, rectangle, ellipse, or novel)"),
            FieldSchema("width_m", "float", min_value=0.01),
            FieldSchema("height_m", "float", min_value=0.01),
        ),
        mirrorable=True,
        mirror_fields=("center_v",),
        description="Cutout in a surface — novel shapes allowed",
    ),
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🔴 DEPRECATED: Legacy hull features
    # ═══════════════════════════════════════════════════════════════════════
    #
    # ⚠️ AGENTS MUST NEVER CREATE THESE TYPES ⚠️
    #
    # These exist ONLY for backwards compatibility.
    # ANY NEW DESIGN CONCEPT THAT NEEDS A NEW hull.* TYPE = ARCHITECTURE FAILURE
    # Agents MUST compose from geometry.* primitives instead.
    #
    # ═══════════════════════════════════════════════════════════════════════
    
    "hull.spray_rail": TypeSchema(
        type_name="hull.spray_rail",
        deprecated=True,  # AGENTS: Use geometry.surface_modification instead
        fields=(
            FieldSchema("height_ratio", "float", min_value=0.0, max_value=1.0),
            FieldSchema("start_station", "float", default=0.0),
            FieldSchema("end_station", "float", default=1.0),
            FieldSchema("profile", "enum", enum_values=("triangular", "rounded", "flat")),
            FieldSchema("width_m", "float", min_value=0.01, max_value=0.5),
        ),
        mirrorable=False,
        description="[DEPRECATED] Use geometry.surface_modification",
    ),
    
    "hull.chine": TypeSchema(
        type_name="hull.chine",
        deprecated=True,  # AGENTS: Use geometry.edge_treatment instead
        fields=(
            FieldSchema("height_ratio", "float", min_value=0.0, max_value=1.0),
            FieldSchema("angle_deg", "float", min_value=0.0, max_value=90.0),
            FieldSchema("is_hard", "bool", default=True),
        ),
        mirrorable=False,
        description="[DEPRECATED] Use geometry.edge_treatment",
    ),
}

def get_type_schema(type_name: str) -> TypeSchema:
    """Get canonical schema for a type. Raises if unknown."""
    if type_name not in TYPE_SCHEMAS:
        raise UnknownTypeError(f"Unknown type: {type_name}")
    return TYPE_SCHEMAS[type_name]

def validate_resource_params(type_name: str, params: Dict[str, Any]) -> List[str]:
    """Validate params against type schema. Returns list of errors."""
    schema = get_type_schema(type_name)
    errors = []
    
    for field in schema.fields:
        if field.required and field.name not in params:
            errors.append(f"Missing required field: {field.name}")
    
    for name, value in params.items():
        field = next((f for f in schema.fields if f.name == name), None)
        if not field:
            errors.append(f"Unknown field: {name}")
            continue
        if field.min_value is not None and value < field.min_value:
            errors.append(f"{name}: {value} < min {field.min_value}")
        if field.max_value is not None and value > field.max_value:
            errors.append(f"{name}: {value} > max {field.max_value}")
        if field.enum_values and value not in field.enum_values:
            errors.append(f"{name}: {value} not in {field.enum_values}")
    
    return errors
```

**WHY NO STYLE REGISTRY?**

The old approach:
```python
# BAD: Enumerated styles limit creativity
STYLE_REGISTRY = {
    "aggressive_patrol": {...features...},  # Can only make these
    "rugged_workboat": {...features...},    # predefined designs
}
```

The new approach:
```python
# GOOD: Geometric primitives compose infinitely
CREATE geometry.body { body_type: "hull", offset_y_m: 3.0 }  # Any offset
CREATE geometry.section { station: 0.5, deadrise_deg: 25 }   # Any shape
LOFT [sections] INTO surface                                  # Any surface

# A "catamaran" is NOT a type — it's a composition of two bodies
# An "aggressive bow" is NOT a type — it's geometry with high deadrise
```

### Task 1.2: Design Language AST
**File:** `magnet/deployment/program_ast.py`

```python
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from abc import ABC

# ═══════════════════════════════════════════════════════════════════════════
# AST NODE TYPES — The internal representation of agent programs
# ═══════════════════════════════════════════════════════════════════════════

class ASTNode(ABC):
    """Base class for all AST nodes."""
    pass

@dataclass
class CreateNode(ASTNode):
    """CREATE <type> <id> { field: value, ... }"""
    resource_type: str           # "geometry.body", "geometry.section", etc.
    resource_id: str             # Unique identifier
    params: Dict[str, Any]       # Field values

@dataclass
class UpdateNode(ASTNode):
    """UPDATE <id> { field: value, ... }"""
    resource_id: str
    params: Dict[str, Any]

@dataclass
class DeleteNode(ASTNode):
    """DELETE <id>"""
    resource_id: str

@dataclass
class SetNode(ASTNode):
    """SET <path> = <value>"""
    path: str                    # e.g., "hull.loa"
    value: Any
    
@dataclass
class AlignNode(ASTNode):
    """ALIGN <ids> ON <axis>"""
    resource_ids: List[str]
    axis: str                    # "x", "y", "z", or "station"
    reference_value: Optional[float] = None  # If provided, align to this
    reference_id: Optional[str] = None       # Or align to this resource

@dataclass
class MirrorNode(ASTNode):
    """MIRROR <id> [AS <new_id>]"""
    source_id: str
    target_id: Optional[str] = None  # If None, mirrors in place

@dataclass
class LoftNode(ASTNode):
    """LOFT [section_ids] INTO <surface_id>"""
    section_ids: List[str]
    surface_id: str
    tension: float = 0.5
    continuity_bow: str = "G1"   # G0, G1, G2
    continuity_stern: str = "G1"

@dataclass
class OffsetNode(ASTNode):
    """OFFSET <surface_id> BY <distance_m>"""
    source_surface_id: str
    distance_m: float
    target_surface_id: Optional[str] = None

@dataclass
class ConstrainNode(ASTNode):
    """CONSTRAIN <path> <op> <value>"""
    path: str
    operator: str                # ">=", "<=", "==", "!=", ">", "<"
    value: Any
    persistent: bool = False     # PIN CONSTRAINT if True

@dataclass
class PreferNode(ASTNode):
    """PREFER <path> <direction> [weight]"""
    path: str
    direction: str               # "minimize", "maximize"
    weight: float = 1.0

@dataclass
class DeriveNode(ASTNode):
    """DERIVE <path> USING <policy>"""
    target_path: str
    policy_name: str
    params: Dict[str, Any] = field(default_factory=dict)
    
# ═══════════════════════════════════════════════════════════════════════════
# PROGRAM STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DesignProgram:
    """
    A complete program from an agent.
    
    This is what agents output. Contains geometric operations, not styles.
    """
    statements: List[ASTNode] = field(default_factory=list)
    
    # Metadata for auditability
    agent_id: Optional[str] = None
    rationale: str = ""
    confidence: float = 1.0
    assumptions: List[str] = field(default_factory=list)

@dataclass
class SemanticTrace:
    """Record of DesignProgram → ActionPlan compilation."""
    original_program: Dict[str, Any]
    statements_processed: int = 0
    kernel_functions_called: List[str] = field(default_factory=list)
    type_validations: List[Dict[str, Any]] = field(default_factory=list)
    actions_produced: int = 0
    compiler_version: str = "1.0"
    compiled_at: datetime = field(default_factory=datetime.utcnow)
    
    # For each action, trace back to originating statement
    action_provenance: Dict[int, int] = field(default_factory=dict)
```

### Task 1.3: Program Parser
**File:** `magnet/deployment/program_parser.py`

```python
"""
Parse textual design language into AST.

Example input:
```
CREATE geometry.body demihull_port {
    body_type: "hull",
    offset_y_m: -3.0
}

CREATE geometry.section section_00 {
    station: 0.0,
    definition_type: "parametric",
    half_beam_m: 0.8,
    draft_m: 0.5,
    deadrise_deg: 30
}

LOFT [section_00, section_05, section_10] INTO port_surface

CONSTRAIN stability.gm_m >= 2.0
```

The parser is SYNTACTIC ONLY. It does NOT:
- Validate types (kernel does this)
- Check field ranges (kernel does this)
- Resolve references (semantic expander does this)
"""

from typing import List
import re
from .program_ast import *

class ParseError(Exception):
    """Syntax error in design program."""
    pass

class ProgramParser:
    """Parse design language text into AST."""
    
    def parse(self, source: str) -> DesignProgram:
        """Parse source text into DesignProgram."""
        statements = []
        
        # Tokenize and parse each statement
        lines = self._preprocess(source)
        
        for line in lines:
            if not line.strip():
                continue
            
            node = self._parse_statement(line)
            if node:
                statements.append(node)
        
        return DesignProgram(statements=statements)
    
    def _parse_statement(self, line: str) -> Optional[ASTNode]:
        """Parse a single statement."""
        tokens = line.split()
        if not tokens:
            return None
        
        verb = tokens[0].upper()
        
        if verb == "CREATE":
            return self._parse_create(tokens[1:], line)
        elif verb == "UPDATE":
            return self._parse_update(tokens[1:], line)
        elif verb == "DELETE":
            return DeleteNode(resource_id=tokens[1])
        elif verb == "SET":
            return self._parse_set(tokens[1:])
        elif verb == "ALIGN":
            return self._parse_align(tokens[1:])
        elif verb == "MIRROR":
            return self._parse_mirror(tokens[1:])
        elif verb == "LOFT":
            return self._parse_loft(tokens[1:])
        elif verb == "OFFSET":
            return self._parse_offset(tokens[1:])
        elif verb == "CONSTRAIN":
            return self._parse_constrain(tokens[1:])
        elif verb == "PREFER":
            return self._parse_prefer(tokens[1:])
        elif verb == "DERIVE":
            return self._parse_derive(tokens[1:])
        elif verb == "PIN" and tokens[1].upper() == "CONSTRAINT":
            node = self._parse_constrain(tokens[2:])
            node.persistent = True
            return node
        else:
            raise ParseError(f"Unknown verb: {verb}")
    
    def _parse_create(self, tokens: List[str], full_line: str) -> CreateNode:
        """Parse CREATE statement with inline params."""
        # CREATE geometry.body demihull_port { body_type: "hull", ... }
        resource_type = tokens[0]
        resource_id = tokens[1]
        
        # Extract params from { ... }
        params = self._extract_params(full_line)
        
        return CreateNode(
            resource_type=resource_type,
            resource_id=resource_id,
            params=params,
        )
    
    def _parse_loft(self, tokens: List[str]) -> LoftNode:
        """Parse LOFT [ids] INTO surface_id."""
        # Find the bracket content
        ids_str = " ".join(tokens)
        match = re.search(r'\[(.*?)\]', ids_str)
        if not match:
            raise ParseError("LOFT requires [section_ids]")
        
        section_ids = [s.strip() for s in match.group(1).split(',')]
        
        # Find INTO
        into_idx = ids_str.upper().find("INTO")
        if into_idx == -1:
            raise ParseError("LOFT requires INTO <surface_id>")
        
        surface_id = ids_str[into_idx + 4:].strip().split()[0]
        
        return LoftNode(section_ids=section_ids, surface_id=surface_id)
    
    # ... other parse methods ...
```

### Task 1.4: Semantic Expander
**File:** `kernel/semantic_expander.py`

```python
"""
The Semantic Expander is the ONLY bridge from Design Language to ActionPlan.

It translates abstract operations (CREATE, LOFT, ALIGN) into concrete Actions
by calling KERNEL FUNCTIONS from the stdlib. This ensures:

1. All semantics live in the kernel (not a separate "language runtime")
2. The kernel owns geometry compilation (no second engine)
3. Every expansion is traceable

CRITICAL INVARIANTS:
- No arbitrary code execution
- geometry.section → HullSection (existing canonical class)
- geometry.surface → NURBSSurface (existing canonical class)
- All IDs are deterministic (same input → same output)
"""

from typing import List, Dict, Any
from dataclasses import asdict

from magnet.kernel.intent_protocol import Action, ActionType, ActionPlan
from magnet.control_plane.hsv import HypotheticalStateView
from magnet.core.state_manager import StateManager

# Kernel stdlib — ALL geometry semantics live here
from kernel.stdlib import resources, geometry, synthesis, constraints
from kernel.stdlib.type_registry import get_type_schema, validate_resource_params

from .program_ast import (
    DesignProgram, ASTNode, CreateNode, UpdateNode, DeleteNode,
    SetNode, AlignNode, MirrorNode, LoftNode, OffsetNode,
    ConstrainNode, PreferNode, DeriveNode, SemanticTrace
)

class ExpansionError(Exception):
    """Raised when semantic expansion fails."""
    pass

class SemanticExpander:
    """
    Expands DesignProgram AST into ActionPlan.
    
    The expander is THIN — it delegates all real logic to kernel/stdlib.
    This ensures the kernel owns all semantics.
    """
    
    VERSION = "1.0"
    
    def __init__(self, state: StateManager, design_id: str):
        self.state = state
        self.design_id = design_id
        self.actions: List[Action] = []
        self.trace = SemanticTrace(original_program={})
    
    def expand(self, program: DesignProgram, plan_id: str) -> ActionPlan:
        """Expand program to ActionPlan."""
        self.actions = []
        self.trace = SemanticTrace(original_program=asdict(program))
        
        for i, node in enumerate(program.statements):
            try:
                self._expand_node(node, statement_index=i)
            except Exception as e:
                raise ExpansionError(f"Statement {i}: {e}")
        
        self.trace.statements_processed = len(program.statements)
        self.trace.actions_produced = len(self.actions)
        
        return ActionPlan(
            plan_id=plan_id,
            intent_id=plan_id,
            design_id=self.design_id,
            actions=tuple(self.actions),
            design_version_before=self.state.design_version,
            semantic_trace=self.trace,
        )
    
    def _expand_node(self, node: ASTNode, statement_index: int):
        """Expand a single AST node by calling kernel functions."""
        
        if isinstance(node, CreateNode):
            # Type validation happens in kernel
            errors = validate_resource_params(node.resource_type, node.params)
            if errors:
                raise ExpansionError(f"Invalid params: {errors}")
            
            # Call kernel function
            actions = resources.create_resource(
                node.resource_type, 
                node.resource_id, 
                node.params,
                self.state
            )
            self._record_actions(actions, statement_index, "resources.create_resource")
            
        elif isinstance(node, LoftNode):
            # LOFT → kernel/stdlib/geometry.loft_sections_to_surface
            # This compiles geometry.section → HullSection
            # and creates geometry.surface → NURBSSurface
            actions = geometry.loft_sections_to_surface(
                node.section_ids,
                self.state,
                node.surface_id,
                tension=node.tension,
                continuity_bow=node.continuity_bow,
                continuity_stern=node.continuity_stern,
            )
            self._record_actions(actions, statement_index, "geometry.loft_sections_to_surface")
            
        elif isinstance(node, AlignNode):
            # ALIGN → kernel/stdlib/geometry.align_resources
            actions = geometry.align_resources(
                node.resource_ids,
                node.axis,
                self.state,
                reference_value=node.reference_value,
                reference_id=node.reference_id,
            )
            self._record_actions(actions, statement_index, "geometry.align_resources")
            
        elif isinstance(node, MirrorNode):
            # MIRROR → kernel/stdlib/geometry.mirror_resource
            # Uses TypeSchema.mirror_fields to know what to negate
            actions = geometry.mirror_resource(
                node.source_id,
                self.state,
                target_id=node.target_id,
            )
            self._record_actions(actions, statement_index, "geometry.mirror_resource")
            
        elif isinstance(node, OffsetNode):
            # OFFSET → kernel/stdlib/geometry.offset_surface
            actions = geometry.offset_surface(
                node.source_surface_id,
                node.distance_m,
                self.state,
                target_surface_id=node.target_surface_id,
            )
            self._record_actions(actions, statement_index, "geometry.offset_surface")
            
        elif isinstance(node, SetNode):
            # SET → direct Action
            self.actions.append(Action(
                action_type=ActionType.SET,
                path=node.path,
                value=node.value,
            ))
            self.trace.action_provenance[len(self.actions) - 1] = statement_index
            
        elif isinstance(node, ConstrainNode):
            # CONSTRAIN → kernel/stdlib/constraints.add_constraint
            actions = constraints.add_constraint(
                node.path,
                node.operator,
                node.value,
                self.state,
                persistent=node.persistent,
            )
            self._record_actions(actions, statement_index, "constraints.add_constraint")
            
        elif isinstance(node, DeriveNode):
            # DERIVE → kernel/stdlib/synthesis.derive_value
            actions = synthesis.derive_value(
                node.target_path,
                node.policy_name,
                self.state,
                params=node.params,
            )
            self._record_actions(actions, statement_index, "synthesis.derive_value")
            
        elif isinstance(node, UpdateNode):
            actions = resources.update_resource(
                node.resource_id,
                node.params,
                self.state
            )
            self._record_actions(actions, statement_index, "resources.update_resource")
            
        elif isinstance(node, DeleteNode):
            actions = resources.delete_resource(node.resource_id, self.state)
            self._record_actions(actions, statement_index, "resources.delete_resource")
    
    def _record_actions(self, actions: List[Action], stmt_idx: int, func_name: str):
        """Record actions with provenance."""
        start_idx = len(self.actions)
        self.actions.extend(actions)
        
        # Record provenance
        for i in range(start_idx, len(self.actions)):
            self.trace.action_provenance[i] = stmt_idx
        
        self.trace.kernel_functions_called.append(func_name)
```

### Task 1.5: Kernel stdlib Geometry Functions
**File:** `kernel/stdlib/geometry.py`

```python
"""
Kernel geometry functions.

CRITICAL: These functions compile design language primitives INTO
the existing canonical geometry classes. They do NOT create a new
geometry engine.

geometry.section → HullSection
geometry.surface → NURBSSurface
geometry.body   → entry in HullGeometry.bodies

All downstream consumers (tessellation, hydrostatics, export)
use the existing canonical classes unchanged.
"""

from typing import List, Dict, Any, Optional
from magnet.kernel.intent_protocol import Action, ActionType
from magnet.hull_gen.geometry import HullSection, NURBSSurface, Point3D
from magnet.hull_gen.nurbs import NURBSCurve, create_section_nurbs
from kernel.stdlib.type_registry import get_type_schema

def loft_sections_to_surface(
    section_ids: List[str],
    state: "StateManager",
    target_surface_id: str,
    tension: float = 0.5,
    continuity_bow: str = "G1",
    continuity_stern: str = "G1",
) -> List[Action]:
    """
    LOFT operation: Create NURBSSurface from geometry.sections.
    
    This is a KERNEL FUNCTION — called by the semantic expander.
    Returns Actions to be validated and executed.
    
    COMPILATION PATH:
    1. Fetch geometry.section resources from state
    2. Convert each to HullSection (canonical class)
    3. Fit NURBSSurface through sections
    4. Emit UPDATE actions to store surface
    """
    actions = []
    
    # 1. Gather sections and convert to HullSection
    hull_sections: List[HullSection] = []
    for section_id in section_ids:
        section_data = state.get(f"hull.features.geometry.section[{section_id}]")
        if not section_data:
            raise ValueError(f"Section not found: {section_id}")
        
        # Convert to canonical HullSection
        hull_section = _geometry_section_to_hull_section(section_data)
        hull_sections.append(hull_section)
    
    # 2. Sort by station
    hull_sections.sort(key=lambda s: s.station)
    
    # 3. Fit NURBSSurface (using existing nurbs.py functions)
    from magnet.hull_gen.nurbs import fit_surface_through_sections
    
    nurbs_surface = fit_surface_through_sections(
        hull_sections,
        degree_u=3,
        degree_v=3,
        tension=tension,
    )
    
    # 4. Create geometry.surface resource
    surface_data = {
        "surface_type": "hull_shell",
        "definition_type": "lofted",
        "section_ids": section_ids,
        "loft_tension": tension,
        "continuity_bow": continuity_bow,
        "continuity_stern": continuity_stern,
        # Store the compiled NURBS data
        "_compiled_nurbs": nurbs_surface.to_dict(),
    }
    
            actions.append(Action(
        action_type=ActionType.UPDATE,
        path=f"hull.features.geometry.surface[{target_surface_id}]",
        value=surface_data,
    ))
    
    return actions


def _geometry_section_to_hull_section(section_data: Dict[str, Any]) -> HullSection:
    """
    Convert geometry.section resource to canonical HullSection.
    
    This is the BRIDGE from language primitives to existing geometry.
    """
    from magnet.hull_gen.geometry import HullSection, SectionPoint
    
    definition_type = section_data.get("definition_type", "parametric")
    
    if definition_type == "parametric":
        # Generate section curve from parametric definition
        points = _generate_parametric_section(
            half_beam_m=section_data.get("half_beam_m", 1.0),
            draft_m=section_data.get("draft_m", 0.5),
            deadrise_deg=section_data.get("deadrise_deg", 15),
            fullness=section_data.get("fullness", 0.5),
        )
    elif definition_type == "points":
        # Direct point definition
        points = [
            SectionPoint(y=p["y"], z=p["z"])
            for p in section_data.get("points", [])
        ]
    elif definition_type == "nurbs_curve":
        # NURBS curve definition
        curve = NURBSCurve(
            control_points=section_data["nurbs_control_points"],
            degree=section_data.get("nurbs_degree", 3),
        )
        points = [SectionPoint(y=p[1], z=p[2]) for p in curve.sample(20)]
    else:
        raise ValueError(f"Unknown definition_type: {definition_type}")
    
    return HullSection(
        station=section_data.get("station", 0.5),
        x_position=section_data.get("x_position_m", 0.0),
        points=tuple(points),
        is_midship=section_data.get("is_midship", False),
        is_transom=section_data.get("is_transom", False),
    )


def align_resources(
    resource_ids: List[str],
    axis: str,
    state: "StateManager",
    reference_value: Optional[float] = None,
    reference_id: Optional[str] = None,
) -> List[Action]:
    """
    ALIGN operation: Set axis values to match.
    
    Uses TypeSchema.alignable_axes to determine valid axes.
    """
    from kernel.stdlib.type_registry import get_type_schema
    
    actions = []
    
    # Determine reference value
    if reference_value is None and reference_id:
        ref_resource = state.get_resource(reference_id)
        reference_value = ref_resource.get(axis)
    elif reference_value is None:
        # Use first resource as reference
        first_resource = state.get_resource(resource_ids[0])
        reference_value = first_resource.get(axis)
    
    # Update all resources
    for rid in resource_ids:
        actions.append(Action(
            action_type=ActionType.UPDATE,
            path=f"{rid}.{axis}",
            value=reference_value,
        ))
    
    return actions


def mirror_resource(
    source_id: str,
    state: "StateManager",
    target_id: Optional[str] = None,
) -> List[Action]:
    """
    MIRROR operation: Create mirrored copy of resource.
    
    Uses TypeSchema.mirror_fields and mirror_behavior to determine
    which fields to negate.
    """
    from kernel.stdlib.type_registry import get_type_schema
    
    source = state.get_resource(source_id)
    if not source:
        raise ValueError(f"Resource not found: {source_id}")
    
    resource_type = source.get("_type")
    schema = get_type_schema(resource_type)
    
    if not schema.mirrorable:
        if schema.mirror_behavior == "error":
            raise ValueError(f"Cannot mirror {resource_type}")
        elif schema.mirror_behavior == "no_op":
            return []
    
    # Create mirrored copy
    mirrored = dict(source)
    for field in schema.mirror_fields:
        if field in mirrored:
            mirrored[field] = -mirrored[field]  # Negate
    
    target = target_id or f"{source_id}_mirrored"
    
    return [Action(
        action_type=ActionType.UPDATE,
        path=f"hull.features.{resource_type}[{target}]",
        value=mirrored,
    )]
```

### Task 1.6: Design Language API Endpoint
**File:** `magnet/deployment/api.py` (add endpoint)

```python
from kernel.semantic_expander import SemanticExpander
from magnet.deployment.program_parser import ProgramParser
from magnet.deployment.program_ast import DesignProgram

@app.post("/api/v1/designs/{design_id}/program")
async def execute_program(
    design_id: str,
    body: Dict[str, Any],
    state_manager: StateManager = Depends(get_state_manager),
    validator: ActionValidator = Depends(get_validator),
    executor: ActionExecutor = Depends(get_executor),
):
    """
    Execute a Design Language program.
    
    Accepts either:
    - "source": String of design language text
    - "program": Pre-parsed AST as JSON
    
    Program is parsed → expanded → validated → executed.
    Returns result with semantic trace for auditability.
    """
    # Parse or accept pre-parsed AST
    if "source" in body:
        parser = ProgramParser()
        program = parser.parse(body["source"])
    else:
        program = DesignProgram(**body.get("program", {}))
    
    # Expand to ActionPlan (calls kernel/stdlib functions)
    expander = SemanticExpander(state_manager, design_id)
    plan = expander.expand(program, plan_id=str(uuid.uuid4()))
    
    # Validate (existing kernel validator)
    validation = validator.validate_plan(plan, state_manager)
    
    if not validation.all_approved:
        return {
            "success": False,
            "rejected": [(str(a), r) for a, r in validation.rejected],
            "semantic_trace": asdict(plan.semantic_trace),
        }
    
    # Execute (existing kernel executor)
    exec_result = executor.execute(validation.approved, plan, state_manager)
    
    # Generate digest
    digest = generate_digest(state_manager, exec_result.design_version_after)
    
    return {
        "success": True,
        "version": exec_result.design_version_after,
        "digest": digest,
        "semantic_trace": asdict(plan.semantic_trace),
        "explain_record_id": exec_result.explain_record_id,
    }


@app.post("/api/v1/designs/{design_id}/program/preview")
async def preview_program(
    design_id: str,
    body: Dict[str, Any],
    state_manager: StateManager = Depends(get_state_manager),
):
    """
    Preview a Design Language program without execution.
    
    Uses HSV to show what would change.
    """
    parser = ProgramParser()
    program = parser.parse(body.get("source", ""))
    
    expander = SemanticExpander(state_manager, design_id)
    plan = expander.expand(program, plan_id="preview")
    
    # Use HSV to preview
    from magnet.control_plane.hsv import HypotheticalStateView
    hsv = HypotheticalStateView(state_manager, list(plan.actions))
    
    return {
        "preview": hsv.to_digest(),
        "actions_count": len(plan.actions),
        "semantic_trace": asdict(plan.semantic_trace),
    }
```

### Deliverables (Phase 1)
- [ ] `kernel/stdlib/type_registry.py` — Kernel-owned type schemas
- [ ] `magnet/deployment/program_ast.py` — AST node definitions
- [ ] `magnet/deployment/program_parser.py` — Text → AST parser
- [ ] `kernel/semantic_expander.py` — AST → ActionPlan expander
- [ ] `kernel/stdlib/geometry.py` — Geometry functions (LOFT, ALIGN, MIRROR)
- [ ] `kernel/stdlib/resources.py` — Resource functions (CREATE, UPDATE, DELETE)
- [ ] `/api/v1/designs/{design_id}/program` endpoint
- [ ] `/api/v1/designs/{design_id}/program/preview` endpoint
- [ ] Unit tests for parser and expander

**Acid Test for Phase 1:**
```
# This program should create a catamaran without any "catamaran" type
CREATE geometry.body port_hull { body_type: "hull", offset_y_m: -3.0 }
CREATE geometry.body stbd_hull { body_type: "hull", offset_y_m: 3.0 }

CREATE geometry.section port_bow { station: 0.0, half_beam_m: 0.5, draft_m: 0.3 }
CREATE geometry.section port_mid { station: 0.5, half_beam_m: 1.0, draft_m: 0.8 }
CREATE geometry.section port_stern { station: 1.0, half_beam_m: 0.8, draft_m: 0.6 }

LOFT [port_bow, port_mid, port_stern] INTO port_surface
MIRROR port_hull AS stbd_hull
MIRROR port_surface AS stbd_surface

CONSTRAIN stability.gm_m >= 2.0
```

---

## Phase 2: Agent Protocol & Base Agent (Days 6-10)

### Goal
Define how agents communicate and create the base agent implementation.

**Key Principle:** Agents output **DesignProgram** with geometric primitives only.

### Task 2.1: Agent Protocol
**File:** `magnet/agents/protocol.py`

```python
from typing import Protocol, List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from magnet.deployment.program_ast import DesignProgram, ConstrainNode, PreferNode

@dataclass
class DesignProblem:
    """User intent decomposed into a structured design problem."""
    problem_id: str
    raw_intent: str
    
    # Extracted requirements (as AST nodes)
    constraints: List[ConstrainNode] = field(default_factory=list)
    preferences: List[PreferNode] = field(default_factory=list)
    
    # Context
    design_id: str = ""
    design_version: int = 0
    state_snapshot: Dict[str, Any] = field(default_factory=dict)
    
    # Existing geometry (for agents to extend/modify)
    existing_bodies: List[str] = field(default_factory=list)
    existing_surfaces: List[str] = field(default_factory=list)

@dataclass
class AgentProposal:
    """What an agent proposes — GEOMETRIC PRIMITIVES, not styles."""
    proposal_id: str
    agent_id: str
    domain: str
    
    # The proposal: a DesignProgram with CREATE, LOFT, ALIGN, etc.
    program: DesignProgram
    
    # Reasoning
    rationale: str
    confidence: float  # 0.0 - 1.0
    assumptions: List[str] = field(default_factory=list)
    trade_offs: List[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_source(self) -> str:
        """Convert program to text for debugging/display."""
        lines = []
        for stmt in self.program.statements:
            lines.append(str(stmt))  # AST node __str__
        return "\n".join(lines)

@dataclass
class CritiqueIssue:
    """A single issue found in a proposal."""
    severity: str  # "blocking", "warning", "suggestion"
    message: str
    statement_index: Optional[int] = None  # Which statement has the issue
    suggested_replacement: Optional[str] = None  # Replacement statement

@dataclass
class AgentCritique:
    """Critique of another agent's proposal."""
    critique_id: str
    critic_agent_id: str
    proposal_id: str
    
    verdict: str  # "approve", "reject", "modify"
    issues: List[CritiqueIssue] = field(default_factory=list)
    
    # Suggested modifications as additional statements
    additional_statements: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)

@dataclass
class FeedbackPackage:
    """Kernel feedback packaged for agent consumption."""
    passed: bool
    findings: List[Dict[str, Any]]
    blocking_issues: List[str]
    suggested_adjustments: List[Dict[str, Any]]
    
    # Which statements failed validation
    failed_statements: List[int] = field(default_factory=list)
    
    def to_prompt_context(self) -> str:
        """Format for LLM consumption."""
        if self.passed:
            return "All validations passed."
        
        lines = ["Validation failed:"]
        for issue in self.blocking_issues:
            lines.append(f"  - {issue}")
        if self.failed_statements:
            lines.append(f"\nFailed statements: {self.failed_statements}")
        if self.suggested_adjustments:
            lines.append("\nSuggested adjustments:")
            for adj in self.suggested_adjustments:
                lines.append(f"  - {adj}")
        return "\n".join(lines)

class AgentProtocol(Protocol):
    """Interface all agents must implement."""
    agent_id: str
    domain: str
    
    def propose(self, problem: DesignProblem, state: "AgentStateAccessor") -> AgentProposal:
        """Generate a proposal from this agent's perspective using geometric primitives."""
        ...
    
    def critique(self, proposal: AgentProposal, state: "AgentStateAccessor") -> AgentCritique:
        """Critique another agent's proposal."""
        ...
    
    def refine(self, proposal: AgentProposal, critiques: List[AgentCritique]) -> AgentProposal:
        """Refine proposal based on critiques."""
        ...
    
    def ingest_feedback(self, feedback: FeedbackPackage) -> None:
        """Learn from kernel validation feedback."""
        ...
```

### Task 2.2: Agent State Accessor
**File:** `magnet/agents/state_accessor.py`

```python
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from magnet.core.state_manager import StateManager
from magnet.control_plane.hsv import HypotheticalStateView
from magnet.control_plane.query import query_explain, query_history
from kernel.semantic_expander import SemanticExpander
from magnet.deployment.program_ast import DesignProgram, ConstrainNode

@dataclass
class ConstraintViolation:
    constraint: ConstrainNode
    actual_value: Any
    expected: str

class AgentStateAccessor:
    """
    Unified state access for agents.
    
    Provides:
    - Current state reading
    - Existing geometry queries (bodies, sections, surfaces)
    - Hypothetical preview
    - Constraint checking
    - History queries
    """
    
    def __init__(self, state_manager: StateManager, design_id: str):
        self._state = state_manager
        self._design_id = design_id
    
    @property
    def design_version(self) -> int:
        return self._state.design_version
    
    # Current state
    def get_current(self, path: str) -> Any:
        return self._state.get(path)
    
    def get_snapshot(self, paths: List[str]) -> Dict[str, Any]:
        return {p: self._state.get(p) for p in paths}
    
    # Geometry queries — agents need to know what exists
    def list_bodies(self) -> List[str]:
        """List all geometry.body IDs."""
        bodies = self._state.get("hull.features.geometry.body") or {}
        return list(bodies.keys())
    
    def list_sections(self, body_id: Optional[str] = None) -> List[str]:
        """List all geometry.section IDs, optionally filtered by body."""
        sections = self._state.get("hull.features.geometry.section") or {}
        if body_id:
            return [sid for sid, s in sections.items() if s.get("body_id") == body_id]
        return list(sections.keys())
    
    def list_surfaces(self, body_id: Optional[str] = None) -> List[str]:
        """List all geometry.surface IDs."""
        surfaces = self._state.get("hull.features.geometry.surface") or {}
        if body_id:
            return [sid for sid, s in surfaces.items() if s.get("body_id") == body_id]
        return list(surfaces.keys())
    
    def get_body(self, body_id: str) -> Optional[Dict[str, Any]]:
        """Get body definition."""
        return self._state.get(f"hull.features.geometry.body[{body_id}]")
    
    def get_section(self, section_id: str) -> Optional[Dict[str, Any]]:
        """Get section definition."""
        return self._state.get(f"hull.features.geometry.section[{section_id}]")
    
    # Hypothetical preview
    def preview(self, program: DesignProgram) -> Dict[str, Any]:
        """Preview program without execution."""
        expander = SemanticExpander(self._state, self._design_id)
        plan = expander.expand(program, "preview")
        hsv = HypotheticalStateView(self._state, list(plan.actions))
        return hsv.to_digest()
    
    # Constraint checking
    def check_constraints(
        self,
        constraints: List[ConstrainNode],
        program: DesignProgram,
    ) -> List[ConstraintViolation]:
        """Check if program satisfies constraints."""
        expander = SemanticExpander(self._state, self._design_id)
        plan = expander.expand(program, "check")
        hsv = HypotheticalStateView(self._state, list(plan.actions))
        
        violations = []
        for c in constraints:
            projected = hsv.get(c.path)
            if projected.value is not None:
                # Evaluate constraint
                ops = {
                    ">=": lambda a, b: a >= b,
                    "<=": lambda a, b: a <= b,
                    "==": lambda a, b: a == b,
                }
                if not ops.get(c.operator, lambda a, b: True)(projected.value, c.value):
                violations.append(ConstraintViolation(
                    constraint=c,
                    actual_value=projected.value,
                        expected=f"{c.path} {c.operator} {c.value}",
                ))
        return violations
    
    # History queries
    def why_changed(self, path: str) -> Dict[str, Any]:
        return query_explain(path, self._design_id)
    
    def get_history(self, path: str, limit: int = 10) -> List[Dict[str, Any]]:
        return query_history(path, self._design_id, limit)
```

### Task 2.3: Base Agent
**File:** `magnet/agents/base.py`

```python
from typing import List, Optional
import uuid

from magnet.llm.providers.base import BaseProvider
from magnet.deployment.program_ast import DesignProgram
from magnet.deployment.program_parser import ProgramParser

from .protocol import (
    AgentProtocol, DesignProblem, AgentProposal, 
    AgentCritique, FeedbackPackage
)
from .state_accessor import AgentStateAccessor

class BaseAgent:
    """
    Base agent implementation with LLM integration.
    
    Agents output DESIGN PROGRAMS with geometric primitives, not styles.
    
    Example agent output:
        CREATE geometry.body demihull { body_type: "hull", offset_y_m: 3.0 }
        CREATE geometry.section bow { station: 0.0, half_beam_m: 0.8 }
        LOFT [bow, mid, stern] INTO surface
        CONSTRAIN stability.gm_m >= 2.0
    """
    
    def __init__(
        self,
        agent_id: str,
        domain: str,
        llm_provider: BaseProvider,
        system_prompt: str,
    ):
        self.agent_id = agent_id
        self.domain = domain
        self._llm = llm_provider
        self._system_prompt = system_prompt
        self._parser = ProgramParser()
        self._memory: List[dict] = []
        self._last_feedback: Optional[FeedbackPackage] = None
    
    def propose(self, problem: DesignProblem, state: AgentStateAccessor) -> AgentProposal:
        """Generate a proposal using LLM — outputs geometric primitives."""
        prompt = self._build_propose_prompt(problem, state)
        
        response = self._llm.complete_json(
            prompt,
            schema=GeometricProposalSchema,  # Expects program source
        )
        
        # Parse the program source into AST
        program = self._parser.parse(response.program_source)
        program.agent_id = self.agent_id
        program.rationale = response.rationale
        program.confidence = response.confidence
        
        return AgentProposal(
            proposal_id=str(uuid.uuid4()),
            agent_id=self.agent_id,
            domain=self.domain,
            program=program,
            rationale=response.rationale,
            confidence=response.confidence,
            assumptions=response.assumptions,
        )
    
    def critique(self, proposal: AgentProposal, state: AgentStateAccessor) -> AgentCritique:
        """Critique another agent's proposal."""
        prompt = self._build_critique_prompt(proposal, state)
        
        response = self._llm.complete_json(
            prompt,
            schema=CritiqueSchema,
        )
        
        return AgentCritique(
            critique_id=str(uuid.uuid4()),
            critic_agent_id=self.agent_id,
            proposal_id=proposal.proposal_id,
            verdict=response.verdict,
            issues=response.issues,
            additional_statements=response.additional_statements,
            risks=response.risks,
        )
    
    def refine(self, proposal: AgentProposal, critiques: List[AgentCritique]) -> AgentProposal:
        """Refine proposal based on critiques."""
        prompt = self._build_refine_prompt(proposal, critiques)
        
        response = self._llm.complete_json(
            prompt,
            schema=GeometricProposalSchema,
        )
        
        program = self._parser.parse(response.program_source)
        program.agent_id = self.agent_id
        
        return AgentProposal(
            proposal_id=str(uuid.uuid4()),
            agent_id=self.agent_id,
            domain=self.domain,
            program=program,
            rationale=response.rationale,
            confidence=response.confidence,
        )
    
    def ingest_feedback(self, feedback: FeedbackPackage) -> None:
        """Store feedback for next iteration."""
        self._last_feedback = feedback
        self._memory.append({
            "type": "feedback",
            "passed": feedback.passed,
            "issues": feedback.blocking_issues,
        })
    
    def _build_propose_prompt(self, problem: DesignProblem, state: AgentStateAccessor) -> str:
        feedback_context = ""
        if self._last_feedback and not self._last_feedback.passed:
            feedback_context = f"""
## Previous Attempt Failed
{self._last_feedback.to_prompt_context()}

Adjust your proposal to address these issues.
"""
        
        # Show existing geometry so agent can extend it
        existing_bodies = state.list_bodies()
        existing_surfaces = state.list_surfaces()
        
        return f"""
{self._system_prompt}

## Current Design State
Version: {state.design_version}
{self._format_state(state.get_snapshot(self._relevant_paths()))}

Existing bodies: {existing_bodies}
Existing surfaces: {existing_surfaces}

## Design Problem
User intent: {problem.raw_intent}
Constraints: {[str(c) for c in problem.constraints]}
Preferences: {[str(p) for p in problem.preferences]}
{feedback_context}

## Your Task
Propose geometry changes from your {self.domain} perspective.

Output a DESIGN PROGRAM using these primitives:
- CREATE geometry.body <id> {{ body_type: "hull"|"pontoon", offset_y_m: N }}
- CREATE geometry.section <id> {{ station: 0-1, half_beam_m: N, draft_m: N, deadrise_deg: N }}
- LOFT [section_id, ...] INTO <surface_id>
- MIRROR <id> AS <new_id>
- ALIGN [ids] ON <axis>
- CONSTRAIN <path> >= <value>
- SET <path> = <value>

DO NOT use "styles" — compose geometry directly.

Return JSON:
{{
  "program_source": "CREATE geometry.body...\\nLOFT...\\nCONSTRAIN...",
  "rationale": "Why this proposal",
  "confidence": 0.0-1.0,
  "assumptions": ["assumption1", ...]
}}
"""
    
    def _relevant_paths(self) -> List[str]:
        """Override in subclass to specify domain-relevant paths."""
        return []
```

### Task 2.4: Domain Agents
**Files:** `magnet/agents/domains/*.py`

```python
# magnet/agents/domains/hull_agent.py

HULL_AGENT_PROMPT = """
You are the Hull Form Agent. Your expertise:
- Hull geometry: bodies, sections, surfaces
- Section shape: deadrise, beam, draft, fullness
- Surface lofting and continuity
- Multi-hull configurations (catamaran = two bodies with offset)

You optimize for: hydrodynamic efficiency, internal volume, structural simplicity.

You do NOT know about: stability calculations, resistance predictions, manufacturing.
Those are other agents' domains. Focus only on hull form geometry.

CRITICAL: You output GEOMETRIC PRIMITIVES, not named styles.

Example for a catamaran:
```
CREATE geometry.body port_hull { body_type: "hull", offset_y_m: -3.0 }
CREATE geometry.body stbd_hull { body_type: "hull", offset_y_m: 3.0 }

CREATE geometry.section port_bow { station: 0.0, half_beam_m: 0.5, draft_m: 0.3, deadrise_deg: 30 }
CREATE geometry.section port_mid { station: 0.5, half_beam_m: 1.0, draft_m: 0.8, deadrise_deg: 15 }
CREATE geometry.section port_stern { station: 1.0, half_beam_m: 0.8, draft_m: 0.6, deadrise_deg: 20 }

LOFT [port_bow, port_mid, port_stern] INTO port_surface
MIRROR port_hull AS stbd_hull
MIRROR port_surface AS stbd_surface
```

A "stepped hull" is NOT a type — it's:
```
CREATE geometry.discontinuity step_1 { surface_id: "main_surface", station: 0.65, depth_m: 0.08 }
CREATE geometry.opening vent_inlet { surface_id: "main_surface", center_u: 0.7, shape: "rectangle" }
```
"""

class HullFormAgent(BaseAgent):
    def __init__(self, llm_provider: BaseProvider):
        super().__init__(
            agent_id="hull_form",
            domain="hull",
            llm_provider=llm_provider,
            system_prompt=HULL_AGENT_PROMPT,
        )
    
    def _relevant_paths(self) -> List[str]:
        return [
            "hull.loa", "hull.lwl", "hull.beam", "hull.draft", "hull.depth",
            "hull.cb", "hull.cp", "hull.cm",
        ]


# magnet/agents/domains/stability_agent.py

STABILITY_AGENT_PROMPT = """
You are the Stability Agent. Your expertise:
- Metacentric height (GM)
- Roll period and damping
- Righting arm curves
- Weight distribution effects

You ADD CONSTRAINTS to ensure stability requirements are met.
You may suggest geometry changes that improve stability (wider beam, lower CG).

Example output:
```
CONSTRAIN stability.gm_m >= 1.5
CONSTRAIN stability.roll_period_s >= 4.0
UPDATE geometry.section mid { half_beam_m: 2.5 }  # Wider for better GM
```

You do NOT design the hull form — you constrain and modify it for stability.
"""


# magnet/agents/domains/resistance_agent.py

RESISTANCE_AGENT_PROMPT = """
You are the Resistance Agent. Your expertise:
- Frictional resistance
- Wave-making resistance  
- Form factor effects
- Speed-length ratio optimization

You may suggest section shapes that reduce resistance.

Example output:
```
UPDATE geometry.section bow { deadrise_deg: 25, fullness: 0.4 }  # Fine entry
CREATE geometry.discontinuity step { station: 0.65, depth_m: 0.08 }  # Reduce wetted area
PREFER resistance.total_kw minimize
```

You do NOT design the overall form — you optimize for resistance.
"""
```

### Deliverables (Phase 2)
- [ ] `magnet/agents/protocol.py` — Agent protocol with DesignProgram
- [ ] `magnet/agents/state_accessor.py` — State access with geometry queries
- [ ] `magnet/agents/base.py` — Base agent outputting geometric primitives
- [ ] `magnet/agents/domains/hull_agent.py` — Hull geometry expert
- [ ] `magnet/agents/domains/stability_agent.py` — Stability constraints expert
- [ ] `magnet/agents/domains/resistance_agent.py` — Resistance optimization expert
- [ ] `magnet/agents/domains/manufacturing_agent.py` — Manufacturing constraints
- [ ] `magnet/agents/domains/aesthetics_agent.py` — Aesthetic composition

**Acid Test for Phase 2:**
Given: "Design a fast catamaran"
Hull Agent should output something like:
```
CREATE geometry.body port_hull { body_type: "hull", offset_y_m: -3.0 }
CREATE geometry.body stbd_hull { body_type: "hull", offset_y_m: 3.0 }
CREATE geometry.section bow { station: 0.0, half_beam_m: 0.5, deadrise_deg: 30 }
...
LOFT [bow, mid, stern] INTO port_surface
MIRROR port_surface AS stbd_surface
```

NOT:
```
STYLE = "catamaran"  # WRONG: enumerated style
SET hull.hull_type = "CATAMARAN"  # WRONG: type enum
```

---

## Phase 3: Swarm Orchestrator (Days 11-15)

### Goal
Enable parallel agent proposals, cross-critique, conflict resolution, and iteration.

**Key Principle:** Swarm merges **geometric programs**, not enumerated styles.

### Task 3.1: Conflict Detection & Resolution
**File:** `magnet/agents/conflict.py`

```python
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict

from .protocol import AgentProposal
from magnet.deployment.program_ast import (
    DesignProgram, ASTNode, CreateNode, UpdateNode, SetNode
)

@dataclass
class Conflict:
    """Conflict between agent proposals on geometry or values."""
    resource_id: Optional[str]  # For resource conflicts
    path: Optional[str]         # For SET conflicts
    conflict_type: str          # "resource", "value", "constraint"
    proposals: List[Tuple[str, Any]]  # [(agent_id, statement), ...]
    resolution: Optional[Tuple[str, Any]] = None

# Priority order: safety > performance > cost > aesthetics
DOMAIN_PRIORITY = {
    "stability": 1,   # Safety first — their constraints win
    "resistance": 2,  # Performance
    "hull": 3,        # Form — they create the base geometry
    "manufacturing": 4,  # Cost
    "aesthetics": 5,  # Last
}

def detect_conflicts(proposals: List[AgentProposal]) -> List[Conflict]:
    """Find resources or paths where agents propose different values."""
    conflicts = []
    
    # Track resource modifications by ID
    resource_mods: Dict[str, List[Tuple[str, ASTNode]]] = defaultdict(list)
    # Track SET operations by path
    set_ops: Dict[str, List[Tuple[str, Any]]] = defaultdict(list)
    
    for proposal in proposals:
        for stmt in proposal.program.statements:
            if isinstance(stmt, CreateNode):
                resource_mods[stmt.resource_id].append((proposal.agent_id, stmt))
            elif isinstance(stmt, UpdateNode):
                resource_mods[stmt.resource_id].append((proposal.agent_id, stmt))
            elif isinstance(stmt, SetNode):
                set_ops[stmt.path].append((proposal.agent_id, stmt.value))
    
    # Find resource conflicts
    for rid, mods in resource_mods.items():
        if len(mods) > 1:
            conflicts.append(Conflict(
                resource_id=rid,
                path=None,
                conflict_type="resource",
                proposals=mods,
            ))
    
    # Find value conflicts
    for path, values in set_ops.items():
        unique_values = set(v for _, v in values)
        if len(unique_values) > 1:
            conflicts.append(Conflict(
                resource_id=None,
                path=path,
                conflict_type="value",
                proposals=values,
            ))
    
    return conflicts

def resolve_conflicts(conflicts: List[Conflict]) -> List[Conflict]:
    """Resolve conflicts using domain priority."""
    for conflict in conflicts:
        # Sort by priority (lower = higher priority)
        sorted_proposals = sorted(
            conflict.proposals,
            key=lambda x: DOMAIN_PRIORITY.get(x[0].split("_")[0], 99)
        )
        winner = sorted_proposals[0]
        conflict.resolution = winner
    
    return conflicts
```

### Task 3.2: Swarm Orchestrator
**File:** `magnet/agents/swarm.py`

```python
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from collections import defaultdict

from magnet.kernel.action_validator import ActionValidator
from magnet.kernel.action_executor import ActionExecutor
from magnet.core.state_manager import StateManager
from kernel.semantic_expander import SemanticExpander

from .protocol import (
    AgentProtocol, DesignProblem, AgentProposal, 
    AgentCritique, FeedbackPackage
)
from .state_accessor import AgentStateAccessor
from .conflict import detect_conflicts, resolve_conflicts, Conflict
from magnet.deployment.program_ast import (
    DesignProgram, CreateNode, UpdateNode, SetNode, 
    ConstrainNode, LoftNode, MirrorNode, AlignNode
)

class ConvergenceError(Exception):
    """Raised when swarm fails to converge."""
    pass

@dataclass
class SwarmResult:
    """Result of swarm deliberation."""
    success: bool
    merged_program: DesignProgram  # The final merged program
    conflicts_resolved: List[Conflict]
    agent_reasoning: Dict[str, str]
    iterations: int
    version_after: Optional[int] = None
    explain_record_id: Optional[str] = None

class Swarm:
    """
    Multi-agent swarm orchestrator.
    
    Merges GEOMETRIC PROGRAMS from multiple agents.
    
    Runs: propose → critique → refine → merge → expand → validate → feedback loop
    """
    
    def __init__(
        self,
        agents: List[AgentProtocol],
        validator: ActionValidator,
        executor: ActionExecutor,
        max_iterations: int = 5,
    ):
        self.agents = agents
        self.validator = validator
        self.executor = executor
        self.max_iterations = max_iterations
    
    async def deliberate(
        self,
        problem: DesignProblem,
        state: StateManager,
    ) -> SwarmResult:
        """
        Run the swarm deliberation loop.
        
        1. All agents propose geometry programs in parallel
        2. Cross-critique proposals
        3. Refine based on critiques
        4. Detect and resolve conflicts (on resources/values)
        5. Merge into single DesignProgram
        6. Expand to ActionPlan (via kernel/stdlib)
        7. Validate with kernel
        8. If rejected, feed back and iterate
        """
        accessor = AgentStateAccessor(state, problem.design_id)
        
        for iteration in range(self.max_iterations):
            # 1. Parallel proposals
            proposals = await self._propose_parallel(problem, accessor)
            
            # 2. Cross-critique
            critiques = await self._cross_critique(proposals, accessor)
            
            # 3. Refine
            refined = await self._refine_proposals(proposals, critiques)
            
            # 4. Detect conflicts
            conflicts = detect_conflicts(refined)
            
            # 5. Resolve conflicts
            resolved_conflicts = resolve_conflicts(conflicts)
            
            # 6. Merge into single program
            merged_program = self._merge_programs(refined, resolved_conflicts)
            
            # 7. Expand to ActionPlan (calls kernel/stdlib functions)
            expander = SemanticExpander(state, problem.design_id)
            plan = expander.expand(merged_program, f"swarm_{iteration}")
            
            # 8. Validate
            validation = self.validator.validate_plan(plan, state)
            
            if validation.all_approved:
                # 9. Execute
                exec_result = self.executor.execute(
                    validation.approved, 
                    plan, 
                    state
                )
                
                return SwarmResult(
                    success=True,
                    merged_program=merged_program,
                    conflicts_resolved=resolved_conflicts,
                    agent_reasoning={p.agent_id: p.rationale for p in refined},
                    iterations=iteration + 1,
                    version_after=exec_result.design_version_after,
                    explain_record_id=exec_result.explain_record_id,
                )
            
            # 10. Package feedback
            feedback = self._package_feedback(validation, plan)
            
            # 11. Feed back to all agents
            for agent in self.agents:
                agent.ingest_feedback(feedback)
        
        raise ConvergenceError(
            f"Swarm did not converge in {self.max_iterations} iterations"
        )
    
    def _merge_programs(
        self,
        proposals: List[AgentProposal],
        resolved_conflicts: List[Conflict],
    ) -> DesignProgram:
        """
        Merge all agent programs into single DesignProgram.
        
        Strategy:
        1. Collect all CREATE statements (first one wins for same ID)
        2. Collect all UPDATE statements (resolve conflicts by priority)
        3. Collect all SET statements (resolve conflicts by priority)
        4. Collect all CONSTRAIN statements (union - all constraints apply)
        5. Collect all LOFT/MIRROR/ALIGN statements (all apply)
        """
        merged = DesignProgram()
        
        # Build conflict resolution map
        conflict_winners = {}
        for c in resolved_conflicts:
            if c.resolution:
                key = c.resource_id or c.path
                conflict_winners[key] = c.resolution[0]  # winning agent_id
        
        # Track seen resources to avoid duplicates
        seen_creates: Dict[str, str] = {}  # resource_id -> agent_id
        
        for proposal in proposals:
            for stmt in proposal.program.statements:
                if isinstance(stmt, CreateNode):
                    if stmt.resource_id in seen_creates:
                        # Already created by another agent
                        if stmt.resource_id in conflict_winners:
                            # Only add if this agent won the conflict
                            if conflict_winners[stmt.resource_id] == proposal.agent_id:
                                # Replace existing
                                merged.statements = [
                                    s for s in merged.statements 
                                    if not (isinstance(s, CreateNode) and s.resource_id == stmt.resource_id)
                                ]
                                merged.statements.append(stmt)
                    else:
                        seen_creates[stmt.resource_id] = proposal.agent_id
                        merged.statements.append(stmt)
                        
                elif isinstance(stmt, UpdateNode):
                    # Updates are merged; conflicts resolved by priority
                    if stmt.resource_id in conflict_winners:
                        if conflict_winners[stmt.resource_id] == proposal.agent_id:
                            merged.statements.append(stmt)
                    else:
                        merged.statements.append(stmt)
                        
                elif isinstance(stmt, SetNode):
                    # SETs are merged; conflicts resolved by priority
                    if stmt.path in conflict_winners:
                        if conflict_winners[stmt.path] == proposal.agent_id:
                            merged.statements.append(stmt)
                    else:
                        merged.statements.append(stmt)
                        
                elif isinstance(stmt, ConstrainNode):
                    # All constraints apply (union)
                    merged.statements.append(stmt)
                    
                elif isinstance(stmt, (LoftNode, MirrorNode, AlignNode)):
                    # These operations are not conflicting — all apply
                    merged.statements.append(stmt)
        
        return merged
    
    async def _propose_parallel(
        self,
        problem: DesignProblem,
        accessor: AgentStateAccessor,
    ) -> List[AgentProposal]:
        """All agents propose simultaneously."""
        tasks = [
            asyncio.to_thread(agent.propose, problem, accessor)
            for agent in self.agents
        ]
        return await asyncio.gather(*tasks)
    
    async def _cross_critique(
        self,
        proposals: List[AgentProposal],
        accessor: AgentStateAccessor,
    ) -> Dict[str, List[AgentCritique]]:
        """Each agent critiques all other proposals."""
        critiques: Dict[str, List[AgentCritique]] = defaultdict(list)
        
        for agent in self.agents:
            for proposal in proposals:
                if proposal.agent_id != agent.agent_id:
                    critique = await asyncio.to_thread(
                        agent.critique, proposal, accessor
                    )
                    critiques[proposal.proposal_id].append(critique)
        
        return critiques
    
    async def _refine_proposals(
        self,
        proposals: List[AgentProposal],
        critiques: Dict[str, List[AgentCritique]],
    ) -> List[AgentProposal]:
        """Each agent refines based on critiques received."""
        refined = []
        for proposal in proposals:
            agent = next(a for a in self.agents if a.agent_id == proposal.agent_id)
            proposal_critiques = critiques.get(proposal.proposal_id, [])
            
            if any(c.verdict == "reject" for c in proposal_critiques):
                # Must refine if any blocking critique
                new_proposal = await asyncio.to_thread(
                    agent.refine, proposal, proposal_critiques
                )
                refined.append(new_proposal)
            else:
                refined.append(proposal)
        
        return refined
    
    # NOTE: _merge_programs is defined earlier in the class - uses DesignProgram, not SOLProgram
    
    def _package_feedback(self, validation, plan) -> FeedbackPackage:
        """Convert validation result to agent-consumable feedback."""
        blocking = [reason for _, reason in validation.rejected]
        
        # Map failed actions back to statements via semantic trace
        failed_statements = []
        if hasattr(plan, 'semantic_trace') and plan.semantic_trace:
            for i, (action, _) in enumerate(validation.rejected):
                stmt_idx = plan.semantic_trace.action_provenance.get(i)
                if stmt_idx is not None:
                    failed_statements.append(stmt_idx)
        
        return FeedbackPackage(
            passed=validation.all_approved,
            findings=[],
            blocking_issues=blocking,
            suggested_adjustments=[],
            failed_statements=failed_statements,
        )
```

### Task 3.3: Intent Decomposer
**File:** `magnet/agents/intent_decomposer.py`

```python
from typing import List
import uuid

from magnet.llm.providers.base import BaseProvider
from magnet.core.state_manager import StateManager

from .protocol import DesignProblem
from magnet.deployment.program_ast import ConstrainNode, PreferNode

DECOMPOSER_PROMPT = """
You decompose natural language design requests into structured problems.

Extract:
1. Hard constraints (must satisfy)
2. Soft preferences (nice to have)
3. Implied requirements

Return JSON:
{
  "constraints": [{"path": "...", "op": ">=", "value": X}],
  "preferences": [{"path": "...", "direction": "minimize|maximize"}],
  "implied": ["requirement1", ...]
}
"""

class IntentDecomposer:
    """Decomposes user intent into structured DesignProblem."""
    
    def __init__(self, llm_provider: BaseProvider):
        self._llm = llm_provider
    
    def decompose(
        self,
        user_intent: str,
        state: StateManager,
        design_id: str,
    ) -> DesignProblem:
        """Convert natural language to DesignProblem."""
        
        prompt = f"""
{DECOMPOSER_PROMPT}

User request: "{user_intent}"

Current design context:
- LOA: {state.get("hull.loa")}m
- Beam: {state.get("hull.beam")}m
- Phase: {state.get("design.phase")}
"""
        
        response = self._llm.complete_json(prompt, schema=DecomposeSchema)
        
        # Convert to AST nodes
        constraints = [
            ConstrainNode(path=c["path"], operator=c["op"], value=c["value"])
            for c in response.get("constraints", [])
        ]
        preferences = [
            PreferNode(path=p["path"], direction=p["direction"], weight=p.get("weight", 1.0))
            for p in response.get("preferences", [])
        ]
        
        return DesignProblem(
            problem_id=str(uuid.uuid4()),
            raw_intent=user_intent,
            constraints=constraints,
            preferences=preferences,
            design_id=design_id,
            design_version=state.design_version,
            state_snapshot=self._get_snapshot(state),
            existing_bodies=state.list_bodies() if hasattr(state, 'list_bodies') else [],
        )
    
    def _get_snapshot(self, state: StateManager) -> dict:
        """Get relevant state for problem context."""
        paths = [
            "hull.loa", "hull.beam", "hull.draft",
            "hull.displacement_mt", "stability.gm_m",
        ]
        return {p: state.get(p) for p in paths}
```

### Deliverables (Phase 3)
- [ ] `magnet/agents/conflict.py` — Conflict detection and resolution
- [ ] `magnet/agents/swarm.py` — Swarm orchestrator
- [ ] `magnet/agents/intent_decomposer.py` — User intent → DesignProblem
- [ ] Integration tests for swarm loop

---

## Phase 4: Integration & API (Days 16-20)

### Task 4.1: Wire Swarm into Conductor
**File:** `magnet/kernel/conductor.py` (modify)

```python
from magnet.agents.swarm import Swarm
from magnet.agents.intent_decomposer import IntentDecomposer

class Conductor:
    def __init__(
        self,
        state_manager: StateManager,
        validator: ActionValidator,
        executor: ActionExecutor,
        swarm: Optional[Swarm] = None,
        decomposer: Optional[IntentDecomposer] = None,
    ):
        self._state = state_manager
        self._validator = validator
        self._executor = executor
        self._swarm = swarm
        self._decomposer = decomposer
    
    async def process_user_intent(
        self,
        intent: str,
        design_id: str,
    ) -> Dict[str, Any]:
        """Process user intent through swarm or single-LLM path."""
        
        if self._swarm and self._decomposer:
            return await self._process_with_swarm(intent, design_id)
        else:
            return await self._process_single_llm(intent, design_id)
    
    async def _process_with_swarm(
        self,
        intent: str,
        design_id: str,
    ) -> Dict[str, Any]:
        """Multi-agent swarm processing."""
        
        # 1. Decompose intent
        problem = self._decomposer.decompose(intent, self._state, design_id)
        
        # 2. Run swarm
        result = await self._swarm.deliberate(problem, self._state)
        
        # 3. Generate digest
        digest = generate_digest(self._state, result.version_after)
        
        return {
            "success": result.success,
            "version": result.version_after,
            "digest": digest,
            "agent_reasoning": result.agent_reasoning,
            "conflicts_resolved": [asdict(c) for c in result.conflicts_resolved],
            "iterations": result.iterations,
            "explain_record_id": result.explain_record_id,
        }
```

### Task 4.2: Swarm API Endpoint
**File:** `magnet/deployment/api.py` (add endpoint)

```python
@app.post("/api/v1/designs/{design_id}/swarm")
async def execute_with_swarm(
    design_id: str,
    body: Dict[str, Any],
    conductor: Conductor = Depends(get_conductor),
):
    """
    Execute user intent through multi-agent swarm.
    
    The swarm:
    1. Decomposes intent into design problem
    2. Multiple agents propose in parallel
    3. Cross-critique and refine
    4. Resolve conflicts
    5. Compile to ActionPlan
    6. Validate and execute (or iterate)
    """
    intent = body.get("intent", "")
    
    try:
        result = await conductor.process_user_intent(intent, design_id)
        return result
    except ConvergenceError as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Swarm could not reach consensus. Try simplifying the request.",
        }
```

### Task 4.3: Agent Attribution in ExplainRecord
**File:** `magnet/control_plane/explain.py` (modify)

```python
@dataclass
class ExplainRecord:
    # ... existing fields ...
    
    # Agent attribution (NEW)
    proposing_agents: List[str] = field(default_factory=list)
    agent_reasoning: Dict[str, str] = field(default_factory=dict)
    swarm_iterations: int = 1
    conflicts_resolved: List[Dict[str, Any]] = field(default_factory=list)
    design_program: Optional[Dict[str, Any]] = None  # Original Design Language program
    semantic_trace: Optional[Dict[str, Any]] = None  # How program expanded to Actions
```

### Task 4.4: Bootstrap Swarm
**File:** `magnet/bootstrap/swarm.py`

```python
from magnet.agents.swarm import Swarm
from magnet.agents.intent_decomposer import IntentDecomposer
from magnet.agents.domains.hull_agent import HullFormAgent
from magnet.agents.domains.stability_agent import StabilityAgent
from magnet.agents.domains.resistance_agent import ResistanceAgent
from magnet.agents.domains.manufacturing_agent import ManufacturingAgent
from magnet.agents.domains.aesthetics_agent import AestheticsAgent

def create_swarm(
    llm_provider: BaseProvider,
    validator: ActionValidator,
    executor: ActionExecutor,
) -> Swarm:
    """Create the default agent swarm."""
    
    agents = [
        HullFormAgent(llm_provider),
        StabilityAgent(llm_provider),
        ResistanceAgent(llm_provider),
        ManufacturingAgent(llm_provider),
        AestheticsAgent(llm_provider),
    ]
    
    return Swarm(
        agents=agents,
        validator=validator,
        executor=executor,
        max_iterations=5,
    )

def create_decomposer(llm_provider: BaseProvider) -> IntentDecomposer:
    """Create the intent decomposer."""
    return IntentDecomposer(llm_provider)
```

### Deliverables (Phase 4)
- [ ] Modified `magnet/kernel/conductor.py` with swarm integration
- [ ] `/api/v1/designs/{design_id}/swarm` endpoint
- [ ] Modified `ExplainRecord` with agent attribution
- [ ] `magnet/bootstrap/swarm.py` — Swarm factory
- [ ] End-to-end integration tests

---

## File Manifest

### New Files (Create)
| File | Purpose |
|------|---------|
| `kernel/stdlib/type_registry.py` | Kernel-owned type schemas (geometry.* primitives) |
| `magnet/deployment/program_ast.py` | Design Language AST node definitions |
| `magnet/deployment/program_parser.py` | Text → AST parser |
| `kernel/semantic_expander.py` | AST → ActionPlan (calls kernel/stdlib) |
| `kernel/stdlib/geometry.py` | Geometry operations (LOFT, MIRROR, ALIGN) |
| `kernel/stdlib/resources.py` | Resource operations (CREATE, UPDATE, DELETE) |
| `magnet/agents/protocol.py` | Agent interface definitions |
| `magnet/agents/state_accessor.py` | Unified state access for agents |
| `magnet/agents/base.py` | Base agent outputting geometric primitives |
| `magnet/agents/conflict.py` | Conflict detection and resolution |
| `magnet/agents/swarm.py` | Swarm orchestrator |
| `magnet/agents/intent_decomposer.py` | User intent → DesignProblem |
| `magnet/agents/domains/hull_agent.py` | Hull geometry expertise |
| `magnet/agents/domains/stability_agent.py` | Stability constraints expertise |
| `magnet/agents/domains/resistance_agent.py` | Resistance optimization expertise |
| `magnet/agents/domains/manufacturing_agent.py` | Manufacturing constraints |
| `magnet/bootstrap/swarm.py` | Swarm factory |

### Modified Files
| File | Changes |
|------|---------|
| `magnet/deployment/api.py` | Add `/program` and `/swarm` endpoints |
| `magnet/kernel/conductor.py` | Integrate swarm processing |
| `magnet/control_plane/explain.py` | Add agent attribution fields |
| `magnet/kernel/intent_protocol.py` | Add `semantic_trace` to ActionPlan |
| `magnet/kernel/action_validator.py` | Validate geometry.* paths |

---

## Validation Checklist

After implementation, verify:

**Engineer Experience:**
- [ ] Engineer can express any hull form without "type not found" errors
- [ ] Feedback is quantified: "GM = 0.6m, need 0.8m" not just "failed"
- [ ] Suggested adjustments are provided: "Increase beam by ~15cm"
- [ ] Iteration time is < 1 second from intent to feedback
- [ ] Engineer decides when to stop (no auto-convergence required)

**Architecture:**
- [ ] Agents output ONLY geometry.* primitives (no hull.style.*, no named features)
- [ ] DesignProgram compiles to ActionPlan via SemanticExpander
- [ ] geometry.section → HullSection (canonical class, no second engine)
- [ ] geometry.surface → NURBSSurface (canonical class, no second engine)
- [ ] Novel geometry (not in any enum) is accepted if physically valid
- [ ] No `HullFamily` enum in kernel code
- [ ] No `hull_type ==` comparisons in kernel

**Agent Swarm:**
- [ ] Constraints are pre-checked via HSV
- [ ] Multiple agents can propose simultaneously
- [ ] Critiques identify issues and suggest modifications
- [ ] Conflicts are detected and resolved by priority
- [ ] ExplainRecord shows which agents contributed (transparency for engineer)
- [ ] Semantic trace shows which kernel/stdlib functions were called

---

## Success Criteria

**The One Sentence Test:**
> MAGNET ensures engineers can express **anything** (compositional primitives), get **instant physics feedback** (kernel validation with numbers), and never be constrained by **what someone enumerated** (no hull types) — while agents handle the tedious translation from intent to geometry.

**What Success Looks Like:**

| Metric | Target |
|:-------|:-------|
| Engineer can express any hull form | No "type not found" errors for novel geometry |
| Feedback is quantified | "GM = 0.6, need 0.8" not just "failed" |
| Iteration is fast | < 1 second from intent to feedback |
| No creativity blockers | No `HullFamily` enum, no `hull_type` classification |
| Engineer judges quality | System doesn't auto-reject "unusual" designs |

The implementation is complete when:

```
Engineer: "I want a fast catamaran, stable in rough seas, about 12 meters"
       │
       ▼
   IntentDecomposer
   → constraints: [CONSTRAIN stability.gm_m >= 2.0]
   → preferences: [PREFER resistance.total_kw minimize]
       │
       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          SWARM (geometric primitives)                        │
│                                                                              │
│  Hull Agent outputs:                                                         │
│    CREATE geometry.body port_hull { body_type: "hull", offset_y_m: -3.0 }   │
│    CREATE geometry.body stbd_hull { body_type: "hull", offset_y_m: 3.0 }    │
│    CREATE geometry.section bow { station: 0.0, half_beam_m: 0.5, ... }      │
│    CREATE geometry.section mid { station: 0.5, half_beam_m: 1.0, ... }      │
│    CREATE geometry.section stern { station: 1.0, half_beam_m: 0.8, ... }    │
│    LOFT [bow, mid, stern] INTO port_surface                                  │
│    MIRROR port_surface AS stbd_surface                                       │
│    SET hull.loa = 12                                                         │
│                                                                              │
│  Stability Agent outputs:                                                    │
│    CONSTRAIN stability.gm_m >= 2.0                                          │
│    UPDATE geometry.section mid { half_beam_m: 1.2 }  # Wider for GM         │
│                                                                              │
│  Resistance Agent outputs:                                                   │
│    UPDATE geometry.section bow { deadrise_deg: 25, fullness: 0.4 }          │
│    # Fine entry for less resistance                                          │
│                                                                              │
│  Conflict: Hull wants mid.half_beam_m=1.0, Stability wants 1.2              │
│  Resolution: Stability wins (safety priority) → half_beam_m = 1.2           │
│                                                                              │
│  Cross-critique: "Fine bow entry may reduce stability margin"               │
│  Refinement: Keep fine entry, compensate with wider stern                    │
└──────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
   Merged DesignProgram (geometric primitives ONLY — no "catamaran" style):
   ```
   CREATE geometry.body port_hull { body_type: "hull", offset_y_m: -3.0 }
   CREATE geometry.body stbd_hull { body_type: "hull", offset_y_m: 3.0 }
   CREATE geometry.section bow { station: 0.0, half_beam_m: 0.5, deadrise_deg: 25 }
   CREATE geometry.section mid { station: 0.5, half_beam_m: 1.2, deadrise_deg: 15 }
   CREATE geometry.section stern { station: 1.0, half_beam_m: 1.0, deadrise_deg: 20 }
   LOFT [bow, mid, stern] INTO port_surface
   MIRROR port_surface AS stbd_surface
   SET hull.loa = 12
   CONSTRAIN stability.gm_m >= 2.0
   ```
       │
       ▼
   Semantic Expander (kernel/stdlib):
   ├── geometry.section → HullSection (canonical class)
   ├── geometry.surface → NURBSSurface (canonical class)
   ├── geometry.body → entry in HullGeometry.bodies
   └── → ActionPlan
       │
       ▼
   Kernel validates → PASS
       │
       ▼
   Downstream pipeline (UNCHANGED):
   ├── HullGeometryPipeline.tessellate() → WebGL mesh
   ├── compute_hydrostatics() → GM, displacement
   └── STLExporter → files
       │
       ▼
   Result returned to ENGINEER with:
   - New design version
   - Quantified feedback: "GM = 2.3m, displacement = 8.5t, Rt@30kts = 45kN"
   - Agent reasoning (who proposed what, for transparency)
   - Conflicts resolved (with winning agent, for transparency)
   - Semantic trace (which kernel functions were called)
   
   ENGINEER reviews:
   - "GM is good, but resistance is high. Make the bow finer."
   - → Next iteration with new intent
   
   OR:
   - "That looks great. Export to IGES."
   - → DONE (engineer decides convergence)
```

### Acid Tests

**Test 1: Catamaran (no "catamaran" type)**
```
CREATE geometry.body port_hull { body_type: "hull", offset_y_m: -3.0 }
MIRROR port_hull AS stbd_hull
```
✓ Compiles to two bodies with offset
✓ No `HullType.CATAMARAN` enum anywhere

**Test 2: Stepped hull (no "step" type)**
```
CREATE geometry.discontinuity step_1 { surface_id: "main", station: 0.65, depth_m: 0.08 }
CREATE geometry.opening vent_inlet { surface_id: "main", center_u: 0.7, shape: "rectangle" }
CREATE geometry.flow_path ventilation { inlet_surface: "main", outlet_surface: "transom" }
```
✓ Compiles to surface modifications
✓ Kernel knows "discontinuity" and "flow_path", not "stepped hull"

**Test 3: Novel configuration (with freeform body types)**
```
# Physics-semantic body types + a completely novel type
CREATE geometry.body main_hull { 
    body_type: "primary_displacement",  # Freeform - not in any enum!
    physics_category: "surface_piercing",
    offset_y_m: 0 
}
CREATE geometry.body left_stabilizer { 
    body_type: "hydrofoil_strut",  # Novel type - would fail old enum validation
    physics_category: "submerged",
    offset_y_m: -4.0 
}
CREATE geometry.body right_stabilizer { 
    body_type: "hydrofoil_strut",  # Same novel type
    physics_category: "submerged",
    offset_y_m: 4.0 
}
```
✓ Trimaran-like configuration composed from primitives
✓ Uses **novel body_type** values that would fail design-semantic enums
✓ Kernel validates `physics_category`, not `body_type` string
✓ No code change required — just primitive composition

---

## Timeline Summary

| Phase | Days | Deliverables |
|-------|------|--------------|
| 1: Design Language Foundation | 1-5 | TypeRegistry, ProgramAST, Parser, SemanticExpander, kernel/stdlib/geometry |
| 2: Agent Protocol | 6-10 | Protocol, StateAccessor, BaseAgent outputting geometric primitives |
| 3: Swarm | 11-15 | Conflict resolution on geometry, Program merger, IntentDecomposer |
| 4: Integration | 16-20 | Conductor integration, /program endpoint, ExplainRecord updates |

**Total:** 20 working days (4 weeks)

---

## References

| Document | Purpose |
|:---------|:--------|
| `MAGNET_Design_Language_Spec_v1.0.md` | Complete language specification with primitives, invariants, and examples |
| `MAGNET_Failure_Modes_And_Mitigations.md` | Implementation plan prioritized for engineer-in-loop workflow |
| `MAGNET_Audit_Prompts.md` | **Completed audit** with file inventory, failure mode coverage, implementation plan |
| `MAGNET_Implementation_Spec.md` | **Unified spec:** Agent prompts, API contracts, test plan, migration |
| `MAGNET_Physics_Gaps_And_Solutions.md` | **CRITICAL:** Multi-body hydrostatics, resistance selection, novelty detection |
| `MAGNET_Implementation_Guide.md` | **START HERE:** Step-by-step implementation roadmap with code |
| `kernel/stdlib/type_registry.py` | Kernel-owned type schemas (geometry.* primitives) — **to be created** |
| `magnet/hull_gen/geometry.py` | Canonical geometry classes (HullSection, NURBSSurface) — **verified** |

---

## Codebase Audit Summary

The following key findings from `MAGNET_Audit_Prompts.md` v1.0 inform this implementation plan:

### High-Confidence Reuse Components

| Component | Location | Why Reuse |
|:----------|:---------|:----------|
| Canonical geometry | `hull_gen/geometry.py` | HullSection, Point3D, HullGeometry — do not duplicate |
| NURBS implementation | `hull_gen/nurbs.py` | Full NURBS with `gaussian_curvature()` for developability |
| Resistance physics | `physics/resistance.py` | Already has `method_valid`, `validity_note` |
| Sensitivity analysis | `optimization/sensitivity.py` | Computes ∂objective/∂variable (gradients exist!) |
| Stability physics | `stability/intact_gm.py` | Pure physics, clean interface |

### Components to Delete

| Component | Location | Reason |
|:----------|:---------|:-------|
| Hull family priors | `kernel/priors/hull_families.py` | `HullFamily` enum violates "no enumerated designs" |

### Components to Modify

| Component | Location | Required Change |
|:----------|:---------|:----------------|
| Hull generator | `hull_gen/generator.py` | Support primitive composition instead of `HullType` dispatch |
| Parameter bounds | `core/parameter_bounds.py` | Expand from 5 to 30+ parameters |
| API | `deployment/api.py` | Add `/program` endpoint for design language |

---

## Version History

| Version | Date | Changes |
|:--------|:-----|:--------|
| 1.0 | 2026-01-05 | Initial implementation plan |
| 2.0 | 2026-01-05 | **ENGINEER CREATIVITY AMPLIFIER**: Reframed from autonomous design to engineer-in-loop creativity amplifier. Added "What MAGNET Is" section showing engineer at both ends of loop. Added "Core Equation" (creativity × feedback × no limits). Added quantified feedback requirements. Updated validation checklist for engineer experience. Aligned with Design Language Spec v4.0 and Failure Modes v4.0. |
| 2.1 | 2026-01-05 | Added reference to `MAGNET_Audit_Prompts.md` in References. |
| 2.2 | 2026-01-05 | Integrated completed codebase audit findings. Added verified file locations and reuse matrix. |

---

## Non-Negotiable Invariants

| Invariant | Meaning |
|:----------|:--------|
| **Engineer is in the loop** | Engineers express intent, judge quality, decide when to stop |
| **Quantified feedback** | Engineers get numbers ("GM = 0.6, need 0.8"), not just pass/fail |
| **Kernel knows geometry, not design** | No "catamaran", "stepped hull", "aggressive" types in kernel |
| **No second geometry engine** | Language compiles INTO existing HullSection, NURBSSurface |
| **Agents output primitives** | Agents write CREATE/LOFT/MIRROR, not STYLE = "..." |
| **One canonical storage path** | `hull.features.<type>[id]` for all resources |
| **Deterministic expansion** | Same program + state → same ActionPlan always |
| **Kernel owns all semantics** | kernel/stdlib implements all operations |
