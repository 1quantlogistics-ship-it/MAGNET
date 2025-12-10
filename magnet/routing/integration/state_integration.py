"""
state_integration.py - DesignState integration v1.1
BRAVO OWNS THIS FILE.

Module 60: Systems Routing
Integrates routing with MAGNET DesignState.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, TYPE_CHECKING
import logging
import json

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

__all__ = [
    'StateIntegrator',
    'RoutingStateKeys',
]

logger = logging.getLogger(__name__)


# =============================================================================
# STATE KEYS
# =============================================================================

class RoutingStateKeys:
    """Keys for routing data in DesignState."""

    # Main routing layout
    ROUTING_LAYOUT = "routing.layout"

    # Individual system topologies
    TOPOLOGY_PREFIX = "routing.topology."

    # Zone definitions
    ZONES = "routing.zones"
    FIRE_ZONES = "routing.zones.fire"
    WT_COMPARTMENTS = "routing.zones.watertight"

    # Configuration
    CONFIG = "routing.config"

    # Validation results
    VALIDATION = "routing.validation"

    # Metadata
    VERSION = "routing.version"
    LAST_UPDATED = "routing.last_updated"

    @classmethod
    def topology_key(cls, system_type: str) -> str:
        """Get key for a system topology."""
        return f"{cls.TOPOLOGY_PREFIX}{system_type}"


# =============================================================================
# STATE INTEGRATOR
# =============================================================================

class StateIntegrator:
    """
    Integrates routing module with MAGNET DesignState.

    Handles reading and writing routing data to/from the
    central state manager.

    Usage:
        integrator = StateIntegrator(state_manager)
        await integrator.save_routing(design_id, routing_layout)
        layout = await integrator.load_routing(design_id)
    """

    def __init__(self, state_manager: Optional["StateManager"] = None):
        """
        Initialize state integrator.

        Args:
            state_manager: MAGNET state manager instance
        """
        self._sm = state_manager

    def set_state_manager(self, state_manager: "StateManager") -> None:
        """Set or update state manager reference."""
        self._sm = state_manager

    # =========================================================================
    # ROUTING LAYOUT
    # =========================================================================

    async def save_routing(
        self,
        design_id: str,
        routing_layout: Any,
    ) -> bool:
        """
        Save routing layout to state.

        Args:
            design_id: Design identifier
            routing_layout: RoutingLayout to save

        Returns:
            True if saved successfully
        """
        if self._sm is None:
            logger.warning("No state manager configured")
            return False

        try:
            # Convert to dict if needed
            if hasattr(routing_layout, 'to_dict'):
                data = routing_layout.to_dict()
            elif isinstance(routing_layout, dict):
                data = routing_layout
            else:
                logger.error("Cannot serialize routing_layout")
                return False

            # Save main layout
            self._set_state_value(
                RoutingStateKeys.ROUTING_LAYOUT,
                data
            )

            # Save individual topologies for quick access
            topologies = data.get('topologies', {})
            for sys_type, topology in topologies.items():
                key = RoutingStateKeys.topology_key(str(sys_type))
                self._set_state_value(key, topology)

            # Update metadata
            import datetime
            self._set_state_value(
                RoutingStateKeys.LAST_UPDATED,
                datetime.datetime.utcnow().isoformat()
            )

            logger.info(f"Saved routing layout for design {design_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save routing: {e}")
            return False

    async def load_routing(
        self,
        design_id: str,
    ) -> Optional[Any]:
        """
        Load routing layout from state.

        Args:
            design_id: Design identifier

        Returns:
            RoutingLayout or None if not found
        """
        if self._sm is None:
            logger.warning("No state manager configured")
            return None

        try:
            data = self._get_state_value(RoutingStateKeys.ROUTING_LAYOUT)

            if data is None:
                return None

            # Try to import and construct RoutingLayout
            try:
                from magnet.routing.schema import RoutingLayout
                return RoutingLayout.from_dict(data)
            except ImportError:
                # Return raw dict if schema not available
                return data

        except Exception as e:
            logger.error(f"Failed to load routing: {e}")
            return None

    async def load_topology(
        self,
        design_id: str,
        system_type: str,
    ) -> Optional[Any]:
        """
        Load individual system topology.

        Args:
            design_id: Design identifier
            system_type: System type to load

        Returns:
            SystemTopology or None
        """
        if self._sm is None:
            return None

        try:
            key = RoutingStateKeys.topology_key(system_type)
            data = self._get_state_value(key)

            if data is None:
                return None

            try:
                from magnet.routing.schema import SystemTopology
                return SystemTopology.from_dict(data)
            except ImportError:
                return data

        except Exception as e:
            logger.error(f"Failed to load topology: {e}")
            return None

    # =========================================================================
    # INTERIOR LAYOUT (from M59)
    # =========================================================================

    async def load_interior(
        self,
        design_id: str,
    ) -> Optional[Any]:
        """
        Load interior layout from M59.

        Args:
            design_id: Design identifier

        Returns:
            InteriorLayout or None
        """
        if self._sm is None:
            return None

        try:
            # Try to get interior layout from state
            data = self._get_state_value("interior.layout")

            if data is None:
                return None

            try:
                from magnet.interior.schema import InteriorLayout
                return InteriorLayout.from_dict(data)
            except ImportError:
                return data

        except Exception as e:
            logger.error(f"Failed to load interior: {e}")
            return None

    # =========================================================================
    # ZONE DEFINITIONS
    # =========================================================================

    async def save_zones(
        self,
        design_id: str,
        fire_zones: Optional[Dict[str, Any]] = None,
        wt_compartments: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Save zone definitions to state.

        Args:
            design_id: Design identifier
            fire_zones: Fire zone definitions
            wt_compartments: Watertight compartment definitions

        Returns:
            True if saved successfully
        """
        if self._sm is None:
            return False

        try:
            if fire_zones is not None:
                # Convert zone definitions to dict
                zones_data = {}
                for zone_id, zone in fire_zones.items():
                    if hasattr(zone, 'to_dict'):
                        zones_data[zone_id] = zone.to_dict()
                    else:
                        zones_data[zone_id] = zone

                self._set_state_value(RoutingStateKeys.FIRE_ZONES, zones_data)

            if wt_compartments is not None:
                comps_data = {}
                for comp_id, comp in wt_compartments.items():
                    if hasattr(comp, 'to_dict'):
                        comps_data[comp_id] = comp.to_dict()
                    else:
                        comps_data[comp_id] = comp

                self._set_state_value(RoutingStateKeys.WT_COMPARTMENTS, comps_data)

            return True

        except Exception as e:
            logger.error(f"Failed to save zones: {e}")
            return False

    async def load_zones(
        self,
        design_id: str,
    ) -> Dict[str, Any]:
        """
        Load zone definitions from state.

        Returns:
            Dict with 'fire_zones' and 'wt_compartments' keys
        """
        result = {
            'fire_zones': {},
            'wt_compartments': {},
        }

        if self._sm is None:
            return result

        try:
            fire_data = self._get_state_value(RoutingStateKeys.FIRE_ZONES)
            if fire_data:
                try:
                    from magnet.routing.schema import ZoneDefinition
                    result['fire_zones'] = {
                        k: ZoneDefinition.from_dict(v)
                        for k, v in fire_data.items()
                    }
                except ImportError:
                    result['fire_zones'] = fire_data

            wt_data = self._get_state_value(RoutingStateKeys.WT_COMPARTMENTS)
            if wt_data:
                try:
                    from magnet.routing.schema import ZoneDefinition
                    result['wt_compartments'] = {
                        k: ZoneDefinition.from_dict(v)
                        for k, v in wt_data.items()
                    }
                except ImportError:
                    result['wt_compartments'] = wt_data

        except Exception as e:
            logger.error(f"Failed to load zones: {e}")

        return result

    # =========================================================================
    # VALIDATION
    # =========================================================================

    async def save_validation(
        self,
        design_id: str,
        validation_result: Any,
    ) -> bool:
        """Save validation result to state."""
        if self._sm is None:
            return False

        try:
            if hasattr(validation_result, 'to_dict'):
                data = validation_result.to_dict()
            else:
                data = validation_result

            self._set_state_value(RoutingStateKeys.VALIDATION, data)
            return True

        except Exception as e:
            logger.error(f"Failed to save validation: {e}")
            return False

    async def load_validation(
        self,
        design_id: str,
    ) -> Optional[Any]:
        """Load last validation result."""
        if self._sm is None:
            return None

        return self._get_state_value(RoutingStateKeys.VALIDATION)

    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    async def save_config(
        self,
        design_id: str,
        config: Any,
    ) -> bool:
        """Save routing configuration."""
        if self._sm is None:
            return False

        try:
            if hasattr(config, 'to_dict'):
                data = config.to_dict()
            else:
                data = config

            self._set_state_value(RoutingStateKeys.CONFIG, data)
            return True

        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    async def load_config(
        self,
        design_id: str,
    ) -> Optional[Any]:
        """Load routing configuration."""
        if self._sm is None:
            return None

        data = self._get_state_value(RoutingStateKeys.CONFIG)

        if data is None:
            return None

        try:
            from magnet.routing.integration import RoutingConfig
            return RoutingConfig.from_dict(data)
        except ImportError:
            return data

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _get_state_value(self, key: str) -> Optional[Any]:
        """Get value from state manager."""
        if self._sm is None:
            return None

        try:
            # Try different state access methods
            if hasattr(self._sm, 'get'):
                return self._sm.get(key)
            elif hasattr(self._sm, 'get_state_value'):
                return self._sm.get_state_value(key)
            elif hasattr(self._sm, '__getitem__'):
                return self._sm[key]
            else:
                logger.warning(f"Unknown state manager interface")
                return None
        except (KeyError, AttributeError):
            return None

    def _set_state_value(self, key: str, value: Any) -> None:
        """Set value in state manager."""
        if self._sm is None:
            return

        try:
            if hasattr(self._sm, 'set'):
                self._sm.set(key, value)
            elif hasattr(self._sm, 'set_state_value'):
                self._sm.set_state_value(key, value)
            elif hasattr(self._sm, '__setitem__'):
                self._sm[key] = value
            else:
                logger.warning(f"Unknown state manager interface")
        except Exception as e:
            logger.error(f"Failed to set state value: {e}")
