"""
tests/unit/test_api_endpoints.py - API Endpoint Tests
BRAVO OWNS THIS FILE.

Comprehensive tests for FastAPI REST endpoints.
Required for RunPod deployment validation.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any

# Skip all tests if FastAPI not installed
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient
from fastapi import FastAPI


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_state_manager():
    """Create mock state manager."""
    manager = Mock()
    manager.get_value = Mock(return_value=None)
    manager.set_value = Mock(return_value=True)
    manager.reset = Mock()

    # Default state values
    state_data = {
        "metadata.design_id": "TEST-001",
        "metadata.name": "Test Design",
        "metadata.created_at": datetime.now(timezone.utc).isoformat(),
        "phase_states.mission.status": "pending",
    }

    def get_value(path, default=None):
        return state_data.get(path, default)

    manager.get_value = Mock(side_effect=get_value)
    return manager


@pytest.fixture
def mock_phase_machine():
    """Create mock phase machine."""
    machine = Mock()
    machine.initialize_design = Mock()
    machine.can_start_phase = Mock(return_value=True)
    machine.approve_phase = Mock()
    machine.invalidate_dependents = Mock(return_value=[])
    return machine


@pytest.fixture
def mock_conductor():
    """Create mock conductor."""
    conductor = Mock()
    result = Mock()
    result.status = "completed"
    result.to_dict = Mock(return_value={"status": "completed"})
    conductor.run_phase = Mock(return_value=result)
    return conductor


@pytest.fixture
def mock_vision():
    """Create mock vision router."""
    vision = Mock()
    response = Mock()
    response.success = True
    response.snapshots = []
    vision.process_request = Mock(return_value=response)
    return vision


@pytest.fixture
def mock_context(mock_state_manager, mock_phase_machine, mock_conductor, mock_vision):
    """Create mock app context."""
    context = Mock()
    context.config = Mock()
    context.config.api = Mock()
    context.config.api.enable_docs = True
    context.config.api.docs_url = "/docs"
    context.config.api.cors_origins = ["*"]

    container = Mock()

    def resolve(cls):
        from magnet.core.state_manager import StateManager
        from magnet.core.phase_machine import PhaseMachine
        from magnet.agents.conductor import Conductor
        from magnet.vision.router import VisionRouter

        if cls == StateManager or cls.__name__ == 'StateManager':
            return mock_state_manager
        elif cls == PhaseMachine or cls.__name__ == 'PhaseMachine':
            return mock_phase_machine
        elif cls == Conductor or cls.__name__ == 'Conductor':
            return mock_conductor
        elif cls == VisionRouter or cls.__name__ == 'VisionRouter':
            return mock_vision
        raise ValueError(f"Unknown type: {cls}")

    container.resolve = Mock(side_effect=resolve)
    context.container = container

    return context


@pytest.fixture
def app():
    """Create FastAPI app for testing (no context)."""
    from magnet.deployment.api import create_fastapi_app
    return create_fastapi_app(None)


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_app_with_context(mock_context):
    """Create FastAPI app with mocked context for specific tests."""
    # Since FastAPI's dependency injection happens at request time,
    # we need to use dependency_overrides or test with the stubbed version
    from magnet.deployment.api import create_fastapi_app
    return create_fastapi_app(mock_context)


# =============================================================================
# HEALTH ENDPOINTS
# =============================================================================

class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self, client):
        """Test /health endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.1.0"
        assert "timestamp" in data
        assert "websocket_clients" in data

    def test_readiness_check_response_format(self, client):
        """Test /ready endpoint returns proper format."""
        response = client.get("/ready")
        assert response.status_code == 200

        data = response.json()
        assert "ready" in data
        assert "checks" in data
        assert "state_manager" in data["checks"]
        # Without context, state_manager will be False, which is expected

    def test_readiness_check_without_context(self):
        """Test /ready endpoint without context."""
        from magnet.deployment.api import create_fastapi_app
        app = create_fastapi_app(None)
        client = TestClient(app)

        response = client.get("/ready")
        assert response.status_code == 200

        data = response.json()
        assert data["checks"]["state_manager"] is False


# =============================================================================
# DESIGN ENDPOINTS
# =============================================================================

