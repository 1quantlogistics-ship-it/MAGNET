"""
interior - Interior layout and hull integration package.
BRAVO OWNS THIS FILE.

Module 59: Interior Layout

Provides:
- Space definitions and types
- Interior layout management
- Layout generation from hull geometry
- Layout validation against maritime constraints
- REST API endpoints for layout operations
- State management integration
"""

# Hull integration (existing)
from magnet.interior.hull_integration import (
    SectionSampler,
    SamplingConfig,
    SampledSection,
    HullFormType,
)

# Schema - Space definitions
from magnet.interior.schema.space import (
    SpaceType,
    SpaceCategory,
    SpaceDefinition,
    SpaceBoundary,
    SpaceConnection,
    DEFAULT_SPACE_CAPACITIES,
)

# Schema - Layout definitions
from magnet.interior.schema.layout import (
    InteriorLayout,
    LayoutVersion,
    DeckLayout,
    LayoutMetadata,
)

# Schema - Validation
from magnet.interior.schema.validation import (
    ValidationSeverity,
    ValidationIssue,
    ValidationResult,
    LayoutConstraint,
    SpaceConstraint,
    MARITIME_CONSTRAINTS,
    validate_space_constraints,
    validate_adjacency,
)

# Generator
from magnet.interior.generator.layout_generator import (
    LayoutGenerator,
    GenerationConfig,
    GenerationResult,
    DeckConfig,
    generate_basic_layout,
)

# Integration
from magnet.interior.integration.state_integration import (
    InteriorStateIntegrator,
    InteriorStateError,
)

# API (conditional import)
try:
    from magnet.interior.api_endpoints import (
        create_interior_router,
        GenerateRequest,
        GenerateResponse,
        LayoutResponse,
        SpaceRequest,
        SpaceResponse,
        ValidationResponse,
        OptimizeRequest,
        OptimizeResponse,
    )
    _HAS_API = True
except ImportError:
    _HAS_API = False
    create_interior_router = None

__all__ = [
    # Hull integration
    'SectionSampler',
    'SamplingConfig',
    'SampledSection',
    'HullFormType',
    # Space definitions
    'SpaceType',
    'SpaceCategory',
    'SpaceDefinition',
    'SpaceBoundary',
    'SpaceConnection',
    'DEFAULT_SPACE_CAPACITIES',
    # Layout definitions
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
    'validate_space_constraints',
    'validate_adjacency',
    # Generator
    'LayoutGenerator',
    'GenerationConfig',
    'GenerationResult',
    'DeckConfig',
    'generate_basic_layout',
    # Integration
    'InteriorStateIntegrator',
    'InteriorStateError',
    # API
    'create_interior_router',
]
