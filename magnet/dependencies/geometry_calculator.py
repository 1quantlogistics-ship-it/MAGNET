"""
Geometry Calculator for CascadeExecutor.

Bridges the NEW geometry primitives path to the EXISTING cascade infrastructure.

INVARIANT: This module must NEVER reference hull_type, HullFamily, or HullType.
           It calls program_executor which is verified clean by invariant tests.

Reference: MAGNET_Merge_Implementation_Plan.md Phase 3
"""

from typing import Any, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager
    from magnet.dependencies.cascade import CalculatorRegistry

logger = logging.getLogger(__name__)


class GeometryCalculator:
    """
    Calculator that runs program_executor for geometry changes.

    Registered with CascadeExecutor.CalculatorRegistry to handle
    geometry primitive recalculation.
    
    This enables the design spiral:
    - Engineer changes a parameter
    - CascadeExecutor detects geometry needs recalculation
    - GeometryCalculator calls program_executor
    - Geometry is recompiled and validated
    
    INVARIANT: This class MUST NOT contain hull_type, HullFamily, or
               any design type references. It only calls program_executor.
    """

    def __call__(
        self,
        state_manager: "StateManager",
        param: str,
    ) -> Any:
        """
        Recalculate geometry from design_program.

        Args:
            state_manager: Current design state
            param: Parameter being recalculated (ignored — we recompile all geometry)

        Returns:
            HullGeometry or None
        """
        from magnet.kernel.program_executor import execute_program

        # Get the current design program
        program = None
        if hasattr(state_manager, 'get'):
            program = state_manager.get("design_program")
        elif hasattr(state_manager, 'get_value'):
            program = state_manager.get_value("design_program")
        
        if not program:
            logger.debug(f"No design_program found for param {param}")
            return None

        # Execute the program (dry_run=True for validation, we commit separately)
        result = execute_program(program, state_manager, dry_run=True)

        if result.success and result.geometry:
            logger.debug(f"Geometry recalculated successfully for {param}")
            return result.geometry
        
        if result.errors:
            logger.warning(f"Geometry recalculation failed: {result.errors}")

        return None


class HydrostaticsCalculator:
    """
    Calculator for hydrostatics parameters.
    
    Triggered when geometry changes to recompute displacement, GM, etc.
    """
    
    def __call__(
        self,
        state_manager: "StateManager",
        param: str,
    ) -> Any:
        """Recalculate hydrostatics from geometry."""
        # Get geometry
        geometry = None
        if hasattr(state_manager, 'get'):
            geometry = state_manager.get("hull.geometry")
        
        if not geometry:
            return None
        
        # Get parameters for calculation
        draft = 1.5
        vcg = 1.0
        if hasattr(state_manager, 'get'):
            draft = state_manager.get("hull.draft") or draft
            vcg = state_manager.get("hull.vcg") or vcg
        
        try:
            from magnet.stability.intact_gm import compute_gm_from_geometry
            result = compute_gm_from_geometry(geometry, draft, vcg)
            
            # Return the specific parameter requested
            if "gm" in param:
                return result.get("gm_m")
            elif "bm" in param:
                return result.get("bm_m")
            elif "kb" in param:
                return result.get("kb_m")
            elif "displacement" in param:
                return getattr(geometry, 'volume', None)
            
            return result
            
        except ImportError:
            logger.debug("Stability module not available")
            return None
        except Exception as e:
            logger.warning(f"Hydrostatics calculation failed: {e}")
            return None


def register_geometry_calculators(registry: "CalculatorRegistry") -> None:
    """
    Register geometry calculators with the cascade registry.

    Call this during application startup.
    
    Reference: MAGNET_Merge_Implementation_Plan.md Phase 3
    """
    geometry_calculator = GeometryCalculator()
    hydro_calculator = HydrostaticsCalculator()

    # Register for all geometry-related parameters
    geometry_params = [
        "hull.geometry",
        "resources.geometry.section",
        "resources.geometry.body",
        "resources.geometry.surface",
        "resources.geometry.discontinuity",
        "resources.geometry.flow_path",
        "resources.geometry.opening",
        "resources.geometry.attachment",
        "design_program",  # Trigger recalculation if program changes
    ]

    for param in geometry_params:
        registry.register(
            param=param,
            calculator=geometry_calculator,
            estimated_time_ms=500,
            requires_lock=True,  # Geometry compilation is not thread-safe
        )
    
    # Register hydrostatics calculators
    hydro_params = [
        "hull.displacement_m3",
        "stability.gm_m",
        "stability.bm_m",
        "stability.kb_m",
    ]
    
    for param in hydro_params:
        registry.register(
            param=param,
            calculator=hydro_calculator,
            estimated_time_ms=200,
            requires_lock=False,
        )
    
    logger.info(f"Registered {len(geometry_params)} geometry calculators and {len(hydro_params)} hydrostatics calculators")


# =============================================================================
# INVARIANT: No enumeration in this module
# =============================================================================

# This check runs on module import to catch violations early
def _verify_no_enumeration():
    """Verify this module doesn't import enumeration types."""
    import sys
    
    module_source = __file__
    forbidden = ["HullFamily", "HullType", "hull_type"]
    
    # Check if any forbidden imports are in this module's namespace
    current_module = sys.modules.get(__name__, None)
    if current_module:
        for name in dir(current_module):
            for forbidden_term in forbidden:
                if forbidden_term in name:
                    raise ImportError(
                        f"INVARIANT VIOLATION: {__name__} contains '{name}' "
                        f"which matches forbidden term '{forbidden_term}'"
                    )

# Run verification on import
_verify_no_enumeration()

