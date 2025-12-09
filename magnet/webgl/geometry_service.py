"""
webgl/geometry_service.py - Single authoritative geometry source v1.1

Module 58: WebGL 3D Visualization
ALPHA OWNS THIS FILE.

Provides the single entry point for all geometry consumers.
Enforces authoritative geometry source with no silent fallbacks.

Addresses: FM1 (Visual/Engineering hull divergence)
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
import logging
import time

from .schema import (
    MeshData,
    SceneData,
    SchemaMetadata,
    GeometryMode,
    LODLevel,
    MaterialDef,
    StructureSceneData,
    HydrostaticSceneData,
)
from .interfaces import (
    GeometryInputProvider,
    GeometryReferenceModelProvider,
    StateGeometryAdapter,
    HullGeneratorAdapter,
    HullGeometryData,
)
from .errors import (
    GeometryError,
    GeometryUnavailableError,
    MeshGenerationError,
    LODExceededError,
    GeometryValidationError,
)
from .config import (
    GeometryConfig,
    LODConfig,
    TessellationConfig,
    DEFAULT_GEOMETRY_CONFIG,
    LOD_CONFIGS,
)

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger("webgl.geometry_service")


# =============================================================================
# GEOMETRY SERVICE
# =============================================================================

class GeometryService:
    """
    Single entry point for all geometry consumers.

    v1.1: Enforces single authoritative source, no silent fallbacks.

    This service:
    - Provides hull geometry from the authoritative GRM
    - NEVER silently falls back to approximations
    - Requires explicit allow_visual_only flag for approximations
    - Tracks geometry_mode in all responses
    - Integrates with EventBus for change notifications
    """

    def __init__(
        self,
        state_manager: "StateManager",
        config: Optional[GeometryConfig] = None,
    ):
        self._sm = state_manager
        self._config = config or DEFAULT_GEOMETRY_CONFIG

        # Create adapters
        self._inputs = StateGeometryAdapter(state_manager)
        self._grm_provider = HullGeneratorAdapter(state_manager)

        # Cache for generated meshes
        self._mesh_cache: Dict[str, Tuple[MeshData, GeometryMode, float]] = {}

        logger.info("GeometryService initialized")

    # =========================================================================
    # MAIN API
    # =========================================================================

    def get_hull_geometry(
        self,
        design_id: Optional[str] = None,
        lod: LODLevel = LODLevel.MEDIUM,
        allow_visual_only: bool = False,
    ) -> Tuple[MeshData, GeometryMode]:
        """
        Get hull geometry from authoritative source.

        Args:
            design_id: Design identifier (uses current if None)
            lod: Level of detail
            allow_visual_only: If True, fall back to approximation when GRM unavailable

        Returns:
            Tuple of (mesh_data, mode_used)

        Raises:
            GeometryUnavailableError: If GRM unavailable and allow_visual_only=False
            LODExceededError: If requested LOD exceeds resource limits
            MeshGenerationError: If mesh generation fails
        """
        design_id = design_id or self._inputs.design_id
        start_time = time.time()

        # Validate LOD
        actual_lod = self._config.validate_lod(lod)
        if actual_lod != lod:
            logger.warning(
                f"LOD downgraded from {lod.value} to {actual_lod.value} due to resource limits"
            )
            if not allow_visual_only:
                raise LODExceededError(
                    requested=lod.value,
                    max_allowed=actual_lod.value,
                )
            lod = actual_lod

        # Check cache
        cache_key = f"{design_id}:{lod.value}"
        if self._config.enable_geometry_cache and cache_key in self._mesh_cache:
            mesh, mode, cached_time = self._mesh_cache[cache_key]
            cache_age = time.time() - cached_time
            if cache_age < self._config.resource_limits.cache_ttl_seconds:
                logger.debug(f"Cache hit for {cache_key} (age: {cache_age:.1f}s)")
                return mesh, mode

        # Try authoritative source
        try:
            hull_geom = self._grm_provider.get_hull_geometry(design_id)
            mesh = self._tessellate_grm(hull_geom, lod)
            mode = GeometryMode.AUTHORITATIVE

            # Validate mesh
            from .schema import validate_mesh_data
            issues = validate_mesh_data(mesh)
            if issues:
                logger.warning(f"Mesh validation issues: {issues}")
                if not allow_visual_only:
                    raise GeometryValidationError(issues=issues, design_id=design_id)

            # Cache result
            if self._config.enable_geometry_cache:
                self._mesh_cache[cache_key] = (mesh, mode, time.time())

            elapsed = time.time() - start_time
            logger.info(
                f"Generated authoritative hull geometry for {design_id} "
                f"(LOD: {lod.value}, vertices: {mesh.vertex_count}, time: {elapsed:.2f}s)"
            )

            # Emit event
            self._emit_geometry_ready(design_id, mesh, mode, lod)

            return mesh, mode

        except GeometryUnavailableError:
            if allow_visual_only:
                logger.warning(
                    f"GRM unavailable for {design_id}, using visual-only approximation. "
                    "Results may not match engineering calculations."
                )
                mesh = self._generate_visual_approximation(design_id, lod)
                mode = GeometryMode.VISUAL_ONLY

                # Cache result
                if self._config.enable_geometry_cache:
                    self._mesh_cache[cache_key] = (mesh, mode, time.time())

                elapsed = time.time() - start_time
                logger.info(
                    f"Generated visual-only hull geometry for {design_id} "
                    f"(LOD: {lod.value}, vertices: {mesh.vertex_count}, time: {elapsed:.2f}s)"
                )

                # Emit event with visual-only flag
                self._emit_geometry_ready(design_id, mesh, mode, lod)

                return mesh, mode
            else:
                # Re-raise without fallback
                raise

        except Exception as e:
            logger.exception(f"Hull geometry generation failed: {e}")
            raise MeshGenerationError(
                stage="hull_generation",
                reason=str(e),
                design_id=design_id,
            )

    def get_scene(
        self,
        design_id: Optional[str] = None,
        lod: LODLevel = LODLevel.MEDIUM,
        include_structure: bool = False,
        include_hydrostatics: bool = False,
        allow_visual_only: bool = False,
    ) -> SceneData:
        """
        Get complete scene data for 3D rendering.

        Args:
            design_id: Design identifier
            lod: Level of detail
            include_structure: Include structural visualization
            include_hydrostatics: Include hydrostatic visualization
            allow_visual_only: Allow visual-only approximation

        Returns:
            SceneData with all requested components
        """
        design_id = design_id or self._inputs.design_id

        # Get hull geometry
        hull_mesh, geometry_mode = self.get_hull_geometry(
            design_id=design_id,
            lod=lod,
            allow_visual_only=allow_visual_only,
        )

        # Get version info
        version_id = self._grm_provider.get_geometry_version(design_id) or ""

        # Build scene
        scene = SceneData(
            schema=SchemaMetadata(),
            design_id=design_id,
            version_id=version_id,
            geometry_mode=geometry_mode,
            hull=hull_mesh,
            materials=self._get_default_materials(),
            metadata={
                "lod": lod.value,
                "generated_at": time.time(),
            },
        )

        # Add deck if available
        try:
            deck_mesh = self._generate_deck_mesh(lod)
            if deck_mesh:
                scene.deck = deck_mesh
        except Exception as e:
            logger.debug(f"Deck mesh not available: {e}")

        # Add transom if available
        try:
            transom_mesh = self._generate_transom_mesh(lod)
            if transom_mesh:
                scene.transom = transom_mesh
        except Exception as e:
            logger.debug(f"Transom mesh not available: {e}")

        # Add structure if requested
        if include_structure:
            try:
                from .structure_mesh import StructureMeshBuilder
                builder = StructureMeshBuilder(self._sm)
                scene.structure = builder.build(lod)
            except Exception as e:
                logger.warning(f"Structure mesh generation failed: {e}")

        # Add hydrostatics if requested
        if include_hydrostatics:
            try:
                from .hydrostatic_visuals import HydrostaticVisualBuilder
                builder = HydrostaticVisualBuilder(self._sm)
                scene.hydrostatics = builder.build(lod)
            except Exception as e:
                logger.warning(f"Hydrostatic visual generation failed: {e}")

        return scene

    def invalidate_cache(self, design_id: Optional[str] = None) -> None:
        """
        Invalidate geometry cache.

        Args:
            design_id: Invalidate for specific design, or all if None
        """
        if design_id:
            # Invalidate all LOD levels for design
            keys_to_remove = [k for k in self._mesh_cache if k.startswith(f"{design_id}:")]
            for key in keys_to_remove:
                del self._mesh_cache[key]

            # Also invalidate GRM cache
            self._grm_provider.invalidate(design_id)

            logger.info(f"Invalidated geometry cache for {design_id}")
        else:
            self._mesh_cache.clear()
            self._grm_provider.invalidate_all()
            logger.info("Invalidated all geometry cache")

    # =========================================================================
    # TESSELLATION
    # =========================================================================

    def _tessellate_grm(self, hull_geom: HullGeometryData, lod: LODLevel) -> MeshData:
        """
        Tessellate GRM to triangle mesh at specified LOD.

        Uses the HullGeometryPipeline for actual tessellation.
        """
        from .geometry_pipeline import HullGeometryPipeline

        # Get tessellation config for LOD
        tess_config = TessellationConfig.from_lod(lod)
        lod_config = self._config.get_lod_config(lod)

        # Create pipeline and tessellate
        pipeline = HullGeometryPipeline(
            hull_geom=hull_geom,
            config=tess_config,
        )

        mesh = pipeline.tessellate()
        mesh.mesh_id = f"{hull_geom.design_id}_hull_{lod.value}"

        # Validate resource limits
        if mesh.vertex_count > lod_config.max_vertices:
            logger.warning(
                f"Mesh exceeds vertex limit ({mesh.vertex_count} > {lod_config.max_vertices}), "
                f"simplification may be needed"
            )

        return mesh

    def _generate_visual_approximation(self, design_id: str, lod: LODLevel) -> MeshData:
        """
        Generate parametric approximation for visual-only mode.

        This uses simplified parametric hull forms when the authoritative
        geometry is not available. Results are flagged as VISUAL_ONLY.
        """
        from .geometry_pipeline import HullGeometryPipeline

        # Get tessellation config
        tess_config = TessellationConfig.from_lod(lod)

        # Create pipeline with inputs (not GRM)
        pipeline = HullGeometryPipeline.from_inputs(
            inputs=self._inputs,
            config=tess_config,
        )

        mesh = pipeline.tessellate_parametric()
        mesh.mesh_id = f"{design_id}_hull_{lod.value}_visual"

        return mesh

    def _generate_deck_mesh(self, lod: LODLevel) -> Optional[MeshData]:
        """Generate deck surface mesh."""
        from .mesh_builder import MeshBuilder

        tess_config = TessellationConfig.from_lod(lod)
        if not tess_config.include_deck:
            return None

        # Simple deck generation
        builder = MeshBuilder()

        loa = self._inputs.loa
        beam = self._inputs.beam
        depth = self._inputs.depth
        camber = tess_config.deck_camber_height

        # Generate deck vertices (simple rectangular with camber)
        sections = tess_config.sections_count
        points_per_section = 5

        for i in range(sections + 1):
            x = (i / sections) * loa
            for j in range(points_per_section):
                y = (j / (points_per_section - 1) - 0.5) * beam
                # Camber curve
                y_norm = abs(y) / (beam / 2)
                z = depth + camber * (1 - y_norm * y_norm)
                builder.add_vertex(x, y, z)

        # Generate faces
        for i in range(sections):
            for j in range(points_per_section - 1):
                v0 = i * points_per_section + j
                v1 = v0 + 1
                v2 = v0 + points_per_section
                v3 = v2 + 1
                builder.add_quad(v0, v1, v3, v2)

        mesh = builder.build()
        mesh.mesh_id = f"deck_{lod.value}"
        return mesh

    def _generate_transom_mesh(self, lod: LODLevel) -> Optional[MeshData]:
        """Generate transom surface mesh."""
        from .mesh_builder import MeshBuilder

        tess_config = TessellationConfig.from_lod(lod)
        if not tess_config.include_transom:
            return None

        builder = MeshBuilder()

        beam = self._inputs.beam
        draft = self._inputs.draft
        depth = self._inputs.depth
        transom_ratio = self._inputs.transom_width_ratio
        deadrise = self._inputs.deadrise_deg

        import math
        deadrise_rad = math.radians(deadrise)

        # Transom at x=0 (AP)
        x = 0.0
        transom_beam = beam * transom_ratio

        # Generate transom profile
        points = tess_config.circumferential_points
        for i in range(points + 1):
            y = (i / points - 0.5) * transom_beam
            y_norm = abs(y) / (transom_beam / 2) if transom_beam > 0 else 0

            # Z varies from keel to deck with deadrise
            for j in range(3):  # keel, waterline, deck
                if j == 0:
                    z = -draft + abs(y) * math.tan(deadrise_rad)
                elif j == 1:
                    z = 0
                else:
                    z = depth
                builder.add_vertex(x, y, z)

        # Generate faces
        for i in range(points):
            for j in range(2):
                v0 = i * 3 + j
                v1 = v0 + 1
                v2 = v0 + 3
                v3 = v2 + 1
                builder.add_quad(v0, v2, v3, v1)

        mesh = builder.build()
        mesh.mesh_id = f"transom_{lod.value}"
        return mesh

    # =========================================================================
    # MATERIALS
    # =========================================================================

    def _get_default_materials(self) -> List[MaterialDef]:
        """Get default material definitions."""
        from .materials import (
            DEFAULT_HULL_MATERIAL,
            DEFAULT_STRUCTURE_MATERIAL,
            DEFAULT_WATERLINE_MATERIAL,
        )
        return [
            DEFAULT_HULL_MATERIAL,
            DEFAULT_STRUCTURE_MATERIAL,
            DEFAULT_WATERLINE_MATERIAL,
        ]

    # =========================================================================
    # EVENTS
    # =========================================================================

    def _emit_geometry_ready(
        self,
        design_id: str,
        mesh: MeshData,
        mode: GeometryMode,
        lod: LODLevel,
    ) -> None:
        """Emit geometry ready event."""
        if not self._config.emit_geometry_events:
            return

        try:
            from magnet.ui.events import event_bus, EventType

            event_bus.emit_simple(
                EventType.GEOMETRY_GENERATED,
                source="webgl.geometry_service",
                design_id=design_id,
                geometry_mode=mode.value,
                lod=lod.value,
                vertex_count=mesh.vertex_count,
                face_count=mesh.face_count,
            )
        except Exception as e:
            logger.debug(f"Could not emit geometry event: {e}")
