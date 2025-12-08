"""
MAGNET Physics Calculation Framework

Module 05 v1.2 - Production-Ready

Provides hydrostatics, resistance, and naval architecture calculations.

v1.2 Changes:
- 11 hydrostatic outputs (up from 6 in v1.1)
- New fields: kb_m, bm_m, tpc, mct, lcf_m, freeboard
- ResistanceCalculator with Holtrop-Mennen method
- ResistanceValidator for validation pipeline
"""

from .hydrostatics import (
    HydrostaticsResults,
    HydrostaticsCalculator,
    HYDROSTATICS_INPUTS,
    HYDROSTATICS_OUTPUTS,
)

from .resistance import (
    ResistanceResults,
    ResistanceCalculator,
    RESISTANCE_INPUTS,
    RESISTANCE_OUTPUTS,
)

from .validators import (
    HydrostaticsValidator,
    ResistanceValidator,
    get_hydrostatics_definition,
    get_resistance_definition,
    register_physics_validators,
)

__all__ = [
    # Results
    "HydrostaticsResults",
    "ResistanceResults",
    # Calculators
    "HydrostaticsCalculator",
    "ResistanceCalculator",
    # Validators
    "HydrostaticsValidator",
    "ResistanceValidator",
    # Definitions
    "get_hydrostatics_definition",
    "get_resistance_definition",
    # Constants
    "HYDROSTATICS_INPUTS",
    "HYDROSTATICS_OUTPUTS",
    "RESISTANCE_INPUTS",
    "RESISTANCE_OUTPUTS",
    # Registration
    "register_physics_calculators",
    "register_physics_validators",
]


# =============================================================================
# CALCULATOR REGISTRATION
# =============================================================================

def register_physics_calculators(registry) -> None:
    """
    Register all physics calculators with the CascadeExecutor.

    Args:
        registry: CalculatorRegistry instance from magnet.dependencies.cascade
    """
    from .hydrostatics import HydrostaticsCalculator

    calculator = HydrostaticsCalculator()

    # Register hydrostatics calculator for all produced parameters
    for param in HYDROSTATICS_OUTPUTS:
        registry.register(
            param,
            lambda sm, p, calc=calculator: _calculate_hydrostatic_param(sm, p, calc),
            estimated_time_ms=50,
            requires_lock=False,
        )


def _calculate_hydrostatic_param(state_manager, param: str, calculator: HydrostaticsCalculator):
    """
    Calculate a single hydrostatic parameter.

    Note: This is called per-parameter but the calculator computes all at once.
    The caching in the calculator prevents redundant calculations.
    """
    # Read inputs
    lwl = state_manager.get("hull.lwl", 0.0)
    beam = state_manager.get("hull.beam", 0.0)
    draft = state_manager.get("hull.draft", 0.0)
    depth = state_manager.get("hull.depth", draft + 1.5)  # Default freeboard
    cb = state_manager.get("hull.cb", 0.0)
    cp = state_manager.get("hull.cp")
    cm = state_manager.get("hull.cm")
    cwp = state_manager.get("hull.cwp")
    hull_type = state_manager.get("hull.hull_type", "monohull")
    deadrise_deg = state_manager.get("hull.deadrise_deg", 0.0)

    # Calculate all hydrostatics
    results = calculator.calculate(
        lwl=lwl,
        beam=beam,
        draft=draft,
        depth=depth,
        cb=cb,
        cp=cp,
        cm=cm,
        cwp=cwp,
        hull_type=hull_type,
        deadrise_deg=deadrise_deg,
    )

    # Return the specific parameter requested
    param_map = {
        "hull.displacement_m3": results.volume_displaced_m3,
        "hull.kb_m": results.kb_m,
        "hull.bm_m": results.bm_m,
        "hull.lcb_from_ap_m": results.lcb_m,
        "hull.vcb_m": results.vcb_m,
        "hull.tpc": results.tpc,
        "hull.mct": results.mct,
        "hull.lcf_from_ap_m": results.lcf_m,
        "hull.waterplane_area_m2": results.waterplane_area_m2,
        "hull.wetted_surface_m2": results.wetted_surface_m2,
        "hull.freeboard": results.freeboard_m,
    }

    return param_map.get(param)
