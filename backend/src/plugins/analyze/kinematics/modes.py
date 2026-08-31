"""Turning null-space vectors into KinematicMode objects.

Each basis vector of the null space is one independent motion of the
mechanism. It carries [vx, vy, omega] per node; the Scheibe velocities are
derived from the rigid body each Scheibe is attached to.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from src.models.analyze import KinematicMode, Scheibe, StructuralSystem
from src.plugins.analyze.dofs import THETA, U, V, DofMap

#: Motions smaller than this are treated as no motion at all.
MOTION_TOL = 1e-9


def build_modes(
    system: StructuralSystem, dof_map: DofMap, basis: np.ndarray
) -> List[KinematicMode]:
    """One KinematicMode per null-space basis vector."""
    node_map = {n.id: n for n in system.nodes}
    modes: List[KinematicMode] = []

    for index, raw in enumerate(basis):
        # copy() because the basis rows are views into the SVD output, and
        # normalising in place would mutate it.
        vector = np.array(raw, dtype=float, copy=True)
        peak = np.max(np.abs(vector)) if vector.size else 0.0
        if peak > MOTION_TOL:
            vector /= peak

        node_velocities = {
            node.id: np.array([
                vector[dof_map[node.id][U]],
                vector[dof_map[node.id][V]],
            ])
            for node in system.nodes
            if node.id in dof_map
        }

        scheibe_velocities = {}
        for scheibe in system.scheiben:
            velocity = scheibe_velocity(scheibe, vector, node_map, dof_map)
            if velocity is not None:
                scheibe_velocities[scheibe.id] = velocity

        modes.append(KinematicMode(
            index=index,
            node_velocities=node_velocities,
            scheibe_velocities=scheibe_velocities,
            # Both are filled in by poles.py once the mode exists.
            member_poles={},
            rigid_bodies=[],
        ))

    return modes


def scheibe_velocity(
    scheibe: Scheibe,
    vector: np.ndarray,
    node_map,
    dof_map: DofMap,
) -> Optional[np.ndarray]:
    """[vx, vy, omega] at the Scheibe's centre, or None if it does not apply.

    ELASTIC Scheiben deform rather than move rigidly, so they have no single
    velocity.
    """
    if scheibe.type != "RIGID":
        return None

    reference = next(
        (
            conn.node_id
            for conn in scheibe.connections
            if conn.releases is None and conn.node_id in dof_map
        ),
        None,
    )
    if reference is None:
        return None

    ref_node = node_map[reference]
    iu, iv, ith = dof_map[reference]
    node_vx, node_vy, omega = vector[iu], vector[iv], vector[ith]

    centre_x = (scheibe.corner1.x + scheibe.corner2.x) / 2.0
    centre_y = (scheibe.corner1.y + scheibe.corner2.y) / 2.0

    dx = centre_x - ref_node.position.x
    dy = centre_y - ref_node.position.y

    # v_centre = v_node + omega x r
    return np.array([
        node_vx - dy * omega,
        node_vy + dx * omega,
        omega,
    ])


def is_moving(mode: KinematicMode) -> bool:
    """True when a mode actually displaces something."""
    for velocity in mode.node_velocities.values():
        if float(np.linalg.norm(velocity)) > MOTION_TOL:
            return True
    for velocity in mode.scheibe_velocities.values():
        if float(np.linalg.norm(velocity)) > MOTION_TOL:
            return True
    return False
