"""
tests/webgl/test_exporter.py - Tests for geometry export v1.1

Module 58: WebGL 3D Visualization
Tests for export functionality and traceability (FM8 resolution).
"""

import pytest
import json


class TestExportMetadata:
    """Tests for ExportMetadata (FM8)."""

    def test_metadata_creation(self):
        """Test ExportMetadata creation."""
        from magnet.webgl.exporter import ExportMetadata

        metadata = ExportMetadata(
            export_id="exp_001",
            design_id="d001",
            format="glb",
        )

        assert metadata.export_id == "exp_001"
        assert metadata.design_id == "d001"
        assert metadata.format == "glb"

    def test_metadata_includes_version(self):
        """Test metadata includes version info."""
        from magnet.webgl.exporter import ExportMetadata

        metadata = ExportMetadata(
            export_id="exp_002",
            design_id="d002",
            format="gltf",
        )

        assert metadata.schema_version is not None
        assert "1.1" in metadata.schema_version

    def test_metadata_to_dict(self):
        """Test metadata serialization."""
        from magnet.webgl.exporter import ExportMetadata

        metadata = ExportMetadata(
            export_id="exp_003",
            design_id="d003",
            format="stl",
            vertex_count=1000,
            face_count=500,
        )

        data = metadata.to_dict()

        assert data["export_id"] == "exp_003"
        assert data["vertex_count"] == 1000
        assert data["face_count"] == 500

    def test_metadata_tracks_branch(self):
        """Test metadata tracks source branch."""
        from magnet.webgl.exporter import ExportMetadata

        metadata = ExportMetadata(
            export_id="exp_004",
            design_id="d004",
            format="glb",
            source_branch="feature/webgl",
            commit_hash="abc123",
        )

        assert metadata.source_branch == "feature/webgl"
        assert metadata.commit_hash == "abc123"


class TestExportFormat:
    """Tests for ExportFormat enum."""

    def test_format_values(self):
        """Test ExportFormat enum values."""
        from magnet.webgl.exporter import ExportFormat

        assert ExportFormat.GLTF.value == "gltf"
        assert ExportFormat.GLB.value == "glb"
        assert ExportFormat.STL.value == "stl"
        assert ExportFormat.OBJ.value == "obj"


class TestGeometryExporter:
    """Tests for GeometryExporter class."""

    def test_exporter_creation(self):
        """Test exporter creation."""
        from magnet.webgl.exporter import GeometryExporter

        exporter = GeometryExporter(design_id="d001")

        assert exporter is not None

    def test_set_version_info(self):
        """Test setting version info."""
        from magnet.webgl.exporter import GeometryExporter

        exporter = GeometryExporter(design_id="d001")
        exporter.set_version_info(branch="main", commit_hash="def456")

        assert exporter._source_branch == "main"
        assert exporter._commit_hash == "def456"


