"""
interior/integration - Interior state integration package.
BRAVO OWNS THIS FILE.

Module 59: Interior Layout
Provides integration with core state management and other modules.
"""

from magnet.interior.integration.state_integration import (
    InteriorStateIntegrator,
    InteriorStateError,
)

__all__ = [
    'InteriorStateIntegrator',
    'InteriorStateError',
]
