"""
MAGNET Loading Module (Module 09)

Provides loading condition calculations for vessels.
Includes deadweight computation, trim/heel analysis, and stability checks.

Version 1.1 - Production-Ready with critical fixes.
"""

from .models import (
    # Enumerations
    LoadingConditionType,

    # Data classes
    TankLoad,
    DeadweightItem,
    LoadingConditionResult,
)

from .calculator import (
    LoadingCalculator,
)

from .validators import (
    LoadingComputerValidator,
)

__all__ = [
    # Enumerations
    "LoadingConditionType",

    # Data classes
    "TankLoad",
    "DeadweightItem",
    "LoadingConditionResult",

    # Calculator
    "LoadingCalculator",

    # Validators
    "LoadingComputerValidator",
]
