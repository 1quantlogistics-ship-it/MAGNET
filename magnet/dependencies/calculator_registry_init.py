"""
Calculator Registry Initialization.

Registers all calculators with CascadeExecutor on application startup.

INVARIANT: This module coordinates registration but must NOT contain
           enumeration logic. All calculators must derive from geometry.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from magnet.dependencies.cascade import CalculatorRegistry

logger = logging.getLogger(__name__)


def register_all_calculators(registry: "CalculatorRegistry") -> None:
    """
    Register ALL calculators with the cascade registry.
    
    Call this during application startup (e.g., in bootstrap startup hook).
    
    Registers:
    1. Geometry calculators (NEW path - design language primitives)
    2. Legacy physics calculators (compatibility during migration)
    
    Args:
        registry: CalculatorRegistry instance from CascadeExecutor
    
    Reference: MAGNET_Critical_Corrections.md Issue 3.3
    """
    try:
        # Register NEW geometry-based calculators
        from magnet.dependencies.geometry_calculator import register_geometry_calculators
        register_geometry_calculators(registry)
        logger.info("✅ Registered geometry calculators (NEW PATH)")
    except ImportError as e:
        logger.warning(f"Could not register geometry calculators: {e}")
    except Exception as e:
        logger.error(f"Failed to register geometry calculators: {e}")
        raise
    
    try:
        # Register legacy physics calculators (for backward compatibility)
        # NOTE: These use hull_type but are being kept for migration period
        from magnet.physics import register_physics_calculators
        register_physics_calculators(registry)
        logger.info("⚠️  Registered legacy physics calculators (MIGRATION)")
    except ImportError as e:
        logger.warning(f"Could not register legacy physics calculators: {e}")
    except Exception as e:
        logger.error(f"Failed to register legacy physics calculators: {e}")
        # Don't raise - legacy calculators are optional during migration
    
    # Log summary
    registered_params = registry.list_calculators()
    logger.info(f"📊 Total calculators registered: {len(registered_params)}")
    logger.debug(f"Registered parameters: {registered_params}")


def create_registry_and_register() -> "CalculatorRegistry":
    """
    Convenience function to create a registry and register all calculators.
    
    Returns:
        Fully configured CalculatorRegistry instance
    """
    from magnet.dependencies.cascade import CalculatorRegistry
    
    registry = CalculatorRegistry()
    register_all_calculators(registry)
    
    return registry