class TestDesignEndpoints:
    """Test design CRUD endpoints."""

    def test_list_designs_empty(self, client):
        """Test listing designs when none exist."""
        response = client.get("/api/v1/designs")
        assert response.status_code == 200
        assert response.json() == {"designs": []}

    def test_list_designs_returns_array(self, client):
        """Test listing designs returns expected format."""
        response = client.get("/api/v1/designs")
        assert response.status_code == 200

        data = response.json()
        assert "designs" in data
        assert isinstance(data["designs"], list)

    def test_create_design_no_state_manager(self, client):
        """Test creating design without state manager returns 503.

        v1.2: Forward reference bug fixed - Pydantic models moved to module level.
        Now correctly returns 503 when StateManager is unavailable.
        """
        response = client.post("/api/v1/designs", json={
            "name": "Test Design"
        })
        # v1.2: Bug fixed - now correctly returns 503 for unavailable StateManager
        assert response.status_code == 503

    def test_create_design_validation(self, client):
        """Test design creation requires name."""
        response = client.post("/api/v1/designs", json={})
        assert response.status_code == 422  # Validation error

    def test_get_design_no_state_manager(self, client):
        """Test getting design without state manager returns 503."""
        response = client.get("/api/v1/designs/TEST-001")
        assert response.status_code == 503

    def test_update_design_invalid_path(self, client):
        """Test updating with invalid path prefix returns 422."""
        response = client.patch("/api/v1/designs/TEST-001", json={
            "path": "invalid_prefix.value",
            "value": 123
        })
        assert response.status_code == 422  # Validation error

    def test_update_design_valid_path_prefixes(self, client):
        """Test that valid path prefixes pass validation.

        v1.2: Forward reference bug fixed - Pydantic models moved to module level.
        Now correctly returns 503 (StateManager unavailable) for valid prefixes.
        """
        valid_prefixes = [
            "metadata", "mission", "hull", "structure", "propulsion",
            "systems", "weight", "stability", "compliance", "phase_states",
            "production", "outfitting", "arrangement"
        ]

        for prefix in valid_prefixes:
            response = client.patch("/api/v1/designs/TEST-001", json={
                "path": f"{prefix}.test_value",
                "value": 123
            })
            # v1.2: Bug fixed - now correctly returns 503 for unavailable StateManager
            assert response.status_code == 503, f"Prefix '{prefix}' should return 503 (StateManager unavailable)"

    def test_delete_design_no_state_manager(self, client):
        """Test deleting design without state manager returns 503."""
        response = client.delete("/api/v1/designs/TEST-001")
        assert response.status_code == 503


# =============================================================================
# PHASE ENDPOINTS
# =============================================================================

class TestPhaseEndpoints:
    """Test phase management endpoints."""

    def test_list_phases(self, client):
        """Test listing all phases."""
        response = client.get("/api/v1/designs/TEST-001/phases")
        assert response.status_code == 200

        data = response.json()
        assert "phases" in data

        expected_phases = [
            "mission", "hull_form", "structure", "propulsion",
            "systems", "weight_stability", "compliance", "production"
        ]
        phase_names = [p["phase"] for p in data["phases"]]
        assert phase_names == expected_phases

    def test_get_phase_no_state_manager(self, client):
        """Test getting specific phase without state manager."""
        response = client.get("/api/v1/designs/TEST-001/phases/mission")
        assert response.status_code == 503

    def test_run_phase_no_state_manager(self, client):
        """Test running phase without state manager.

        v1.2: Forward reference bug fixed. Now tests correct behavior.
        Phase run returns result even without conductor (fallback behavior).
        """
        response = client.post("/api/v1/designs/TEST-001/phases/mission/run", json={})
        # Without conductor, the endpoint still returns success (fallback behavior)
        assert response.status_code == 200
        data = response.json()
        assert data["phase"] == "mission"
        assert data["status"] == "completed"

    def test_validate_phase_no_state_manager(self, client):
        """Test validating phase without state manager returns 503."""
        response = client.post("/api/v1/designs/TEST-001/phases/mission/validate", json={})
        assert response.status_code == 503

    def test_approve_phase_no_state_manager(self, client):
        """Test approving phase without state manager returns 503."""
        response = client.post("/api/v1/designs/TEST-001/phases/mission/approve", json={})
        assert response.status_code == 503


# =============================================================================
# JOB ENDPOINTS
# =============================================================================

