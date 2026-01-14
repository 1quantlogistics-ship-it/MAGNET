"""
MAGNET Hull Priors

Hull family priors for synthesis.

MIGRATION NOTE (TASK-003):
- HullFamily is DEPRECATED - use geometry_defaults instead
- New code should use get_defaults_from_froude() or get_defaults_from_dimensions()
- Legacy HullFamily support remains for backward compatibility
"""

# Legacy exports (DEPRECATED - will be removed in Phase 2)
from .hull_families import HullFamily, FAMILY_PRIORS, get_family_prior

# New geometry-derived defaults (PREFERRED)
from .geometry_defaults import (
    get_defaults_from_froude,
    get_defaults_from_dimensions,
    estimate_lightship_kg,
    get_displacement_bounds,
    migrate_from_family,
)

__all__ = [
    # Legacy (deprecated)
    "HullFamily",
    "FAMILY_PRIORS", 
    "get_family_prior",
    # New (preferred)
    "get_defaults_from_froude",
    "get_defaults_from_dimensions",
    "estimate_lightship_kg",
    "get_displacement_bounds",
    "migrate_from_family",
]
