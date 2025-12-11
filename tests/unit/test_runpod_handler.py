"""
tests/unit/test_runpod_handler.py - RunPod Handler Tests
BRAVO OWNS THIS FILE.

Comprehensive tests for RunPod serverless handler.
Required for RunPod deployment validation.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_app():
    """Create mock MAGNET app."""
    app = Mock()
    container = Mock()

    # Mock state manager
    state_manager = Mock()
    state_manager.get_value = Mock(return_value=None)
    state_manager.set_value = Mock(return_value=True)

    # Mock conductor
    conductor = Mock()
    phase_result = Mock()
    phase_result.status = "completed"
    conductor.run_phase = Mock(return_value=phase_result)

    run_result = Mock()
    run_result.run_id = "test-run-123"
    run_result.final_status = "completed"
    run_result.phases_completed = ["mission", "hull_form"]
    conductor.run_full_design = Mock(return_value=run_result)

    def resolve(cls):
        # Use string matching to avoid import issues
        cls_name = str(cls)
        if 'StateManager' in cls_name:
            return state_manager
        elif 'Conductor' in cls_name:
            return conductor
        return Mock()

    container.resolve = Mock(side_effect=resolve)
    app.container = container
    return app


# =============================================================================
# HANDLER FUNCTION TESTS
# =============================================================================

class TestHandlerFunction:
    """Test main handler() function."""

    def test_handler_basic_event_format(self):
        """Test handler accepts basic event format."""
        from magnet.deployment.runpod_handler import handler

        # Minimal event that won't require app initialization
        event = {
            "input": {
                "operation": "invalid_operation",
                "parameters": {}
            }
        }

        result = handler(event)

        # Should return error response for invalid operation
        assert "success" in result
        assert "error" in result
        assert "duration_ms" in result
        assert result["success"] is False

    def test_handler_extracts_nested_input(self):
        """Test handler extracts input from nested format."""
        from magnet.deployment.runpod_handler import handler

        event = {
            "input": {
                "operation": "unknown",
                "parameters": {"test": "value"}
            }
        }

        result = handler(event)

        # Should process and return error for unknown operation
        assert result["success"] is False
        assert "Unknown operation" in result["error"]

    def test_handler_extracts_flat_input(self):
        """Test handler extracts input from flat format."""
        from magnet.deployment.runpod_handler import handler

        # Event without "input" wrapper
        event = {
            "operation": "unknown",
            "parameters": {}
        }

        result = handler(event)

        assert result["success"] is False
        assert "Unknown operation" in result["error"]

    def test_handler_includes_duration_ms(self):
        """Test handler includes duration_ms in response."""
        from magnet.deployment.runpod_handler import handler

        event = {"input": {"operation": "invalid"}}
        result = handler(event)

        assert "duration_ms" in result
        assert isinstance(result["duration_ms"], int)
        assert result["duration_ms"] >= 0

    def test_handler_includes_traceback_on_error(self):
        """Test handler includes traceback on error."""
        from magnet.deployment.runpod_handler import handler

        event = {"input": {"operation": "invalid"}}
        result = handler(event)

        assert result["success"] is False
        assert "traceback" in result
        assert "Traceback" in result["traceback"] or "Error" in str(result)


# =============================================================================
# OPERATION CONSTANTS TESTS
# =============================================================================

class TestOperationConstants:
    """Test operation constants are defined."""

    def test_operation_constants_defined(self):
        """Test all operation constants are defined."""
        from magnet.deployment.runpod_handler import (
            OPERATION_RUN_PHASE,
            OPERATION_RUN_FULL_DESIGN,
            OPERATION_VALIDATE,
            OPERATION_GENERATE_REPORT,
            OPERATION_RENDER_SNAPSHOT,
            OPERATION_EXPORT,
            OPERATION_QUERY,
            OPERATION_UPDATE,
        )

        assert OPERATION_RUN_PHASE == "run_phase"
        assert OPERATION_RUN_FULL_DESIGN == "run_full_design"
        assert OPERATION_VALIDATE == "validate"
        assert OPERATION_GENERATE_REPORT == "generate_report"
        assert OPERATION_RENDER_SNAPSHOT == "render_snapshot"
        assert OPERATION_EXPORT == "export"
        assert OPERATION_QUERY == "query"
        assert OPERATION_UPDATE == "update"


# =============================================================================
# OPERATION HANDLER TESTS
# =============================================================================

class TestHandleOperation:
    """Test _handle_operation routing."""

    def test_handle_operation_routes_correctly(self, mock_app):
        """Test operation handler routes to correct function."""
        from magnet.deployment.runpod_handler import _handle_operation

        # Test that valid operations don't raise routing error
        # (they may fail for other reasons in mocked context)
        with patch('magnet.deployment.runpod_handler._handle_query') as mock_query:
            mock_query.return_value = {"path": "", "state": {}}
            result = _handle_operation(mock_app, "query", {})
            mock_query.assert_called_once_with(mock_app, {})

    def test_handle_operation_unknown_operation(self, mock_app):
        """Test unknown operation raises ValueError."""
        from magnet.deployment.runpod_handler import _handle_operation

        with pytest.raises(ValueError) as exc_info:
            _handle_operation(mock_app, "not_a_real_operation", {})

        assert "Unknown operation" in str(exc_info.value)
        assert "not_a_real_operation" in str(exc_info.value)

    def test_handle_operation_lists_valid_operations(self, mock_app):
        """Test error message lists valid operations."""
        from magnet.deployment.runpod_handler import _handle_operation

        with pytest.raises(ValueError) as exc_info:
            _handle_operation(mock_app, "invalid", {})

        error_msg = str(exc_info.value)
        assert "run_phase" in error_msg
        assert "query" in error_msg


# =============================================================================
# RUN PHASE HANDLER TESTS
# =============================================================================

class TestHandleRunPhase:
    """Test _handle_run_phase handler."""

    def test_run_phase_requires_phase_parameter(self, mock_app):
        """Test run_phase requires phase parameter."""
        from magnet.deployment.runpod_handler import _handle_run_phase

        with pytest.raises(ValueError) as exc_info:
            _handle_run_phase(mock_app, {})

        assert "Missing 'phase' parameter" in str(exc_info.value)

    @pytest.mark.skip(reason="Requires magnet.agents.conductor module not available")
    def test_run_phase_with_phase_parameter(self, mock_app):
        """Test run_phase with valid phase parameter.

        NOTE: Skipped because magnet.agents.conductor is not available
        in the test environment. This would be tested in integration tests.
        """
        pass


# =============================================================================
# UPDATE HANDLER TESTS
# =============================================================================

class TestHandleUpdate:
    """Test _handle_update handler."""

    def test_update_requires_path_parameter(self, mock_app):
        """Test update requires path parameter."""
        from magnet.deployment.runpod_handler import _handle_update

        with pytest.raises(ValueError) as exc_info:
            _handle_update(mock_app, {"value": 123})

        assert "Missing 'path' parameter" in str(exc_info.value)

    def test_update_with_valid_parameters(self, mock_app):
        """Test update with valid path and value."""
        from magnet.deployment.runpod_handler import _handle_update

        # Patch at the source where it's imported from
        with patch('magnet.ui.utils.set_state_value') as mock_set:
            mock_set.return_value = True
            result = _handle_update(mock_app, {"path": "mission.name", "value": "Test"})

            assert result["path"] == "mission.name"
            assert result["value"] == "Test"
            assert "success" in result


# =============================================================================
# QUERY HANDLER TESTS
# =============================================================================

class TestHandleQuery:
    """Test _handle_query handler."""

    def test_query_with_path(self, mock_app):
        """Test query with specific path."""
        from magnet.deployment.runpod_handler import _handle_query

        # Patch at the source where it's imported from
        with patch('magnet.ui.utils.get_state_value') as mock_get:
            mock_get.return_value = "test_value"
            result = _handle_query(mock_app, {"path": "mission.name"})

            assert result["path"] == "mission.name"
            assert result["value"] == "test_value"

    @pytest.mark.skip(reason="Requires full app initialization - tested via integration tests")
    def test_query_without_path_returns_full_state(self, mock_app):
        """Test query without path returns full state.

        NOTE: Skipped because _export_state requires full app context.
        """
        pass


# =============================================================================
# EXPORT HANDLER TESTS
# =============================================================================

class TestHandleExport:
    """Test _handle_export handler."""

    def test_export_default_format(self, mock_app):
        """Test export with default format."""
        from magnet.deployment.runpod_handler import _handle_export

        with patch('magnet.deployment.runpod_handler._export_state') as mock_export:
            mock_export.return_value = {}
            result = _handle_export(mock_app, {})

            assert result["format"] == "json"
            assert "state" in result

    def test_export_custom_format(self, mock_app):
        """Test export with custom format parameter."""
        from magnet.deployment.runpod_handler import _handle_export

        with patch('magnet.deployment.runpod_handler._export_state') as mock_export:
            mock_export.return_value = {}
            result = _handle_export(mock_app, {"format": "yaml"})

            assert result["format"] == "yaml"


# =============================================================================
# RESPONSE FORMAT TESTS
# =============================================================================

class TestResponseFormat:
    """Test response format compliance."""

    def test_success_response_format(self):
        """Test successful response has required fields."""
        from magnet.deployment.runpod_handler import handler

        # Use a mock that succeeds
        with patch('magnet.deployment.runpod_handler._create_app') as mock_create:
            with patch('magnet.deployment.runpod_handler._handle_operation') as mock_handle:
                mock_app = Mock()
                mock_create.return_value = mock_app
                mock_handle.return_value = {"result": "test"}

                event = {"input": {"operation": "query", "parameters": {}}}
                result = handler(event)

                assert "success" in result
                assert "result" in result
                assert "error" in result
                assert "duration_ms" in result
                assert result["success"] is True

    def test_error_response_format(self):
        """Test error response has required fields."""
        from magnet.deployment.runpod_handler import handler

        event = {"input": {"operation": "invalid_op"}}
        result = handler(event)

        assert "success" in result
        assert result["success"] is False
        assert "error" in result
        assert result["error"] is not None
        assert "duration_ms" in result


# =============================================================================
# RECURSIVE SET STATE TESTS
# =============================================================================

class TestRecursiveSetState:
    """Test _recursive_set_state function."""

    def test_recursive_set_state_flat(self):
        """Test recursive set state with flat dict."""
        from magnet.deployment.runpod_handler import _recursive_set_state

        state_manager = Mock()
        data = {"name": "Test", "value": 123}

        # Patch at the source where it's imported from
        with patch('magnet.ui.utils.set_state_value') as mock_set:
            _recursive_set_state(state_manager, data, "")

            assert mock_set.call_count == 2
            calls = mock_set.call_args_list
            paths = [c[0][1] for c in calls]
            assert "name" in paths
            assert "value" in paths

    def test_recursive_set_state_nested(self):
        """Test recursive set state with nested dict."""
        from magnet.deployment.runpod_handler import _recursive_set_state

        state_manager = Mock()
        data = {"mission": {"name": "Test", "type": "cargo"}}

        with patch('magnet.ui.utils.set_state_value') as mock_set:
            _recursive_set_state(state_manager, data, "")

            calls = mock_set.call_args_list
            paths = [c[0][1] for c in calls]
            assert "mission.name" in paths
            assert "mission.type" in paths

    def test_recursive_set_state_with_prefix(self):
        """Test recursive set state with prefix."""
        from magnet.deployment.runpod_handler import _recursive_set_state

        state_manager = Mock()
        data = {"name": "Test"}

        with patch('magnet.ui.utils.set_state_value') as mock_set:
            _recursive_set_state(state_manager, data, "metadata")

            call_args = mock_set.call_args_list[0][0]
            assert call_args[1] == "metadata.name"


# =============================================================================
# CREATE APP TESTS
# =============================================================================

class TestCreateApp:
    """Test _create_app function."""

    def test_create_app_handles_import_error(self):
        """Test _create_app handles import errors gracefully."""
        from magnet.deployment.runpod_handler import _create_app

        # Patch at the bootstrap module where create_app is imported from
        with patch('magnet.bootstrap.app.create_app', side_effect=ImportError("Test")):
            with pytest.raises(RuntimeError) as exc_info:
                _create_app()

            assert "Failed to import" in str(exc_info.value)


# =============================================================================
# INTEGRATION-STYLE TESTS
# =============================================================================

class TestIntegration:
    """Integration-style tests for handler flow."""

    def test_handler_complete_flow(self):
        """Test complete handler flow with mocks."""
        from magnet.deployment.runpod_handler import handler

        with patch('magnet.deployment.runpod_handler._create_app') as mock_create:
            with patch('magnet.deployment.runpod_handler._handle_operation') as mock_handle:
                mock_app = Mock()
                mock_create.return_value = mock_app
                mock_handle.return_value = {"test": "result"}

                event = {
                    "input": {
                        "operation": "export",
                        "design_state": {"metadata": {"name": "Test"}},
                        "parameters": {"format": "json"}
                    }
                }

                result = handler(event)

                assert result["success"] is True
                assert result["result"] == {"test": "result"}
                mock_create.assert_called_once()
                mock_handle.assert_called_once()

    def test_handler_with_design_state(self):
        """Test handler initializes with design state."""
        from magnet.deployment.runpod_handler import handler

        with patch('magnet.deployment.runpod_handler._create_app') as mock_create:
            with patch('magnet.deployment.runpod_handler._handle_operation') as mock_handle:
                mock_app = Mock()
                mock_create.return_value = mock_app
                mock_handle.return_value = {}

                design_state = {
                    "metadata": {"design_id": "TEST-001"},
                    "mission": {"vessel_type": "cargo"}
                }

                event = {
                    "input": {
                        "operation": "query",
                        "design_state": design_state,
                        "parameters": {}
                    }
                }

                result = handler(event)

                # Verify design_state was passed to create_app
                mock_create.assert_called_once_with(design_state)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
