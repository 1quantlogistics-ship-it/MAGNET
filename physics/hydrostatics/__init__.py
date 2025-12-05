"""
MAGNET V1 Hydrostatics Submodule (ALPHA)

Hydrostatic calculations: displacement, buoyancy, stability.
"""

from .displacement import (
    calculate_displacement,
    calculate_wetted_surface,
    SEAWATER_DENSITY,
)

__all__ = [
    'calculate_displacement',
    'calculate_wetted_surface',
    'SEAWATER_DENSITY',
]
