"""
MAGNET Contracts Module

Abstract base classes defining interfaces for:
- DesignState
- StateManager
- PhaseMachine
"""

from magnet.contracts.design_state_contract import DesignStateContract
from magnet.contracts.state_manager_contract import StateManagerContract
from magnet.contracts.phase_machine_contract import PhaseMachineContract

__all__ = [
    "DesignStateContract",
    "StateManagerContract",
    "PhaseMachineContract",
]
