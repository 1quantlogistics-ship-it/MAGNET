"""
tests/webgl/test_mesh_utils.py

Phase 1 (Geometry Stability): tests for trimesh adapter layer.

These tests must pass whether or not `trimesh` is installed:
- If trimesh is missing/disabled, fallback behavior must still work.
"""

import os

import numpy as np
import pytest


def _unit_cube_vertices_faces():
    # Unit cube vertices and triangulated faces (watertight).
    vertices = np.array(
        [
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 1],
            [1, 1, 1],
            [0, 1, 1],
        ],
        dtype=float,
    )
    faces = np.array(
        [
            [0, 1, 2],
            [0, 2, 3],  # bottom
            [4, 6, 5],
            [4, 7, 6],  # top
            [0, 4, 5],
            [0, 5, 1],  # front
            [2, 6, 7],
            [2, 7, 3],  # back
            [0, 3, 7],
            [0, 7, 4],  # left
            [1, 5, 6],
            [1, 6, 2],  # right
        ],
        dtype=int,
    )
    return vertices, faces


class TestMeshVolume:
    def test_unit_cube_volume_is_one(self):
        from magnet.webgl.mesh_utils import compute_mesh_volume

        v, f = _unit_cube_vertices_faces()
        vol = compute_mesh_volume(v, f)
        assert vol == pytest.approx(1.0, abs=0.02)

    def test_empty_mesh_returns_zero(self):
        from magnet.webgl.mesh_utils import compute_mesh_volume

        assert compute_mesh_volume(None, None) == 0.0
        assert compute_mesh_volume(np.array([]), np.array([])) == 0.0

    def test_flat_indices_handled(self):
        from magnet.webgl.mesh_utils import compute_mesh_volume

        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
        flat_indices = np.array([0, 1, 2, 0, 1, 3, 0, 2, 3, 1, 2, 3], dtype=int)

        vol = compute_mesh_volume(vertices, flat_indices)
        assert vol > 0.0  # tetrahedron

    def test_flat_webgl_storage_supported(self):
        """
        MeshData.vertices and .indices are flat lists (3N and 3F).
        The adapter must accept this without callers reshaping.
        """
        from magnet.webgl.mesh_utils import compute_mesh_volume

        v, f = _unit_cube_vertices_faces()
        v_flat = v.reshape(-1).tolist()
        f_flat = f.reshape(-1).tolist()

        vol = compute_mesh_volume(v_flat, f_flat)
        assert vol == pytest.approx(1.0, abs=0.02)


class TestMeshValidation:
    def test_fallback_when_trimesh_unavailable_via_monkeypatch(self, monkeypatch):
        import magnet.webgl.mesh_utils as mu

        monkeypatch.setattr(mu, "_TRIMESH_AVAILABLE", False, raising=True)
        v, f = _unit_cube_vertices_faces()

        res = mu.validate_mesh(v, f)
        assert res.error_message is not None
        assert "trimesh" in res.error_message
        assert res.volume_m3 >= 0.0

    def test_watertight_detection_if_trimesh_available(self):
        import magnet.webgl.mesh_utils as mu

        if not getattr(mu, "_TRIMESH_AVAILABLE", False):
            pytest.skip("trimesh not installed (or disabled)")

        v, f = _unit_cube_vertices_faces()
        res = mu.validate_mesh(v, f)
        assert res.is_watertight is True
        # Euler characteristic for watertight cube triangulation should be 2.
        assert res.euler_number == 2


class TestGracefulDegradation:
    def test_env_flag_disables_trimesh_import_path(self, monkeypatch):
        """
        Running `MAGNET_DISABLE_TRIMESH=1 pytest ...` should keep mesh utils working.

        We validate the key behavior (volume works) without relying on trimesh.
        """
        monkeypatch.setenv("MAGNET_DISABLE_TRIMESH", "1")

        # Re-import module to apply import-time flag.
        import importlib
        import magnet.webgl.mesh_utils as mu

        mu = importlib.reload(mu)
        assert mu._TRIMESH_AVAILABLE is False

        v, f = _unit_cube_vertices_faces()
        vol = mu.compute_mesh_volume(v, f)
        assert vol == pytest.approx(1.0, abs=0.02)

