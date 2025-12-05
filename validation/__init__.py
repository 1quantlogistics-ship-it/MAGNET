"""
MAGNET V1 Validation Module (ALPHA)

Design validation and semantic checking.
"""

from .semantic import (
    SemanticValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    validate_design,
)

from .bounds import (
    BoundsValidator,
    BoundsCheckResult,
    check_bounds,
    MISSION_BOUNDS,
    HULL_BOUNDS,
    STABILITY_BOUNDS,
)

__all__ = [
    # Semantic validation
    'SemanticValidator',
    'ValidationResult',
    'ValidationIssue',
    'ValidationSeverity',
    'validate_design',
    # Bounds validation
    'BoundsValidator',
    'BoundsCheckResult',
    'check_bounds',
    'MISSION_BOUNDS',
    'HULL_BOUNDS',
    'STABILITY_BOUNDS',
]
