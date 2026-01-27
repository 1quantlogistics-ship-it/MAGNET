import numpy as np

from magnet.core.component_kinematics import (
    KinematicDoF,
    apply_kinematics_to_resource,
    kinematic_resource_state_paths,
    read_kinematics_from_resource,
)


def test_transform_matrix_has_translation_and_is_4x4():
    dof = KinematicDoF(x=1.0, y=2.0, z=3.0, roll=0.0, pitch=0.0, yaw=0.0)
    T = dof.to_transform_matrix()
    assert T.shape == (4, 4)
    assert np.allclose(T[:3, 3], np.array([1.0, 2.0, 3.0], dtype=float))


def test_adjustable_params_respects_bounds():
    dof = KinematicDoF(x_bounds=(-1.0, 1.0), yaw_bounds=(-10.0, 10.0))
    assert dof.get_adjustable_params() == ["x", "yaw"]


def test_resource_mapping_roundtrip():
    r = {"_type": "geometry.body", "offset_x_m": 0.5, "offset_y_m": -2.0, "offset_z_m": 0.25, "yaw_deg": 15.0}
    dof = read_kinematics_from_resource(r)
    assert dof.x == 0.5
    assert dof.y == -2.0
    assert dof.z == 0.25
    assert dof.yaw == 15.0

    apply_kinematics_to_resource(r, KinematicDoF(x=1.0, y=2.0, z=3.0, roll=1.0, pitch=2.0, yaw=3.0))
    assert r["offset_x_m"] == 1.0
    assert r["pitch_deg"] == 2.0


def test_kinematic_resource_state_paths_are_under_resources():
    paths = kinematic_resource_state_paths("body_123")
    assert paths["x"] == "resources.body_123.offset_x_m"
    assert paths["yaw"] == "resources.body_123.yaw_deg"

