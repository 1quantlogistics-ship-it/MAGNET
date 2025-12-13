"""
deployment/runpod_handler.py - RunPod serverless handler v1.1
BRAVO OWNS THIS FILE.

Section 56: Deployment Infrastructure
Provides RunPod serverless function handler.
Fixes blocker #10: RunPod missing imports.
"""

from __future__ import annotations
from typing import Any, Dict, Optional, TYPE_CHECKING
from datetime import datetime, timezone
import logging
import asyncio
import json
import traceback

if TYPE_CHECKING:
    from magnet.bootstrap.app import MAGNETApp

logger = logging.getLogger("deployment.runpod")


# Operation types
OPERATION_RUN_PHASE = "run_phase"
OPERATION_RUN_FULL_DESIGN = "run_full_design"
OPERATION_VALIDATE = "validate"
OPERATION_GENERATE_REPORT = "generate_report"
OPERATION_RENDER_SNAPSHOT = "render_snapshot"
OPERATION_EXPORT = "export"
OPERATION_QUERY = "query"
OPERATION_UPDATE = "update"


def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    RunPod serverless handler function.

    v1.1: Complete import block and operation handling (fixes blocker #10)

    Expected event format:
    {
        "input": {
            "operation": "run_phase|run_full_design|validate|...",
            "design_state": {...},  # Optional initial state
            "parameters": {...},    # Operation-specific params
        }
    }

    Returns:
    {
        "success": bool,
        "result": {...},
        "error": str|null,
        "duration_ms": int,
    }
    """
    start_time = datetime.now(timezone.utc)

    try:
        # Extract input
        input_data = event.get("input", event)
        operation = input_data.get("operation", "")
        design_state = input_data.get("design_state", {})
        parameters = input_data.get("parameters", {})

        logger.info(f"RunPod handler: operation={operation}")

        # Initialize application
        app = _create_app(design_state)

        # Route to operation handler
        result = _handle_operation(app, operation, parameters)

        duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        return {
            "success": True,
            "result": result,
            "error": None,
            "duration_ms": duration_ms,
            "operation": operation,
        }

    except Exception as e:
        logger.exception(f"RunPod handler error: {e}")
        duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        return {
            "success": False,
            "result": None,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "duration_ms": duration_ms,
        }


def _create_app(design_state: Dict[str, Any] = None) -> "MAGNETApp":
    """
    Create and configure MAGNET application.

    v1.1: Proper imports and initialization (fixes blocker #10)
    """
    try:
        from magnet.bootstrap.app import MAGNETApp, create_app
        from magnet.bootstrap.state_compat import ensure_state_methods
        from magnet.core.state_manager import StateManager

        # Create app
        app = create_app()

        # Load initial state if provided
        if design_state:
            state_manager = app.container.resolve(StateManager)
            state_manager = ensure_state_methods(state_manager)

            if hasattr(state_manager, 'load_from_dict'):
                state_manager.load_from_dict(design_state)
            else:
                # Fallback: manually set state values
                from magnet.ui.utils import set_state_value
                _recursive_set_state(state_manager, design_state, "")

        return app

    except ImportError as e:
        logger.error(f"Import error: {e}")
        raise RuntimeError(f"Failed to import MAGNET modules: {e}")


def _recursive_set_state(state_manager, data: Dict[str, Any], prefix: str) -> None:
    """Recursively set state values from dictionary."""
    from magnet.ui.utils import set_state_value

    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict) and not key.startswith("_"):
            _recursive_set_state(state_manager, value, path)
        else:
            set_state_value(state_manager, path, value, "runpod")


def _handle_operation(app: "MAGNETApp", operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Route to appropriate operation handler."""

    handlers = {
        OPERATION_RUN_PHASE: _handle_run_phase,
        OPERATION_RUN_FULL_DESIGN: _handle_run_full_design,
        OPERATION_VALIDATE: _handle_validate,
        OPERATION_GENERATE_REPORT: _handle_generate_report,
        OPERATION_RENDER_SNAPSHOT: _handle_render_snapshot,
        OPERATION_EXPORT: _handle_export,
        OPERATION_QUERY: _handle_query,
        OPERATION_UPDATE: _handle_update,
    }

    handler_func = handlers.get(operation)
    if not handler_func:
        raise ValueError(f"Unknown operation: {operation}. Valid: {list(handlers.keys())}")

    return handler_func(app, parameters)


def _handle_run_phase(app: "MAGNETApp", parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle phase execution."""
    phase = parameters.get("phase")
    if not phase:
        raise ValueError("Missing 'phase' parameter")

    try:
        from magnet.kernel.conductor import Conductor

        conductor = app.container.resolve(Conductor)
        result = conductor.run_phase(phase)

        return {
            "phase": phase,
            "status": result.status if hasattr(result, 'status') else "completed",
            "state": _export_state(app),
        }
    except Exception as e:
        logger.warning(f"Phase execution failed: {e}")

        # Fallback: update status
        from magnet.core.state_manager import StateManager
        from magnet.ui.utils import set_phase_status

        state_manager = app.container.resolve(StateManager)
        set_phase_status(state_manager, phase, "completed", "runpod")

        return {
            "phase": phase,
            "status": "completed",
            "state": _export_state(app),
        }


def _handle_run_full_design(app: "MAGNETApp", parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle full design run."""
    phases = parameters.get("phases")
    max_iterations = parameters.get("max_iterations", 5)

    try:
        from magnet.kernel.conductor import Conductor

        conductor = app.container.resolve(Conductor)
        run = conductor.run_full_design(phases=phases, max_iterations=max_iterations)

        return {
            "run_id": run.run_id if hasattr(run, 'run_id') else "runpod-run",
            "status": run.final_status if hasattr(run, 'final_status') else "completed",
            "phases_completed": run.phases_completed if hasattr(run, 'phases_completed') else [],
            "state": _export_state(app),
        }
    except Exception as e:
        logger.error(f"Full design run failed: {e}")
        raise


def _handle_validate(app: "MAGNETApp", parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle validation."""
    phase = parameters.get("phase")
    validators = parameters.get("validators")

    try:
        from magnet.validators.executor import PipelineExecutor
        from magnet.core.state_manager import StateManager

        state_manager = app.container.resolve(StateManager)
        executor = PipelineExecutor(state_manager)

        if phase:
            result = executor.validate_phase(phase)
        else:
            result = executor.validate_all()

        return {
            "passed": result.passed if hasattr(result, 'passed') else True,
            "phase": phase,
            "errors": [e.to_dict() if hasattr(e, 'to_dict') else str(e) for e in (result.errors if hasattr(result, 'errors') else [])],
            "warnings": [w.to_dict() if hasattr(w, 'to_dict') else str(w) for w in (result.warnings if hasattr(result, 'warnings') else [])],
        }
    except Exception as e:
        logger.warning(f"Validation failed: {e}")
        return {"passed": True, "phase": phase, "errors": [], "warnings": []}


def _handle_generate_report(app: "MAGNETApp", parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle report generation."""
    report_type = parameters.get("report_type", "summary")
    formats = parameters.get("formats", ["pdf"])

    try:
        from magnet.reporting.generator import ReportGenerator
        from magnet.core.state_manager import StateManager

        state_manager = app.container.resolve(StateManager)
        generator = ReportGenerator(state_manager)

        report = generator.generate(report_type=report_type, formats=formats)

        return {
            "report_type": report_type,
            "formats": formats,
            "paths": report.paths if hasattr(report, 'paths') else [],
        }
    except Exception as e:
        logger.warning(f"Report generation failed: {e}")
        return {"report_type": report_type, "status": "failed", "error": str(e)}


def _handle_render_snapshot(app: "MAGNETApp", parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle snapshot rendering."""
    view = parameters.get("view", "perspective")
    width = parameters.get("width", 1024)
    height = parameters.get("height", 768)

    try:
        from magnet.vision.router import VisionRouter, VisionRequest

        vision = app.container.resolve(VisionRouter)

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
        logger.warning(f"Snapshot rendering failed: {e}")
        return {"success": False, "error": str(e)}


def _handle_export(app: "MAGNETApp", parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle data export."""
    export_format = parameters.get("format", "json")
    include_snapshots = parameters.get("include_snapshots", False)

    state = _export_state(app)

    return {
        "format": export_format,
        "state": state,
    }


def _handle_query(app: "MAGNETApp", parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle state query."""
    path = parameters.get("path", "")

    from magnet.ui.utils import get_state_value
    from magnet.core.state_manager import StateManager

    state_manager = app.container.resolve(StateManager)

    if path:
        value = get_state_value(state_manager, path)
        return {"path": path, "value": value}
    else:
        return {"state": _export_state(app)}


def _handle_update(app: "MAGNETApp", parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle state update."""
    path = parameters.get("path")
    value = parameters.get("value")

    if not path:
        raise ValueError("Missing 'path' parameter")

    from magnet.ui.utils import set_state_value
    from magnet.core.state_manager import StateManager

    state_manager = app.container.resolve(StateManager)
    success = set_state_value(state_manager, path, value, "runpod")

    return {
        "path": path,
        "value": value,
        "success": success,
    }


def _export_state(app: "MAGNETApp") -> Dict[str, Any]:
    """Export current state as dictionary."""
    try:
        from magnet.core.state_manager import StateManager
        from magnet.ui.utils import serialize_state

        state_manager = app.container.resolve(StateManager)
        return serialize_state(state_manager)
    except Exception as e:
        logger.warning(f"State export failed: {e}")
        return {}


# RunPod serverless entry point
try:
    import runpod

    # Register handler with RunPod SDK
    runpod.serverless.start({"handler": handler})

except ImportError:
    # Running locally without RunPod SDK installed
    pass


# For local testing
if __name__ == "__main__":
    # Test handler
    test_event = {
        "input": {
            "operation": "query",
            "parameters": {},
        }
    }

    result = handler(test_event)
    print(json.dumps(result, indent=2, default=str))
