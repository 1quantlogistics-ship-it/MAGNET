"""
tests/webgl/test_geometry_service.py - Tests for GeometryService v1.1

Module 58: WebGL 3D Visualization
Tests for single authoritative geometry source (FM1 resolution).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestGeometryServiceCreation:
    """Tests for GeometryService initialization."""

    def test_service_creation_with_mock_state_manager(self):
        """Test GeometryService creation with mock state manager."""
        from magnet.webgl.geometry_service import GeometryService

        # Create mock state manager
        mock_sm = Mock()
        mock_sm.get = Mock(side_effect=lambda path, default=None: {
            "hull.loa": 25.0,
            "hull.lwl": 23.0,
            "hull.beam": 6.0,
            "hull.draft": 1.5,
            "hull.depth": 3.0,
        }.get(path, default))

        service = GeometryService(state_manager=mock_sm)

        assert service is not None


class TestGeometryMode:
    """Tests for geometry mode handling."""

    def test_geometry_mode_values(self):
        """Test GeometryMode enum values."""
        from magnet.webgl.schema import GeometryMode

        assert GeometryMode.AUTHORITATIVE.value == "authoritative"
        assert GeometryMode.VISUAL_ONLY.value == "visual_only"

    def test_geometry_mode_in_scene(self):
        """Test geometry mode is included in scene data."""
        from magnet.webgl.schema import SceneData, MeshData, GeometryMode

        hull = MeshData(
            mesh_id="hull",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        scene = SceneData(
            design_id="test",
            hull=hull,
            geometry_mode=GeometryMode.AUTHORITATIVE,
        )

        assert scene.geometry_mode == GeometryMode.AUTHORITATIVE
        data = scene.to_dict()
        assert data["geometry_mode"] == "authoritative"


class TestGeometryConfig:
    """Tests for geometry configuration."""

    def test_lod_configs_exist(self):
        """Test LOD configurations exist."""
        from magnet.webgl.config import LOD_CONFIGS, LODLevel

        assert LODLevel.LOW in LOD_CONFIGS
        assert LODLevel.MEDIUM in LOD_CONFIGS
        assert LODLevel.HIGH in LOD_CONFIGS
        assert LODLevel.ULTRA in LOD_CONFIGS

    def test_default_config_exists(self):
        """Test default config exists."""
        from magnet.webgl.config import DEFAULT_GEOMETRY_CONFIG

        assert DEFAULT_GEOMETRY_CONFIG is not None


class TestGeometryErrors:
    """Tests for geometry error handling."""

    def test_geometry_unavailable_error(self):
        """Test GeometryUnavailableError."""
        from magnet.webgl.errors import GeometryUnavailableError

        error = GeometryUnavailableError(
            design_id="d001",
            reason="GRM not available",
        )

        assert error.code == "GEOM_001"
        assert "d001" in str(error)

    def test_mesh_generation_error(self):
        """Test MeshGenerationError."""
        from magnet.webgl.errors import MeshGenerationError

        error = MeshGenerationError(
            stage="tessellation",
            reason="Invalid parameters",
        )

        assert error.code == "GEOM_003"
        assert "tessellation" in str(error)


class TestLODLevels:
    """Tests for LOD level handling."""

    def test_lod_level_enum(self):
        """Test LODLevel enum values."""
        from magnet.webgl.schema import LODLevel

        assert LODLevel.LOW.value == "low"
        assert LODLevel.MEDIUM.value == "medium"
        assert LODLevel.HIGH.value == "high"
        assert LODLevel.ULTRA.value == "ultra"

    def test_lod_from_string(self):
        """Test creating LODLevel from string."""
        from magnet.webgl.schema import LODLevel

        lod = LODLevel("medium")
        assert lod == LODLevel.MEDIUM


class TestInputProvider:
    """Tests for input provider interface."""

    def test_state_geometry_adapter(self):
        """Test StateGeometryAdapter."""
        from magnet.webgl.interfaces import StateGeometryAdapter

        mock_sm = Mock()
        mock_sm.get = Mock(side_effect=lambda path, default=None: {
            "hull.loa": 25.0,
            "hull.lwl": 23.0,
            "hull.beam": 6.0,
            "hull.draft": 1.5,
            "hull.depth": 3.0,
        }.get(path, default))

        adapter = StateGeometryAdapter(mock_sm)

        assert adapter.loa == 25.0
        assert adapter.beam == 6.0
        assert adapter.draft == 1.5


class TestMeshData:
    """Tests for MeshData."""

    def test_mesh_data_vertex_count(self):
        """Test MeshData vertex count property."""
        from magnet.webgl.schema import MeshData

        mesh = MeshData(
            mesh_id="test",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        assert mesh.vertex_count == 3
        assert mesh.face_count == 1

    def test_mesh_data_is_empty(self):
        """Test MeshData is_empty property."""
        from magnet.webgl.schema import MeshData

        empty = MeshData(mesh_id="empty", vertices=[], indices=[])
        assert empty.is_empty is True

        mesh = MeshData(
            mesh_id="test",
            vertices=[0, 0, 0],
            indices=[],
        )
        assert mesh.is_empty is False
