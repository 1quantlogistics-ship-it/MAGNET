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
from dataclasses import dataclass, asdict
import logging
import time

from magnet.core.dataclasses import SceneReceipt
from magnet.core.turn_contracts import sha256_hex

from .schema import (
    MeshData,
    SceneData,
    SchemaMetadata,
    GeometryMode,
    SimulationIntegrity,
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
    DesignLanguageAdapter,
    CompositeGeometryProvider,
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
        # IMPORTANT: Prefer enum-free design-language compilation whenever resources exist.
        # The legacy hull generator is only a fallback for designs with no primitives.
        self._grm_provider = CompositeGeometryProvider(
            design_language=DesignLanguageAdapter(state_manager),
            legacy=HullGeneratorAdapter(state_manager),
            state_manager=state_manager,
        )

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

        # Check cache (versioned)
        design_version = self._sm.get("design_version", 0) if hasattr(self._sm, "get") else 0
        cache_key = f"{design_id}:{design_version}:{lod.value}"
        if self._config.enable_geometry_cache and cache_key in self._mesh_cache:
            mesh, mode, cached_time = self._mesh_cache[cache_key]
            cache_age = time.time() - cached_time
            if cache_age < self._config.resource_limits.cache_ttl_seconds:
                logger.debug(f"Cache hit for {cache_key} (age: {cache_age:.1f}s)")
                return mesh, mode

        # Try authoritative source
        try:
            hull_geom = self._grm_provider.get_hull_geometry(design_id, lod=lod)
            logger.info(f"[AUTHORITATIVE] Hull geometry generated for {design_id}")
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
                f"[AUTHORITATIVE] Tessellated {design_id} "
                f"(LOD: {lod.value}, vertices: {mesh.vertex_count}, time: {elapsed:.2f}s)"
            )

            # Emit event
            self._emit_geometry_ready(design_id, mesh, mode, lod)

            return mesh, mode

        except GeometryUnavailableError as e:
            logger.warning(f"[VISUAL-ONLY] GRM unavailable for {design_id}: {e}")

            if not allow_visual_only:
                logger.error(f"[BLOCKED] Visual-only not permitted, raising error")
                raise

            logger.warning(f"[FALLBACK] Using visual-only approximation for {design_id}")
            mesh = self._generate_visual_approximation(design_id, lod)
            mode = GeometryMode.VISUAL_ONLY

            # Cache result
            if self._config.enable_geometry_cache:
                self._mesh_cache[cache_key] = (mesh, mode, time.time())

            elapsed = time.time() - start_time
            logger.info(
                f"[VISUAL-ONLY] Tessellated {design_id} "
                f"(LOD: {lod.value}, vertices: {mesh.vertex_count}, time: {elapsed:.2f}s)"
            )

            # Emit event with visual-only flag
            self._emit_geometry_ready(design_id, mesh, mode, lod)

            return mesh, mode

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

        # Build authoritative hull geometry + meshes.
        # For multi-body designs, we must tessellate PER BODY to avoid stitching.
        hull_meshes = None
        geometry_mode = GeometryMode.AUTHORITATIVE
        simulation_integrity = SimulationIntegrity.APPROXIMATE
        hull_mesh = None
        integrity_reason = None
        try:
            hull_geom = self._grm_provider.get_hull_geometry(design_id, lod=lod)
            geometry_mode = GeometryMode.AUTHORITATIVE
            simulation_integrity = SimulationIntegrity.AUTHORITATIVE

            # -----------------------------------------------------------------
            # Truthfulness: detect stale physics vs current geometry edits.
            # - If physics has never been validated, do not claim AUTHORITATIVE.
            # - If physics was validated for a different design_version, the system is DECOUPLED.
            # -----------------------------------------------------------------
            try:
                dv = self._sm.get("design_version")
                pv = self._sm.get("kernel.physics_last_validated_version")
                if pv is None:
                    simulation_integrity = SimulationIntegrity.APPROXIMATE
                    integrity_reason = "missing_physics"
                elif dv is not None and int(pv) != int(dv):
                    simulation_integrity = SimulationIntegrity.DECOUPLED
                    integrity_reason = "stale_physics"
            except Exception:
                pass

            # Panelized integrity ladder hardening:
            # Panelized surfaces MUST have same-version hydrostatics, otherwise we fail closed to DECOUPLED.
            try:
                surface_definition = (getattr(hull_geom, "metadata", {}) or {}).get("surface_definition")
                if surface_definition == "panelized":
                    dv = self._sm.get("design_version")
                    hv = self._sm.get("kernel.hydrostatics_last_validated_version")
                    if hv is None or dv is None or int(hv) != int(dv):
                        simulation_integrity = SimulationIntegrity.DECOUPLED
                        integrity_reason = "missing_hydrostatics_for_panelized"
            except Exception:
                pass

            # Partition by body_id if present; otherwise keep single hull mesh.
            from .geometry_pipeline import HullGeometryPipeline, TessellationConfig
            tess_config = TessellationConfig.from_lod(lod)
            pipeline = HullGeometryPipeline(hull_geom=hull_geom, config=tess_config)
            # Truthfulness: panelized surfaces MUST use faceted tessellation.
            surface_definition = None
            try:
                surface_definition = (getattr(hull_geom, "metadata", {}) or {}).get("surface_definition")
            except Exception:
                surface_definition = None

            if surface_definition == "panelized":
                # Phase 2: hard-gate planarity (panelized surfaces must be developable-ish)
                try:
                    from magnet.kernel.validators.planarity import PlanarityGateError, _compute_quad_warp_factor
                    from magnet.core.constants import EPSILON_GEOMETRY
                    sections_all = list(getattr(hull_geom, "sections", []) or [])
                    # Sort by station/x so adjacency is deterministic.
                    sections_all.sort(key=lambda ss: float(getattr(ss, "station", 0.0) or 0.0))
                    WARP_THRESHOLD = 0.02
                    for i in range(len(sections_all) - 1):
                        a = sections_all[i]
                        b = sections_all[i + 1]
                        pa = list(getattr(a, "points", []) or [])
                        pb = list(getattr(b, "points", []) or [])
                        n = min(len(pa), len(pb))
                        if n < 2:
                            continue
                        for j in range(n - 1):
                            p0 = pa[j].position
                            p1 = pa[j + 1].position
                            p2 = pb[j].position
                            p3 = pb[j + 1].position
                            warp = float(_compute_quad_warp_factor(p0, p1, p2, p3))
                            if warp > WARP_THRESHOLD + float(EPSILON_GEOMETRY):
                                raise PlanarityGateError(
                                    f"Non-planar panel detected (warp={warp:.4f} > {WARP_THRESHOLD:.2f}); "
                                    f"panelized surface cannot be rendered authoritatively.",
                                    max_warp=float(warp),
                                )
                except Exception:
                    # If the check cannot be performed for any reason, fail closed.
                    raise

                sections = list(getattr(hull_geom, "sections", []) or [])
                by: Dict[str, List[Any]] = {}
                for s in sections:
                    bid = str(getattr(s, "body_id", "main") or "main")
                    by.setdefault(bid, []).append(s)
                by_body = {}
                for bid in sorted(by.keys()):
                    s_list = sorted(by[bid], key=lambda ss: float(getattr(ss, "station", 0.0) or 0.0))
                    mesh = pipeline.tessellate_with_options(s_list, faceted=True, panel_edges_hard=True)
                    mesh.mesh_id = mesh.mesh_id or f"hull_{bid}"
                    by_body[bid] = mesh
            else:
                by_body = pipeline.tessellate_by_body()

            # If only one body, preserve legacy shape.
            if len(by_body) <= 1:
                hull_mesh = next(iter(by_body.values())) if by_body else pipeline.tessellate()
            else:
                # Multiple bodies: keep a list for export + a primary for legacy clients.
                hull_meshes = [by_body[k] for k in sorted(by_body.keys())]
                hull_mesh = hull_meshes[0]

        except Exception as e:
            # Authoritative unavailable: optionally fall back to parametric approximation.
            from .errors import GeometryUnavailableError
            if not allow_visual_only:
                raise
            # Visual-only approximation (single mesh)
            logger.warning(f"[VISUAL-ONLY] Authoritative scene unavailable for {design_id}: {e}")
            hull_mesh, _mode = self.get_hull_geometry(
                design_id=design_id,
                lod=lod,
                allow_visual_only=True,
            )
            geometry_mode = GeometryMode.VISUAL_ONLY
            simulation_integrity = SimulationIntegrity.APPROXIMATE

        # Get version info
        version_id = self._grm_provider.get_geometry_version(design_id) or ""

        # Build scene
        scene = SceneData(
            schema=SchemaMetadata(),
            design_id=design_id,
            version_id=version_id,
            geometry_mode=geometry_mode,
            simulation_integrity=simulation_integrity,
            hull=hull_mesh,
            hulls=hull_meshes,
            materials=self._get_default_materials(),
            metadata={
                "lod": lod.value,
                "generated_at": time.time(),
                # Mirror the explicit truth signal in metadata for older clients/tools.
                "simulation_integrity": simulation_integrity.value,
                "physics_last_validated_version": self._sm.get("kernel.physics_last_validated_version"),
                "hydrostatics_last_validated_version": self._sm.get("kernel.hydrostatics_last_validated_version"),
            },
        )

        if scene.simulation_integrity != SimulationIntegrity.AUTHORITATIVE and integrity_reason:
            scene.metadata["simulation_integrity_reason"] = integrity_reason
        # ---------------------------------------------------------------------
        # Turn Contract Vault: AUTHORITATIVE gating
        #
        # AUTHORITATIVE is allowed iff a same-version TurnContract exists and is clean.
        # This prevents "shoebox evidence" (distributed stamps) from being mistaken as proof.
        # ---------------------------------------------------------------------
        try:
            dv = self._sm.get("design_version")
            contracts = self._sm.get("turn_contracts", []) or []
            cid = self._sm.get("current_turn_contract_id")

            contract = None
            if isinstance(contracts, list) and dv is not None:
                # Prefer id match, then latest contract with matching design_version.
                for c in contracts:
                    if getattr(c, "contract_id", None) == cid and int(getattr(c, "design_version", -1)) == int(dv):
                        contract = c
                        break
                if contract is None:
                    for c in reversed(contracts):
                        if int(getattr(c, "design_version", -1)) == int(dv):
                            contract = c
                            break

            if contract is not None:
                scene.metadata["contract_summary"] = {
                    "contract_id": getattr(contract, "contract_id", None),
                    "design_version": int(getattr(contract, "design_version", 0) or 0),
                    "integrity_state": getattr(contract, "integrity_state", None),
                    "primary_reason": getattr(contract, "primary_reason", None),
                }
            else:
                scene.metadata["contract_summary"] = None

            # If no same-version contract exists, we cannot claim AUTHORITATIVE.
            # Do not overwrite existing DECOUPLED/APPROXIMATE reasons; this rule only blocks overclaiming.
            if dv is not None and contract is None and scene.simulation_integrity == SimulationIntegrity.AUTHORITATIVE:
                surface_definition = None
                try:
                    surface_definition = (getattr(hull_geom, "metadata", {}) or {}).get("surface_definition")
                except Exception:
                    surface_definition = None

                scene.simulation_integrity = (
                    SimulationIntegrity.DECOUPLED
                    if surface_definition == "panelized"
                    else SimulationIntegrity.APPROXIMATE
                )
                scene.metadata["simulation_integrity"] = scene.simulation_integrity.value
                scene.metadata["simulation_integrity_reason"] = "missing_contract"

            # If contract exists but is non-authoritative, prefer its classification (conservative).
            if contract is not None:
                cs = str(getattr(contract, "integrity_state", "") or "")
                cr = getattr(contract, "primary_reason", None)
                if cs in ("APPROXIMATE", "DECOUPLED"):
                    scene.simulation_integrity = SimulationIntegrity(cs)
                    scene.metadata["simulation_integrity"] = scene.simulation_integrity.value
                    if cr:
                        scene.metadata["simulation_integrity_reason"] = str(cr)
        except Exception:
            pass

        _integrity_before_scene_checks = scene.simulation_integrity.value

        # ---------------------------------------------------------------------
        # Truthfulness: volume parity check (silent-killer defense)
        # If physics is marked fresh (AUTHORITATIVE) but the watertight mesh volume
        # disagrees materially with physics displacement, flip to DECOUPLED.
        #
        # This catches:
        # - low-warp saddle/twist leakage (area-strip integration vs polyhedral volume)
        # - asymmetric multi-body mirroring/hallucination in rendering paths
        # ---------------------------------------------------------------------
        try:
            if scene.simulation_integrity == SimulationIntegrity.AUTHORITATIVE:
                phys_disp = self._sm.get("hull.displacement_m3")
                if phys_disp is not None and float(phys_disp) > 0:
                    meshes = []
                    if hull_meshes:
                        meshes.extend(list(hull_meshes))
                    if hull_mesh is not None and not meshes:
                        meshes.append(hull_mesh)

                    def _mesh_volume_m3(m) -> float:
                        v = getattr(m, "vertices", []) or []
                        ind = getattr(m, "indices", []) or []
                        if not v or not ind:
                            return 0.0
                        total = 0.0
                        for ii in range(0, len(ind), 3):
                            try:
                                i0, i1, i2 = int(ind[ii]), int(ind[ii + 1]), int(ind[ii + 2])
                                p0 = (float(v[i0 * 3]), float(v[i0 * 3 + 1]), float(v[i0 * 3 + 2]))
                                p1 = (float(v[i1 * 3]), float(v[i1 * 3 + 1]), float(v[i1 * 3 + 2]))
                                p2 = (float(v[i2 * 3]), float(v[i2 * 3 + 1]), float(v[i2 * 3 + 2]))
                                cross = (
                                    p1[1] * p2[2] - p1[2] * p2[1],
                                    p1[2] * p2[0] - p1[0] * p2[2],
                                    p1[0] * p2[1] - p1[1] * p2[0],
                                )
                                total += (p0[0] * cross[0] + p0[1] * cross[1] + p0[2] * cross[2]) / 6.0
                            except Exception:
                                continue
                        return abs(float(total))

                    mesh_vol = sum(_mesh_volume_m3(m) for m in meshes)
                    if mesh_vol > 0:
                        rel = abs(mesh_vol - float(phys_disp)) / float(phys_disp)
                        scene.metadata["mesh_volume_m3"] = float(mesh_vol)
                        scene.metadata["physics_displacement_m3"] = float(phys_disp)
                        scene.metadata["volume_parity_rel_error"] = float(rel)
                        if rel > 0.005:
                            scene.simulation_integrity = SimulationIntegrity.DECOUPLED
                            scene.metadata["simulation_integrity"] = scene.simulation_integrity.value
                            scene.metadata["simulation_integrity_reason"] = "volume_parity_violation"
        except Exception:
            pass

        # Phase 2: physics-domain validity downgrades (Engineering Truth)
        # If physics outputs explicitly mark out-of-envelope, never claim AUTHORITATIVE.
        try:
            if scene.simulation_integrity == SimulationIntegrity.AUTHORITATIVE:
                method_valid = self._sm.get("resistance.method_valid")
                if method_valid is False:
                    scene.simulation_integrity = SimulationIntegrity.APPROXIMATE
                    scene.metadata["simulation_integrity"] = scene.simulation_integrity.value
                    scene.metadata["simulation_integrity_reason"] = "physics_domain_violation"
                    scene.metadata["resistance_validity_note"] = self._sm.get("resistance.validity_note")
        except Exception:
            pass

        # ---------------------------------------------------------------------
        # SceneReceipt (v0): scene-time checks (mesh/parity/etc) are recorded here
        # and must not be confused with phase-time TurnContracts.
        # ---------------------------------------------------------------------
        try:
            dv = int(self._sm.get("design_version", 0) or 0)
            geo_ver = ""
            try:
                geo_ver = str(self._grm_provider.get_geometry_version(design_id) or "")
            except Exception:
                geo_ver = ""

            checks: Dict[str, Any] = {}
            for k in ("mesh_volume_m3", "physics_displacement_m3", "volume_parity_rel_error"):
                if k in scene.metadata:
                    checks[k] = scene.metadata.get(k)

            mesh_hash = ""
            try:
                # v0: order-sensitive identifier only; NOT semantic equivalence.
                primary_mesh = hull_meshes[0] if hull_meshes else hull_mesh
                if primary_mesh is not None:
                    mesh_hash = sha256_hex(
                        {
                            "vertices": list(getattr(primary_mesh, "vertices", []) or []),
                            "indices": list(getattr(primary_mesh, "indices", []) or []),
                        }
                    )
            except Exception:
                mesh_hash = ""

            integrity_effect: Dict[str, Any] = {}
            if scene.simulation_integrity.value != _integrity_before_scene_checks:
                integrity_effect = {
                    "before": _integrity_before_scene_checks,
                    "after": scene.simulation_integrity.value,
                    "reason": scene.metadata.get("simulation_integrity_reason"),
                }

            sr = SceneReceipt(
                scene_receipt_id=str(int(time.time() * 1000)),
                design_id=str(design_id),
                design_version=dv,
                geometry_version_id=geo_ver,
                mesh_hash=mesh_hash,
                checks=checks,
                integrity_effect=integrity_effect,
                timestamp_s=float(time.time()),
            )
            scene.metadata["scene_receipt"] = asdict(sr)
        except Exception:
            pass

        # Phase 3: Universal primitives (diagnostic markers only)
        # These are preserved for UI/inspection. Semantics are staged:
        # - diagnostic_only: pass-through markers only
        # - explicit_volume_semantics: some primitives include explicit volume fields used for hydrostatics correction
        try:
            if hull_geom is not None:
                openings = list(getattr(hull_geom, "openings", []) or [])
                flow_paths = list(getattr(hull_geom, "flow_paths", []) or [])
                attachments = list(getattr(hull_geom, "attachments", []) or [])

                def _has_explicit_semantics() -> bool:
                    for o in openings:
                        if isinstance(o, dict) and (o.get("void_volume_m3") is not None or o.get("through_hull_length_m") is not None):
                            return True
                    for f in flow_paths:
                        if isinstance(f, dict) and (f.get("void_volume_m3") is not None):
                            return True
                    for a in attachments:
                        if isinstance(a, dict) and (a.get("buoyancy_volume_m3") is not None):
                            return True
                    return False

                scene.metadata["primitives"] = {
                    "semantics": "explicit_volume_semantics" if _has_explicit_semantics() else "diagnostic_only",
                    "openings": openings,
                    "flow_paths": flow_paths,
                    "attachments": attachments,
                }
        except Exception:
            pass

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

        surface_definition = None
        try:
            surface_definition = (getattr(hull_geom, "metadata", {}) or {}).get("surface_definition")
        except Exception:
            surface_definition = None
        if surface_definition == "panelized":
            mesh = pipeline.tessellate_with_options(hull_geom.sections, faceted=True, panel_edges_hard=True)
        else:
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
