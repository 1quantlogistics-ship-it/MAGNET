"""
MAGNET Design Language Standard Library.

The kernel knows geometry, not design.
Any hull form that requires a new language primitive is a failure of the language.

Core components:
- parser: Program text → AST
- ast_nodes: AST node definitions
- expander: AST → Actions
- type_registry: Resource type schemas
- policies: DERIVE policy implementations
- compiler: Resources → HullGeometry
- section_compiler: geometry.section → HullSection
"""

from .parser import parse, ParseError
from .ast_nodes import (
    Program,
    Statement,
    CreateStatement,
    UpdateStatement,
    DeleteStatement,
    SetStatement,
    LoftStatement,
    MirrorStatement,
    AlignStatement,
    ConstrainStatement,
    DeriveStatement,
)
from .expander import expand, ExpansionError, ExpansionResult, Action, Constraint
from .type_registry import (
    TYPE_REGISTRY,
    TypeSchema,
    FieldSchema,
    get_schema,
    validate_resource,
    get_all_geometry_types,
)
from .compiler import compile_to_geometry, CompilationError


__all__ = [
    # Parser
    "parse",
    "ParseError",
    # AST
    "Program",
    "Statement",
    "CreateStatement",
    "UpdateStatement", 
    "DeleteStatement",
    "SetStatement",
    "LoftStatement",
    "MirrorStatement",
    "AlignStatement",
    "ConstrainStatement",
    "DeriveStatement",
    # Expander
    "expand",
    "ExpansionError",
    "ExpansionResult",
    "Action",
    "Constraint",
    # Type Registry
    "TYPE_REGISTRY",
    "TypeSchema",
    "FieldSchema",
    "get_schema",
    "validate_resource",
    "get_all_geometry_types",
    # Compiler
    "compile_to_geometry",
    "CompilationError",
]


