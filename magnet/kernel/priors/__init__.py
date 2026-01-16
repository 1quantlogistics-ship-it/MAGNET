"""
MAGNET Hull Priors

Hull family priors for synthesis.

TASK-002: HullFamily is DEPRECATED
- New code MUST use geometry_defaults instead
- HullFamily imports are lazy-loaded and emit deprecation warnings
- Legacy support remains ONLY for backward compatibility during migration
"""

import warnings

# New geometry-derived defaults (PREFERRED - use these)
from .geometry_defaults import (
    get_defaults_from_froude,
    get_defaults_from_dimensions,
    estimate_lightship_kg,
    get_displacement_bounds,
    migrate_from_family,
)


# =============================================================================
# DEPRECATED EXPORTS (Lazy-loaded with warnings)
# =============================================================================

_legacy_imported = False
_HullFamily = None
_FAMILY_PRIORS = None
_get_family_prior = None


def _import_legacy():
    """Lazy import of deprecated hull_families module."""
    global _legacy_imported, _HullFamily, _FAMILY_PRIORS, _get_family_prior
    if not _legacy_imported:
        from .hull_families import HullFamily, FAMILY_PRIORS, get_family_prior
        _HullFamily = HullFamily
        _FAMILY_PRIORS = FAMILY_PRIORS
        _get_family_prior = get_family_prior
        _legacy_imported = True


def __getattr__(name):
    """Lazy attribute access for deprecated exports."""
    if name == "HullFamily":
        warnings.warn(
            "HullFamily is deprecated. Use get_defaults_from_froude() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        _import_legacy()
        return _HullFamily
    elif name == "FAMILY_PRIORS":
        warnings.warn(
            "FAMILY_PRIORS is deprecated. Use get_defaults_from_froude() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        _import_legacy()
        return _FAMILY_PRIORS
    elif name == "get_family_prior":
        warnings.warn(
            "get_family_prior is deprecated. Use get_defaults_from_froude() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        _import_legacy()
        return _get_family_prior
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # PREFERRED (use these)
    "get_defaults_from_froude",
    "get_defaults_from_dimensions",
    "estimate_lightship_kg",
    "get_displacement_bounds",
    "migrate_from_family",
    # DEPRECATED (lazy-loaded with warnings)
    "HullFamily",
    "FAMILY_PRIORS", 
    "get_family_prior",
]
