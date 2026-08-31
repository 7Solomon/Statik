"""Instantaneous centres of rotation, and grouping members into rigid bodies.

For a member whose ends move with velocities v_A and v_B, the angular velocity
follows from the rigid-body relation v_B = v_A + omega x r_BA:

    omega = (r_BA x v_BA) / |r_BA|^2

A non-zero omega gives a finite pole (the instantaneous centre, the point of
zero velocity); a zero omega means the member translates and its pole is at
infinity, recorded as None with the translation direction kept separately.

Members sharing a pole belong to the same rigid body. This is the grouping
the API actually renders. The old kinematics.py additionally ran a
Scheibe-based ``detect_rigid_bodies`` whose result api.py then overwrote with
this one, so two rigid-body detectors existed and one was dead. Only this one
survives.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.models.analyze import RigidBody, StructuralSystem

#: Angular velocities below this count as pure translation.
OMEGA_TOL = 1e-6

#: Velocities below this count as no motion.
VELOCITY_TOL = 1e-9


def calculate_poles(
    system: StructuralSystem,
    velocity_dict: Dict[str, np.ndarray],
) -> Tuple[Dict[str, Optional[np.ndarray]], Dict[str, np.ndarray]]:
    """Pole per member, plus the direction of the purely translating ones."""
    member_poles: Dict[str, Optional[np.ndarray]] = {}
    translation_dirs: Dict[str, np.ndarray] = {}

    node_map = {n.id: n for n in system.nodes}

    for member in system.members:
        start = node_map.get(member.start_node_id)
        end = node_map.get(member.end_node_id)
        if start is None or end is None:
            continue

        v_start = velocity_dict.get(start.id, np.zeros(2))
        v_end = velocity_dict.get(end.id, np.zeros(2))

        r = end.coordinates - start.coordinates
        v_rel = v_end - v_start

        length_squared = float(np.dot(r, r))
        if length_squared < 1e-12:
            continue

        omega = (r[0] * v_rel[1] - r[1] * v_rel[0]) / length_squared

        if abs(omega) < OMEGA_TOL:
            member_poles[member.id] = None
            norm = float(np.linalg.norm(v_start))
            translation_dirs[member.id] = (
                v_start / norm if norm > VELOCITY_TOL else np.zeros(2)
            )
        else:
            # v_start = omega x (A - P)  =>  P = A - (v_start x k) / omega
            member_poles[member.id] = np.array([
                start.position.x - v_start[1] / omega,
                start.position.y + v_start[0] / omega,
            ])

    return member_poles, translation_dirs


def group_into_subsystems(
    member_poles: Dict[str, Optional[np.ndarray]],
    translation_velocity_dict: Optional[Dict[str, np.ndarray]] = None,
    tolerance: float = 1e-4,
) -> List[RigidBody]:
    """Collect members that share a pole into RigidBody objects."""
    groups: List[Dict[str, Any]] = []

    for member_id, pole in member_poles.items():
        direction = _direction_of(member_id, translation_velocity_dict)

        for group in groups:
            if _belongs(group, pole, direction, tolerance):
                group["members"].append(member_id)
                break
        else:
            groups.append({
                "type": "rotation" if pole is not None else "translation",
                "val": pole if pole is not None else direction,
                "members": [member_id],
            })

    return [
        RigidBody(
            id=index,
            member_ids=group["members"],
            movement_type=group["type"],
            center_or_vector=group["val"],
        )
        for index, group in enumerate(groups)
    ]


def _direction_of(member_id, translation_velocity_dict) -> np.ndarray:
    if not translation_velocity_dict:
        return np.zeros(2)
    return translation_velocity_dict.get(member_id, np.zeros(2))


def _belongs(group, pole, direction, tolerance: float) -> bool:
    """Does a member with this pole belong to an existing group?"""
    if pole is not None:
        if group["type"] != "rotation":
            return False
        return float(np.linalg.norm(pole - group["val"])) < tolerance

    if group["type"] != "translation":
        return False

    group_direction = group["val"]
    moving = float(np.linalg.norm(direction)) > VELOCITY_TOL
    group_moving = float(np.linalg.norm(group_direction)) > VELOCITY_TOL

    if not moving and not group_moving:
        # Both stationary. Previously two zero vectors had a dot product of 0
        # and so never matched, giving every stationary member a rigid body of
        # its own; they belong to one group.
        return True
    if moving != group_moving:
        return False

    return bool(np.isclose(np.dot(direction, group_direction), 1.0,
                           atol=tolerance))
