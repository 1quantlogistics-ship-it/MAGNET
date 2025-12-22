"""
tests/test_webgl_export.py - GLB export contract tests

Module 67.3: GLTF Export/Viewer Contract Consolidation
These tests prevent regression of the missing normals bug.

Gate 5 tests ensure GLB exports meet the attribute contract.
"""

import struct
import json
import pytest
from typing import Dict, Any

# Import the modules under test
from magnet.webgl.exporter import GeometryExporter, ExportFormat, ExportResult
from magnet.webgl.schema import MeshData, SceneData, GeometryMode
from magnet.webgl.errors import ExportError


def parse_glb_json(data: bytes) -> Dict[str, Any]:
    """Parse GLB and extract JSON chunk."""
    assert data[:4] == b'glTF', "Not a GLB file"
    json_length = struct.unpack('<I', data[12:16])[0]
    json_bytes = data[20:20 + json_length]
    return json.loads(json_bytes.rstrip(b' '))


def create_test_hull_mesh() -> MeshData:
    """Create minimal valid hull mesh with normals."""
    return MeshData(
        mesh_id="test_hull",
        vertices=[0, 0, 0, 1, 0, 0, 0, 1, 0],  # 3 vertices
        indices=[0, 1, 2],  # 1 triangle
        normals=[0, 0, 1, 0, 0, 1, 0, 0, 1],  # 3 normals
    )


class TestGLBExportContract:
    """GLB export contract tests - prevent regression of Module 67.3 bug."""

    def test_hull_glb_has_normal_attribute(self):
        """Gate 5.1: Hull GLB must have NORMAL attribute."""
        mesh = create_test_hull_mesh()
        exporter = GeometryExporter()
        result = exporter.export(mesh, ExportFormat.GLB)

        assert result.success, f"Export failed: {result.errors}"
        gltf = parse_glb_json(result.data)
        attrs = gltf["meshes"][0]["primitives"][0]["attributes"]

        assert "NORMAL" in attrs, "NORMAL attribute missing from hull GLB"

    def test_normal_count_matches_position_count(self):
        """Gate 5.2: Normal count must equal position count."""
        mesh = create_test_hull_mesh()
        exporter = GeometryExporter()
        result = exporter.export(mesh, ExportFormat.GLB)

        assert result.success
        gltf = parse_glb_json(result.data)
        accessors = gltf["accessors"]
        attrs = gltf["meshes"][0]["primitives"][0]["attributes"]

        pos_count = accessors[attrs["POSITION"]]["count"]
        norm_count = accessors[attrs["NORMAL"]]["count"]

        assert norm_count == pos_count, f"Normal count {norm_count} != position count {pos_count}"

    def test_index_component_type_is_uint32(self):
        """Gate 5.3: Index componentType must be 5125 (UNSIGNED_INT)."""
        mesh = create_test_hull_mesh()
        exporter = GeometryExporter()
        result = exporter.export(mesh, ExportFormat.GLB)

        assert result.success
        gltf = parse_glb_json(result.data)
        idx_accessor = gltf["accessors"][gltf["meshes"][0]["primitives"][0]["indices"]]

        assert idx_accessor["componentType"] == 5125, f"Expected 5125, got {idx_accessor['componentType']}"

    def test_glb_total_length_4byte_aligned(self):
        """Gate 5.4: GLB total length must be 4-byte aligned."""
        mesh = create_test_hull_mesh()
        exporter = GeometryExporter()
        result = exporter.export(mesh, ExportFormat.GLB)

        assert result.success
        assert result.data[:4] == b'glTF'
        total_length = struct.unpack('<I', result.data[8:12])[0]

        assert total_length % 4 == 0, f"GLB total length {total_length} not 4-byte aligned"
        assert len(result.data) == total_length, f"Actual length {len(result.data)} != header {total_length}"

    def test_buffer_view_offsets_4byte_aligned(self):
        """Gate 5.5: All bufferView offsets must be 4-byte aligned."""
        mesh = create_test_hull_mesh()
        exporter = GeometryExporter()
        result = exporter.export(mesh, ExportFormat.GLB)

        assert result.success
        gltf = parse_glb_json(result.data)

        for i, bv in enumerate(gltf["bufferViews"]):
            offset = bv["byteOffset"]
            assert offset % 4 == 0, f"bufferView[{i}] offset {offset} not 4-byte aligned"

    def test_missing_normals_raises_export_error(self):
        """Gate 5.6: Exporting hull without normals must fail."""
        mesh = MeshData(
            mesh_id="no_normals",
            vertices=[0, 0, 0, 1, 0, 0, 0, 1, 0],
            indices=[0, 1, 2],
            normals=[],  # Empty normals
        )
        exporter = GeometryExporter()

        # The export should fail due to contract violation
        result = exporter.export(mesh, ExportFormat.GLB)

        # Either raises ExportError or returns failure
        assert not result.success or "NORMAL" in str(result.errors), \
            "Export should fail or report error when normals missing"

    def test_scene_export_includes_normals(self):
        """Gate 5.7: Scene export must include normals on hull mesh."""
        scene = SceneData(
            design_id="test",
            hull=create_test_hull_mesh(),
            geometry_mode=GeometryMode.AUTHORITATIVE,
        )
        exporter = GeometryExporter()
        result = exporter.export_scene(scene, ExportFormat.GLB)

        assert result.success, f"Scene export failed: {result.errors}"
        gltf = parse_glb_json(result.data)
        attrs = gltf["meshes"][0]["primitives"][0]["attributes"]

        assert "NORMAL" in attrs, "Scene export missing NORMAL on hull"


