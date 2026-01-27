"""
Truthfulness Torture Tests: Negative Path Verification

These tests prove the system can *fail correctly*:
- APPROXIMATE when physics is out-of-envelope
- DECOUPLED when geometry changes without physics refresh
- ERROR when surface intent is missing (no silent default-to-smooth)
"""

import math
import pytest
from unittest.mock import Mock, patch
from magnet.core.dataclasses import TurnContract


class MockStateManager:
    def __init__(self, values=None):
        self._values = values or {}

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value, source=None):
        self._values[key] = value

    def to_dict(self):
        # Some validators call to_dict(); keep it minimal for our tests.
        return dict(self._values)


def test_savitsky_oob_flips_scene_integrity_to_approximate():
    """
    Savitsky out-of-bounds:
    - deadrise 45°
    - Fn (beam) < 1.0 equivalent behavior via method_valid False

    We verify SceneData.simulation_integrity becomes APPROXIMATE (never AUTHORITATIVE).
    """
    from magnet.webgl.geometry_service import GeometryService
    from magnet.webgl.schema import LODLevel, SimulationIntegrity
    from magnet.webgl.schema import MeshData
    from magnet.webgl.interfaces import HullGeometryData

    # Physics already ran for this design_version, but marks resistance invalid.
    sm = MockStateManager(
        {
            "design_version": 7,
            "kernel.physics_last_validated_version": 7,
            "resistance.method_valid": False,
        }
    )

    svc = GeometryService(state_manager=sm)
    fake_geom = HullGeometryData(
        design_id="d1",
        version_id="d1:v7",
        sections=[],
        keel_profile=[],
        stem_profile=[],
        openings=[],
        flow_paths=[],
        attachments=[],
    )

    with patch.object(svc._grm_provider, "get_hull_geometry", return_value=fake_geom), patch.object(
        svc, "_tessellate_grm", return_value=MeshData(mesh_id="hull", vertices=[0, 0, 0], indices=[])
    ):
        scene = svc.get_scene(design_id="d1", lod=LODLevel.MEDIUM, allow_visual_only=False)
        assert scene.simulation_integrity == SimulationIntegrity.APPROXIMATE


def test_dirty_geometry_flips_scene_integrity_to_decoupled():
    """
    Dirty Geometry:
    Mutate geometry / commit a new design_version without rerunning physics.
    Scene must immediately read DECOUPLED.
    """
    from magnet.webgl.geometry_service import GeometryService
    from magnet.webgl.schema import LODLevel, SimulationIntegrity
    from magnet.webgl.schema import MeshData
    from magnet.webgl.interfaces import HullGeometryData

    c = TurnContract(
        contract_id="tc_stale",
        design_id="d1",
        design_version=11,
        state_snapshot_hash="h",
        intent_snapshot_hash="i",
        integrity_state="DECOUPLED",
        primary_reason="stale_physics",
        violations=["stale_physics"],
        timestamp_s=0.0,
    )
    sm = MockStateManager(
        {
            "design_version": 11,
            "kernel.physics_last_validated_version": 10,  # stale physics
            "resistance.method_valid": True,
            "turn_contracts": [c],
            "current_turn_contract_id": "tc_stale",
        }
    )

    svc = GeometryService(state_manager=sm)
    fake_geom = HullGeometryData(
        design_id="d1",
        version_id="d1:v11",
        sections=[],
        keel_profile=[],
        stem_profile=[],
        openings=[],
        flow_paths=[],
        attachments=[],
    )

    with patch.object(svc._grm_provider, "get_hull_geometry", return_value=fake_geom), patch.object(
        svc, "_tessellate_grm", return_value=MeshData(mesh_id="hull", vertices=[0, 0, 0], indices=[])
    ):
        scene = svc.get_scene(design_id="d1", lod=LODLevel.MEDIUM, allow_visual_only=False)
        assert scene.simulation_integrity == SimulationIntegrity.DECOUPLED


def test_missing_surface_intent_raises():
    """
    Missing Intent:
    Remove surface_definition from payload. Kernel must raise MissingSurfaceIntentError
    (never defaulting to 'smooth').
    """
    from magnet.kernel.stdlib.compiler import compile_to_geometry, MissingSurfaceIntentError

    with pytest.raises(MissingSurfaceIntentError):
        compile_to_geometry({"resources": {}}, loa=25.0)


def test_station_spacing_warning_triggers_on_high_rms_variation():
    """
    Volume parity edge-case safety: warn when station spacing variation is high.
    """
    from magnet.physics.geometry_hydrostatics import compute_hydrostatics_from_geometry
    from magnet.hull_gen.geometry import HullGeometry, HullSection, SectionPoint, Point3D, EdgeType

    # Non-uniform station spacing: dx = [0.1, 0.1, 1.8] => high RMS variation
    xs = [0.0, 0.1, 0.2, 2.0]
    secs = []
    for x in xs:
        pts = [
            SectionPoint(position=Point3D(x=x, y=0.0, z=0.0), edge_type=EdgeType.SMOOTH),
            SectionPoint(position=Point3D(x=x, y=1.0, z=1.0), edge_type=EdgeType.SMOOTH),
            SectionPoint(position=Point3D(x=x, y=0.0, z=2.0), edge_type=EdgeType.SMOOTH),
        ]
        secs.append(HullSection(x_position=x, station=0.0 if xs[-1] == 0 else x / xs[-1], points=pts))

    geom = HullGeometry(sections=secs, metadata={"surface_definition": "panelized"})
    res = compute_hydrostatics_from_geometry(geom, draft=1.0)
    assert any("IntegrationRiskWarning" in w for w in (res.warnings or []))

