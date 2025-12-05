"""
MAGNET V1 Constraints Module (ALPHA)

Physics-informed design constraints to prevent absurd designs.
"""

from .hull_form import HullFormConstraints, ConstraintResult

__all__ = [
    'HullFormConstraints',
    'ConstraintResult',
]
