"""Constraint rows contributed by RIGID Scheiben.

A RIGID Scheibe forces the nodes attached to it to move as one body. Taking
its first rigidly attached node as the reference r, every other attached node
i at offset (dx, dy) satisfies

    theta_i = theta_r
    u_i     = u_r - dy * theta_r
    v_i     = v_r + dx * theta_r

A connection carrying releases is partially free: each released component
drops its row. ELASTIC Scheiben deform and impose no kinematic constraint.

The previous implementation skipped a whole Scheibe when it had fewer than
two RIGID connections, which also skipped the released connections below it,
so a Scheibe attached entirely through hinges constrained nothing at all.
Here the reference node is chosen from all connections, so partially hinged
Scheiben still contribute their rows.
"""

from __future__ import annotations

from typing import List

import numpy as np

from src.models.analyze import Scheibe
from src.plugins.analyze.dofs import DofMap


def scheibe_rows(
    scheiben: List[Scheibe], node_map, dof_map: DofMap
) -> List[np.ndarray]:
    """Rigid-body rows for every RIGID Scheibe."""
    rows: List[np.ndarray] = []

    for scheibe in scheiben:
        if scheibe.type != "RIGID":
            continue

        connections = [
            conn for conn in scheibe.connections if conn.node_id in dof_map
        ]
        if len(connections) < 2:
            continue

        # Prefer a rigid connection as the reference; fall back to the first.
        reference = next(
            (c for c in connections if c.releases is None), connections[0]
        )
        ref_node = node_map[reference.node_id]
        ref_ux, ref_uy, ref_theta = dof_map[reference.node_id]

        for conn in connections:
            if conn.node_id == reference.node_id:
                continue

            other = node_map[conn.node_id]
            ux, uy, theta = dof_map[conn.node_id]

            dx = other.position.x - ref_node.position.x
            dy = other.position.y - ref_node.position.y

            releases = conn.releases

            if releases is None or not releases.mz:
                row = np.zeros(dof_map.n_dof)
                row[theta] = 1.0
                row[ref_theta] = -1.0
                rows.append(row)

            if releases is None or not releases.fx:
                row = np.zeros(dof_map.n_dof)
                row[ux] = 1.0
                row[ref_ux] = -1.0
                row[ref_theta] = dy
                rows.append(row)

            if releases is None or not releases.fy:
                row = np.zeros(dof_map.n_dof)
                row[uy] = 1.0
                row[ref_uy] = -1.0
                row[ref_theta] = -dx
                rows.append(row)

    return rows
