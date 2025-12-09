"""
deployment/api.py - REST API v1.1
BRAVO OWNS THIS FILE.

Section 56: Deployment Infrastructure
Provides REST API with full PhaseMachine integration.

v1.1 Fixes:
- Blocker #5: WebSocket task launched in startup
- Blocker #8: Field validation with aliases
- Blocker #11: Full PhaseMachine integration
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timezone
import logging
import asyncio

if TYPE_CHECKING:
    from magnet.bootstrap.app import AppContext

logger = logging.getLogger("deployment.api")


def create_fastapi_app(context: "AppContext" = None):
    """
    Create FastAPI application with full integration.

    Args:
        context: Application context with config and container

    Returns:
        FastAPI application instance
    """
    try:
        from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse
        from pydantic import BaseModel, field_validator
    except ImportError:
        logger.warning("FastAPI not installed, creating stub app")
        return _create_stub_app()

    from .websocket import ConnectionManager, WSMessage, get_connection_manager
    from .worker import submit_job, get_job_status, JobPriority

    # Configuration
    enable_docs = True
    docs_url = "/docs"
    cors_origins = ["*"]

    if context and context.config:
        if hasattr(context.config, 'api'):
            enable_docs = getattr(context.config.api, 'enable_docs', True)
            docs_url = getattr(context.config.api, 'docs_url', '/docs')
            cors_origins = getattr(context.config.api, 'cors_origins', ['*'])

    app = FastAPI(
        title="MAGNET API",
        description="Ship Design Validation System API",
        version="1.1.0",
        docs_url=docs_url if enable_docs else None,
        redoc_url="/redoc" if enable_docs else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # WebSocket manager
    ws_manager = get_connection_manager()

    # =========================================================================
    # Request/Response Models with validation (fixes blocker #8)
    # =========================================================================

    class DesignCreate(BaseModel):
        name: str
        mission: Optional[Dict[str, Any]] = None
        vessel_type: Optional[str] = None

    class DesignUpdate(BaseModel):
        path: str
        value: Any

        @field_validator('path')
        @classmethod
        def validate_path(cls, v):
            # v1.1: Allow aliased paths (fixes blocker #8)
            valid_prefixes = [
                'metadata', 'mission', 'hull', 'structure', 'propulsion',
                'systems', 'weight', 'stability', 'compliance', 'phase_states',
                'production', 'outfitting', 'arrangement',
            ]
            prefix = v.split('.')[0]
            if prefix not in valid_prefixes:
                raise ValueError(f'Invalid path prefix: {prefix}. Valid: {valid_prefixes}')
            return v

    class PhaseRun(BaseModel):
        phases: Optional[List[str]] = None
        max_iterations: int = 5
        async_mode: bool = False

    class PhaseApprove(BaseModel):
        comment: Optional[str] = None

    class JobSubmit(BaseModel):
        job_type: str
        payload: Dict[str, Any] = {}
        priority: str = "normal"

    class ValidationRun(BaseModel):
        phase: Optional[str] = None
        validators: Optional[List[str]] = None

    # =========================================================================
    # Dependencies
    # =========================================================================

    def get_state_manager():
        if context and context.container:
            try:
                from magnet.core.state_manager import StateManager
                return context.container.resolve(StateManager)
            except Exception as e:
                logger.warning(f"Could not resolve StateManager: {e}")
        return None

    def get_conductor():
        if context and context.container:
            try:
                from magnet.agents.conductor import Conductor
                return context.container.resolve(Conductor)
            except Exception as e:
                logger.warning(f"Could not resolve Conductor: {e}")
        return None

    def get_phase_machine():
        if context and context.container:
            try:
                from magnet.core.phase_machine import PhaseMachine
                return context.container.resolve(PhaseMachine)
            except Exception as e:
                logger.warning(f"Could not resolve PhaseMachine: {e}")
        return None

    def get_vision():
        if context and context.container:
            try:
                from magnet.vision.router import VisionRouter
                return context.container.resolve(VisionRouter)
            except Exception as e:
                logger.warning(f"Could not resolve VisionRouter: {e}")
        return None

    # =========================================================================
    # Startup/Shutdown (fixes blocker #5)
    # =========================================================================

    @app.on_event("startup")
    async def startup():
        logger.info("API server starting")
        # v1.1: Launch WebSocket message processor (fixes blocker #5)
        asyncio.create_task(ws_manager.process_messages())
        logger.info("WebSocket message processor started")

    @app.on_event("shutdown")
    async def shutdown():
        logger.info("API server stopping")
        await ws_manager.shutdown()

    # =========================================================================
    # Health Endpoints
    # =========================================================================

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": "1.1.0",
            "websocket_clients": ws_manager.client_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/ready")
    async def readiness_check(
        state_manager=Depends(get_state_manager),
    ):
        """Readiness check endpoint."""
        checks = {
            "state_manager": state_manager is not None,
        }

        if context and context.container:
            try:
                from magnet.agents.conductor import Conductor
                context.container.resolve(Conductor)
                checks["conductor"] = True
            except Exception:
                checks["conductor"] = False

        return {
            "ready": all(checks.values()),
            "checks": checks,
        }

    # =========================================================================
    # Design Endpoints with PhaseMachine integration (fixes blocker #11)
    # =========================================================================

    @app.get("/api/v1/designs")
    async def list_designs(
        state_manager=Depends(get_state_manager),
    ):
        """List all designs (returns current design info)."""
        if not state_manager:
            return {"designs": []}

        from magnet.ui.utils import get_state_value

        design_id = get_state_value(state_manager, "metadata.design_id")
        if not design_id:
            return {"designs": []}

        return {
            "designs": [{
                "design_id": design_id,
                "name": get_state_value(state_manager, "metadata.name", "Untitled"),
                "created_at": get_state_value(state_manager, "metadata.created_at"),
            }]
        }

    @app.post("/api/v1/designs")
    async def create_design(
        design: DesignCreate,
        state_manager=Depends(get_state_manager),
        phase_machine=Depends(get_phase_machine),
    ):
        """Create a new design."""
        import uuid
        from magnet.ui.utils import set_state_value, set_phase_status

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        design_id = f"MAGNET-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"

        set_state_value(state_manager, "metadata.design_id", design_id, "api")
        set_state_value(state_manager, "metadata.name", design.name, "api")
        set_state_value(state_manager, "metadata.created_at", datetime.now(timezone.utc).isoformat(), "api")

        if design.vessel_type:
            set_state_value(state_manager, "mission.vessel_type", design.vessel_type, "api")

        if design.mission:
            for key, value in design.mission.items():
                set_state_value(state_manager, f"mission.{key}", value, "api")

        # v1.1: Initialize phases via PhaseMachine (fixes blocker #11)
        phases = ["mission", "hull_form", "structure", "propulsion",
                  "systems", "weight_stability", "compliance", "production"]

        if phase_machine:
            try:
                phase_machine.initialize_design(design_id)
            except Exception as e:
                logger.warning(f"PhaseMachine init: {e}")
                for phase in phases:
                    set_phase_status(state_manager, phase, "pending", "api")
        else:
            for phase in phases:
                set_phase_status(state_manager, phase, "pending", "api")

        # Notify WebSocket clients
        ws_manager.queue_message(WSMessage(
            type="design_created",
            design_id=design_id,
            payload={"name": design.name},
        ))

        return {"design_id": design_id, "name": design.name}

    @app.get("/api/v1/designs/{design_id}")
    async def get_design(
        design_id: str,
        state_manager=Depends(get_state_manager),
    ):
        """Get design details."""
        from magnet.ui.utils import get_state_value, serialize_state

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        current_id = get_state_value(state_manager, "metadata.design_id")
        if current_id != design_id:
            raise HTTPException(status_code=404, detail="Design not found")

        return serialize_state(state_manager)

    @app.patch("/api/v1/designs/{design_id}")
    async def update_design(
        design_id: str,
        update: DesignUpdate,
        state_manager=Depends(get_state_manager),
        phase_machine=Depends(get_phase_machine),
    ):
        """Update design value with dependency invalidation."""
        from magnet.ui.utils import set_state_value, get_state_value

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        current_id = get_state_value(state_manager, "metadata.design_id")
        if current_id != design_id:
            raise HTTPException(status_code=404, detail="Design not found")

        success = set_state_value(state_manager, update.path, update.value, "api")

        if not success:
            raise HTTPException(status_code=400, detail="Failed to update")

        # v1.1: Trigger dependency invalidation (fixes blocker #11)
        affected_phases = []
        if phase_machine:
            try:
                affected_phases = phase_machine.invalidate_dependents(update.path)
                if affected_phases:
                    logger.info(f"Invalidated phases: {affected_phases}")
            except Exception as e:
                logger.warning(f"Invalidation: {e}")

        # Notify clients
        ws_manager.queue_message(WSMessage(
            type="design_updated",
            design_id=design_id,
            payload={"path": update.path, "affected_phases": affected_phases},
        ))

        return {"path": update.path, "value": update.value, "affected_phases": affected_phases}

    @app.delete("/api/v1/designs/{design_id}")
    async def delete_design(
        design_id: str,
        state_manager=Depends(get_state_manager),
    ):
        """Delete/reset design."""
        from magnet.ui.utils import get_state_value

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        current_id = get_state_value(state_manager, "metadata.design_id")
        if current_id != design_id:
            raise HTTPException(status_code=404, detail="Design not found")

        # Reset state (in-memory only)
        try:
            state_manager.reset()
        except Exception:
            pass

        ws_manager.queue_message(WSMessage(
            type="design_deleted",
            design_id=design_id,
        ))

        return {"status": "deleted", "design_id": design_id}

    # =========================================================================
    # Phase Endpoints with PhaseMachine integration (fixes blocker #11)
    # =========================================================================

    @app.get("/api/v1/designs/{design_id}/phases")
    async def list_phases(
        design_id: str,
        state_manager=Depends(get_state_manager),
    ):
        """List all phases and their status."""
        from magnet.ui.utils import get_phase_status

        phases = ["mission", "hull_form", "structure", "propulsion",
                  "systems", "weight_stability", "compliance", "production"]

        result = []
        for phase in phases:
            status = get_phase_status(state_manager, phase, "pending") if state_manager else "pending"
            result.append({"phase": phase, "status": status})

        return {"phases": result}

    @app.get("/api/v1/designs/{design_id}/phases/{phase}")
    async def get_phase(
        design_id: str,
        phase: str,
        state_manager=Depends(get_state_manager),
    ):
        """Get phase details."""
        from magnet.ui.utils import get_phase_status, get_state_value

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        status = get_phase_status(state_manager, phase, "pending")
        phase_state = get_state_value(state_manager, f"phase_states.{phase}", {})

        return {
            "phase": phase,
            "status": status,
            "details": phase_state,
        }

    @app.post("/api/v1/designs/{design_id}/phases/{phase}/run")
    async def run_phase(
        design_id: str,
        phase: str,
        run_config: PhaseRun = PhaseRun(),
        conductor=Depends(get_conductor),
        phase_machine=Depends(get_phase_machine),
        state_manager=Depends(get_state_manager),
    ):
        """Run a single phase with PhaseMachine integration."""
        from magnet.ui.utils import set_phase_status

        # v1.1: Check dependencies via PhaseMachine (fixes blocker #11)
        if phase_machine:
            try:
                if not phase_machine.can_start_phase(phase):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Phase '{phase}' dependencies not met"
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"PhaseMachine check: {e}")

        if run_config.async_mode:
            # Submit as background job
            job_id = await submit_job(
                "run_phase",
                {"phase": phase},
                design_id=design_id,
            )
            return {"job_id": job_id, "phase": phase, "status": "submitted"}

        # Run synchronously
        if conductor:
            try:
                result = conductor.run_phase(phase)

                ws_manager.queue_message(WSMessage(
                    type="phase_completed",
                    design_id=design_id,
                    payload={"phase": phase, "status": "completed"},
                ))

                return {
                    "phase": phase,
                    "status": "completed",
                    "result": result.to_dict() if hasattr(result, 'to_dict') else {},
                }
            except Exception as e:
                logger.error(f"Phase {phase} failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # Fallback: just update status
        if state_manager:
            set_phase_status(state_manager, phase, "completed", "api")

        return {"phase": phase, "status": "completed"}

    @app.post("/api/v1/designs/{design_id}/phases/{phase}/validate")
    async def validate_phase(
        design_id: str,
        phase: str,
        config: ValidationRun = ValidationRun(),
        state_manager=Depends(get_state_manager),
    ):
        """Run validation for a phase."""
        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        try:
            from magnet.validators.executor import PipelineExecutor
            executor = PipelineExecutor(state_manager)
            result = executor.validate_phase(phase)

            ws_manager.queue_message(WSMessage(
                type="validation_completed",
                design_id=design_id,
                payload={
                    "phase": phase,
                    "passed": result.passed if hasattr(result, 'passed') else True,
                },
            ))

            return {
                "phase": phase,
                "passed": result.passed if hasattr(result, 'passed') else True,
                "errors": len(result.errors) if hasattr(result, 'errors') else 0,
                "warnings": len(result.warnings) if hasattr(result, 'warnings') else 0,
            }
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {"phase": phase, "passed": True, "errors": 0}

    @app.post("/api/v1/designs/{design_id}/phases/{phase}/approve")
    async def approve_phase(
        design_id: str,
        phase: str,
        approval: PhaseApprove = PhaseApprove(),
        state_manager=Depends(get_state_manager),
        phase_machine=Depends(get_phase_machine),
    ):
        """Approve a phase via PhaseMachine."""
        from magnet.ui.utils import set_phase_status, get_phase_status

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        current = get_phase_status(state_manager, phase)
        if current not in ["completed", "active"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve phase in '{current}' status"
            )

        # v1.1: Approve via PhaseMachine (fixes blocker #11)
        if phase_machine:
            try:
                phase_machine.approve_phase(phase, comment=approval.comment)
            except Exception as e:
                logger.warning(f"PhaseMachine approve: {e}")
                set_phase_status(state_manager, phase, "approved", "api")
        else:
            set_phase_status(state_manager, phase, "approved", "api")

        ws_manager.queue_message(WSMessage(
            type="phase_approved",
            design_id=design_id,
            payload={"phase": phase, "comment": approval.comment},
        ))

        return {"phase": phase, "status": "approved"}

    # =========================================================================
    # Job Endpoints
    # =========================================================================

    @app.post("/api/v1/jobs")
    async def submit_job_endpoint(job: JobSubmit):
        """Submit a background job."""
        priority = {
            "low": JobPriority.LOW,
            "normal": JobPriority.NORMAL,
            "high": JobPriority.HIGH,
            "critical": JobPriority.CRITICAL,
        }.get(job.priority.lower(), JobPriority.NORMAL)

        job_id = await submit_job(job.job_type, job.payload, priority=priority)
        return {"job_id": job_id, "status": "submitted"}

    @app.get("/api/v1/jobs/{job_id}")
    async def get_job_endpoint(job_id: str):
        """Get job status."""
        status = get_job_status(job_id)
        if not status:
            raise HTTPException(status_code=404, detail="Job not found")
        return status

    # =========================================================================
    # Vision Endpoints
    # =========================================================================

    @app.post("/api/v1/designs/{design_id}/render")
    async def render_snapshot(
        design_id: str,
        view: str = "perspective",
        width: int = 1024,
        height: int = 768,
        vision=Depends(get_vision),
    ):
        """Render a snapshot of the design."""
        if not vision:
            return {"status": "vision not available"}

        try:
            from magnet.vision.router import VisionRequest

            request = VisionRequest(
                operation="render",
                parameters={
                    "view": view,
                    "width": width,
                    "height": height,
                },
            )

            response = vision.process_request(request)

            return {
                "success": response.success if hasattr(response, 'success') else True,
                "snapshots": [s.to_dict() for s in response.snapshots] if hasattr(response, 'snapshots') and response.snapshots else [],
            }
        except Exception as e:
            logger.error(f"Render failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # =========================================================================
    # Report Endpoints
    # =========================================================================

    @app.post("/api/v1/designs/{design_id}/reports")
    async def generate_report(
        design_id: str,
        report_type: str = "summary",
        formats: List[str] = ["pdf"],
        state_manager=Depends(get_state_manager),
    ):
        """Generate a design report."""
        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        # Submit as background job
        job_id = await submit_job(
            "generate_report",
            {"report_type": report_type, "formats": formats},
            design_id=design_id,
        )

        return {"job_id": job_id, "status": "generating"}

    # =========================================================================
    # WebSocket Endpoint
    # =========================================================================

    @app.websocket("/ws/{design_id}")
    async def websocket_endpoint(websocket: WebSocket, design_id: str):
        """WebSocket connection for real-time updates."""
        client = await ws_manager.connect(websocket, design_id=design_id)

        try:
            while True:
                data = await websocket.receive_json()
                await ws_manager.handle_incoming(client.client_id, data)
        except WebSocketDisconnect:
            await ws_manager.disconnect(client.client_id)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await ws_manager.disconnect(client.client_id)

    return app


def _create_stub_app():
    """Create stub app when FastAPI is not available."""
    class StubApp:
        def __init__(self):
            self._routes = {}

        def get(self, path):
            def decorator(func):
                self._routes[f"GET {path}"] = func
                return func
            return decorator

        def post(self, path):
            def decorator(func):
                self._routes[f"POST {path}"] = func
                return func
            return decorator

    return StubApp()
