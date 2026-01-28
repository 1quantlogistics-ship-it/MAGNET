"""
Integrity ladder hardening for panelized surfaces.

Rules:
- A panelized scene must never be AUTHORITATIVE without same-version hydrostatics.
- If panelized and hydrostatics is missing/stale => DECOUPLED with reason missing_hydrostatics_for_panelized.
"""

from unittest.mock import patch


class MockStateManager:
    def __init__(self, values=None):
        self._values = values or {}

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value, source=None):
        self._values[key] = value


def test_panelized_requires_hydrostatics_freshness():
    from magnet.webgl.geometry_service import GeometryService
    from magnet.webgl.schema import LODLevel, SimulationIntegrity
    from magnet.webgl.schema import MeshData
    from magnet.webgl.interfaces import HullGeometryData

    sm = MockStateManager(
        {
            "design_version": 5,
            "kernel.physics_last_validated_version": 5,
            # hydrostatics missing/stale:
            "kernel.hydrostatics_last_validated_version": None,
            "resistance.method_valid": True,
        }
    )
    svc = GeometryService(state_manager=sm)

    fake_geom = HullGeometryData(
        design_id="dP",
        version_id="dP:v5",
        sections=[],
        keel_profile=[],
        stem_profile=[],
        openings=[],
        flow_paths=[],
        attachments=[],
        metadata={"surface_definition": "panelized"},
    )

    with patch.object(svc._grm_provider, "get_hull_geometry", return_value=fake_geom), patch.object(
        svc._grm_provider, "get_geometry_version", return_value="dP:v5"
    ), patch.object(svc, "_tessellate_grm", return_value=MeshData(mesh_id="hull", vertices=[0, 0, 0], indices=[])):
        scene = svc.get_scene(design_id="dP", lod=LODLevel.MEDIUM, allow_visual_only=False)
        assert scene.simulation_integrity == SimulationIntegrity.DECOUPLED
        assert scene.metadata.get("simulation_integrity_reason") == "missing_hydrostatics_for_panelized"

