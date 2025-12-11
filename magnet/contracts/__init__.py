"""
MAGNET Contracts Module

Abstract base classes defining interfaces for:
- DesignState
- StateManager
- PhaseMachine
- Domain Hashes (V1.4)
"""

from magnet.contracts.design_state_contract import DesignStateContract
from magnet.contracts.state_manager_contract import StateManagerContract
from magnet.contracts.phase_machine_contract import PhaseMachineContract
from magnet.contracts.domain_hashes import (
    DomainHashes,
    DomainHashProvider,
    DomainHashService,
    compute_domain_hash,
    compute_composite_hash,
)

__all__ = [
    "DesignStateContract",
    "StateManagerContract",
    "PhaseMachineContract",
    # V1.4 Domain Hashes
    "DomainHashes",
    "DomainHashProvider",
    "DomainHashService",
    "compute_domain_hash",
    "compute_composite_hash",
]
