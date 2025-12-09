"""
webgl/dependency_integration.py - Dependency and lifecycle integration v1.1

Module 58: WebGL 3D Visualization
ALPHA OWNS THIS FILE.

Integrates geometry system with PhaseMachine, LifecycleManager, and artifact registration.

Addresses: FM3 (Performance collapse through proper job integration)
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
import weakref

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager
    from magnet.core.phase_states import PhaseMachine

logger = logging.getLogger("webgl.dependency_integration")


# =============================================================================
# GEOMETRY ARTIFACT REGISTRATION
# =============================================================================

class GeometryArtifactType(Enum):
    """Types of geometry artifacts."""
    HULL_MESH = "hull_mesh"
    DECK_MESH = "deck_mesh"
    STRUCTURE_MESH = "structure_mesh"
    SECTION_CUT = "section_cut"
    HYDROSTATIC_VISUAL = "hydrostatic_visual"
    WATERLINE = "waterline"
    COMPLETE_SCENE = "complete_scene"


@dataclass
class GeometryArtifact:
    """Registered geometry artifact with metadata."""
    artifact_type: GeometryArtifactType
    artifact_id: str
    design_id: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: int = 1
    lod: str = "medium"
    geometry_mode: str = "authoritative"
    vertex_count: int = 0
    face_count: int = 0
    is_valid: bool = True
    invalidation_reason: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class GeometryArtifactRegistry:
    """
    Registry for geometry artifacts with dependency tracking.

    Tracks all generated geometry and their dependencies on state values.
    """

    def __init__(self):
        self._artifacts: Dict[str, GeometryArtifact] = {}
        self._dependency_map: Dict[str, List[str]] = {}  # state_path -> artifact_ids
        self._invalidation_callbacks: List[Callable[[str, str], None]] = []

    def register(self, artifact: GeometryArtifact) -> None:
        """Register a geometry artifact."""
        key = f"{artifact.design_id}:{artifact.artifact_type.value}:{artifact.artifact_id}"
        self._artifacts[key] = artifact

        # Register dependencies
        for dep in artifact.dependencies:
            if dep not in self._dependency_map:
                self._dependency_map[dep] = []
            if key not in self._dependency_map[dep]:
                self._dependency_map[dep].append(key)

        logger.debug(f"Registered geometry artifact: {key}")

    def get(self, design_id: str, artifact_type: GeometryArtifactType, artifact_id: str = "") -> Optional[GeometryArtifact]:
        """Get a registered artifact."""
        key = f"{design_id}:{artifact_type.value}:{artifact_id}"
        return self._artifacts.get(key)

    def invalidate_by_dependency(self, state_path: str, reason: str = "") -> List[str]:
        """
        Invalidate all artifacts dependent on a state path.

        Returns list of invalidated artifact keys.
        """
        invalidated = []

        artifact_keys = self._dependency_map.get(state_path, [])
        for key in artifact_keys:
            artifact = self._artifacts.get(key)
            if artifact and artifact.is_valid:
                artifact.is_valid = False
                artifact.invalidation_reason = reason or f"Dependency changed: {state_path}"
                invalidated.append(key)
                logger.debug(f"Invalidated artifact {key} due to {state_path} change")

                # Notify callbacks
                for callback in self._invalidation_callbacks:
                    try:
                        callback(key, artifact.invalidation_reason)
                    except Exception as e:
                        logger.error(f"Invalidation callback failed: {e}")

        return invalidated

    def invalidate_design(self, design_id: str, reason: str = "") -> List[str]:
        """Invalidate all artifacts for a design."""
        invalidated = []

        for key, artifact in self._artifacts.items():
            if artifact.design_id == design_id and artifact.is_valid:
                artifact.is_valid = False
                artifact.invalidation_reason = reason or "Design invalidated"
                invalidated.append(key)

        return invalidated

    def get_valid_artifacts(self, design_id: str) -> List[GeometryArtifact]:
        """Get all valid artifacts for a design."""
        return [
            artifact for artifact in self._artifacts.values()
            if artifact.design_id == design_id and artifact.is_valid
        ]

    def on_invalidation(self, callback: Callable[[str, str], None]) -> None:
        """Register callback for artifact invalidation."""
        self._invalidation_callbacks.append(callback)

    def clear_design(self, design_id: str) -> None:
        """Clear all artifacts for a design."""
        keys_to_remove = [
            key for key, artifact in self._artifacts.items()
            if artifact.design_id == design_id
        ]

        for key in keys_to_remove:
            del self._artifacts[key]

        # Clean up dependency map
        for dep_list in self._dependency_map.values():
            for key in keys_to_remove:
                if key in dep_list:
                    dep_list.remove(key)


# Singleton registry
_artifact_registry: Optional[GeometryArtifactRegistry] = None


def get_artifact_registry() -> GeometryArtifactRegistry:
    """Get the global artifact registry."""
    global _artifact_registry
    if _artifact_registry is None:
        _artifact_registry = GeometryArtifactRegistry()
    return _artifact_registry


# =============================================================================
# PHASE MACHINE INTEGRATION
# =============================================================================

class GeometryPhaseHooks:
    """
    Hooks for PhaseMachine integration.

    Manages geometry lifecycle based on design phase transitions.
    """

    # State paths that affect geometry
    GEOMETRY_DEPENDENCIES = [
        "hull.loa",
        "hull.lwl",
        "hull.beam",
        "hull.draft",
        "hull.depth",
        "hull.displacement",
        "hull.bow_shape",
        "hull.stern_shape",
        "hull.midship_coefficient",
        "hull.prismatic_coefficient",
        "hull.block_coefficient",
        "hull.entry_angle",
        "hull.deadrise_angle",
        "structure.frame_spacing",
        "structure.frame_depth_mm",
        "structure.frame_thickness_mm",
        "structure.stringer_count",
        "structure.keel_depth_mm",
    ]

    def __init__(self, state_manager: "StateManager"):
        self._sm = weakref.ref(state_manager)
        self._registry = get_artifact_registry()
        self._subscriptions: List[Any] = []

    @property
    def state_manager(self) -> Optional["StateManager"]:
        return self._sm() if self._sm else None

    def attach(self) -> None:
        """Attach hooks to state manager."""
        sm = self.state_manager
        if not sm:
            return

        # Subscribe to geometry-affecting state changes
        try:
            if hasattr(sm, 'subscribe'):
                for path in self.GEOMETRY_DEPENDENCIES:
                    sub = sm.subscribe(path, self._on_state_change)
                    self._subscriptions.append(sub)
                logger.info(f"Attached {len(self.GEOMETRY_DEPENDENCIES)} geometry state hooks")
        except Exception as e:
            logger.warning(f"Could not attach state subscriptions: {e}")

    def detach(self) -> None:
        """Detach all hooks."""
        for sub in self._subscriptions:
            try:
                if hasattr(sub, 'unsubscribe'):
                    sub.unsubscribe()
            except Exception:
                pass
        self._subscriptions.clear()

    def _on_state_change(self, path: str, old_value: Any, new_value: Any) -> None:
        """Handle state change affecting geometry."""
        if old_value != new_value:
            reason = f"State changed: {path} from {old_value} to {new_value}"
            invalidated = self._registry.invalidate_by_dependency(path, reason)

            if invalidated:
                logger.info(f"Invalidated {len(invalidated)} artifacts due to {path} change")

                # Emit invalidation event
                try:
                    from .events import emit_geometry_invalidated
                    sm = self.state_manager
                    if sm:
                        design_id = getattr(sm, 'design_id', 'unknown')
                        emit_geometry_invalidated(
                            design_id=design_id,
                            reason=reason,
                            source_phase=None,
                            affected_components=[a.split(':')[1] for a in invalidated],
                        )
                except Exception as e:
                    logger.debug(f"Could not emit invalidation event: {e}")

    def on_phase_enter(self, phase: str) -> None:
        """
        Handle phase entry.

        Certain phases may require geometry regeneration or validation.
        """
        sm = self.state_manager
        if not sm:
            return

        design_id = getattr(sm, 'design_id', 'unknown')

        if phase == "concept":
            # Entering concept - may need visual-only geometry
            logger.debug(f"Entering concept phase for {design_id}")

        elif phase == "preliminary":
            # Entering preliminary - need authoritative geometry
            logger.info(f"Entering preliminary phase - validating geometry for {design_id}")
            valid_artifacts = self._registry.get_valid_artifacts(design_id)

            # Check if we have valid authoritative geometry
            has_authoritative = any(
                a.geometry_mode == "authoritative"
                for a in valid_artifacts
            )

            if not has_authoritative:
                logger.warning(f"No authoritative geometry for design {design_id} in preliminary phase")

        elif phase == "detailed":
            # Detailed phase requires high-quality geometry
            logger.info(f"Entering detailed phase for {design_id}")

    def on_phase_exit(self, phase: str) -> None:
        """Handle phase exit."""
        pass  # Currently no exit handling needed


# =============================================================================
# LIFECYCLE MANAGER INTEGRATION
# =============================================================================

class GeometryLifecycleIntegration:
    """
    Integrates geometry system with LifecycleManager.

    Handles startup, shutdown, and health checks.
    """

    def __init__(self):
        self._initialized = False
        self._hooks: Dict[str, GeometryPhaseHooks] = {}

    def initialize(self) -> None:
        """Initialize geometry lifecycle integration."""
        if self._initialized:
            return

        logger.info("Initializing geometry lifecycle integration")

        # Register with lifecycle manager if available
        try:
            from magnet.lifecycle.manager import LifecycleManager, get_lifecycle_manager

            lm = get_lifecycle_manager()
            if lm:
                lm.register_component(
                    name="webgl_geometry",
                    startup=self._startup,
                    shutdown=self._shutdown,
                    health_check=self._health_check,
                )
                logger.info("Registered geometry component with lifecycle manager")
        except ImportError:
            logger.debug("LifecycleManager not available - running standalone")
        except Exception as e:
            logger.warning(f"Could not register with lifecycle manager: {e}")

        self._initialized = True

    def attach_to_state_manager(self, state_manager: "StateManager", design_id: str = "") -> None:
        """Attach hooks to a state manager."""
        hooks = GeometryPhaseHooks(state_manager)
        hooks.attach()
        self._hooks[design_id or id(state_manager)] = hooks

    def detach_from_state_manager(self, design_id: str = "") -> None:
        """Detach hooks from a state manager."""
        key = design_id or None
        if key in self._hooks:
            self._hooks[key].detach()
            del self._hooks[key]

    def _startup(self) -> bool:
        """Lifecycle startup callback."""
        logger.info("Geometry system starting up")

        # Initialize artifact registry
        get_artifact_registry()

        return True

    def _shutdown(self) -> bool:
        """Lifecycle shutdown callback."""
        logger.info("Geometry system shutting down")

        # Detach all hooks
        for hooks in self._hooks.values():
            hooks.detach()
        self._hooks.clear()

        return True

    def _health_check(self) -> Dict[str, Any]:
        """Lifecycle health check callback."""
        registry = get_artifact_registry()

        return {
            "status": "healthy",
            "artifact_count": len(registry._artifacts),
            "active_hooks": len(self._hooks),
            "initialized": self._initialized,
        }


# Singleton integration
_lifecycle_integration: Optional[GeometryLifecycleIntegration] = None


def get_lifecycle_integration() -> GeometryLifecycleIntegration:
    """Get the geometry lifecycle integration singleton."""
    global _lifecycle_integration
    if _lifecycle_integration is None:
        _lifecycle_integration = GeometryLifecycleIntegration()
    return _lifecycle_integration


def initialize_geometry_system() -> None:
    """
    Initialize the complete geometry system.

    Call this during application startup.
    """
    integration = get_lifecycle_integration()
    integration.initialize()


# =============================================================================
# JOB QUEUE INTEGRATION
# =============================================================================

@dataclass
class GeometryJob:
    """Geometry generation job for queue processing."""
    job_id: str
    design_id: str
    job_type: str  # "hull", "structure", "scene", "export"
    lod: str = "medium"
    priority: int = 5  # 1=highest, 10=lowest
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class GeometryJobQueue:
    """
    Job queue for geometry generation.

    Integrates with existing job infrastructure for background processing.
    """

    def __init__(self, max_concurrent: int = 2):
        self._jobs: Dict[str, GeometryJob] = {}
        self._queue: List[str] = []  # job_ids in priority order
        self._max_concurrent = max_concurrent
        self._running_count = 0

    def submit(self, job: GeometryJob) -> str:
        """Submit a job to the queue."""
        self._jobs[job.job_id] = job

        # Insert by priority
        insert_idx = 0
        for i, jid in enumerate(self._queue):
            existing = self._jobs.get(jid)
            if existing and existing.priority > job.priority:
                insert_idx = i
                break
            insert_idx = i + 1

        self._queue.insert(insert_idx, job.job_id)
        logger.debug(f"Submitted geometry job {job.job_id} with priority {job.priority}")

        return job.job_id

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status."""
        job = self._jobs.get(job_id)
        if not job:
            return None

        return {
            "job_id": job.job_id,
            "status": job.status,
            "job_type": job.job_type,
            "lod": job.lod,
            "created_at": job.created_at,
            "error": job.error,
        }

    def get_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job result if completed."""
        job = self._jobs.get(job_id)
        if job and job.status == "completed":
            return job.result
        return None

    def cancel(self, job_id: str) -> bool:
        """Cancel a pending job."""
        if job_id in self._queue:
            self._queue.remove(job_id)
            job = self._jobs.get(job_id)
            if job:
                job.status = "cancelled"
            return True
        return False

    def process_next(self) -> Optional[GeometryJob]:
        """
        Get next job to process.

        Returns None if queue empty or at max concurrent.
        """
        if self._running_count >= self._max_concurrent:
            return None

        if not self._queue:
            return None

        job_id = self._queue.pop(0)
        job = self._jobs.get(job_id)

        if job:
            job.status = "running"
            self._running_count += 1

        return job

    def complete_job(self, job_id: str, result: Dict[str, Any]) -> None:
        """Mark job as completed with result."""
        job = self._jobs.get(job_id)
        if job:
            job.status = "completed"
            job.result = result
            self._running_count = max(0, self._running_count - 1)

    def fail_job(self, job_id: str, error: str) -> None:
        """Mark job as failed with error."""
        job = self._jobs.get(job_id)
        if job:
            job.status = "failed"
            job.error = error
            self._running_count = max(0, self._running_count - 1)


# Singleton job queue
_job_queue: Optional[GeometryJobQueue] = None


def get_job_queue() -> GeometryJobQueue:
    """Get the geometry job queue singleton."""
    global _job_queue
    if _job_queue is None:
        _job_queue = GeometryJobQueue()
    return _job_queue
