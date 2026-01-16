"""
AST nodes for MAGNET design language.

The kernel knows geometry, not design.
Any hull form that requires a new language primitive is a failure of the language.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Statement:
    """Base class for all statements."""
    line_number: int = 0


@dataclass
class CreateStatement(Statement):
    """CREATE geometry.section name { ... }"""
    resource_type: str = ""     # "geometry.section"
    resource_id: str = ""       # "bow"
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UpdateStatement(Statement):
    """UPDATE resource_id { ... }"""
    resource_id: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeleteStatement(Statement):
    """DELETE resource_id"""
    resource_id: str = ""


@dataclass
class SetStatement(Statement):
    """SET path = value"""
    path: str = ""
    value: Any = None


@dataclass
class LoftStatement(Statement):
    """LOFT surface_id FROM [section1, section2, ...]"""
    surface_id: str = ""
    section_ids: List[str] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MirrorStatement(Statement):
    """MIRROR resource_id AS new_id"""
    source_id: str = ""
    target_id: str = ""


@dataclass
class AlignStatement(Statement):
    """ALIGN resource_id TO target AXIS axis"""
    resource_id: str = ""
    target_id: str = ""
    axis: str = ""  # "x", "y", "z"


@dataclass
class ConstrainStatement(Statement):
    """CONSTRAIN path operator value"""
    path: str = ""          # "hull.gm"
    operator: str = ""      # ">=", "<=", "=="
    value: float = 0.0
    priority: str = "hard"  # "hard" or "soft"


@dataclass
class DeriveStatement(Statement):
    """DERIVE target FROM policy(inputs)"""
    target_path: str = ""
    policy_name: str = ""
    inputs: Dict[str, str] = field(default_factory=dict)


@dataclass
class AskStatement(Statement):
    """ASK \"question\" { options: [...] }"""
    question: str = ""
    options: List[str] = field(default_factory=list)


@dataclass
class Program:
    """Complete design program."""
    statements: List[Statement] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

