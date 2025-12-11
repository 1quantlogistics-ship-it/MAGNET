"""
api_endpoints.py - REST API routes v1.2
BRAVO OWNS THIS FILE.

Module 60: Systems Routing
FastAPI endpoints for routing operations.

v1.2 Changes:
- Added domain hash fields (V1.4 FIX #2)
- Added routing_hash to all responses
- Added update_id/prev_update_id chain tracking (V1.4 FIX #1)
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import logging
import hashlib
import json

try:
    from fastapi import APIRouter, HTTPException, Query
    from pydantic import BaseModel
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    APIRouter = None

__all__ = [
    'create_routing_router',
    'RouteRequest',
    'RouteResponse',
    'ValidationResponse',
]

logger = logging.getLogger(__name__)


def _compute_routing_hash(layout: Any) -> Optional[str]:
    """Compute SHA256 hash for routing layout."""
    if layout is None:
        return None
    try:
        if hasattr(layout, 'to_dict'):
            data = layout.to_dict()
        elif isinstance(layout, dict):
            data = layout
        else:
            return None
        normalized = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    except Exception:
        return None


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

if HAS_FASTAPI:

    class RouteRequest(BaseModel):
        """Request to route systems."""
        systems: List[str]
        force_reroute: bool = False

    class RouteSystemRequest(BaseModel):
        """Request to route a single system."""
        constraints: Dict[str, Any] = {}

    class RouteResponse(BaseModel):
        """Response from routing operation."""
        success: bool
        systems_routed: List[str]
        systems_failed: List[str]
        total_trunks: int
        total_length_m: float
        zone_violations: int
        log: List[str]
        # V1.4 domain hash fields
        routing_hash: Optional[str] = None
        update_id: Optional[str] = None
        prev_update_id: Optional[str] = None
        version: int = 1

    class ValidationResponse(BaseModel):
        """Response from validation operation."""
        is_valid: bool
        systems_validated: int
        total_violations: int
        violations: List[Dict[str, Any]]
        # V1.4 domain hash fields
        routing_hash: Optional[str] = None
        version: int = 1

    class TopologyResponse(BaseModel):
        """Response with system topology."""
        system_type: str
        node_count: int
        trunk_count: int
        total_length_m: float
        is_complete: bool
        # V1.4 domain hash fields
        routing_hash: Optional[str] = None
        version: int = 1

    class ConflictResponse(BaseModel):
        """Response with conflict information."""
        total_conflicts: int
        resolved: int
        unresolved: int
        conflicts: List[Dict[str, Any]]
        # V1.4 domain hash fields
        routing_hash: Optional[str] = None
        version: int = 1

else:
    # Fallback dataclasses when FastAPI not available
    @dataclass
    class RouteRequest:
        systems: List[str] = field(default_factory=list)
        force_reroute: bool = False

    @dataclass
    class RouteResponse:
        success: bool = False
        systems_routed: List[str] = field(default_factory=list)
        systems_failed: List[str] = field(default_factory=list)
        total_trunks: int = 0
        total_length_m: float = 0.0
        zone_violations: int = 0
        log: List[str] = field(default_factory=list)
        # V1.4 domain hash fields
        routing_hash: Optional[str] = None
        update_id: Optional[str] = None
        prev_update_id: Optional[str] = None
        version: int = 1

    @dataclass
    class ValidationResponse:
        is_valid: bool = False
        systems_validated: int = 0
        total_violations: int = 0
        violations: List[Dict[str, Any]] = field(default_factory=list)
        # V1.4 domain hash fields
        routing_hash: Optional[str] = None
        version: int = 1


# =============================================================================
# ROUTER FACTORY
# =============================================================================

def create_routing_router(
    state_integrator: Any,
    routing_agent: Optional[Any] = None,
    validator: Optional[Any] = None,
) -> Any:
    """
    Create FastAPI router for routing endpoints.

    Args:
        state_integrator: StateIntegrator instance
        routing_agent: RoutingAgent instance (optional)
        validator: RoutingValidator instance (optional)

    Returns:
        FastAPI APIRouter or None if FastAPI not available
    """
    if not HAS_FASTAPI:
        logger.warning("FastAPI not available, cannot create router")
        return None

    router = APIRouter(
        prefix="/api/v1/designs/{design_id}/routing",
        tags=["routing"],
    )

    # =========================================================================
    # ROUTING ENDPOINTS
    # =========================================================================

    @router.post("/route", response_model=RouteResponse)
    async def route_systems(
        design_id: str,
        request: RouteRequest,
    ) -> RouteResponse:
        """
        Route specified systems through the interior layout.

        Args:
            design_id: Design identifier
            request: Systems to route

        Returns:
            Routing result with statistics
        """
        # Load interior layout
        interior = await state_integrator.load_interior(design_id)
        if interior is None:
            raise HTTPException(
                status_code=404,
                detail="No interior layout found. Generate interior first."
            )

        # Check for routing agent
        if routing_agent is None:
            raise HTTPException(
                status_code=500,
                detail="Routing agent not configured"
            )

        # Parse system types
        try:
            from magnet.routing.schema import SystemType
            systems = []
            for s in request.systems:
                try:
                    systems.append(SystemType(s))
                except ValueError:
                    systems.append(s)  # Use string if not valid enum
        except ImportError:
            systems = request.systems

        # Route systems
        result = routing_agent.route_all(
            interior_layout=interior,
            systems=systems,
        )

        # Save routing
        await state_integrator.save_routing(design_id, result.routing_layout)

        # V1.4: Compute routing hash
        routing_hash = _compute_routing_hash(result.routing_layout)

        # Get version info if available
        update_id = None
        prev_update_id = None
        version = 1
        if hasattr(result.routing_layout, 'version_info'):
            vi = result.routing_layout.version_info
            update_id = getattr(vi, 'update_id', None)
            prev_update_id = getattr(vi, 'prev_update_id', None)
            version = getattr(vi, 'version', 1)

        return RouteResponse(
            success=result.is_complete,
            systems_routed=[str(s) for s in result.systems_routed],
            systems_failed=[str(s) for s in result.systems_failed],
            total_trunks=result.total_trunks,
            total_length_m=result.total_length_m,
            zone_violations=result.zone_violations,
            log=result.log,
            routing_hash=routing_hash,
            update_id=update_id,
            prev_update_id=prev_update_id,
            version=version,
        )

    @router.get("/layout")
    async def get_routing_layout(design_id: str) -> dict:
        """Get current routing layout."""
        layout = await state_integrator.load_routing(design_id)
        if layout is None:
            raise HTTPException(
                status_code=404,
                detail="No routing layout found"
            )

        # V1.4: Include routing hash in response
        result = {}
        if hasattr(layout, 'to_dict'):
            result = layout.to_dict()
        else:
            result = layout if isinstance(layout, dict) else {}

        result['routing_hash'] = _compute_routing_hash(layout)

        # Add version info if available
        if hasattr(layout, 'version_info'):
            vi = layout.version_info
            result['update_id'] = getattr(vi, 'update_id', None)
            result['prev_update_id'] = getattr(vi, 'prev_update_id', None)
            result['version'] = getattr(vi, 'version', 1)
        else:
            result['version'] = 1

        return result

    @router.delete("/layout")
    async def clear_routing(design_id: str) -> dict:
        """Clear all routing for a design."""
        # Save empty layout
        await state_integrator.save_routing(design_id, {'topologies': {}})

        return {"success": True, "message": "Routing cleared"}

    # =========================================================================
    # SYSTEM ENDPOINTS
    # =========================================================================

    @router.get("/systems")
    async def list_routed_systems(design_id: str) -> List[str]:
        """List all systems with routing."""
        layout = await state_integrator.load_routing(design_id)
        if layout is None:
            return []

        if hasattr(layout, 'topologies'):
            return [str(k) for k in layout.topologies.keys()]
        elif isinstance(layout, dict):
            return list(layout.get('topologies', {}).keys())

        return []

    @router.get("/systems/{system_type}")
    async def get_system_topology(
        design_id: str,
        system_type: str,
    ) -> dict:
        """Get topology for a specific system."""
        topology = await state_integrator.load_topology(design_id, system_type)

        if topology is None:
            raise HTTPException(
                status_code=404,
                detail=f"No topology found for {system_type}"
            )

        if hasattr(topology, 'to_dict'):
            return topology.to_dict()
        return topology

    @router.post("/systems/{system_type}/reroute")
    async def reroute_system(
        design_id: str,
        system_type: str,
    ) -> dict:
        """Reroute a specific system."""
        if routing_agent is None:
            raise HTTPException(
                status_code=500,
                detail="Routing agent not configured"
            )

        interior = await state_integrator.load_interior(design_id)
        if interior is None:
            raise HTTPException(
                status_code=404,
                detail="No interior layout found"
            )

        layout = await state_integrator.load_routing(design_id)
        if layout is None:
            # Create empty layout
            try:
                from magnet.routing.schema import RoutingLayout
                layout = RoutingLayout()
            except ImportError:
                layout = {'topologies': {}}

        # Reroute
        try:
            from magnet.routing.schema import SystemType
            sys_type = SystemType(system_type)
        except (ImportError, ValueError):
            sys_type = system_type

        topology = routing_agent.reroute(interior, layout, sys_type)

        # Update layout
        if hasattr(layout, 'topologies'):
            layout.topologies[sys_type] = topology
        elif isinstance(layout, dict):
            layout.setdefault('topologies', {})[system_type] = topology

        await state_integrator.save_routing(design_id, layout)

        trunk_count = 0
        total_length = 0.0

        if hasattr(topology, 'trunks'):
            trunk_count = len(topology.trunks)
            total_length = sum(
                getattr(t, 'length_m', 0) for t in topology.trunks.values()
            )

        return {
            'success': True,
            'system_type': system_type,
            'trunk_count': trunk_count,
            'total_length_m': total_length,
        }

    @router.delete("/systems/{system_type}")
    async def clear_system_routing(
        design_id: str,
        system_type: str,
    ) -> dict:
        """Clear routing for a specific system."""
        layout = await state_integrator.load_routing(design_id)
        if layout is None:
            return {"success": True, "message": "No routing to clear"}

        # Remove system topology
        if hasattr(layout, 'topologies'):
            try:
                from magnet.routing.schema import SystemType
                sys_type = SystemType(system_type)
                layout.topologies.pop(sys_type, None)
            except (ImportError, ValueError):
                layout.topologies.pop(system_type, None)
        elif isinstance(layout, dict):
            layout.get('topologies', {}).pop(system_type, None)

        await state_integrator.save_routing(design_id, layout)

        return {"success": True, "message": f"Cleared routing for {system_type}"}

    # =========================================================================
    # VALIDATION ENDPOINTS
    # =========================================================================

    @router.post("/validate", response_model=ValidationResponse)
    async def validate_routing(design_id: str) -> ValidationResponse:
        """Validate routing for all systems."""
        if validator is None:
            raise HTTPException(
                status_code=500,
                detail="Validator not configured"
            )

        layout = await state_integrator.load_routing(design_id)
        if layout is None:
            raise HTTPException(
                status_code=404,
                detail="No routing layout found"
            )

        # Load zones for validation
        zones = await state_integrator.load_zones(design_id)

        # Validate
        result = validator.validate(
            routing_layout=layout,
            zone_definitions=zones.get('fire_zones', {}),
        )

        # Save validation result
        await state_integrator.save_validation(design_id, result)

        violations = []
        for v in result.violations:
            if hasattr(v, 'to_dict'):
                violations.append(v.to_dict())
            else:
                violations.append(v)

        # V1.4: Include routing hash
        routing_hash = _compute_routing_hash(layout)
        version = 1
        if hasattr(layout, 'version_info'):
            version = getattr(layout.version_info, 'version', 1)

        return ValidationResponse(
            is_valid=result.is_valid,
            systems_validated=len(result.systems_validated),
            total_violations=len(result.violations),
            violations=violations,
            routing_hash=routing_hash,
            version=version,
        )

    @router.get("/validation")
    async def get_validation_result(design_id: str) -> dict:
        """Get last validation result."""
        result = await state_integrator.load_validation(design_id)
        if result is None:
            raise HTTPException(
                status_code=404,
                detail="No validation result found"
            )

        if hasattr(result, 'to_dict'):
            return result.to_dict()
        return result

    # =========================================================================
    # ZONE ENDPOINTS
    # =========================================================================

    @router.get("/zones")
    async def get_zones(design_id: str) -> dict:
        """Get zone definitions."""
        zones = await state_integrator.load_zones(design_id)

        result = {}
        for key, zone_dict in zones.items():
            result[key] = {}
            for zone_id, zone in zone_dict.items():
                if hasattr(zone, 'to_dict'):
                    result[key][zone_id] = zone.to_dict()
                else:
                    result[key][zone_id] = zone

        return result

    @router.post("/zones")
    async def update_zones(
        design_id: str,
        zones: dict,
    ) -> dict:
        """Update zone definitions."""
        fire_zones = zones.get('fire_zones')
        wt_compartments = zones.get('wt_compartments')

        success = await state_integrator.save_zones(
            design_id,
            fire_zones=fire_zones,
            wt_compartments=wt_compartments,
        )

        return {"success": success}

    # =========================================================================
    # CONFIG ENDPOINTS
    # =========================================================================

    @router.get("/config")
    async def get_config(design_id: str) -> dict:
        """Get routing configuration."""
        config = await state_integrator.load_config(design_id)
        if config is None:
            # Return default config
            try:
                from magnet.routing.integration import DEFAULT_CONFIG
                return DEFAULT_CONFIG.to_dict()
            except ImportError:
                return {}

        if hasattr(config, 'to_dict'):
            return config.to_dict()
        return config

    @router.put("/config")
    async def update_config(
        design_id: str,
        config: dict,
    ) -> dict:
        """Update routing configuration."""
        try:
            from magnet.routing.integration import RoutingConfig
            config_obj = RoutingConfig.from_dict(config)
        except ImportError:
            config_obj = config

        success = await state_integrator.save_config(design_id, config_obj)

        return {"success": success}

    return router


# =============================================================================
# DEFAULT ROUTER
# =============================================================================

# Create default router for direct import
if HAS_FASTAPI:
    default_router = APIRouter(
        prefix="/api/v1/designs/{design_id}/routing",
        tags=["routing"],
    )
else:
    default_router = None
