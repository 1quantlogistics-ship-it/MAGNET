"""
api_endpoints.py - Interior REST API routes v1.0
BRAVO OWNS THIS FILE.

Module 59: Interior Layout
FastAPI endpoints for interior layout operations.

Endpoints (per V1.4 spec):
- POST /interior/generate - Generate interior layout
- GET /interior/layout - Get current layout
- POST /interior/spaces - Create new space
- PUT /interior/spaces/{space_id} - Update space
- DELETE /interior/spaces/{space_id} - Delete space
- POST /interior/validate - Validate layout
- POST /interior/optimize - Optimize layout
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import logging

try:
    from fastapi import APIRouter, HTTPException, Query, Body
    from pydantic import BaseModel, Field
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    APIRouter = None

from magnet.interior.schema.space import (
    SpaceType,
    SpaceCategory,
    SpaceDefinition,
    SpaceBoundary,
)
from magnet.interior.schema.layout import InteriorLayout
from magnet.interior.schema.validation import ValidationResult
from magnet.interior.generator.layout_generator import (
    LayoutGenerator,
    GenerationConfig,
    GenerationResult,
)
from magnet.interior.integration.state_integration import (
    InteriorStateIntegrator,
    InteriorStateError,
)

__all__ = [
    'create_interior_router',
    'GenerateRequest',
    'GenerateResponse',
    'LayoutResponse',
    'SpaceRequest',
    'SpaceResponse',
    'ValidationResponse',
    'OptimizeRequest',
    'OptimizeResponse',
]

logger = logging.getLogger(__name__)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

if HAS_FASTAPI:

    class GenerateRequest(BaseModel):
        """Request to generate interior layout."""
        loa: float = Field(100.0, description="Length overall (m)")
        beam: float = Field(20.0, description="Beam (m)")
        depth: float = Field(10.0, description="Depth (m)")
        num_decks: int = Field(4, description="Number of decks")
        crew_capacity: int = Field(20, description="Crew capacity")
        passenger_capacity: int = Field(0, description="Passenger capacity")
        ship_type: str = Field("general_cargo", description="Ship type")

    class GenerateResponse(BaseModel):
        """Response from layout generation."""
        success: bool
        layout_id: Optional[str] = None
        design_id: str
        space_count: int = 0
        deck_count: int = 0
        total_area_m2: float = 0.0
        arrangement_hash: Optional[str] = None
        update_id: Optional[str] = None
        prev_update_id: Optional[str] = None
        version: int = 1
        errors: List[str] = []
        warnings: List[str] = []

    class LayoutResponse(BaseModel):
        """Response with full layout data."""
        layout_id: str
        design_id: str
        version: int
        update_id: str
        prev_update_id: Optional[str] = None
        arrangement_hash: str
        space_count: int
        deck_count: int
        total_area_m2: float
        total_volume_m3: float
        decks: Dict[str, Any]
        metadata: Dict[str, Any]

    class SpaceBoundaryRequest(BaseModel):
        """Space boundary definition."""
        points: List[List[float]]
        deck_id: str
        z_min: float = 0.0
        z_max: float = 2.5

    class SpaceRequest(BaseModel):
        """Request to create/update a space."""
        name: str
        space_type: str
        category: str
        boundary: SpaceBoundaryRequest
        deck_id: str
        zone_id: Optional[str] = None
        max_occupancy: int = 0
        is_manned: bool = False
        notes: str = ""

    class SpaceResponse(BaseModel):
        """Response for space operations."""
        success: bool
        space_id: str
        update_id: str
        prev_update_id: Optional[str] = None
        arrangement_hash: str
        version: int
        message: str = ""

    class ValidationResponse(BaseModel):
        """Response from validation operation."""
        is_valid: bool
        design_id: str
        errors_count: int
        warnings_count: int
        issues: List[Dict[str, Any]]
        arrangement_hash: str
        version: int

    class OptimizeRequest(BaseModel):
        """Request to optimize layout."""
        objectives: Dict[str, float] = Field(
            default_factory=dict,
            description="Optimization objectives and weights"
        )

    class OptimizeResponse(BaseModel):
        """Response from optimization operation."""
        success: bool
        design_id: str
        improvements: Dict[str, float] = {}
        update_id: str
        prev_update_id: Optional[str] = None
        arrangement_hash: str
        version: int
        message: str = ""

else:
    # Fallback dataclasses when FastAPI not available
    @dataclass
    class GenerateRequest:
        loa: float = 100.0
        beam: float = 20.0
        depth: float = 10.0
        num_decks: int = 4
        crew_capacity: int = 20
        passenger_capacity: int = 0
        ship_type: str = "general_cargo"

    @dataclass
    class GenerateResponse:
        success: bool = False
        layout_id: Optional[str] = None
        design_id: str = ""
        space_count: int = 0
        deck_count: int = 0
        total_area_m2: float = 0.0
        arrangement_hash: Optional[str] = None
        update_id: Optional[str] = None
        prev_update_id: Optional[str] = None
        version: int = 1
        errors: List[str] = field(default_factory=list)
        warnings: List[str] = field(default_factory=list)

    @dataclass
    class LayoutResponse:
        layout_id: str = ""
        design_id: str = ""
        version: int = 1
        update_id: str = ""
        prev_update_id: Optional[str] = None
        arrangement_hash: str = ""
        space_count: int = 0
        deck_count: int = 0
        total_area_m2: float = 0.0
        total_volume_m3: float = 0.0
        decks: Dict[str, Any] = field(default_factory=dict)
        metadata: Dict[str, Any] = field(default_factory=dict)

    @dataclass
    class ValidationResponse:
        is_valid: bool = False
        design_id: str = ""
        errors_count: int = 0
        warnings_count: int = 0
        issues: List[Dict[str, Any]] = field(default_factory=list)
        arrangement_hash: str = ""
        version: int = 1


# =============================================================================
# ROUTER FACTORY
# =============================================================================

def create_interior_router(
    state_integrator: Optional[InteriorStateIntegrator] = None,
) -> Any:
    """
    Create FastAPI router for interior layout endpoints.

    Args:
        state_integrator: InteriorStateIntegrator instance

    Returns:
        FastAPI APIRouter or None if FastAPI not available
    """
    if not HAS_FASTAPI:
        logger.warning("FastAPI not available, cannot create router")
        return None

    # Create state integrator if not provided
    if state_integrator is None:
        state_integrator = InteriorStateIntegrator()

    router = APIRouter(
        prefix="/api/v1/designs/{design_id}/interior",
        tags=["interior"],
    )

    # =========================================================================
    # GENERATION ENDPOINT
    # =========================================================================

    @router.post("/generate", response_model=GenerateResponse)
    async def generate_layout(
        design_id: str,
        request: GenerateRequest,
    ) -> GenerateResponse:
        """
        Generate interior layout for a design.

        Creates a new interior layout based on principal dimensions
        and ship characteristics. Includes spaces, decks, and connections.

        Args:
            design_id: Design identifier
            request: Generation parameters

        Returns:
            Generation result with layout summary
        """
        try:
            # Create generation config
            config = GenerationConfig(
                loa=request.loa,
                beam=request.beam,
                depth=request.depth,
                num_decks=request.num_decks,
                crew_capacity=request.crew_capacity,
                passenger_capacity=request.passenger_capacity,
                ship_type=request.ship_type,
            )

            # Generate layout
            generator = LayoutGenerator(config)
            result = generator.generate(design_id)

            if not result.success or not result.layout:
                return GenerateResponse(
                    success=False,
                    design_id=design_id,
                    errors=result.errors,
                )

            # Save to state
            update_id = state_integrator.save_layout(result.layout)
            layout = result.layout

            return GenerateResponse(
                success=True,
                layout_id=layout.layout_id,
                design_id=design_id,
                space_count=layout.space_count,
                deck_count=layout.deck_count,
                total_area_m2=layout.total_area,
                arrangement_hash=layout.arrangement_hash,
                update_id=layout.version_info.update_id,
                prev_update_id=layout.version_info.prev_update_id,
                version=layout.version_info.version,
                warnings=result.warnings,
            )

        except Exception as e:
            logger.error(f"Layout generation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # =========================================================================
    # LAYOUT RETRIEVAL ENDPOINT
    # =========================================================================

    @router.get("/layout", response_model=LayoutResponse)
    async def get_layout(design_id: str) -> LayoutResponse:
        """
        Get current interior layout for a design.

        Returns the complete layout including all decks, spaces,
        and connections with version tracking info.

        Args:
            design_id: Design identifier

        Returns:
            Complete layout data
        """
        layout = state_integrator.get_layout(design_id)
        if not layout:
            raise HTTPException(
                status_code=404,
                detail=f"Layout not found for design {design_id}"
            )

        return LayoutResponse(
            layout_id=layout.layout_id,
            design_id=layout.design_id,
            version=layout.version_info.version,
            update_id=layout.version_info.update_id,
            prev_update_id=layout.version_info.prev_update_id,
            arrangement_hash=layout.arrangement_hash,
            space_count=layout.space_count,
            deck_count=layout.deck_count,
            total_area_m2=layout.total_area,
            total_volume_m3=layout.total_volume,
            decks={did: d.to_dict() for did, d in layout.decks.items()},
            metadata=layout.metadata.to_dict(),
        )

    # =========================================================================
    # SPACE CREATION ENDPOINT
    # =========================================================================

    @router.post("/spaces", response_model=SpaceResponse)
    async def create_space(
        design_id: str,
        request: SpaceRequest,
    ) -> SpaceResponse:
        """
        Create a new space in the layout.

        Args:
            design_id: Design identifier
            request: Space definition

        Returns:
            Created space info with version tracking
        """
        try:
            # Convert boundary points
            points = [tuple(p) for p in request.boundary.points]

            # Create space definition
            space = SpaceDefinition(
                space_id="",  # Auto-generated
                name=request.name,
                space_type=SpaceType(request.space_type),
                category=SpaceCategory(request.category),
                boundary=SpaceBoundary(
                    points=points,
                    deck_id=request.boundary.deck_id,
                    z_min=request.boundary.z_min,
                    z_max=request.boundary.z_max,
                ),
                deck_id=request.deck_id,
                zone_id=request.zone_id,
                max_occupancy=request.max_occupancy,
                is_manned=request.is_manned,
                notes=request.notes,
            )

            # Add to layout
            update_id = state_integrator.add_space(design_id, space)

            # Get updated version info
            version_info = state_integrator.get_version_info(design_id)

            return SpaceResponse(
                success=True,
                space_id=space.space_id,
                update_id=version_info["update_id"],
                prev_update_id=version_info["prev_update_id"],
                arrangement_hash=version_info["arrangement_hash"],
                version=version_info["version"],
                message=f"Space {space.name} created",
            )

        except InteriorStateError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Space creation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # =========================================================================
    # SPACE UPDATE ENDPOINT
    # =========================================================================

    @router.put("/spaces/{space_id}", response_model=SpaceResponse)
    async def update_space(
        design_id: str,
        space_id: str,
        request: SpaceRequest,
    ) -> SpaceResponse:
        """
        Update an existing space.

        Args:
            design_id: Design identifier
            space_id: Space identifier
            request: Updated space definition

        Returns:
            Update result with version tracking
        """
        try:
            # Convert boundary points
            points = [tuple(p) for p in request.boundary.points]

            # Create updated space definition
            space = SpaceDefinition(
                space_id=space_id,
                name=request.name,
                space_type=SpaceType(request.space_type),
                category=SpaceCategory(request.category),
                boundary=SpaceBoundary(
                    points=points,
                    deck_id=request.boundary.deck_id,
                    z_min=request.boundary.z_min,
                    z_max=request.boundary.z_max,
                ),
                deck_id=request.deck_id,
                zone_id=request.zone_id,
                max_occupancy=request.max_occupancy,
                is_manned=request.is_manned,
                notes=request.notes,
            )

            # Update in layout
            update_id = state_integrator.update_space(design_id, space)

            # Get updated version info
            version_info = state_integrator.get_version_info(design_id)

            return SpaceResponse(
                success=True,
                space_id=space_id,
                update_id=version_info["update_id"],
                prev_update_id=version_info["prev_update_id"],
                arrangement_hash=version_info["arrangement_hash"],
                version=version_info["version"],
                message=f"Space {space.name} updated",
            )

        except InteriorStateError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Space update failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # =========================================================================
    # SPACE DELETION ENDPOINT
    # =========================================================================

    @router.delete("/spaces/{space_id}", response_model=SpaceResponse)
    async def delete_space(
        design_id: str,
        space_id: str,
    ) -> SpaceResponse:
        """
        Delete a space from the layout.

        Args:
            design_id: Design identifier
            space_id: Space identifier

        Returns:
            Deletion result with version tracking
        """
        try:
            update_id = state_integrator.delete_space(design_id, space_id)

            # Get updated version info
            version_info = state_integrator.get_version_info(design_id)

            return SpaceResponse(
                success=True,
                space_id=space_id,
                update_id=version_info["update_id"],
                prev_update_id=version_info["prev_update_id"],
                arrangement_hash=version_info["arrangement_hash"],
                version=version_info["version"],
                message=f"Space {space_id} deleted",
            )

        except InteriorStateError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Space deletion failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # =========================================================================
    # VALIDATION ENDPOINT
    # =========================================================================

    @router.post("/validate", response_model=ValidationResponse)
    async def validate_layout(design_id: str) -> ValidationResponse:
        """
        Validate the interior layout.

        Checks all spaces against maritime constraints and
        regulations. Returns issues with severity levels.

        Args:
            design_id: Design identifier

        Returns:
            Validation result with issues
        """
        try:
            result = state_integrator.validate_layout(design_id)
            version_info = state_integrator.get_version_info(design_id)

            if not version_info:
                raise HTTPException(
                    status_code=404,
                    detail=f"Layout not found for design {design_id}"
                )

            return ValidationResponse(
                is_valid=result.is_valid,
                design_id=design_id,
                errors_count=result.errors_count,
                warnings_count=result.warnings_count,
                issues=[i.to_dict() for i in result.issues],
                arrangement_hash=version_info["arrangement_hash"],
                version=version_info["version"],
            )

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # =========================================================================
    # OPTIMIZATION ENDPOINT
    # =========================================================================

    @router.post("/optimize", response_model=OptimizeResponse)
    async def optimize_layout(
        design_id: str,
        request: OptimizeRequest,
    ) -> OptimizeResponse:
        """
        Optimize the interior layout.

        Runs optimization algorithms to improve layout based on
        specified objectives (area efficiency, circulation, etc.).

        Args:
            design_id: Design identifier
            request: Optimization parameters

        Returns:
            Optimization result with improvements
        """
        try:
            update_id = state_integrator.optimize_layout(
                design_id,
                objectives=request.objectives,
            )

            version_info = state_integrator.get_version_info(design_id)

            if not version_info:
                raise HTTPException(
                    status_code=404,
                    detail=f"Layout not found for design {design_id}"
                )

            return OptimizeResponse(
                success=True,
                design_id=design_id,
                improvements={},  # TODO: Return actual improvements
                update_id=version_info["update_id"],
                prev_update_id=version_info["prev_update_id"],
                arrangement_hash=version_info["arrangement_hash"],
                version=version_info["version"],
                message="Layout optimization complete",
            )

        except InteriorStateError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return router
