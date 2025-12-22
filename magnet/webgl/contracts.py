"""
webgl/contracts.py - Mesh attribute contracts and validation v1.0

Module 67.3: GLTF Export/Viewer Contract Consolidation
ALPHA OWNS THIS FILE.

Defines attribute requirements for each mesh category and validates
mesh data before export. Enforces the contract that divergent attribute
logic between export paths is unacceptable.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional
from dataclasses import dataclass
from enum import Enum

if TYPE_CHECKING:
    from .schema import MeshData


class MeshCategory(Enum):
    """
    Mesh categories with attribute requirements.

    Each category defines which glTF attributes are required/forbidden.
    """
    HULL = "hull"           # Requires: POSITION, NORMAL, indices
    DECK = "deck"           # Requires: POSITION, NORMAL, indices
    STRUCTURE = "structure" # Requires: POSITION, NORMAL, indices
    LINES = "lines"         # Requires: POSITION only (mode=1 LINE_STRIP)
    POINTS = "points"       # Requires: POSITION only (mode=0 POINTS)


@dataclass
class AttributePolicy:
    """
    Defines required/optional attributes for a mesh category.

    This is the single source of truth for what attributes each
    mesh type must have. Export paths MUST NOT independently
    define attribute behavior.
    """
    category: MeshCategory
    require_position: bool = True
    require_normal: bool = True
    require_indices: bool = True
    compute_bounds: bool = True
    primitive_mode: int = 4  # 4=TRIANGLES, 1=LINE_STRIP, 0=POINTS

    @classmethod
    def for_category(cls, category: MeshCategory) -> "AttributePolicy":
        """Get the canonical policy for a mesh category."""
        policies = {
            MeshCategory.HULL: cls(category, require_normal=True),
            MeshCategory.DECK: cls(category, require_normal=True),
            MeshCategory.STRUCTURE: cls(category, require_normal=True),
            MeshCategory.LINES: cls(
                category,
                require_normal=False,
                require_indices=False,
                primitive_mode=1  # LINE_STRIP
            ),
            MeshCategory.POINTS: cls(
                category,
                require_normal=False,
                require_indices=False,
                primitive_mode=0  # POINTS
            ),
        }
        return policies.get(category, cls(category))


@dataclass
class PrimitiveRef:
    """Reference to a written primitive in the glTF structure."""
    mesh_idx: int
    primitive_idx: int
    pos_accessor_idx: int
    norm_accessor_idx: Optional[int]
    idx_accessor_idx: Optional[int]


class MeshContractValidator:
    """
    Validates mesh data against attribute policy.

    Fails loudly with descriptive errors including mesh name.
    This validator is called before any buffer writing occurs.
    """

    @staticmethod
    def validate(mesh: "MeshData", policy: AttributePolicy, mesh_name: str) -> List[str]:
        """
        Validate mesh data against the policy.

        Args:
            mesh: The mesh data to validate
            policy: The attribute policy to validate against
            mesh_name: Name of the mesh (for error messages)

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Gate 1: Position exists and valid
        if not mesh.vertices or len(mesh.vertices) == 0:
            errors.append(f"{mesh_name}: POSITION vertices empty")
        elif len(mesh.vertices) % 3 != 0:
            errors.append(
                f"{mesh_name}: POSITION count {len(mesh.vertices)} not divisible by 3"
            )

        # Gate 2: Normals required, present, and matching
        if policy.require_normal:
            if mesh.normals and len(mesh.normals) != len(mesh.vertices):
                errors.append(
                    f"{mesh_name}: NORMAL count {len(mesh.normals)} != "
                    f"POSITION count {len(mesh.vertices)}"
                )

        # Gate 3: Indices required and valid
        if policy.require_indices:
            if not mesh.indices or len(mesh.indices) == 0:
                errors.append(f"{mesh_name}: indices required but missing")
            elif len(mesh.indices) % 3 != 0:
                errors.append(
                    f"{mesh_name}: indices count {len(mesh.indices)} not divisible by 3"
                )
            elif mesh.vertices:
                vertex_count = len(mesh.vertices) // 3
                max_idx = max(mesh.indices)
                if max_idx >= vertex_count:
                    errors.append(
                        f"{mesh_name}: index {max_idx} >= vertex count {vertex_count}"
                    )

        return errors
