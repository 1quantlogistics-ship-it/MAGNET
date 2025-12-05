"""
Tests for MAGNET API Control Plane
==================================

Tests FastAPI endpoints.
"""

import pytest
import tempfile
import shutil
from fastapi.testclient import TestClient

from api.control_plane import create_app
from memory.file_io import MemoryFileIO
from memory.schemas import MissionSchema, DesignPhase


@pytest.fixture
def temp_memory_dir():
    """Create temporary memory directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def client(temp_memory_dir):
    """Create test client with temp memory."""
    app = create_app(memory_path=temp_memory_dir)
    return TestClient(app)


@pytest.fixture
def memory(temp_memory_dir):
    """Create memory instance."""
    return MemoryFileIO(temp_memory_dir)


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root(self, client):
        """Test root returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "MAGNET Control Plane"
        assert "endpoints" in data

    def test_health(self, client):
        """Test health check."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestChatEndpoint:
    """Test chat endpoint."""

    def test_chat_basic(self, client):
        """Test basic chat message."""
        response = client.post("/chat", json={
            "message": "Design a patrol boat"
        })
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "phase" in data

    def test_chat_with_session(self, client):
        """Test chat with session ID."""
        response = client.post("/chat", json={
            "message": "Design a 30m catamaran",
            "session_id": "test-session-001"
        })
        assert response.status_code == 200


class TestStatusEndpoint:
    """Test status endpoint."""

    def test_status(self, client):
        """Test status returns current state."""
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "current_phase" in data
        assert "design_iteration" in data


class TestDesignEndpoint:
    """Test design endpoint."""

    def test_design_empty(self, client):
        """Test design returns empty state initially."""
        response = client.get("/design")
        assert response.status_code == 200
        data = response.json()
        assert data["mission"] is None
        assert "phase" in data

    def test_design_with_mission(self, client, memory):
        """Test design returns mission when set."""
        # Create a mission
        mission = MissionSchema(
            mission_id="TEST-001",
            vessel_type="patrol_catamaran",
            loa_m=22.0,
            beam_m=8.5,
            design_speed_kts=35.0,
            cruise_speed_kts=25.0,
            crew=8,
            endurance_nm=500.0,
        )
        memory.write_schema("mission", mission)

        response = client.get("/design")
        assert response.status_code == 200
        data = response.json()
        assert data["mission"] is not None
        assert data["mission"]["mission_id"] == "TEST-001"


class TestValidateEndpoint:
    """Test validate endpoint."""

    def test_validate(self, client):
        """Test validation endpoint."""
        response = client.post("/validate", json={
            "validate_all": True
        })
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "errors" in data
        assert "warnings" in data


class TestExportEndpoint:
    """Test export endpoint."""

    def test_export_json(self, client):
        """Test JSON export."""
        response = client.post("/export", json={
            "format": "json"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "file_path" in data

    def test_export_unsupported(self, client):
        """Test unsupported export format."""
        response = client.post("/export", json={
            "format": "xlsx"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not yet implemented" in data["message"]


class TestRollbackEndpoint:
    """Test rollback endpoint."""

    def test_rollback_at_start(self, client):
        """Test rollback at iteration 1."""
        response = client.post("/rollback", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Cannot rollback" in data["message"]

    def test_rollback_after_iterations(self, client, memory):
        """Test rollback after iterations."""
        # Set iteration to 3
        memory.update_system_state(design_iteration=3)

        response = client.post("/rollback", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["previous_iteration"] == 3
        assert data["current_iteration"] == 2

    def test_rollback_to_specific(self, client, memory):
        """Test rollback to specific iteration."""
        memory.update_system_state(design_iteration=5)

        response = client.post("/rollback", json={
            "target_iteration": 2
        })
        assert response.status_code == 200
        data = response.json()
        assert data["current_iteration"] == 2


class TestPhaseEndpoint:
    """Test phase advancement endpoint."""

    def test_advance_phase(self, client):
        """Test advancing design phase."""
        response = client.post("/phase/advance")
        assert response.status_code == 200
        data = response.json()
        assert data["previous_phase"] == "mission"
        assert data["current_phase"] == "hull_form"

    def test_advance_multiple(self, client):
        """Test advancing multiple phases."""
        # First advance
        client.post("/phase/advance")
        # Second advance
        response = client.post("/phase/advance")
        assert response.status_code == 200
        data = response.json()
        assert data["current_phase"] == "propulsion"


class TestMemoryEndpoints:
    """Test memory access endpoints."""

    def test_list_memory_files(self, client):
        """Test listing memory files."""
        response = client.get("/memory/files")
        assert response.status_code == 200
        data = response.json()
        assert "mission" in data
        assert "hull_params" in data

    def test_get_memory_file(self, client, memory):
        """Test getting specific memory file."""
        # Create mission
        mission = MissionSchema(
            mission_id="TEST-002",
            vessel_type="patrol_catamaran",
            loa_m=22.0,
            beam_m=8.5,
            design_speed_kts=35.0,
            cruise_speed_kts=25.0,
            crew=8,
            endurance_nm=500.0,
        )
        memory.write_schema("mission", mission)

        response = client.get("/memory/mission")
        assert response.status_code == 200
        data = response.json()
        assert data["mission_id"] == "TEST-002"

    def test_get_nonexistent_file(self, client):
        """Test getting non-existent memory file."""
        response = client.get("/memory/mission")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
