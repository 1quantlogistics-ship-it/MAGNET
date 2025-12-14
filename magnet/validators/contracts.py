"""
Phase Contracts - Enforces inputs and outputs for phases.

BRAVO OWNS THIS FILE.

Guardrail #1: No-Op Is Failure - phases must mutate state, not just pass validators.
Hole #5 Fix: Input contracts - phases must have required inputs BEFORE execution.
v1.1: Path-strict checking to catch contract definition bugs early.
"""
from typing import Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
import logging

if TYPE_CHECKING:
    from ..core.state_manager import StateManager

logger = logging.getLogger(__name__)


class ContractDefinitionError(Exception):
    """
    Raised when a contract references paths not in the state schema.

    This indicates a BUG in the contract definition, not missing data.
    Contract paths should be validated during development.
    """
    pass


@dataclass
class ContractResult:
    """Result of contract check."""
    phase_name: str
    satisfied: bool
    missing_outputs: List[str]  # Also used for missing inputs
    message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "phase": self.phase_name,
            "satisfied": self.satisfied,
            "missing_outputs": self.missing_outputs,
            "message": self.message,
        }


@dataclass
class PhaseContract:
    """
    Defines required inputs AND outputs for a phase.

    Hole #5 Fix: Contracts now check inputs BEFORE phase execution.
    """
    phase_name: str
    required_inputs: List[str] = field(default_factory=list)   # MUST exist BEFORE phase
    required_outputs: List[str] = field(default_factory=list)  # MUST exist AFTER phase
    optional_outputs: List[str] = field(default_factory=list)  # Nice to have

    def check_inputs(self, state_manager: 'StateManager') -> ContractResult:
        """
        Check if required inputs are present BEFORE phase execution.

        v1.1: Uses path-strict checking to catch contract bugs early.
        """
        from ..core.state_manager import MISSING, InvalidPathError

        missing = []
        invalid_paths = []

        for path in self.required_inputs:
            try:
                value = state_manager.get_strict(path)
                if value is MISSING or value is None:
                    missing.append(path)
            except InvalidPathError:
                # Contract references a path not in schema - this is a BUG
                invalid_paths.append(f"{path} (CONTRACT BUG: not in schema)")

        # Surface contract definition bugs immediately
        if invalid_paths:
            raise ContractDefinitionError(
                f"Phase '{self.phase_name}' contract has invalid paths: {invalid_paths}"
            )

        return ContractResult(
            phase_name=self.phase_name,
            satisfied=len(missing) == 0,
            missing_outputs=missing,
            message=f"Phase {self.phase_name} missing required INPUTS: {missing}" if missing else None
        )

    def check_outputs(self, state_manager: 'StateManager') -> ContractResult:
        """
        Check if required outputs are present AFTER phase execution.

        v1.1: Uses path-strict checking to catch contract bugs early.
        """
        from ..core.state_manager import MISSING, InvalidPathError

        missing = []
        invalid_paths = []

        for path in self.required_outputs:
            try:
                value = state_manager.get_strict(path)
                if value is MISSING or value is None:
                    missing.append(path)
            except InvalidPathError:
                # Contract references a path not in schema - this is a BUG
                invalid_paths.append(f"{path} (CONTRACT BUG: not in schema)")

        # Surface contract definition bugs immediately
        if invalid_paths:
            raise ContractDefinitionError(
                f"Phase '{self.phase_name}' contract has invalid paths: {invalid_paths}"
            )

        return ContractResult(
            phase_name=self.phase_name,
            satisfied=len(missing) == 0,
            missing_outputs=missing,
            message=f"Phase {self.phase_name} missing required OUTPUTS: {missing}" if missing else None
        )

    # Backwards compatibility - check outputs only
    def check(self, state_manager: 'StateManager') -> ContractResult:
        """Check if phase produced required outputs (backwards compatible)."""
        return self.check_outputs(state_manager)


# Backwards compatibility alias
PhaseOutputContract = PhaseContract


# ============================================================================
# PHASE CONTRACTS (Hole #5: Now includes input contracts)
# ============================================================================

