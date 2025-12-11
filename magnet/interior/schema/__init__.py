"""
interior/schema - Interior layout schema package.
BRAVO OWNS THIS FILE.

Module 59: Interior Layout
Provides data models for spaces, layouts, and validation.
"""

from magnet.interior.schema.space import (
    SpaceType,
    SpaceCategory,
    SpaceDefinition,
    SpaceBoundary,
    SpaceConnection,
    DEFAULT_SPACE_CAPACITIES,
)
from magnet.interior.schema.layout import (
    InteriorLayout,
    LayoutVersion,
    DeckLayout,
    LayoutMetadata,
)
from magnet.interior.schema.validation import (
    ValidationSeverity,
    ValidationIssue,
    ValidationResult,
    LayoutConstraint,
    SpaceConstraint,
    MARITIME_CONSTRAINTS,
)

__all__ = [
    # Space types and definitions
    'SpaceType',
    'SpaceCategory',
    'SpaceDefinition',
    'SpaceBoundary',
    'SpaceConnection',
    'DEFAULT_SPACE_CAPACITIES',
    # Layout
    'InteriorLayout',
    'LayoutVersion',
    'DeckLayout',
    'LayoutMetadata',
    # Validation
    'ValidationSeverity',
    'ValidationIssue',
    'ValidationResult',
    'LayoutConstraint',
    'SpaceConstraint',
    'MARITIME_CONSTRAINTS',
]