class TestGLTFExport:
    """Tests for glTF/GLB export."""

    def test_export_gltf(self):
        """Test glTF JSON export."""
        from magnet.webgl.schema import MeshData
        from magnet.webgl.exporter import GeometryExporter, ExportFormat

        mesh = MeshData(
            mesh_id="test_hull",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        exporter = GeometryExporter(design_id="d001")
        result = exporter.export(mesh, ExportFormat.GLTF)

        assert result.success is True
        assert result.format == ExportFormat.GLTF
        assert len(result.data) > 0

        # Verify it's valid JSON
        gltf = json.loads(result.data.decode('utf-8'))
        assert "asset" in gltf
        assert gltf["asset"]["version"] == "2.0"

    def test_export_glb(self):
        """Test GLB binary export."""
        from magnet.webgl.schema import MeshData
        from magnet.webgl.exporter import GeometryExporter, ExportFormat

        mesh = MeshData(
            mesh_id="test_hull",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        exporter = GeometryExporter(design_id="d001")
        result = exporter.export(mesh, ExportFormat.GLB)

        assert result.success is True
        assert result.format == ExportFormat.GLB
        assert len(result.data) > 0

        # Verify GLB magic
        assert result.data[:4] == b"glTF"

    def test_gltf_includes_metadata(self):
        """Test glTF export includes metadata."""
        from magnet.webgl.schema import MeshData
        from magnet.webgl.exporter import GeometryExporter, ExportFormat

        mesh = MeshData(
            mesh_id="metadata_test",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        exporter = GeometryExporter(design_id="d001")
        exporter.set_version_info(branch="main", commit_hash="abc123")

        result = exporter.export(mesh, ExportFormat.GLTF)

        gltf = json.loads(result.data.decode('utf-8'))
        assert "extras" in gltf["asset"]
        # Metadata embedded in extras


class TestSTLExport:
    """Tests for STL export."""

    def test_export_stl_binary(self):
        """Test binary STL export."""
        from magnet.webgl.schema import MeshData
        from magnet.webgl.exporter import GeometryExporter, ExportFormat

        mesh = MeshData(
            mesh_id="stl_test",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        exporter = GeometryExporter(design_id="d001")
        result = exporter.export(mesh, ExportFormat.STL)

        assert result.success is True
        assert result.format == ExportFormat.STL
        assert len(result.data) > 0

        # Binary STL has 80-byte header
        assert len(result.data) >= 80

    def test_export_stl_ascii(self):
        """Test ASCII STL export."""
        from magnet.webgl.schema import MeshData
        from magnet.webgl.exporter import GeometryExporter, ExportFormat

        mesh = MeshData(
            mesh_id="stl_ascii_test",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        exporter = GeometryExporter(design_id="d001")
        result = exporter.export(mesh, ExportFormat.STL_ASCII)

        assert result.success is True
        assert result.format == ExportFormat.STL_ASCII

        # Verify ASCII STL format
        content = result.data.decode('ascii')
        assert content.startswith("solid")
        assert "facet normal" in content
        assert "endsolid" in content


class TestOBJExport:
    """Tests for OBJ export."""

    def test_export_obj(self):
        """Test OBJ export."""
        from magnet.webgl.schema import MeshData
        from magnet.webgl.exporter import GeometryExporter, ExportFormat

        mesh = MeshData(
            mesh_id="obj_test",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        exporter = GeometryExporter(design_id="d001")
        result = exporter.export(mesh, ExportFormat.OBJ)

        assert result.success is True
        assert result.format == ExportFormat.OBJ

        # Verify OBJ format
        content = result.data.decode('utf-8')
        assert "v " in content  # Vertices
        assert "f " in content  # Faces

    def test_obj_with_normals(self):
        """Test OBJ export with normals."""
        from magnet.webgl.schema import MeshData
        from magnet.webgl.exporter import GeometryExporter, ExportFormat

        mesh = MeshData(
            mesh_id="obj_normals",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
            normals=[0, 0, 1, 0, 0, 1, 0, 0, 1],
        )

        exporter = GeometryExporter(design_id="d001")
        result = exporter.export(mesh, ExportFormat.OBJ)

        content = result.data.decode('utf-8')
        assert "vn " in content  # Vertex normals


class TestSceneExport:
    """Tests for scene export."""

    def test_export_scene_glb(self):
        """Test scene export to GLB."""
        from magnet.webgl.schema import SceneData, MeshData, GeometryMode
        from magnet.webgl.exporter import GeometryExporter, ExportFormat

        hull = MeshData(
            mesh_id="hull",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        deck = MeshData(
            mesh_id="deck",
            vertices=[0, 0, 1, 1, 0, 1, 0.5, 1, 1],
            indices=[0, 1, 2],
        )

        scene = SceneData(
            design_id="d001",
            hull=hull,
            deck=deck,
            geometry_mode=GeometryMode.AUTHORITATIVE,
        )

        exporter = GeometryExporter(design_id="d001")
        result = exporter.export_scene(scene, ExportFormat.GLB)

        assert result.success is True
        assert result.data[:4] == b"glTF"

    def test_export_scene_includes_materials(self):
        """Test scene export includes materials."""
        from magnet.webgl.schema import SceneData, MeshData, MaterialDef, GeometryMode
        from magnet.webgl.exporter import GeometryExporter, ExportFormat

        hull = MeshData(
            mesh_id="hull",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        scene = SceneData(
            design_id="d002",
            hull=hull,
            geometry_mode=GeometryMode.AUTHORITATIVE,
            materials=[
                MaterialDef(name="hull_paint", color="#3366CC"),
            ],
        )

        exporter = GeometryExporter(design_id="d002")
        result = exporter.export_scene(scene, ExportFormat.GLTF)

        gltf = json.loads(result.data.decode('utf-8'))
        assert "materials" in gltf


class TestExportResult:
    """Tests for ExportResult."""

    def test_result_file_extension(self):
        """Test ExportResult file extension."""
        from magnet.webgl.exporter import ExportResult, ExportFormat, ExportMetadata

        result = ExportResult(
            success=True,
            format=ExportFormat.GLB,
            data=b"test",
            metadata=ExportMetadata(
                export_id="exp",
                design_id="d",
                format="glb",
            ),
        )

        assert result.file_extension == ".glb"

    def test_result_with_warnings(self):
        """Test ExportResult with warnings."""
        from magnet.webgl.exporter import ExportResult, ExportFormat, ExportMetadata

        result = ExportResult(
            success=True,
            format=ExportFormat.STL,
            data=b"test",
            metadata=ExportMetadata(
                export_id="exp",
                design_id="d",
                format="stl",
            ),
            warnings=["Mesh simplified for export"],
        )

        assert len(result.warnings) == 1


class TestExportTraceability:
    """Tests for FM8 export traceability."""

    def test_export_has_id(self):
        """Test every export has unique ID."""
        from magnet.webgl.schema import MeshData
        from magnet.webgl.exporter import GeometryExporter, ExportFormat

        mesh = MeshData(
            mesh_id="trace_test",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        exporter = GeometryExporter(design_id="d001")

        result1 = exporter.export(mesh, ExportFormat.GLB)
        result2 = exporter.export(mesh, ExportFormat.GLB)

        assert result1.metadata.export_id != result2.metadata.export_id

    def test_export_timestamps(self):
        """Test exports have timestamps."""
        from magnet.webgl.schema import MeshData
        from magnet.webgl.exporter import GeometryExporter, ExportFormat

        mesh = MeshData(
            mesh_id="timestamp_test",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        exporter = GeometryExporter(design_id="d001")
        result = exporter.export(mesh, ExportFormat.GLB)

        assert result.metadata.exported_at is not None
        # Should be ISO format
        assert "T" in result.metadata.exported_at

    def test_export_includes_statistics(self):
        """Test exports include statistics."""
        from magnet.webgl.schema import MeshData
        from magnet.webgl.exporter import GeometryExporter, ExportFormat

        mesh = MeshData(
            mesh_id="stats_test",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        exporter = GeometryExporter(design_id="d001")
        result = exporter.export(mesh, ExportFormat.GLB)

        assert result.metadata.vertex_count == 3
        assert result.metadata.face_count == 1
        assert result.metadata.file_size_bytes > 0
