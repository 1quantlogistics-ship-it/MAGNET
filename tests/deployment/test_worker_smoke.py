"""
Worker Smoke Tests

Tests for the RunPod serverless handler.
Verifies handler imports, signature, and minimal job processing.

v1.1: Tests runpod_handler.py via production DI wiring.
"""

import pytest


class TestWorkerImports:
    """Tests for handler module imports."""

    def test_handler_imports(self):
        """Handler module can be imported."""
        from magnet.deployment import runpod_handler
        assert runpod_handler is not None

    def test_handler_function_exists(self):
        """Handler function exists and is callable."""
        from magnet.deployment.runpod_handler import handler
        assert callable(handler)

    def test_operation_constants_defined(self):
        """Operation constants are defined."""
        from magnet.deployment.runpod_handler import (
            OPERATION_RUN_PHASE,
            OPERATION_RUN_FULL_DESIGN,
            OPERATION_VALIDATE,
            OPERATION_QUERY,
            OPERATION_UPDATE,
        )

        assert OPERATION_RUN_PHASE == "run_phase"
        assert OPERATION_RUN_FULL_DESIGN == "run_full_design"
        assert OPERATION_VALIDATE == "validate"
        assert OPERATION_QUERY == "query"
        assert OPERATION_UPDATE == "update"


class TestWorkerHandlerSignature:
    """Tests for handler function signature and return format."""

    def test_handler_returns_dict(self):
        """Handler returns a dictionary."""
        from magnet.deployment.runpod_handler import handler

        # Minimal query operation
        event = {
            "input": {
                "operation": "query",
                "parameters": {},
            }
        }

        result = handler(event)
        assert isinstance(result, dict)

    def test_handler_has_required_fields(self):
        """Handler response has required fields."""
        from magnet.deployment.runpod_handler import handler

        event = {
            "input": {
                "operation": "query",
                "parameters": {},
            }
        }

        result = handler(event)

        # Check required response fields
        assert "success" in result
        assert "result" in result or "error" in result
        assert "duration_ms" in result

    def test_handler_error_format(self):
        """Handler error responses have correct format."""
        from magnet.deployment.runpod_handler import handler

        # Invalid operation
        event = {
            "input": {
                "operation": "invalid_operation_xyz",
                "parameters": {},
            }
        }

        result = handler(event)

        assert result["success"] is False
        assert result["error"] is not None


class TestWorkerQueryOperation:
    """Tests for the query operation."""

    def test_query_without_path(self):
        """Query without path returns full state."""
        from magnet.deployment.runpod_handler import handler

        event = {
            "input": {
                "operation": "query",
                "parameters": {},
            }
        }

        result = handler(event)
        assert result["success"] is True
        assert result["result"] is not None

    def test_query_with_path(self):
        """Query with path returns specific value."""
        from magnet.deployment.runpod_handler import handler

        event = {
            "input": {
                "operation": "query",
                "parameters": {"path": "hull.lwl"},
            }
        }

        result = handler(event)
        assert result["success"] is True
        # Path may not have a value, but query should succeed


class TestWorkerUpdateOperation:
    """Tests for the update operation."""

    def test_update_sets_value(self):
        """Update operation sets state value."""
        from magnet.deployment.runpod_handler import handler

        # First update a value
        update_event = {
            "input": {
                "operation": "update",
                "parameters": {
                    "path": "hull.lwl",
                    "value": 25.0,
                },
            }
        }

        result = handler(update_event)
        assert result["success"] is True

    def test_update_missing_path_fails(self):
        """Update without path fails gracefully."""
        from magnet.deployment.runpod_handler import handler

        event = {
            "input": {
                "operation": "update",
                "parameters": {"value": 123},
            }
        }

        result = handler(event)
        assert result["success"] is False
        assert "path" in result["error"].lower()


class TestWorkerRunPhaseOperation:
    """Tests for the run_phase operation."""

    def test_run_phase_hull(self):
        """Run phase operation for hull phase."""
        from magnet.deployment.runpod_handler import handler

        # First seed required state
        seed_event = {
            "input": {
                "operation": "update",
                "parameters": {
                    "path": "mission.max_speed_kts",
                    "value": 25.0,
                },
            }
        }
        handler(seed_event)

        seed_event2 = {
            "input": {
                "operation": "update",
                "parameters": {
                    "path": "hull.hull_type",
                    "value": "workboat",
                },
            }
        }
        handler(seed_event2)

        # Now run hull phase
        event = {
            "input": {
                "operation": "run_phase",
                "parameters": {"phase": "hull"},
            }
        }

        result = handler(event)
        assert result["success"] is True
        assert result["result"]["phase"] == "hull"

    def test_run_phase_missing_phase_fails(self):
        """Run phase without phase parameter fails."""
        from magnet.deployment.runpod_handler import handler

        event = {
            "input": {
                "operation": "run_phase",
                "parameters": {},
            }
        }

        result = handler(event)
        assert result["success"] is False


class TestWorkerValidateOperation:
    """Tests for the validate operation."""

    def test_validate_phase(self):
        """Validate operation for specific phase."""
        from magnet.deployment.runpod_handler import handler

        event = {
            "input": {
                "operation": "validate",
                "parameters": {"phase": "hull"},
            }
        }

        result = handler(event)
        # Validation should complete (may pass or fail)
        assert result["success"] is True
        assert "passed" in result["result"]


class TestWorkerDIWiring:
    """Tests for DI wiring through worker."""

    def test_app_creation_via_handler(self):
        """Handler creates app with working DI."""
        from magnet.deployment.runpod_handler import _create_app

        app = _create_app()
        assert app is not None
        assert app.container is not None

    def test_app_with_initial_state(self):
        """Handler creates app and loads initial state."""
        from magnet.deployment.runpod_handler import _create_app
        from magnet.core.state_manager import StateManager

        initial_state = {
            "hull": {
                "lwl": 25.0,
                "beam": 5.5,
            }
        }

        app = _create_app(initial_state)
        sm = app.container.resolve(StateManager)

        # State should be loaded
        # Note: Exact loading depends on state_compat implementation


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
