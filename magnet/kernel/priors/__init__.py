"""
MAGNET Hull Priors

Hull family priors for synthesis.

Phase 3 (Enum Deletion):
- Legacy family priors are removed. Use geometry-derived defaults only.
"""

# New geometry-derived defaults (PREFERRED - use these)
from .geometry_defaults import (
    get_defaults_from_froude,
    get_defaults_from_dimensions,
    estimate_lightship_kg,
    get_displacement_bounds,
)


__all__ = [
    # Geometry-derived defaults (use these)
    "get_defaults_from_froude",
    "get_defaults_from_dimensions",
    "estimate_lightship_kg",
    "get_displacement_bounds",
]