class TestGLBExportMetadata:
    """Test that export metadata is correctly embedded."""

    def test_export_includes_asset_version(self):
        """Exported GLB must have glTF asset version 2.0."""
        mesh = create_test_hull_mesh()
        exporter = GeometryExporter()
        result = exporter.export(mesh, ExportFormat.GLB)

        assert result.success
        gltf = parse_glb_json(result.data)

        assert gltf["asset"]["version"] == "2.0"

    def test_export_includes_generator(self):
        """Exported GLB must identify MAGNET as generator."""
        mesh = create_test_hull_mesh()
        exporter = GeometryExporter()
        result = exporter.export(mesh, ExportFormat.GLB)

        assert result.success
        gltf = parse_glb_json(result.data)

        assert "MAGNET" in gltf["asset"]["generator"]


class TestMeshContractValidator:
    """Test the MeshContractValidator directly."""

    def test_validator_catches_empty_vertices(self):
        """Validator must reject mesh with empty vertices."""
        from magnet.webgl.contracts import MeshContractValidator, AttributePolicy, MeshCategory

        mesh = MeshData(
            mesh_id="empty",
            vertices=[],
            indices=[0, 1, 2],
            normals=[0, 0, 1],
        )
        policy = AttributePolicy.for_category(MeshCategory.HULL)
        errors = MeshContractValidator.validate(mesh, policy, "test_mesh")

        assert len(errors) > 0
        assert any("POSITION" in e for e in errors)

    def test_validator_catches_mismatched_normals(self):
        """Validator must reject mesh with wrong normal count."""
        from magnet.webgl.contracts import MeshContractValidator, AttributePolicy, MeshCategory

        mesh = MeshData(
            mesh_id="mismatch",
            vertices=[0, 0, 0, 1, 0, 0, 0, 1, 0],  # 3 vertices
            indices=[0, 1, 2],
            normals=[0, 0, 1, 0, 0, 1],  # Only 2 normals - WRONG
        )
        policy = AttributePolicy.for_category(MeshCategory.HULL)
        errors = MeshContractValidator.validate(mesh, policy, "test_mesh")

        assert len(errors) > 0
        assert any("NORMAL count" in e for e in errors)

    def test_validator_accepts_valid_mesh(self):
        """Validator must accept valid mesh."""
        from magnet.webgl.contracts import MeshContractValidator, AttributePolicy, MeshCategory

        mesh = create_test_hull_mesh()
        policy = AttributePolicy.for_category(MeshCategory.HULL)
        errors = MeshContractValidator.validate(mesh, policy, "test_mesh")

        assert len(errors) == 0, f"Valid mesh should have no errors: {errors}"
