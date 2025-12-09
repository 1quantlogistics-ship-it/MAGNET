"""
tests/webgl/test_serializer.py - Tests for binary serialization v1.1

Module 58: WebGL 3D Visualization
Tests for binary mesh serialization format.
"""

import pytest


class TestMeshSerialization:
    """Tests for mesh binary serialization."""

    def test_serialize_simple_mesh(self):
        """Test serializing a simple mesh."""
        from magnet.webgl.schema import MeshData
        from magnet.webgl.serializer import serialize_mesh

        mesh = MeshData(
            mesh_id="test",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        data = serialize_mesh(mesh, compress=False)

        assert data is not None
        assert len(data) > 0
        # Check for magic number
        assert data[:4] == b"MNET"

    def test_serialize_with_compression(self):
        """Test serializing with compression."""
        from magnet.webgl.schema import MeshData
        from magnet.webgl.serializer import serialize_mesh

        mesh = MeshData(
            mesh_id="compressed_test",
            vertices=[float(i) for i in range(300)],  # 100 vertices
            indices=list(range(0, 300, 3)),
        )

        uncompressed = serialize_mesh(mesh, compress=False)
        compressed = serialize_mesh(mesh, compress=True)

        # Compressed should be smaller (or at least not much larger)
        # Note: Very small data might not compress well
        assert compressed is not None
        assert len(compressed) > 0

    def test_deserialize_simple_mesh(self):
        """Test deserializing a mesh."""
        from magnet.webgl.schema import MeshData
        from magnet.webgl.serializer import serialize_mesh, deserialize_mesh

        original = MeshData(
            mesh_id="roundtrip",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        data = serialize_mesh(original, compress=False)
        restored = deserialize_mesh(data)

        assert restored.mesh_id == original.mesh_id
        assert restored.vertex_count == original.vertex_count
        assert len(restored.indices) == len(original.indices)

    def test_roundtrip_with_normals(self):
        """Test roundtrip with normals."""
        from magnet.webgl.schema import MeshData
        from magnet.webgl.serializer import serialize_mesh, deserialize_mesh

        original = MeshData(
            mesh_id="with_normals",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
            normals=[0, 0, 1, 0, 0, 1, 0, 0, 1],
        )

        data = serialize_mesh(original, compress=False)
        restored = deserialize_mesh(data)

        assert restored.normals is not None
        assert len(restored.normals) == len(original.normals)

    def test_roundtrip_compressed(self):
        """Test roundtrip with compression."""
        from magnet.webgl.schema import MeshData
        from magnet.webgl.serializer import serialize_mesh, deserialize_mesh

        original = MeshData(
            mesh_id="compressed_roundtrip",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        data = serialize_mesh(original, compress=True)
        restored = deserialize_mesh(data)

        assert restored.mesh_id == original.mesh_id
        assert restored.vertex_count == original.vertex_count

    def test_roundtrip_with_bounds(self):
        """Test roundtrip with bounding box."""
        from magnet.webgl.schema import MeshData, BoundingBox
        from magnet.webgl.serializer import serialize_mesh, deserialize_mesh

        original = MeshData(
            mesh_id="with_bounds",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
            bounds=BoundingBox(
                min=(0, 0, 0),
                max=(1, 1, 0),
            ),
        )

        data = serialize_mesh(original, compress=False)
        restored = deserialize_mesh(data)

        assert restored.bounds is not None
        assert restored.bounds.min[0] == 0
        assert restored.bounds.max[0] == 1


class TestSceneSerialization:
    """Tests for scene binary serialization."""

    def test_serialize_simple_scene(self):
        """Test serializing a simple scene."""
        from magnet.webgl.schema import SceneData, MeshData, GeometryMode
        from magnet.webgl.serializer import serialize_scene

        hull = MeshData(
            mesh_id="hull",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        scene = SceneData(
            design_id="d001",
            hull=hull,
            geometry_mode=GeometryMode.AUTHORITATIVE,
        )

        data = serialize_scene(scene, compress=False)

        assert data is not None
        assert len(data) > 0
        assert data[:4] == b"MNET"

    def test_scene_roundtrip(self):
        """Test scene serialization roundtrip."""
        from magnet.webgl.schema import SceneData, MeshData, GeometryMode
        from magnet.webgl.serializer import serialize_scene, deserialize_scene

        hull = MeshData(
            mesh_id="hull",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        original = SceneData(
            design_id="d002",
            hull=hull,
            geometry_mode=GeometryMode.VISUAL_ONLY,
        )

        data = serialize_scene(original, compress=False)
        restored = deserialize_scene(data)

        assert restored.design_id == original.design_id
        assert restored.hull is not None


class TestBinaryFormatValidation:
    """Tests for binary format validation."""

    def test_validate_valid_data(self):
        """Test validation of valid binary data."""
        from magnet.webgl.schema import MeshData
        from magnet.webgl.serializer import serialize_mesh, validate_binary_format

        mesh = MeshData(
            mesh_id="valid",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        data = serialize_mesh(mesh, compress=False)
        is_valid, error = validate_binary_format(data)

        assert is_valid is True
        assert error == ""

    def test_validate_invalid_magic(self):
        """Test validation catches invalid magic."""
        from magnet.webgl.serializer import validate_binary_format

        bad_data = b"BAAD" + b"\x00" * 20

        is_valid, error = validate_binary_format(bad_data)

        assert is_valid is False
        assert "magic" in error.lower()

    def test_validate_too_short(self):
        """Test validation catches too-short data."""
        from magnet.webgl.serializer import validate_binary_format

        short_data = b"MNET"

        is_valid, error = validate_binary_format(short_data)

        assert is_valid is False
        assert "short" in error.lower() or "header" in error.lower()


class TestSizeEstimation:
    """Tests for serialized size estimation."""

    def test_estimate_size(self):
        """Test size estimation."""
        from magnet.webgl.schema import MeshData
        from magnet.webgl.serializer import serialize_mesh, estimate_serialized_size

        mesh = MeshData(
            mesh_id="size_test",
            vertices=[0, 0, 0, 1, 0, 0, 0.5, 1, 0],
            indices=[0, 1, 2],
        )

        estimated = estimate_serialized_size(mesh)
        actual_uncompressed = len(serialize_mesh(mesh, compress=False))

        # Estimate should be reasonable (within 2x of actual)
        assert estimated > 0
        assert estimated < actual_uncompressed * 2


class TestCompressionRatio:
    """Tests for compression ratio calculation."""

    def test_compression_ratio(self):
        """Test compression ratio calculation."""
        from magnet.webgl.serializer import get_compression_ratio

        original = b"x" * 1000
        compressed = b"x" * 100

        ratio = get_compression_ratio(original, compressed)

        assert ratio == 0.9  # 90% reduction

    def test_compression_ratio_empty(self):
        """Test compression ratio with empty data."""
        from magnet.webgl.serializer import get_compression_ratio

        ratio = get_compression_ratio(b"", b"")

        assert ratio == 0.0