PHASE_CONTRACTS: Dict[str, PhaseContract] = {
    "hull": PhaseContract(
        phase_name="hull",
        required_inputs=[
            "hull.lwl",       # Length at waterline
            "hull.beam",      # Beam
            "hull.draft",     # Draft
            "hull.cb",        # Block coefficient
        ],
        required_outputs=[
            "hull.displacement_m3",
            "hull.vcb_m",     # Vertical center of buoyancy (KB)
            "hull.bmt",       # Transverse metacentric radius (BM) - matches HullState.bmt
        ],
        optional_outputs=[
            "hull.wetted_surface_m2",
            "hull.waterplane_area_m2",
            "hull.kb_m",
        ],
    ),
    "stability": PhaseContract(
        phase_name="stability",
        required_inputs=[
            "hull.displacement_m3",  # From hull phase
            "hull.vcb_m",            # KB from hull
            "hull.bmt",              # BM from hull - matches HullState.bmt
            "weight.lightship_vcg_m",  # VCG from weight phase
        ],
        required_outputs=[
            "stability.gm_transverse_m",  # Transverse metacentric height - matches StabilityState
        ],
        optional_outputs=[
            "stability.gz_curve",
            "stability.gz_max_m",
            "stability.kb_m",
            "stability.bm_m",
        ],
    ),
    "weight": PhaseContract(
        phase_name="weight",
        required_inputs=[
            "hull.lwl",
            "hull.beam",
            "hull.depth",
        ],
        required_outputs=[
            "weight.lightship_weight_mt",  # Lightship weight - matches WeightEstimate
            "weight.lightship_vcg_m",      # Lightship VCG
        ],
        optional_outputs=[
            "weight.full_load_displacement_mt",
            "weight.deadweight_mt",
        ],
    ),
    "propulsion": PhaseContract(
        phase_name="propulsion",
        required_inputs=[
            # Propulsion can be user-supplied, so minimal requirements
        ],
        required_outputs=[
            # Propulsion can be user-supplied, so minimal requirements
        ],
        optional_outputs=[
            "propulsion.installed_power_kw",
        ],
    ),
    "compliance": PhaseContract(
        phase_name="compliance",
        required_inputs=[
            "stability.gm_transverse_m",  # Need stability results - matches StabilityState
        ],
        required_outputs=[
            "compliance.status",
            "compliance.pass_count",
            "compliance.fail_count",
        ],
    ),
    "arrangement": PhaseContract(
        phase_name="arrangement",
        required_inputs=[
            "hull.lwl",
            "hull.beam",
            "hull.depth",
        ],
        required_outputs=[
            "arrangement.compartment_count",
        ],
    ),
    "loading": PhaseContract(
        phase_name="loading",
        required_inputs=[
            "weight.lightship_weight_mt",  # Matches WeightEstimate
            "weight.lightship_vcg_m",
            "arrangement.tanks",  # Need tank arrangement
        ],
        required_outputs=[
            "loading.all_conditions_pass",
        ],
    ),
    "production": PhaseContract(
        phase_name="production",
        required_inputs=[],   # Optional phase
        required_outputs=[],  # Optional phase
    ),
    "cost": PhaseContract(
        phase_name="cost",
        required_inputs=[],   # Optional phase
        required_outputs=[],  # Optional phase
    ),
}


def check_phase_inputs(phase_name: str, state_manager: 'StateManager') -> ContractResult:
    """
    Check if phase has required inputs BEFORE execution.

    Hole #5 Fix: Prevents phases from running without required inputs.
    """
    contract = PHASE_CONTRACTS.get(phase_name)
    if not contract:
        # No contract defined - phase passes by default
        return ContractResult(
            phase_name=phase_name,
            satisfied=True,
            missing_outputs=[],
        )

    return contract.check_inputs(state_manager)


def check_phase_outputs(phase_name: str, state_manager: 'StateManager') -> ContractResult:
    """
    Check if phase produced required outputs AFTER execution.

    Guardrail #1: Prevents "validators pass but nothing happened" situation.
    """
    contract = PHASE_CONTRACTS.get(phase_name)
    if not contract:
        # No contract defined - phase passes by default
        return ContractResult(
            phase_name=phase_name,
            satisfied=True,
            missing_outputs=[],
        )

    return contract.check_outputs(state_manager)


# Backwards compatibility
def check_phase_contract(phase_name: str, state_manager: 'StateManager') -> ContractResult:
    """
    Check if a phase satisfied its output contract.

    Guardrail #1: Prevents "validators pass but nothing happened" situation.

    NOTE: This is the backwards-compatible function. For full input+output
    checking, use check_phase_inputs() and check_phase_outputs() separately.
    """
    return check_phase_outputs(phase_name, state_manager)
