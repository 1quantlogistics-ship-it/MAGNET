"""
webgl/api_endpoints.py - FastAPI endpoints for geometry API v1.1

Module 58: WebGL 3D Visualization
ALPHA OWNS THIS FILE.

Provides REST API endpoints for geometry access, section cuts, and export.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import logging

# Conditional FastAPI import
try:
    from fastapi import APIRouter, HTTPException, Query, Path, Response, BackgroundTasks
    from fastapi.responses import StreamingResponse, JSONResponse
    from pydantic import BaseModel, Field
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    # Stub classes for type checking
    class APIRouter:
        def __init__(self, **kwargs): pass
        def get(self, *args, **kwargs): return lambda f: f
        def post(self, *args, **kwargs): return lambda f: f
    class BaseModel: pass
    class Field:
        def __init__(self, **kwargs): pass

from .schema import GeometryMode, LODLevel
from .errors import (
    GeometryUnavailableError,
    GeometryParameterError,
    MeshGenerationError,
    ExportError,
    SectionCutError,
    geometry_error_response,
)

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger("webgl.api_endpoints")


# =============================================================================
# API MODELS (Pydantic)
# =============================================================================

if HAS_FASTAPI:
    class GeometryRequest(BaseModel):
        """Request model for geometry operations."""
        lod: str = Field(default="medium", description="Level of detail: low, medium, high, ultra")
        allow_visual_only: bool = Field(default=False, description="Allow visual-only fallback")
        include_structure: bool = Field(default=False, description="Include structural visualization")
        include_hydrostatics: bool = Field(default=False, description="Include hydrostatic visuals")

    class SectionCutRequest(BaseModel):
        """Request model for section cuts."""
        plane: str = Field(description="Section plane: transverse, longitudinal, waterplane")
        position: float = Field(description="Position along the cut axis")
        lod: str = Field(default="medium", description="Level of detail")

    class ExportRequest(BaseModel):
        """Request model for geometry export."""
        format: str = Field(description="Export format: gltf, glb, stl, stl_ascii, obj")
        lod: str = Field(default="medium", description="Level of detail")
        include_structure: bool = Field(default=False, description="Include structure in export")

    class GeometryResponse(BaseModel):
        """Response model for geometry data."""
        success: bool
        geometry_mode: str
        lod: str
        vertex_count: int
        face_count: int
        scene_id: str
        schema_version: str
        data: Optional[Dict[str, Any]] = None
        error: Optional[str] = None

    class SectionResponse(BaseModel):
        """Response model for section cut."""
        success: bool
        plane: str
        position: float
        points: List[List[float]]
        closed: bool
        area: Optional[float] = None
        error: Optional[str] = None

    class ExportResponse(BaseModel):
        """Response model for export metadata."""
        success: bool
        format: str
        file_size_bytes: int
        vertex_count: int
        face_count: int
        export_id: str
        error: Optional[str] = None
else:
    # Stub classes when FastAPI not available
    class GeometryRequest: pass
    class SectionCutRequest: pass
    class ExportRequest: pass
    class GeometryResponse: pass
    class SectionResponse: pass
    class ExportResponse: pass


# =============================================================================
# API ROUTER
# =============================================================================

router = APIRouter(
    prefix="/api/v1/designs",
    tags=["geometry", "3d"],
)


# =============================================================================
# STATE MANAGER ACCESS
# =============================================================================

_state_manager_getter = None


def set_state_manager_getter(getter):
    """Set the function used to get StateManager for a design."""
    global _state_manager_getter
    _state_manager_getter = getter


def get_state_manager(design_id: str) -> "StateManager":
    """Get StateManager for a design."""
    if _state_manager_getter is None:
        raise HTTPException(
            status_code=500,
            detail="State manager not configured",
        )
    return _state_manager_getter(design_id)


# =============================================================================
# GEOMETRY ENDPOINTS
# =============================================================================

@router.get("/{design_id}/3d/hull")
async def get_hull_geometry(
    design_id: str = Path(..., description="Design ID"),
    lod: str = Query("medium", description="Level of detail"),
    allow_visual_only: bool = Query(False, description="Allow visual-only fallback"),
):
    """
    Get hull geometry mesh.

    Returns authoritative geometry from GRM when available.
    If allow_visual_only=True and GRM unavailable, returns parametric approximation.

    Returns:
        JSON with mesh data including vertices, indices, normals.
    """
    try:
        from .geometry_service import GeometryService
        from .interfaces import StateGeometryAdapter

        sm = get_state_manager(design_id)
        adapter = StateGeometryAdapter(sm)

        service = GeometryService(
            input_provider=adapter,
            design_id=design_id,
        )

        lod_level = LODLevel(lod) if lod in [l.value for l in LODLevel] else LODLevel.MEDIUM

        mesh, mode = service.get_hull_geometry(
            lod=lod_level,
            allow_visual_only=allow_visual_only,
        )

        # Compute hull_hash for cache invalidation tracking
        hull_hash = None
        try:
            from magnet.contracts.domain_hashes import GeometryHashProvider
            hash_provider = GeometryHashProvider(sm)
            hull_hash = hash_provider.compute_hash(design_id)
        except Exception as e:
            logger.debug(f"Could not compute hull_hash: {e}")

        return {
            "success": True,
            "geometry_mode": mode.value,
            "lod": lod,
            "vertex_count": mesh.vertex_count,
            "face_count": mesh.face_count,
            "mesh_id": mesh.mesh_id,
            "hull_hash": hull_hash,
            "data": mesh.to_dict(),
        }

    except GeometryUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=geometry_error_response(e),
        )
    except GeometryParameterError as e:
        raise HTTPException(
            status_code=400,
            detail=geometry_error_response(e),
        )
    except Exception as e:
        logger.error(f"Hull geometry error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "code": "GEOM_999"},
        )


@router.get("/{design_id}/3d/scene")
async def get_scene(
    design_id: str = Path(..., description="Design ID"),
    lod: str = Query("medium", description="Level of detail"),
    include_structure: bool = Query(False, description="Include structure"),
    include_hydrostatics: bool = Query(False, description="Include hydrostatics"),
    allow_visual_only: bool = Query(False, description="Allow visual-only fallback"),
):
    """
    Get complete 3D scene data.

    Returns SceneData with hull, deck, structure, and materials.
    """
    try:
        from .geometry_service import GeometryService
        from .interfaces import StateGeometryAdapter

        sm = get_state_manager(design_id)
        adapter = StateGeometryAdapter(sm)

        service = GeometryService(
            input_provider=adapter,
            design_id=design_id,
        )

        lod_level = LODLevel(lod) if lod in [l.value for l in LODLevel] else LODLevel.MEDIUM

        scene = service.get_scene(
            lod=lod_level,
            include_structure=include_structure,
            include_hydrostatics=include_hydrostatics,
            allow_visual_only=allow_visual_only,
        )

        return {
            "success": True,
            "geometry_mode": scene.geometry_mode.value if hasattr(scene.geometry_mode, 'value') else scene.geometry_mode,
            "lod": scene.lod,
            "scene_id": scene.scene_id,
            "version": scene.version,
            "schema_version": "1.1.0",
            "data": scene.to_dict(),
        }

    except GeometryUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=geometry_error_response(e),
        )
    except Exception as e:
        logger.error(f"Scene error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "code": "GEOM_999"},
        )


@router.get("/{design_id}/3d/binary")
async def get_binary_geometry(
    design_id: str = Path(..., description="Design ID"),
    lod: str = Query("medium", description="Level of detail"),
):
    """
    Get hull geometry in optimized binary format.

    Returns binary data with MNET format header for efficient transmission.
    """
    try:
        from .geometry_service import GeometryService
        from .interfaces import StateGeometryAdapter
        from .serializer import serialize_mesh

        sm = get_state_manager(design_id)
        adapter = StateGeometryAdapter(sm)

        service = GeometryService(
            input_provider=adapter,
            design_id=design_id,
        )

        lod_level = LODLevel(lod) if lod in [l.value for l in LODLevel] else LODLevel.MEDIUM

        mesh, mode = service.get_hull_geometry(
            lod=lod_level,
            allow_visual_only=True,
        )

        binary_data = serialize_mesh(mesh, compress=True)

        return Response(
            content=binary_data,
            media_type="application/octet-stream",
            headers={
                "X-Geometry-Mode": mode.value,
                "X-Vertex-Count": str(mesh.vertex_count),
                "X-Face-Count": str(mesh.face_count),
                "X-Schema-Version": "1.1.0",
            },
        )

    except Exception as e:
        logger.error(f"Binary geometry error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e)},
        )


# =============================================================================
# SECTION CUT ENDPOINTS
# =============================================================================

@router.post("/{design_id}/3d/section")
async def create_section_cut(
    design_id: str = Path(..., description="Design ID"),
    request: SectionCutRequest = None,
):
    """
    Create a section cut through the hull.

    Supported planes:
    - transverse: Cross-section at longitudinal position X
    - longitudinal: Vertical section at transverse position Y
    - waterplane: Horizontal section at vertical position Z
    """
    if request is None:
        raise HTTPException(status_code=400, detail="Request body required")

    try:
        from .geometry_service import GeometryService
        from .interfaces import StateGeometryAdapter
        from .section_cuts import SectionPlane

        sm = get_state_manager(design_id)
        adapter = StateGeometryAdapter(sm)

        service = GeometryService(
            input_provider=adapter,
            design_id=design_id,
        )

        # Map plane string to enum
        plane_map = {
            "transverse": SectionPlane.TRANSVERSE,
            "longitudinal": SectionPlane.LONGITUDINAL,
            "waterplane": SectionPlane.WATERPLANE,
        }

        plane = plane_map.get(request.plane.lower())
        if not plane:
            raise GeometryParameterError(
                message=f"Invalid section plane: {request.plane}",
                parameter="plane",
                valid_values=list(plane_map.keys()),
            )

        lod_level = LODLevel(request.lod) if request.lod in [l.value for l in LODLevel] else LODLevel.MEDIUM

        result = service.get_section_cut(
            plane=plane,
            position=request.position,
            lod=lod_level,
        )

        return {
            "success": True,
            "plane": request.plane,
            "position": request.position,
            "points": result.points,
            "closed": result.closed,
            "area": result.area,
        }

    except (GeometryParameterError, SectionCutError) as e:
        raise HTTPException(
            status_code=400,
            detail=geometry_error_response(e),
        )
    except Exception as e:
        logger.error(f"Section cut error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e)},
        )


@router.get("/{design_id}/3d/sections/transverse")
async def get_transverse_sections(
    design_id: str = Path(..., description="Design ID"),
    count: int = Query(10, description="Number of sections"),
    lod: str = Query("medium", description="Level of detail"),
):
    """
    Get multiple transverse sections evenly distributed along hull length.
    """
    try:
        from .geometry_service import GeometryService
        from .interfaces import StateGeometryAdapter
        from .section_cuts import SectionPlane

        sm = get_state_manager(design_id)
        adapter = StateGeometryAdapter(sm)

        service = GeometryService(
            input_provider=adapter,
            design_id=design_id,
        )

        lod_level = LODLevel(lod) if lod in [l.value for l in LODLevel] else LODLevel.MEDIUM

        # Get hull length from adapter
        loa = adapter.loa

        sections = []
        for i in range(count):
            x = loa * (i + 1) / (count + 1)
            try:
                result = service.get_section_cut(
                    plane=SectionPlane.TRANSVERSE,
                    position=x,
                    lod=lod_level,
                )
                sections.append({
                    "position": x,
                    "points": result.points,
                    "closed": result.closed,
                    "area": result.area,
                })
            except Exception as e:
                logger.warning(f"Section at x={x} failed: {e}")

        return {
            "success": True,
            "count": len(sections),
            "sections": sections,
        }

    except Exception as e:
        logger.error(f"Transverse sections error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e)},
        )


# =============================================================================
# EXPORT ENDPOINTS
# =============================================================================

@router.get("/{design_id}/3d/export/{format}")
async def export_geometry(
    design_id: str = Path(..., description="Design ID"),
    format: str = Path(..., description="Export format: gltf, glb, stl, obj"),
    lod: str = Query("medium", description="Level of detail"),
    include_structure: bool = Query(False, description="Include structure"),
):
    """
    Export geometry to specified format.

    Supported formats:
    - gltf: JSON format with embedded buffer
    - glb: Binary glTF (recommended for production)
    - stl: Binary STL
    - stl_ascii: ASCII STL
    - obj: Wavefront OBJ

    Returns binary file with appropriate Content-Type.
    """
    try:
        from .geometry_service import GeometryService
        from .interfaces import StateGeometryAdapter
        from .exporter import GeometryExporter, ExportFormat

        sm = get_state_manager(design_id)
        adapter = StateGeometryAdapter(sm)

        service = GeometryService(
            input_provider=adapter,
            design_id=design_id,
        )

        # Map format string to enum
        format_map = {
            "gltf": ExportFormat.GLTF,
            "glb": ExportFormat.GLB,
            "stl": ExportFormat.STL,
            "stl_ascii": ExportFormat.STL_ASCII,
            "obj": ExportFormat.OBJ,
        }

        export_format = format_map.get(format.lower())
        if not export_format:
            raise ExportError(
                message=f"Unsupported export format: {format}",
                format=format,
                design_id=design_id,
            )

        lod_level = LODLevel(lod) if lod in [l.value for l in LODLevel] else LODLevel.MEDIUM

        # Get scene with optional structure
        scene = service.get_scene(
            lod=lod_level,
            include_structure=include_structure,
            allow_visual_only=True,
        )

        # Export
        exporter = GeometryExporter(design_id=design_id)
        result = exporter.export_scene(
            scene=scene,
            format=export_format,
            include_structure=include_structure,
        )

        if not result.success:
            raise ExportError(
                message=result.errors[0] if result.errors else "Export failed",
                format=format,
                design_id=design_id,
            )

        # Content types
        content_types = {
            ExportFormat.GLTF: "model/gltf+json",
            ExportFormat.GLB: "model/gltf-binary",
            ExportFormat.STL: "model/stl",
            ExportFormat.STL_ASCII: "model/stl",
            ExportFormat.OBJ: "model/obj",
        }

        filename = f"{design_id}_hull{result.file_extension}"

        return Response(
            content=result.data,
            media_type=content_types.get(export_format, "application/octet-stream"),
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Export-Id": result.metadata.export_id,
                "X-Geometry-Mode": result.metadata.geometry_mode,
                "X-Vertex-Count": str(result.metadata.vertex_count),
                "X-Face-Count": str(result.metadata.face_count),
                "X-Schema-Version": result.metadata.schema_version,
            },
        )

    except ExportError as e:
        raise HTTPException(
            status_code=400,
            detail=geometry_error_response(e),
        )
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e)},
        )


@router.post("/{design_id}/3d/export")
async def export_with_options(
    design_id: str = Path(..., description="Design ID"),
    request: ExportRequest = None,
    background_tasks: BackgroundTasks = None,
):
    """
    Export geometry with detailed options.

    Returns export metadata immediately. For large exports, use background processing.
    """
    if request is None:
        raise HTTPException(status_code=400, detail="Request body required")

    try:
        from .geometry_service import GeometryService
        from .interfaces import StateGeometryAdapter
        from .exporter import GeometryExporter, ExportFormat

        format_map = {
            "gltf": ExportFormat.GLTF,
            "glb": ExportFormat.GLB,
            "stl": ExportFormat.STL,
            "stl_ascii": ExportFormat.STL_ASCII,
            "obj": ExportFormat.OBJ,
        }

        export_format = format_map.get(request.format.lower())
        if not export_format:
            raise ExportError(
                message=f"Unsupported format: {request.format}",
                format=request.format,
                design_id=design_id,
            )

        sm = get_state_manager(design_id)
        adapter = StateGeometryAdapter(sm)

        service = GeometryService(
            input_provider=adapter,
            design_id=design_id,
        )

        lod_level = LODLevel(request.lod) if request.lod in [l.value for l in LODLevel] else LODLevel.MEDIUM

        scene = service.get_scene(
            lod=lod_level,
            include_structure=request.include_structure,
            allow_visual_only=True,
        )

        exporter = GeometryExporter(design_id=design_id)
        result = exporter.export_scene(
            scene=scene,
            format=export_format,
            include_structure=request.include_structure,
        )

        if not result.success:
            return {
                "success": False,
                "error": result.errors[0] if result.errors else "Export failed",
            }

        return {
            "success": True,
            "format": request.format,
            "file_size_bytes": result.metadata.file_size_bytes,
            "vertex_count": result.metadata.vertex_count,
            "face_count": result.metadata.face_count,
            "export_id": result.metadata.export_id,
            "metadata": result.metadata.to_dict(),
        }

    except Exception as e:
        logger.error(f"Export with options error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e)},
        )


# =============================================================================
# METADATA ENDPOINTS
# =============================================================================

@router.get("/{design_id}/3d/info")
async def get_geometry_info(
    design_id: str = Path(..., description="Design ID"),
):
    """
    Get geometry status and metadata without fetching full mesh data.
    """
    try:
        from .geometry_service import GeometryService
        from .interfaces import StateGeometryAdapter
        from .dependency_integration import get_artifact_registry

        sm = get_state_manager(design_id)
        adapter = StateGeometryAdapter(sm)

        registry = get_artifact_registry()
        valid_artifacts = registry.get_valid_artifacts(design_id)

        # Check if authoritative geometry available
        try:
            from .interfaces import HullGeneratorAdapter
            grm_adapter = HullGeneratorAdapter()
            has_grm = grm_adapter.has_geometry(design_id)
        except Exception:
            has_grm = False

        return {
            "design_id": design_id,
            "has_grm_geometry": has_grm,
            "cached_artifacts": len(valid_artifacts),
            "input_parameters": {
                "loa": adapter.loa,
                "lwl": adapter.lwl,
                "beam": adapter.beam,
                "draft": adapter.draft,
                "depth": adapter.depth,
            },
            "supported_lods": [l.value for l in LODLevel],
            "supported_exports": ["gltf", "glb", "stl", "stl_ascii", "obj"],
            "schema_version": "1.1.0",
        }

    except Exception as e:
        logger.error(f"Geometry info error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e)},
        )


@router.delete("/{design_id}/3d/cache")
async def clear_geometry_cache(
    design_id: str = Path(..., description="Design ID"),
):
    """
    Clear cached geometry for a design.

    Forces regeneration on next request.
    """
    try:
        from .dependency_integration import get_artifact_registry

        registry = get_artifact_registry()
        registry.clear_design(design_id)

        return {
            "success": True,
            "design_id": design_id,
            "message": "Geometry cache cleared",
        }

    except Exception as e:
        logger.error(f"Clear cache error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e)},
        )


# =============================================================================
# ROUTER FACTORY
# =============================================================================

def create_geometry_router(state_manager_getter=None) -> APIRouter:
    """
    Create geometry API router with configured state manager access.

    Args:
        state_manager_getter: Function that takes design_id and returns StateManager

    Returns:
        Configured APIRouter
    """
    if state_manager_getter:
        set_state_manager_getter(state_manager_getter)

    return router
