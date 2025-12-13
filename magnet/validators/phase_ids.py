"""
Canonical Phase IDs - Single source of truth for phase names.

BRAVO OWNS THIS FILE.

ALL phase references MUST use these constants to prevent mismatches
between validators, contracts, and phase registry.
"""
from enum import Enum


class PhaseId(str, Enum):
    """
    Canonical phase identifiers.

    Use these constants instead of string literals to prevent
    phase name mismatches (e.g., "hull_form" vs "hull").
    """
    MISSION = "mission"
    HULL = "hull"  # NOT "hull_form" - canonical name
    STRUCTURE = "structure"
    PROPULSION = "propulsion"
    WEIGHT = "weight"
    STABILITY = "stability"
    LOADING = "loading"
    ARRANGEMENT = "arrangement"
    COMPLIANCE = "compliance"
    PRODUCTION = "production"
    COST = "cost"
    OPTIMIZATION = "optimization"
    REPORTING = "reporting"

    def __str__(self) -> str:
        return self.value
