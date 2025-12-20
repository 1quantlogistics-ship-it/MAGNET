"""
deployment/api.py - REST API v1.2
BRAVO OWNS THIS FILE.

Section 56: Deployment Infrastructure
Provides REST API with full PhaseMachine integration.

v1.2 Fixes:
- Blocker #12: Forward reference bug - Pydantic models at module level

v1.1 Fixes:
- Blocker #5: WebSocket task launched in startup
- Blocker #8: Field validation with aliases
- Blocker #11: Full PhaseMachine integration
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timezone
import logging
import asyncio
import os

if TYPE_CHECKING:
    from magnet.bootstrap.app import AppContext

logger = logging.getLogger("deployment.api")

# Frontend dist path (relative to project root)
FRONTEND_DIST_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "app", "dist")

# Module 65.2: Serve ui_v2 directly (no build step required)
UI_V2_PATH = os.path.join(os.path.dirname(__file__), "..", "ui_v2")


# =============================================================================
# Request/Response Models (v1.2: Moved to module level to fix forward ref bug)
# =============================================================================

try:
    from pydantic import BaseModel, field_validator

    class DesignCreate(BaseModel):
        """Request model for creating a new design."""
        name: str
        mission: Optional[Dict[str, Any]] = None
        vessel_type: Optional[str] = None

    class DesignUpdate(BaseModel):
        """Request model for updating a design value."""
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
        """Request model for running a phase."""
        phases: Optional[List[str]] = None
        max_iterations: int = 5
        async_mode: bool = False

    class PhaseApprove(BaseModel):
        """Request model for approving a phase."""
        comment: Optional[str] = None

    class JobSubmit(BaseModel):
        """Request model for submitting a background job."""
        job_type: str
        payload: Dict[str, Any] = {}
        priority: str = "normal"

    class ValidationRun(BaseModel):
        """Request model for running validation."""
        phase: Optional[str] = None
        validators: Optional[List[str]] = None

    class ActionSubmit(BaseModel):
        """Request model for submitting an ActionPlan."""
        plan_id: str
        intent_id: str
        design_version_before: int
        actions: List[Dict[str, Any]]

        @field_validator('actions')
        @classmethod
        def validate_actions(cls, v):
            if not v:
                raise ValueError('actions list cannot be empty')
            return v

    class IntentPreviewRequest(BaseModel):
        """Request model for previewing an intent (Module 63/65.1)."""
        text: str
        design_version_before: Optional[int] = None
        mode: Optional[str] = "single"  # Module 65.1: "single" or "compound"

    _PYDANTIC_AVAILABLE = True

except ImportError:
    _PYDANTIC_AVAILABLE = False
    # Stub classes for when pydantic is not available
    class DesignCreate:
        pass
    class DesignUpdate:
        pass
    class PhaseRun:
        pass
    class PhaseApprove:
        pass
    class JobSubmit:
        pass
    class ValidationRun:
        pass
    class ActionSubmit:
        pass
    class IntentPreviewRequest:
        pass


# =============================================================================
# Module 65.1: HypotheticalStateView for Gate Reuse
# =============================================================================

class HypotheticalStateView:
    """
    Read-only view that overlays proposed actions on real state.

    Implements same get(path) interface as StateManager, allowing
    GateCondition.evaluate() to run against hypothetical post-apply state
    WITHOUT any mutation.

    Module 65.1: This is the key mechanism for computing missing_for_phases.
    """

    def __init__(self, real_state_manager, proposed_actions: list):
        """
        Args:
            real_state_manager: The real StateManager to read from
            proposed_actions: List of Action objects to overlay
        """
        self._real = real_state_manager
        # Build overlay: {path: value}
        self._overlay = {}
        for action in proposed_actions:
            # Only SET actions contribute to overlay
            if hasattr(action, 'action_type'):
                from magnet.kernel.intent_protocol import ActionType
                if action.action_type == ActionType.SET:
                    self._overlay[action.path] = action.value
            elif isinstance(action, dict) and action.get('action_type') == 'set':
                self._overlay[action['path']] = action['value']

    def get(self, path: str, default=None):
        """
        Return proposed value if exists, else real state.

        This is the only method needed by GateCondition.evaluate().
        """
        if path in self._overlay:
            return self._overlay[path]
        return self._real.get(path, default)


def check_gates_on_hypothetical(phase: str, hypothetical_view: HypotheticalStateView) -> list:
    """
    Check gate conditions for a phase using hypothetical state.

    Module 65.1: Uses existing GATE_CONDITIONS and GateCondition.evaluate()
    with zero new validation logic. The hypothetical_view overlays proposed
    actions on real state.

    Args:
        phase: Phase name (e.g., "hull_form")
        hypothetical_view: HypotheticalStateView with proposed values

    Returns:
        List of dicts for missing/failed gates: [{path, reason, gate_name}]
    """
    from magnet.core.phase_states import GATE_CONDITIONS

    gates = GATE_CONDITIONS.get(phase, [])
    missing = []

    for gate in gates:
        if not gate.required:
            continue

        # Use existing gate.evaluate() - the core reuse mechanism
        passed, message = gate.evaluate(hypothetical_view)

        if not passed:
            missing.append({
                "path": gate.check_path,
                "reason": gate.error_message or message,
                "gate_name": gate.name,
                "phase": phase,
            })

    return missing


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
        from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
        from fastapi.staticfiles import StaticFiles
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
    # Wire Geometry Router (Intent→Action Protocol integration)
    # =========================================================================

    try:
        from magnet.webgl.api_endpoints import create_geometry_router

        def state_manager_getter(design_id: str):
            """Get StateManager for geometry endpoints."""
            if context and context.container:
                try:
                    from magnet.core.state_manager import StateManager
                    return context.container.resolve(StateManager)
                except Exception as e:
                    logger.warning(f"Could not resolve StateManager for geometry: {e}")
            return None

        geometry_router = create_geometry_router(state_manager_getter)
        app.include_router(geometry_router)
        logger.info("Geometry router wired successfully")
    except Exception as e:
        logger.warning(f"Could not wire geometry router: {e}")

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
                from magnet.kernel.conductor import Conductor
                return context.container.resolve(Conductor)
            except Exception as e:
                logger.warning(f"Could not resolve Conductor: {e}")
        return None

    def get_phase_machine():
        if context and context.container:
            try:
                from magnet.core.phase_states import PhaseMachine
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

    def get_pipeline_executor():
        """Get configured PipelineExecutor from DI container."""
        if context and context.container:
            try:
                from magnet.validators.executor import PipelineExecutor
                return context.container.resolve(PipelineExecutor)
            except Exception as e:
                logger.warning(f"Could not resolve PipelineExecutor: {e}")
        return None

    def get_validator_topology():
        """Get ValidatorTopology from DI container."""
        if context and context.container:
            try:
                from magnet.validators.topology import ValidatorTopology
                return context.container.resolve(ValidatorTopology)
            except Exception as e:
                logger.warning(f"Could not resolve ValidatorTopology: {e}")
        return None

    def get_result_aggregator():
        """Get ResultAggregator from DI container."""
        if context and context.container:
            try:
                from magnet.validators.aggregator import ResultAggregator
                return context.container.resolve(ResultAggregator)
            except Exception as e:
                logger.warning(f"Could not resolve ResultAggregator: {e}")
        return None

    def get_action_validator():
        """Get ActionPlanValidator for action validation."""
        try:
            from magnet.kernel.action_validator import ActionPlanValidator
            return ActionPlanValidator()
        except Exception as e:
            logger.warning(f"Could not create ActionPlanValidator: {e}")
        return None

    def get_action_executor():
        """Get ActionExecutor for action execution."""
        state_manager = get_state_manager()
        if not state_manager:
            return None
        try:
            from magnet.kernel.action_executor import ActionExecutor
            from magnet.kernel.event_dispatcher import EventDispatcher
            dispatcher = EventDispatcher(design_id=getattr(state_manager._state, 'design_id', ''))
            return ActionExecutor(state_manager, dispatcher)
        except Exception as e:
            logger.warning(f"Could not create ActionExecutor: {e}")
        return None

    def get_event_dispatcher():
        """Get EventDispatcher instance."""
        state_manager = get_state_manager()
        design_id = ""
        if state_manager:
            design_id = getattr(state_manager._state, 'design_id', '')
        try:
            from magnet.kernel.event_dispatcher import EventDispatcher
            return EventDispatcher(design_id=design_id)
        except Exception as e:
            logger.warning(f"Could not create EventDispatcher: {e}")
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
                from magnet.kernel.conductor import Conductor
                context.container.resolve(Conductor)
                checks["conductor"] = True
            except Exception:
                checks["conductor"] = False

        return {
            "ready": all(checks.values()),
            "checks": checks,
        }

    # =========================================================================
    # Module 65.2: Meta endpoint for UI auto-configuration
    # =========================================================================

    @app.get("/api/v1/meta")
    async def get_meta():
        """Return server capabilities for UI auto-configuration."""
        return {
            "version": "1.2.0",
            "capabilities": ["compound_intent", "glb_export", "websocket"],
            "endpoints": {
                "designs": "/api/v1/designs",
                "health": "/health",
                "ws": "/ws/{design_id}"
            }
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
        validator=Depends(get_action_validator),
        executor=Depends(get_action_executor),
    ):
        """
        Update design value via Intent→Action Protocol.

        Routes through:
        1. ActionPlanValidator (REFINABLE_SCHEMA check, unit conversion, bounds)
        2. ActionExecutor (transactional execution, event emission)
        3. StateManager.commit() (design_version increment)

        Module 62 P0.1: Closed bypass route - no longer uses set_state_value()
        """
        import uuid
        from magnet.ui.utils import get_state_value
        from magnet.kernel.intent_protocol import Action, ActionPlan, ActionType
        from magnet.kernel.action_validator import StalePlanError

        # === BOUNDARY CHECK: Reject non-refinable paths at API level ===
        # Audit P0-4: Fail fast FIRST, before any other checks
        from magnet.core.refinable_schema import is_refinable
        if not is_refinable(update.path):
            raise HTTPException(
                status_code=400,
                detail={"error": "not_refinable", "path": update.path,
                        "message": f"Path '{update.path}' is not refinable via PATCH. "
                                   f"Only paths in REFINABLE_SCHEMA can be modified."}
            )
        # === END BOUNDARY CHECK ===

        # Verify dependencies
        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")
        if not validator:
            raise HTTPException(status_code=503, detail="ActionPlanValidator not available")
        if not executor:
            raise HTTPException(status_code=503, detail="ActionExecutor not available")

        # Verify design exists
        current_id = get_state_value(state_manager, "metadata.design_id")
        if current_id != design_id:
            raise HTTPException(status_code=404, detail="Design not found")

        # Build Action from PATCH payload
        action = Action(
            action_type=ActionType.SET,
            path=update.path,
            value=update.value,
        )

        # Create ActionPlan
        plan = ActionPlan(
            plan_id=f"patch_{uuid.uuid4().hex[:8]}",
            intent_id=f"patch_intent_{uuid.uuid4().hex[:8]}",
            design_id=design_id,
            design_version_before=state_manager.design_version,
            actions=[action],
            proposed_at=datetime.now(timezone.utc),
        )

        # Validate through ActionPlanValidator
        try:
            validation_result = validator.validate(plan, state_manager)
        except StalePlanError as e:
            raise HTTPException(
                status_code=409,
                detail={"error": "stale_plan", "message": str(e)}
            )

        if validation_result.has_rejections:
            rejection = validation_result.rejected[0]
            raise HTTPException(
                status_code=400,
                detail={"error": "validation_failed", "path": rejection[0].path, "reason": rejection[1]}
            )

        # Execute through ActionExecutor (owns transaction)
        exec_result = executor.execute(validation_result.approved, plan)
        if not exec_result.success:
            raise HTTPException(
                status_code=500,
                detail={"error": "execution_failed", "errors": exec_result.errors}
            )

        # Trigger dependency invalidation
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
            payload={
                "path": update.path,
                "design_version": exec_result.design_version_after,
                "affected_phases": affected_phases,
            },
        ))

        return {
            "path": update.path,
            "value": update.value,
            "design_version_before": exec_result.design_version_before,
            "design_version_after": exec_result.design_version_after,
            "affected_phases": affected_phases,
            "warnings": validation_result.warnings,
        }

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
    # Actions Endpoint (Intent→Action Protocol)
    # =========================================================================

    @app.post("/api/v1/designs/{design_id}/actions")
    async def submit_actions(
        design_id: str,
        action_submit: ActionSubmit,
        state_manager=Depends(get_state_manager),
        validator=Depends(get_action_validator),
        executor=Depends(get_action_executor),
    ):
        """
        Submit an ActionPlan for validation and execution.

        This is the REST interface to the Intent→Action Protocol.
        All actions are validated against REFINABLE_SCHEMA before execution.

        Returns:
            Execution result with design_version_before/after
        """
        from magnet.ui.utils import get_state_value

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")
        if not validator:
            raise HTTPException(status_code=503, detail="ActionPlanValidator not available")
        if not executor:
            raise HTTPException(status_code=503, detail="ActionExecutor not available")

        # Verify design exists
        current_id = get_state_value(state_manager, "metadata.design_id")
        if current_id != design_id:
            raise HTTPException(status_code=404, detail="Design not found")

        try:
            from magnet.kernel.intent_protocol import Action, ActionPlan, ActionType
            from magnet.kernel.action_validator import StalePlanError

            # Convert raw action dicts to Action objects
            actions = []
            for action_dict in action_submit.actions:
                action_type_str = action_dict.get("action_type", "set")
                try:
                    action_type = ActionType(action_type_str)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid action_type: {action_type_str}"
                    )

                action = Action(
                    action_type=action_type,
                    path=action_dict.get("path"),
                    value=action_dict.get("value"),
                    amount=action_dict.get("amount"),
                    unit=action_dict.get("unit"),
                    phases=action_dict.get("phases"),
                    format=action_dict.get("format"),
                    message=action_dict.get("message"),
                )
                actions.append(action)

            # Create ActionPlan
            plan = ActionPlan(
                plan_id=action_submit.plan_id,
                intent_id=action_submit.intent_id,
                design_id=design_id,
                design_version_before=action_submit.design_version_before,
                actions=actions,
                proposed_at=datetime.now(timezone.utc),
            )

            # Validate the plan
            try:
                validation_result = validator.validate(plan, state_manager)
            except StalePlanError as e:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "stale_plan",
                        "message": str(e),
                        "current_design_version": state_manager.design_version,
                    }
                )

            # Check for rejections
            if validation_result.has_rejections:
                return {
                    "success": False,
                    "plan_id": plan.plan_id,
                    "design_version": state_manager.design_version,
                    "approved_count": len(validation_result.approved),
                    "rejected_count": len(validation_result.rejected),
                    "rejections": [
                        {"path": action.path, "reason": reason}
                        for action, reason in validation_result.rejected
                    ],
                    "warnings": validation_result.warnings,
                }

            # Execute approved actions
            exec_result = executor.execute(validation_result.approved, plan)

            # Notify WebSocket clients
            ws_manager.queue_message(WSMessage(
                type="actions_executed",
                design_id=design_id,
                payload={
                    "plan_id": plan.plan_id,
                    "actions_executed": exec_result.actions_executed,
                    "design_version": exec_result.design_version_after,
                },
            ))

            return {
                "success": exec_result.success,
                "plan_id": plan.plan_id,
                "actions_executed": exec_result.actions_executed,
                "design_version_before": exec_result.design_version_before,
                "design_version_after": exec_result.design_version_after,
                "warnings": validation_result.warnings + exec_result.warnings,
                "errors": exec_result.errors,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Action submission failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # =========================================================================
    # Intent Preview Endpoint (Module 63 / 65.1)
    # =========================================================================

    @app.post("/api/v1/designs/{design_id}/intent/preview")
    async def preview_intent(
        design_id: str,
        request: IntentPreviewRequest,
        state_manager=Depends(get_state_manager),
        validator=Depends(get_action_validator),
    ):
        """
        Preview an intent without executing (Module 63 / 65.1).

        Parses natural language using REFINABLE_SCHEMA keywords only,
        validates via ActionPlanValidator, returns preview without mutation.

        Module 65.1 adds compound mode:
        - mode="single" (default): Single-action parsing (legacy)
        - mode="compound": Multi-pass extraction with gate checks

        No state changes, no version bump. ZERO MUTATION.

        Returns:
            Preview with approved/rejected/warnings from ActionPlanValidator
            Plus (compound mode): missing_required, unsupported_mentions
        """
        import uuid
        from magnet.ui.utils import get_state_value

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")
        if not validator:
            raise HTTPException(status_code=503, detail="ActionPlanValidator not available")

        # Verify design exists
        current_id = get_state_value(state_manager, "metadata.design_id")
        if current_id != design_id:
            raise HTTPException(status_code=404, detail="Design not found")

        # Module 65.1: Compound mode
        mode = getattr(request, 'mode', 'single') or 'single'

        if mode == "compound":
            return await _preview_intent_compound(
                design_id, request, state_manager, validator
            )

        # Legacy single-action mode
        from magnet.deployment.intent_parser import parse_intent_to_actions, get_guidance_message

        actions = parse_intent_to_actions(request.text)

        if not actions:
            return {
                "preview": True,
                "intent_mode": "single",
                "plan_id": None,
                "intent_id": None,
                "design_version_before": state_manager.design_version,
                "actions": [],
                "approved": [],
                "rejected": [],
                "warnings": [],
                "guidance": get_guidance_message(),
            }

        # Build ActionPlan
        from magnet.kernel.intent_protocol import ActionPlan

        plan_id = f"preview_{uuid.uuid4().hex[:8]}"
        intent_id = f"intent_{uuid.uuid4().hex[:8]}"
        version_before = request.design_version_before or state_manager.design_version

        plan = ActionPlan(
            plan_id=plan_id,
            intent_id=intent_id,
            design_id=design_id,
            design_version_before=version_before,
            actions=actions,
            proposed_at=datetime.now(timezone.utc),
        )

        # Validate via firewall (NO execution, check_stale=False for preview)
        try:
            result = validator.validate(plan, state_manager, check_stale=False)
        except Exception as e:
            logger.error(f"Validation error: {e}")
            raise HTTPException(status_code=500, detail=f"Validation error: {e}")

        # Return validator's exact output
        return {
            "preview": True,
            "plan_id": plan_id,
            "intent_id": intent_id,
            "design_version_before": state_manager.design_version,
            "actions": [
                {
                    "action_type": a.action_type.value,
                    "path": a.path,
                    "value": a.value,
                    "amount": a.amount,
                    "unit": a.unit,
                }
                for a in plan.actions
            ],
            "approved": [
                {
                    "action_type": a.action_type.value,
                    "path": a.path,
                    "value": a.value,
                    "amount": a.amount,
                    "unit": a.unit,
                }
                for a in result.approved
            ],
            "rejected": [
                {"action": {"path": a.path, "value": a.value}, "reason": reason}
                for a, reason in result.rejected
            ],
            "warnings": result.warnings,
            # Module 63.1: apply_payload - exact shape for POST /actions
            "apply_payload": {
                "plan_id": plan_id,
                "intent_id": intent_id,
                "design_version_before": state_manager.design_version,
                "actions": [
                    {
                        "action_type": a.action_type.value,
                        "path": a.path,
                        "value": a.value,
                        "amount": a.amount,
                        "unit": a.unit,
                    }
                    for a in result.approved
                ]
            },
        }

    # =========================================================================
    # Module 65.1: Compound Intent Preview Helper
    # =========================================================================

    async def _preview_intent_compound(
        design_id: str,
        request,
        state_manager,
        validator,
    ):
        """
        Compound mode preview with gate reuse on hypothetical state.

        Module 65.1: Multi-pass extraction + gate checks.
        Uses HypotheticalStateView and check_gates_on_hypothetical().

        ZERO MUTATION - no state.set(), no begin_transaction(), no commit().
        """
        import uuid
        from magnet.deployment.intent_parser import (
            extract_compound_intent,
            get_guidance_message,
        )
        from magnet.kernel.intent_protocol import ActionPlan
        from magnet.core.phase_ownership import get_phase_for_path

        # Step 1: Multi-pass extraction
        compound = extract_compound_intent(request.text)
        proposed_actions = compound["proposed_actions"]
        unsupported_mentions = compound["unsupported_mentions"]

        if not proposed_actions:
            return {
                "preview": True,
                "intent_mode": "compound",
                "plan_id": None,
                "intent_id": None,
                "design_version_before": state_manager.design_version,
                "proposed_actions": [],
                "approved": [],
                "rejected": [],
                "warnings": [],
                "missing_required": [],
                "unsupported_mentions": unsupported_mentions,
                "intent_status": "blocked",
                "guidance": get_guidance_message(),
                "apply_payload": None,
            }

        # Step 2: Build ActionPlan and validate
        plan_id = f"preview_{uuid.uuid4().hex[:8]}"
        intent_id = f"intent_{uuid.uuid4().hex[:8]}"
        version_before = request.design_version_before or state_manager.design_version

        plan = ActionPlan(
            plan_id=plan_id,
            intent_id=intent_id,
            design_id=design_id,
            design_version_before=version_before,
            actions=proposed_actions,
            proposed_at=datetime.now(timezone.utc),
        )

        try:
            result = validator.validate(plan, state_manager, check_stale=False)
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return {
                "preview": True,
                "intent_mode": "compound",
                "error": str(e),
                "intent_status": "blocked",
            }

        # Step 3: Create HypotheticalStateView with approved actions
        hypothetical = HypotheticalStateView(state_manager, result.approved)

        # Step 4: Determine target phases and check gates on hypothetical
        target_phases = set()
        for action in result.approved:
            phase = get_phase_for_path(action.path)
            if phase:
                target_phases.add(phase)

        missing_required = []
        for phase in target_phases:
            phase_missing = check_gates_on_hypothetical(phase, hypothetical)
            missing_required.extend(phase_missing)

        # Remove duplicates (same path might appear from multiple phases)
        seen_paths = set()
        unique_missing = []
        for m in missing_required:
            if m["path"] not in seen_paths:
                unique_missing.append(m)
                seen_paths.add(m["path"])
        missing_required = unique_missing

        # Step 5: Compute intent_status
        if not result.approved:
            intent_status = "blocked"
        elif missing_required:
            intent_status = "partial"
        else:
            intent_status = "complete"

        # Return compound preview response
        return {
            "preview": True,
            "intent_mode": "compound",
            "plan_id": plan_id,
            "intent_id": intent_id,
            "design_version_before": state_manager.design_version,
            "proposed_actions": [
                {
                    "action_type": a.action_type.value,
                    "path": a.path,
                    "value": a.value,
                    "amount": getattr(a, 'amount', None),
                    "unit": a.unit,
                    "source": "extracted",
                }
                for a in proposed_actions
            ],
            "approved": [
                {
                    "action_type": a.action_type.value,
                    "path": a.path,
                    "value": a.value,
                    "amount": getattr(a, 'amount', None),
                    "unit": a.unit,
                }
                for a in result.approved
            ],
            "rejected": [
                {"action": {"path": a.path, "value": a.value}, "reason": reason}
                for a, reason in result.rejected
            ],
            "warnings": result.warnings,
            "missing_required": missing_required,
            "unsupported_mentions": unsupported_mentions,
            "intent_status": intent_status,
            "apply_payload": {
                "plan_id": plan_id,
                "intent_id": intent_id,
                "design_version_before": state_manager.design_version,
                "actions": [
                    {
                        "action_type": a.action_type.value,
                        "path": a.path,
                        "value": a.value,
                        "amount": getattr(a, 'amount', None),
                        "unit": a.unit,
                    }
                    for a in result.approved
                ]
            } if result.approved else None,
        }

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

    # Module 63: Phase ID mapping (UI names → kernel canonical names)
    PHASE_ID_MAP = {
        "hull_form": "hull",
        "weight_stability": "weight",  # Note: stability is separate phase
        # All other names pass through unchanged
    }

    def _map_phase_id(ui_phase: str) -> str:
        """Map UI phase name to kernel canonical phase ID."""
        return PHASE_ID_MAP.get(ui_phase, ui_phase)

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

        # Module 63: Map UI phase name to kernel canonical name
        kernel_phase = _map_phase_id(phase)

        # v1.1: Check dependencies via PhaseMachine (fixes blocker #11)
        if phase_machine:
            try:
                if not phase_machine.can_start_phase(kernel_phase):
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
                {"phase": kernel_phase},
                design_id=design_id,
            )
            return {"job_id": job_id, "phase": phase, "status": "submitted"}

        # Run synchronously
        if conductor:
            try:
                result = conductor.run_phase(kernel_phase)

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
        executor=Depends(get_pipeline_executor),
        aggregator=Depends(get_result_aggregator),
    ):
        """Validate a specific phase using the configured pipeline executor."""
        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        # Module 63: Map UI phase name to kernel canonical name
        kernel_phase = _map_phase_id(phase)

        if not executor:
            return {
                "status": "error",
                "message": "PipelineExecutor not available",
                "phase": phase,
            }

        try:
            # Run phase validation via single authority (Guardrail #2)
            execution_state = executor.execute_phase(kernel_phase)

            # Check phase output contract (Guardrail #1)
            from magnet.validators.contracts import check_phase_contract
            contract_result = check_phase_contract(kernel_phase, state_manager)

            # Get gate status
            gate_status = None
            if aggregator:
                try:
                    gate_status = aggregator.check_gate(kernel_phase, execution_state)
                except Exception as e:
                    logger.warning(f"Gate check failed: {e}")

            # Determine overall success
            validators_passed = len([
                v for v, r in execution_state.results.items()
                if r.state.value in ["passed", "warning"]
            ])

            # Phase fails if: validators failed OR contract not satisfied
            phase_success = (
                len(execution_state.failed) == 0 and
                contract_result.satisfied
            )

            ws_manager.queue_message(WSMessage(
                type="validation_completed",
                design_id=design_id,
                payload={
                    "phase": phase,
                    "passed": phase_success,
                },
            ))

            return {
                "status": "success" if phase_success else "failed",
                "phase": phase,
                "validators_run": len(execution_state.completed) + len(execution_state.failed),
                "validators_passed": validators_passed,
                "validators_failed": len(execution_state.failed),
                "contract_satisfied": contract_result.satisfied,
                "missing_outputs": contract_result.missing_outputs,
                "can_advance": (gate_status.can_advance if gate_status else True) and contract_result.satisfied,
                "blocking_validators": gate_status.blocking_validators if gate_status else [],
                "results": {
                    vid: result.to_dict() if hasattr(result, 'to_dict') else {}
                    for vid, result in execution_state.results.items()
                },
            }
        except Exception as e:
            logger.error(f"Phase validation failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "phase": phase,
            }

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

    # =========================================================================
    # Frontend Static Files (Module 65.2: Serve ui_v2 directly)
    # =========================================================================

    # Priority 1: Serve ui_v2 directly (no build step required)
    if os.path.exists(UI_V2_PATH):
        # Mount JS and CSS directories
        js_path = os.path.join(UI_V2_PATH, "js")
        css_path = os.path.join(UI_V2_PATH, "css")
        if os.path.exists(js_path):
            app.mount("/js", StaticFiles(directory=js_path), name="js")
        if os.path.exists(css_path):
            app.mount("/css", StaticFiles(directory=css_path), name="css")
        logger.info(f"Mounted Studio UI from {UI_V2_PATH}")

        @app.get("/", response_class=HTMLResponse)
        async def serve_ui():
            """Serve Studio v7 UI (Module 65.2: single-origin architecture)."""
            index_path = os.path.join(UI_V2_PATH, "index.html")
            if os.path.exists(index_path):
                with open(index_path, 'r') as f:
                    return HTMLResponse(content=f.read())
            return HTMLResponse(content="<h1>MAGNET API</h1><p>UI not found.</p>")

        @app.get("/{full_path:path}")
        async def serve_frontend_spa(full_path: str):
            """Serve frontend SPA for all non-API routes."""
            # Don't serve frontend for API, docs, or WebSocket paths
            if full_path.startswith(("api/", "docs", "redoc", "openapi", "ws/", "health", "ready")):
                raise HTTPException(status_code=404, detail="Not found")

            # Try to serve static file from ui_v2
            static_path = os.path.join(UI_V2_PATH, full_path)
            if os.path.exists(static_path) and os.path.isfile(static_path):
                return FileResponse(static_path)

            # Fall back to index.html for SPA routing
            index_path = os.path.join(UI_V2_PATH, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            raise HTTPException(status_code=404, detail="UI not found")

    # Priority 2: Fall back to built frontend (app/dist)
    elif os.path.exists(FRONTEND_DIST_PATH):
        assets_path = os.path.join(FRONTEND_DIST_PATH, "assets")
        if os.path.exists(assets_path):
            app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
            logger.info(f"Mounted frontend assets from {assets_path}")

        @app.get("/")
        async def serve_frontend_root():
            """Serve the frontend SPA."""
            index_path = os.path.join(FRONTEND_DIST_PATH, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            raise HTTPException(status_code=404, detail="Frontend not built")

        @app.get("/{full_path:path}")
        async def serve_frontend_spa_fallback(full_path: str):
            """Serve frontend SPA for all non-API routes."""
            if full_path.startswith(("api/", "docs", "redoc", "openapi", "ws/", "health", "ready")):
                raise HTTPException(status_code=404, detail="Not found")

            static_path = os.path.join(FRONTEND_DIST_PATH, full_path)
            if os.path.exists(static_path) and os.path.isfile(static_path):
                return FileResponse(static_path)

            index_path = os.path.join(FRONTEND_DIST_PATH, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            raise HTTPException(status_code=404, detail="Frontend not built")
    else:
        logger.info(f"No UI found at {UI_V2_PATH} or {FRONTEND_DIST_PATH}")

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


# Module-level app instance for uvicorn
app = create_fastapi_app()
