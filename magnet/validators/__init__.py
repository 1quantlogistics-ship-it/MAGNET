"""
MAGNET Validation Pipeline

Module 04 v1.1 - Production-Ready

Provides:
- ValidatorTaxonomy: Categories, types, and definitions
- ValidatorTopology: DAG of validator dependencies
- PipelineExecutor: Parallel execution with caching
- ResultAggregator: Gate condition checking
"""

from .taxonomy import (
    ValidatorCategory,
    ValidatorPriority,
    ValidatorState,
    ResultSeverity,
    ResourceRequirements,
    ResourcePool,
    ValidatorDefinition,
    ValidationFinding,
    ValidationResult,
    ValidatorInterface,
)
from .topology import (
    ValidatorTopology,
    TopologyNode,
    ExecutionGroup,
    TopologyError,
    CyclicDependencyError,
)
from .executor import (
    PipelineExecutor,
    ExecutionState,
    ValidationCache,
)
from .aggregator import (
    ResultAggregator,
    GateStatus,
)
from .builtin import (
    get_all_validators,
    get_validators_for_phase,
    get_gate_validators_for_phase,
    get_validator_by_id,
    PHYSICS_VALIDATORS,
    BOUNDS_VALIDATORS,
    STABILITY_VALIDATORS,
    CLASS_VALIDATORS,
    PRODUCTION_VALIDATORS,
)
from .registry import (
    ValidatorRegistry,
)
from .contracts import (
    PhaseContract,
    PhaseOutputContract,  # Backwards compatibility alias
    ContractResult,
    PHASE_CONTRACTS,
    check_phase_contract,
    check_phase_inputs,
    check_phase_outputs,
)

__all__ = [
    # Taxonomy
    "ValidatorCategory",
    "ValidatorPriority",
    "ValidatorState",
    "ResultSeverity",
    "ResourceRequirements",
    "ResourcePool",
    "ValidatorDefinition",
    "ValidationFinding",
    "ValidationResult",
    "ValidatorInterface",
    # Topology
    "ValidatorTopology",
    "TopologyNode",
    "ExecutionGroup",
    "TopologyError",
    "CyclicDependencyError",
    # Executor
    "PipelineExecutor",
    "ExecutionState",
    "ValidationCache",
    # Aggregator
    "ResultAggregator",
    "GateStatus",
    # Builtin
    "get_all_validators",
    "get_validators_for_phase",
    "get_gate_validators_for_phase",
    "get_validator_by_id",
    "PHYSICS_VALIDATORS",
    "BOUNDS_VALIDATORS",
    "STABILITY_VALIDATORS",
    "CLASS_VALIDATORS",
    "PRODUCTION_VALIDATORS",
    # Registry
    "ValidatorRegistry",
    # Contracts
    "PhaseContract",
    "PhaseOutputContract",
    "ContractResult",
    "PHASE_CONTRACTS",
    "check_phase_contract",
    "check_phase_inputs",
    "check_phase_outputs",
]
