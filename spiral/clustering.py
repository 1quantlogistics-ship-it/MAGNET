"""
MAGNET Phase Clustering
=======================

Phase clustering for design spiral iteration.
Groups related phases that iterate together.

Per Operations Guide:
- Cluster A (CONCEPT): Mission <-> Hull Form
- Cluster B (SYSTEMS): Propulsion <-> Structure <-> Arrangement
- Cluster C (VALIDATION): Weight/Stability <-> Compliance <-> Production

Within a cluster, phases may iterate together when changes
in one phase impact others.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from enum import Enum

from memory.schemas import DesignPhase


class PhaseCluster(str, Enum):
    """Design spiral phase clusters."""
    CONCEPT = "concept"      # Cluster A: Mission, Hull Form
    SYSTEMS = "systems"      # Cluster B: Propulsion, Structure, Arrangement
    VALIDATION = "validation"  # Cluster C: Weight/Stability, Compliance, Production


# Cluster definitions
CLUSTER_A = PhaseCluster.CONCEPT
CLUSTER_B = PhaseCluster.SYSTEMS
CLUSTER_C = PhaseCluster.VALIDATION


# Phase to cluster mapping
PHASE_CLUSTERS: Dict[DesignPhase, PhaseCluster] = {
    DesignPhase.MISSION: PhaseCluster.CONCEPT,
    DesignPhase.HULL_FORM: PhaseCluster.CONCEPT,
    DesignPhase.PROPULSION: PhaseCluster.SYSTEMS,
    DesignPhase.STRUCTURE: PhaseCluster.SYSTEMS,
    DesignPhase.ARRANGEMENT: PhaseCluster.SYSTEMS,
    DesignPhase.WEIGHT_STABILITY: PhaseCluster.VALIDATION,
    DesignPhase.COMPLIANCE: PhaseCluster.VALIDATION,
    DesignPhase.PRODUCTION: PhaseCluster.VALIDATION,
}


# Cluster phase lists
CLUSTER_PHASES: Dict[PhaseCluster, List[DesignPhase]] = {
    PhaseCluster.CONCEPT: [
        DesignPhase.MISSION,
        DesignPhase.HULL_FORM,
    ],
    PhaseCluster.SYSTEMS: [
        DesignPhase.PROPULSION,
        DesignPhase.STRUCTURE,
        DesignPhase.ARRANGEMENT,
    ],
    PhaseCluster.VALIDATION: [
        DesignPhase.WEIGHT_STABILITY,
        DesignPhase.COMPLIANCE,
        DesignPhase.PRODUCTION,
    ],
}


# Dependencies that trigger cluster iteration
CLUSTER_DEPENDENCIES: Dict[PhaseCluster, Dict[str, List[str]]] = {
    PhaseCluster.CONCEPT: {
        # Hull form depends on mission
        "hull_params": ["mission"],
        # Stability depends on hull
        "stability_results": ["hull_params"],
    },
    PhaseCluster.SYSTEMS: {
        # Propulsion depends on hull and resistance
        "propulsion_config": ["hull_params", "resistance_results"],
        # Structure depends on hull and loads
        "structural_design": ["hull_params", "propulsion_config"],
        # Arrangement depends on all systems
        "general_arrangement": ["hull_params", "propulsion_config", "structural_design"],
    },
    PhaseCluster.VALIDATION: {
        # Weight depends on structure and propulsion
        "weight_estimate": ["structural_design", "propulsion_config"],
        # Final stability depends on weight
        "stability_results": ["weight_estimate"],
        # Compliance depends on everything
        "reviews": ["stability_results", "structural_design"],
    },
}


@dataclass
class ClusterIterationTrigger:
    """
    Tracks what triggered cluster iteration.

    Attributes:
        cluster: The cluster that needs iteration
        trigger_file: File that changed
        affected_files: Files that need recalculation
        reason: Human-readable explanation
    """
    cluster: PhaseCluster
    trigger_file: str
    affected_files: List[str]
    reason: str


def get_cluster_for_phase(phase: DesignPhase) -> PhaseCluster:
    """
    Get the cluster a phase belongs to.

    Args:
        phase: Design phase

    Returns:
        PhaseCluster the phase belongs to
    """
    return PHASE_CLUSTERS.get(phase, PhaseCluster.CONCEPT)


def get_phases_in_cluster(cluster: PhaseCluster) -> List[DesignPhase]:
    """
    Get all phases in a cluster.

    Args:
        cluster: Phase cluster

    Returns:
        List of phases in the cluster
    """
    return CLUSTER_PHASES.get(cluster, []).copy()


def should_iterate_cluster(
    cluster: PhaseCluster,
    changed_file: str,
) -> Optional[ClusterIterationTrigger]:
    """
    Check if a file change should trigger cluster iteration.

    Args:
        cluster: Current cluster
        changed_file: File that was changed

    Returns:
        ClusterIterationTrigger if iteration needed, None otherwise
    """
    dependencies = CLUSTER_DEPENDENCIES.get(cluster, {})

    affected_files = []
    for output_file, deps in dependencies.items():
        if changed_file in deps:
            affected_files.append(output_file)

    if affected_files:
        return ClusterIterationTrigger(
            cluster=cluster,
            trigger_file=changed_file,
            affected_files=affected_files,
            reason=f"Change to {changed_file} requires recalculation of {affected_files}",
        )

    return None


def get_cluster_iteration_phases(
    cluster: PhaseCluster,
    changed_file: str,
) -> List[DesignPhase]:
    """
    Get phases that need to iterate based on a file change.

    Args:
        cluster: Current cluster
        changed_file: File that was changed

    Returns:
        List of phases that need iteration
    """
    trigger = should_iterate_cluster(cluster, changed_file)
    if not trigger:
        return []

    # Map affected files to phases
    phases_to_iterate: Set[DesignPhase] = set()
    cluster_phases = get_phases_in_cluster(cluster)

    # Find which phases produce the affected files
    # This is a simplified mapping - in production, would use
    # the full output mapping from PHASE_GATES
    file_to_phase: Dict[str, DesignPhase] = {
        "mission": DesignPhase.MISSION,
        "hull_params": DesignPhase.HULL_FORM,
        "stability_results": DesignPhase.HULL_FORM,  # Also WEIGHT_STABILITY
        "resistance_results": DesignPhase.HULL_FORM,
        "propulsion_config": DesignPhase.PROPULSION,
        "structural_design": DesignPhase.STRUCTURE,
        "general_arrangement": DesignPhase.ARRANGEMENT,
        "weight_estimate": DesignPhase.WEIGHT_STABILITY,
        "reviews": DesignPhase.COMPLIANCE,
    }

    for affected_file in trigger.affected_files:
        if affected_file in file_to_phase:
            phase = file_to_phase[affected_file]
            if phase in cluster_phases:
                phases_to_iterate.add(phase)

    # Return phases in order
    return [p for p in cluster_phases if p in phases_to_iterate]


def get_cluster_entry_phase(cluster: PhaseCluster) -> DesignPhase:
    """
    Get the entry (first) phase of a cluster.

    Args:
        cluster: Phase cluster

    Returns:
        First phase in the cluster
    """
    phases = get_phases_in_cluster(cluster)
    return phases[0] if phases else DesignPhase.MISSION


def get_cluster_exit_phase(cluster: PhaseCluster) -> DesignPhase:
    """
    Get the exit (last) phase of a cluster.

    Args:
        cluster: Phase cluster

    Returns:
        Last phase in the cluster
    """
    phases = get_phases_in_cluster(cluster)
    return phases[-1] if phases else DesignPhase.MISSION


def get_next_cluster(cluster: PhaseCluster) -> Optional[PhaseCluster]:
    """
    Get the next cluster in sequence.

    Args:
        cluster: Current cluster

    Returns:
        Next cluster, or None if at final cluster
    """
    clusters = [PhaseCluster.CONCEPT, PhaseCluster.SYSTEMS, PhaseCluster.VALIDATION]
    try:
        idx = clusters.index(cluster)
        if idx < len(clusters) - 1:
            return clusters[idx + 1]
        return None
    except ValueError:
        return None


def check_cluster_complete(
    cluster: PhaseCluster,
    memory_path: str,
) -> tuple[bool, List[str]]:
    """
    Check if all phases in a cluster are complete.

    Args:
        cluster: Cluster to check
        memory_path: Path to memory directory

    Returns:
        Tuple of (complete, missing_outputs)
    """
    from pathlib import Path
    from .phases import PHASE_GATES

    memory_dir = Path(memory_path)
    missing = []

    for phase in get_phases_in_cluster(cluster):
        gate = PHASE_GATES.get(phase)
        if gate:
            for output in gate.required_outputs:
                file_path = memory_dir / f"{output}.json"
                if not file_path.exists():
                    missing.append(output)

    return len(missing) == 0, missing


def get_cluster_iteration_count(
    cluster: PhaseCluster,
    memory_path: str,
) -> int:
    """
    Get number of times a cluster has iterated.

    Currently reads from system state, but could be
    enhanced to track per-cluster iteration history.

    Args:
        cluster: Cluster to check
        memory_path: Path to memory directory

    Returns:
        Iteration count (0 if not started)
    """
    from memory.file_io import MemoryFileIO

    try:
        memory = MemoryFileIO(memory_path)
        state = memory.get_system_state()
        # For now, return phase iteration as proxy
        # Could be enhanced to track cluster-specific iterations
        return state.phase_iteration
    except Exception:
        return 0
