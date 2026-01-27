"""
TurnContract Vault: version mismatch must decouple.
"""

from magnet.core.dataclasses import TurnContract


class MockStateManager:
    def __init__(self, values=None):
        self._values = values or {}

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value, source=None):
        self._values[key] = value


def test_version_mismatch_decouples():
    from unittest.mock import patch
    from magnet.webgl.geometry_service import GeometryService
    from magnet.webgl.schema import LODLevel, SimulationIntegrity
    from magnet.webgl.interfaces import HullGeometryData

    # Contract exists for v10, but state is now v11.
    c = TurnContract(
        contract_id="abc123",
        design_id="d",
        design_version=10,
        state_snapshot_hash="h",
        intent_snapshot_hash="i",
        integrity_state="AUTHORITATIVE",
        primary_reason=None,
        violations=[],
        timestamp_s=0.0,
    )

    sm = MockStateManager(
        {
            "design_version": 11,
            "turn_contracts": [c],
            "current_turn_contract_id": "abc123",
            "kernel.physics_last_validated_version": 10,
            "kernel.hydrostatics_last_validated_version": 10,
        }
    )
    svc = GeometryService(state_manager=sm)

    fake_geom = HullGeometryData(
        design_id="d",
        version_id="d:v11",
        sections=[],
        keel_profile=[],
        stem_profile=[],
        openings=[],
        flow_paths=[],
        attachments=[],
        metadata={"surface_definition": "panelized"},
    )

    with patch.object(svc._grm_provider, "get_hull_geometry", return_value=fake_geom), patch.object(
        svc._grm_provider, "get_geometry_version", return_value="d:v11"
    ):
        scene = svc.get_scene(design_id="d", lod=LODLevel.MEDIUM, allow_visual_only=False)
        assert scene.simulation_integrity == SimulationIntegrity.DECOUPLED
        # Stale version must not be AUTHORITATIVE; reason may be any conservative ladder reason.
        assert scene.metadata.get("simulation_integrity_reason") in (
            "stale_physics",
            "missing_contract",
            "missing_hydrostatics_for_panelized",
        )

