"""
TurnContract Vault: AUTHORITATIVE requires a same-version contract.
"""

from unittest.mock import patch


class MockStateManager:
    def __init__(self, values=None):
        self._values = values or {}

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value, source=None):
        self._values[key] = value


def test_authoritative_requires_contract():
    from magnet.webgl.geometry_service import GeometryService
    from magnet.webgl.schema import LODLevel, SimulationIntegrity
    from magnet.webgl.interfaces import HullGeometryData

    sm = MockStateManager(
        {
            "design_version": 3,
            "kernel.physics_last_validated_version": 3,
            "kernel.hydrostatics_last_validated_version": 3,
            "hull.displacement_m3": 10.0,
            "resistance.method_valid": True,
            # No turn_contracts + no current_turn_contract_id
        }
    )
    svc = GeometryService(state_manager=sm)

    fake_geom = HullGeometryData(
        design_id="d",
        version_id="d:v3",
        sections=[],
        keel_profile=[],
        stem_profile=[],
        openings=[],
        flow_paths=[],
        attachments=[],
        metadata={"surface_definition": "panelized"},
    )

    with patch.object(svc._grm_provider, "get_hull_geometry", return_value=fake_geom), patch.object(
        svc._grm_provider, "get_geometry_version", return_value="d:v3"
    ):
        scene = svc.get_scene(design_id="d", lod=LODLevel.MEDIUM, allow_visual_only=False)
        assert scene.simulation_integrity != SimulationIntegrity.AUTHORITATIVE
        assert scene.metadata.get("simulation_integrity_reason") == "missing_contract"

