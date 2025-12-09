"""
tests/webgl/test_schema.py - Tests for WebGL schema v1.1

Module 58: WebGL 3D Visualization
Tests for versioned data contracts and schema validation.
"""

import pytest
from datetime import datetime, timezone


class TestMeshData:
    """Tests for MeshData dataclass."""

    def test_mesh_data_creation(self):
        """Test basic MeshData creation."""
        from magnet.webgl.schema import MeshData

        mesh = MeshData(
            mesh_id="test_hull",
            vertices=[0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.5, 1.0, 0.0],
            indices=[0, 1, 2],
        )

        assert mesh.mesh_id == "test_hull"
        assert mesh.vertex_count == 3
        assert mesh.face_count == 1
        assert len(mesh.vertices) == 9
        assert len(mesh.indices) == 3

    def test_mesh_data_with_normals(self):
        """Test MeshData with normals."""
        from magnet.webgl.schema import MeshData

        mesh = MeshData(
            mesh_id="test",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
            normals=[0, 0, 1, 0, 0, 1, 0, 0, 1],
        )

        assert mesh.normals is not None
        assert len(mesh.normals) == 9

    def test_mesh_data_to_dict(self):
        """Test MeshData serialization."""
        from magnet.webgl.schema import MeshData

        mesh = MeshData(
            mesh_id="test",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        data = mesh.to_dict()

        assert "mesh_id" in data
        assert "vertices" in data
        assert "indices" in data
        assert data["metadata"]["vertex_count"] == 3
        assert data["metadata"]["face_count"] == 1

    def test_mesh_data_from_dict(self):
        """Test MeshData deserialization."""
        from magnet.webgl.schema import MeshData

        data = {
            "mesh_id": "from_dict",
            "vertices": [0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            "indices": [0, 1, 2],
        }

        mesh = MeshData.from_dict(data)

        assert mesh.mesh_id == "from_dict"
        assert mesh.vertex_count == 3

    def test_mesh_data_empty(self):
        """Test empty MeshData."""
        from magnet.webgl.schema import MeshData

        mesh = MeshData(mesh_id="empty", vertices=[], indices=[])

        assert mesh.vertex_count == 0
        assert mesh.face_count == 0


class TestBoundingBox:
    """Tests for BoundingBox dataclass."""

    def test_bounding_box_creation(self):
        """Test BoundingBox creation."""
        from magnet.webgl.schema import BoundingBox

        bounds = BoundingBox(
            min=(0.0, -3.0, -1.5),
            max=(25.0, 3.0, 3.0),
        )

        assert bounds.min[0] == 0.0
        assert bounds.max[0] == 25.0

    def test_bounding_box_size(self):
        """Test BoundingBox size calculation."""
        from magnet.webgl.schema import BoundingBox

        bounds = BoundingBox(
            min=(0.0, -3.0, -1.5),
            max=(25.0, 3.0, 3.0),
        )

        size = bounds.size
        assert size[0] == 25.0
        assert size[1] == 6.0
        assert size[2] == 4.5

    def test_bounding_box_center(self):
        """Test BoundingBox center calculation."""
        from magnet.webgl.schema import BoundingBox

        bounds = BoundingBox(
            min=(0.0, -3.0, -1.5),
            max=(25.0, 3.0, 3.0),
        )

        center = bounds.center
        assert center[0] == 12.5
        assert center[1] == 0.0
        assert center[2] == 0.75


class TestSceneData:
    """Tests for SceneData dataclass."""

    def test_scene_data_creation(self):
        """Test SceneData creation."""
        from magnet.webgl.schema import SceneData, MeshData, GeometryMode

        hull = MeshData(
            mesh_id="hull",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        scene = SceneData(
            design_id="design_001",
            hull=hull,
            geometry_mode=GeometryMode.AUTHORITATIVE,
        )

        assert scene.design_id == "design_001"
        assert scene.hull is not None
        assert scene.geometry_mode == GeometryMode.AUTHORITATIVE

    def test_scene_data_to_dict(self):
        """Test SceneData serialization."""
        from magnet.webgl.schema import SceneData, MeshData, GeometryMode

        hull = MeshData(
            mesh_id="hull",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        scene = SceneData(
            design_id="d001",
            hull=hull,
            geometry_mode=GeometryMode.VISUAL_ONLY,
        )

        data = scene.to_dict()

        assert "design_id" in data
        assert "hull" in data
        assert data["geometry_mode"] == "visual_only"


class TestMaterialDef:
    """Tests for MaterialDef dataclass."""

    def test_material_creation(self):
        """Test MaterialDef creation."""
        from magnet.webgl.schema import MaterialDef

        mat = MaterialDef(
            name="hull_paint",
            color="#3366CC",
            metalness=0.1,
            roughness=0.7,
        )

        assert mat.name == "hull_paint"
        assert mat.color == "#3366CC"
        assert mat.metalness == 0.1
        assert mat.roughness == 0.7

    def test_material_to_dict(self):
        """Test MaterialDef serialization."""
        from magnet.webgl.schema import MaterialDef

        mat = MaterialDef(name="test", color="#FF0000")
        data = mat.to_dict()

        assert data["name"] == "test"
        assert "color" in data


class TestGeometryMode:
    """Tests for GeometryMode enum."""

    def test_geometry_mode_values(self):
        """Test GeometryMode enum values."""
        from magnet.webgl.schema import GeometryMode

        assert GeometryMode.AUTHORITATIVE.value == "authoritative"
        assert GeometryMode.VISUAL_ONLY.value == "visual_only"

    def test_geometry_mode_from_string(self):
        """Test GeometryMode from string."""
        from magnet.webgl.schema import GeometryMode

        mode = GeometryMode("authoritative")
        assert mode == GeometryMode.AUTHORITATIVE


class TestLODLevel:
    """Tests for LODLevel enum."""

    def test_lod_level_values(self):
        """Test LODLevel enum values."""
        from magnet.webgl.schema import LODLevel

        assert LODLevel.LOW.value == "low"
        assert LODLevel.MEDIUM.value == "medium"
        assert LODLevel.HIGH.value == "high"
        assert LODLevel.ULTRA.value == "ultra"


class TestSchemaVersion:
    """Tests for schema versioning."""

    def test_schema_version_defined(self):
        """Test SCHEMA_VERSION is defined."""
        from magnet.webgl.schema import SCHEMA_VERSION

        assert SCHEMA_VERSION is not None
        assert isinstance(SCHEMA_VERSION, str)
        assert "1.1" in SCHEMA_VERSION

    def test_schema_version_in_scene(self):
        """Test schema version in SceneData."""
        from magnet.webgl.schema import SceneData, MeshData

        scene = SceneData(
            design_id="d001",
            hull=MeshData(mesh_id="h", vertices=[], indices=[]),
        )

        data = scene.to_dict()
        # Check schema contains version
        assert "schema" in data
        assert "schema_version" in data["schema"]


class TestValidation:
    """Tests for schema validation."""

    def test_validate_mesh_data_valid(self):
        """Test validation of valid mesh with normals."""
        from magnet.webgl.schema import MeshData, validate_mesh_data

        mesh = MeshData(
            mesh_id="valid",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
            normals=[0, 0, 1, 0, 0, 1, 0, 0, 1],  # Include normals for validation
        )

        errors = validate_mesh_data(mesh)
        assert len(errors) == 0

    def test_validate_mesh_data_bad_vertex_count(self):
        """Test validation catches bad vertex count."""
        from magnet.webgl.schema import MeshData, validate_mesh_data

        # Create mesh with bad vertex count (vertices not divisible by 3)
        mesh = MeshData.__new__(MeshData)
        mesh.vertices = [0, 0, 0, 1, 0]  # Not divisible by 3
        mesh.indices = [0, 1]
        mesh.normals = []
        mesh.mesh_id = "bad"
        mesh.uvs = None
        mesh.colors = None
        mesh.tangents = None
        mesh.bounds = None

        errors = validate_mesh_data(mesh)
        assert len(errors) > 0

    def test_validate_mesh_data_invalid_index(self):
        """Test validation catches invalid index."""
        from magnet.webgl.schema import MeshData, validate_mesh_data

        mesh = MeshData(
            mesh_id="bad_idx",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 10],  # Index 10 out of range
        )

        errors = validate_mesh_data(mesh)
        assert len(errors) > 0


class TestTypeScriptGeneration:
    """Tests for TypeScript type generation."""

    def test_generate_typescript_types(self):
        """Test TypeScript type generation."""
        from magnet.webgl.schema import generate_typescript_types

        ts_code = generate_typescript_types()

        assert "interface MeshData" in ts_code
        assert "interface SceneData" in ts_code
        assert "interface MaterialDef" in ts_code
        assert "GeometryMode" in ts_code
        assert "SCHEMA_VERSION" in ts_code


class TestStructureSceneData:
    """Tests for StructureSceneData."""

    def test_structure_scene_creation(self):
        """Test StructureSceneData creation."""
        from magnet.webgl.schema import StructureSceneData, MeshData

        frame = MeshData(mesh_id="frame_0", vertices=[], indices=[])

        structure = StructureSceneData(
            frames=[frame],
            stringers=[],
            keel=None,
        )

        assert len(structure.frames) == 1

    def test_structure_scene_to_dict(self):
        """Test StructureSceneData serialization."""
        from magnet.webgl.schema import StructureSceneData, MeshData

        structure = StructureSceneData(
            frames=[MeshData(mesh_id="f0", vertices=[], indices=[])],
        )

        data = structure.to_dict()
        assert "frames" in data
        assert len(data["frames"]) == 1