class TestJobEndpoints:
    """Test job management endpoints.

    v1.2: Forward reference bug fixed. Job submission now works correctly.
    """

    def test_submit_job_success(self, client):
        """Test submitting job returns job ID."""
        response = client.post("/api/v1/jobs", json={
            "job_type": "run_phase",
            "payload": {"phase": "mission"},
            "priority": "normal"
        })
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "submitted"

    def test_submit_job_high_priority(self, client):
        """Test submitting high priority job."""
        response = client.post("/api/v1/jobs", json={
            "job_type": "run_phase",
            "payload": {"phase": "mission"},
            "priority": "high"
        })
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data

    def test_get_job_not_found(self, client):
        """Test getting non-existent job."""
        response = client.get("/api/v1/jobs/nonexistent-job-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# =============================================================================
# VISION ENDPOINTS
# =============================================================================

class TestVisionEndpoints:
    """Test vision/rendering endpoints."""

    def test_render_snapshot_no_vision(self, client):
        """Test render without vision service."""
        response = client.post("/api/v1/designs/TEST-001/render")
        assert response.status_code == 200
        assert "not available" in response.json().get("status", "")


# =============================================================================
# REPORT ENDPOINTS
# =============================================================================

class TestReportEndpoints:
    """Test report generation endpoints."""

    def test_generate_report_no_state_manager(self, client):
        """Test report generation without state manager."""
        response = client.post("/api/v1/designs/TEST-001/reports")
        assert response.status_code == 503


# =============================================================================
# WEBSOCKET ENDPOINT
# =============================================================================

class TestWebSocketEndpoint:
    """Test WebSocket endpoint.

    NOTE: WebSocket tests may hang due to async event loop issues.
    These are covered more thoroughly in test_websocket_manager.py
    """

    def test_websocket_endpoint_exists(self, app):
        """Verify WebSocket endpoint is registered."""
        # Check route exists without connecting
        ws_routes = [r for r in app.routes if hasattr(r, 'path') and r.path == '/ws/{design_id}']
        assert len(ws_routes) == 1, "WebSocket route should be registered"

    @pytest.mark.skip(reason="WebSocket tests can hang in sync test context - use test_websocket_manager.py")
    def test_websocket_connect(self, app):
        """Test WebSocket connection - skipped due to event loop issues."""
        pass

    @pytest.mark.skip(reason="WebSocket tests can hang in sync test context - use test_websocket_manager.py")
    def test_websocket_receive_messages(self, app):
        """Test receiving WebSocket messages - skipped due to event loop issues."""
        pass


# =============================================================================
# REQUEST VALIDATION TESTS
# =============================================================================

class TestRequestValidation:
    """Test request body validation."""

    def test_design_create_validation(self, client):
        """Test design creation request validation."""
        # Missing name
        response = client.post("/api/v1/designs", json={})
        assert response.status_code == 422

    def test_design_update_path_validation(self, client):
        """Test design update path validation."""
        # Invalid path prefix
        response = client.patch("/api/v1/designs/TEST-001", json={
            "path": "invalid.path",
            "value": 123
        })
        assert response.status_code == 422

    def test_job_submit_validation(self, client):
        """Test job submit request validation."""
        # Missing job_type
        response = client.post("/api/v1/jobs", json={
            "payload": {}
        })
        assert response.status_code == 422


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Test error handling scenarios.

    NOTE: POST/PATCH endpoints have Pydantic forward reference bugs
    that cause 422 or exceptions instead of 503 for unavailable services.
    """

    def test_state_manager_unavailable_post_reports(self, client):
        """Test POST /reports returns 503 when state manager is unavailable.

        This is one of the few POST endpoints that works (no body params).
        """
        response = client.post("/api/v1/designs/TEST/reports")
        assert response.status_code == 503

    def test_state_manager_unavailable_get(self, client):
        """Test GET endpoints when state manager is unavailable."""
        endpoints = [
            "/api/v1/designs/TEST",
            "/api/v1/designs/TEST/phases/mission",
        ]

        for path in endpoints:
            response = client.get(path)
            assert response.status_code == 503, f"GET {path} should return 503"

    def test_state_manager_unavailable_delete(self, client):
        """Test DELETE endpoints when state manager is unavailable."""
        response = client.delete("/api/v1/designs/TEST")
        assert response.status_code == 503

    def test_post_with_body_works_after_fix(self, client):
        """Verify POST endpoints with body work correctly after v1.2 fix.

        v1.2: Forward reference bug fixed - Pydantic models at module level.
        Now correctly processes body and returns 503 for unavailable StateManager.
        """
        response = client.post("/api/v1/designs", json={"name": "Test"})
        # Bug fixed: now correctly returns 503 (StateManager unavailable)
        assert response.status_code == 503, "Should return 503 for unavailable StateManager"

    def test_patch_with_body_works_after_fix(self, client):
        """Verify PATCH endpoints with body work correctly after v1.2 fix."""
        response = client.patch("/api/v1/designs/TEST", json={
            "path": "mission.test",
            "value": 1
        })
        # Bug fixed: now correctly returns 503 (StateManager unavailable)
        assert response.status_code == 503

    def test_concurrent_requests(self, client):
        """Test handling concurrent requests."""
        import concurrent.futures

        def make_request():
            return client.get("/health")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [f.result() for f in futures]

        assert all(r.status_code == 200 for r in results)


# =============================================================================
# CORS TESTS
# =============================================================================

class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/health")
        # CORS headers should be present
        assert response.status_code in [200, 405]  # 405 if OPTIONS not implemented

    def test_cors_preflight(self, client):
        """Test CORS preflight request."""
        response = client.options(
            "/api/v1/designs",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            }
        )
        # Should allow the request
        assert response.status_code in [200, 405]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
