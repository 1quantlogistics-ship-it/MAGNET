"""
MAGNET Spiral Module
====================

Design spiral phases, gates, and clustering logic.
Manages phase progression and iteration control.
"""

from .phases import (
    PhaseGate,
    PhaseGateResult,
    check_phase_gate,
    can_advance_to_phase,
    get_required_outputs,
    get_phase_requirements,
)

from .clustering import (
    PhaseCluster,
    CLUSTER_A,
    CLUSTER_B,
    CLUSTER_C,
    get_cluster_for_phase,
    get_phases_in_cluster,
    should_iterate_cluster,
    get_cluster_iteration_phases,
)

__all__ = [
    # Phase gates
    "PhaseGate",
    "PhaseGateResult",
    "check_phase_gate",
    "can_advance_to_phase",
    "get_required_outputs",
    "get_phase_requirements",
    # Clustering
    "PhaseCluster",
    "CLUSTER_A",
    "CLUSTER_B",
    "CLUSTER_C",
    "get_cluster_for_phase",
    "get_phases_in_cluster",
    "should_iterate_cluster",
    "get_cluster_iteration_phases",
]
