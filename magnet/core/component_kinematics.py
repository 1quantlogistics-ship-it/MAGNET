"""
magnet/core/component_kinematics.py

T6.5 / §0.9.3: Component kinematics (6-DoF) for multi-body optimization.

This module provides an enum-free, numeric representation of component pose:
- translation (x,y,z) in meters (vessel frame)
- rotation (roll,pitch,yaw) in degrees

Integration note (current codebase reality):
- Component placement is represented in DesignState via `resources` entries
  (e.g. `geometry.body` with `offset_*_m`). To keep the control plane simple,
  kinematic DoFs map to state paths under `resources.<resource_id>.*`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np


Bounds = Optional[Tuple[float, float]]


@dataclass
class KinematicDoF:
    """6-DoF kinematic parameters for a component."""

    # Translation (meters, vessel frame: +x forward, +y port, +z up)
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    # Rotation (degrees, right-handed about vessel axes)
    roll: float = 0.0   # about x
    pitch: float = 0.0  # about y
    yaw: float = 0.0    # about z

    # Optional bounds (if None => fixed/non-adjustable)
    x_bounds: Bounds = None
    y_bounds: Bounds = None
    z_bounds: Bounds = None
    roll_bounds: Bounds = None
    pitch_bounds: Bounds = None
    yaw_bounds: Bounds = None

    def to_transform_matrix(self) -> np.ndarray:
        """
        Convert to a 4x4 homogeneous transform matrix.

        Convention:
        - Translation is applied after rotation (standard homogeneous form).
        - Rotation uses extrinsic Z (yaw) then Y (pitch) then X (roll):
            R = Rz(yaw) @ Ry(pitch) @ Rx(roll)
        """
        rx = np.deg2rad(float(self.roll))
        ry = np.deg2rad(float(self.pitch))
        rz = np.deg2rad(float(self.yaw))

        cx, sx = float(np.cos(rx)), float(np.sin(rx))
        cy, sy = float(np.cos(ry)), float(np.sin(ry))
        cz, sz = float(np.cos(rz)), float(np.sin(rz))

        Rx = np.array(
            [[1.0, 0.0, 0.0],
             [0.0, cx, -sx],
             [0.0, sx, cx]],
            dtype=float,
        )
        Ry = np.array(
            [[cy, 0.0, sy],
             [0.0, 1.0, 0.0],
             [-sy, 0.0, cy]],
            dtype=float,
        )
        Rz = np.array(
            [[cz, -sz, 0.0],
             [sz, cz, 0.0],
             [0.0, 0.0, 1.0]],
            dtype=float,
        )

        R = Rz @ Ry @ Rx

        T = np.eye(4, dtype=float)
        T[:3, :3] = R
        T[:3, 3] = np.array([float(self.x), float(self.y), float(self.z)], dtype=float)
        return T

    def get_adjustable_params(self) -> List[str]:
        adjustable: List[str] = []
        if self.x_bounds is not None:
            adjustable.append("x")
        if self.y_bounds is not None:
            adjustable.append("y")
        if self.z_bounds is not None:
            adjustable.append("z")
        if self.roll_bounds is not None:
            adjustable.append("roll")
        if self.pitch_bounds is not None:
            adjustable.append("pitch")
        if self.yaw_bounds is not None:
            adjustable.append("yaw")
        return adjustable


def kinematic_resource_state_paths(resource_id: str) -> Dict[str, str]:
    """
    Map dof names to StateManager paths for a given `resources` entry.
    """
    rid = str(resource_id)
    return {
        "x": f"resources.{rid}.offset_x_m",
        "y": f"resources.{rid}.offset_y_m",
        "z": f"resources.{rid}.offset_z_m",
        "roll": f"resources.{rid}.roll_deg",
        "pitch": f"resources.{rid}.pitch_deg",
        "yaw": f"resources.{rid}.yaw_deg",
    }


def read_kinematics_from_resource(resource: Dict) -> KinematicDoF:
    """Read kinematics from a geometry resource dict (best-effort)."""
    try:
        x = float(resource.get("offset_x_m", 0.0) or 0.0)
        y = float(resource.get("offset_y_m", 0.0) or 0.0)
        z = float(resource.get("offset_z_m", 0.0) or 0.0)
        roll = float(resource.get("roll_deg", 0.0) or 0.0)
        pitch = float(resource.get("pitch_deg", 0.0) or 0.0)
        yaw = float(resource.get("yaw_deg", 0.0) or 0.0)
    except Exception:
        x = y = z = roll = pitch = yaw = 0.0
    return KinematicDoF(x=x, y=y, z=z, roll=roll, pitch=pitch, yaw=yaw)


def apply_kinematics_to_resource(resource: Dict, dof: KinematicDoF) -> Dict:
    """
    Apply kinematics into a geometry resource dict in-place and return it.
    """
    resource["offset_x_m"] = float(dof.x)
    resource["offset_y_m"] = float(dof.y)
    resource["offset_z_m"] = float(dof.z)
    resource["roll_deg"] = float(dof.roll)
    resource["pitch_deg"] = float(dof.pitch)
    resource["yaw_deg"] = float(dof.yaw)
    return resource

