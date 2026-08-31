"""Constraint rows contributed by members.

A member imposes two kinds of kinematic constraint:

AXIAL -- a rigid link cannot stretch, so the relative velocity of its ends
has no component along the member axis:

    (v_j - v_i) . n = 0        n = the unit vector from start to end

An axial release at either end lets the member telescope, removing the row.

ROTATIONAL -- a rigidly framed end must rotate with the member:

    theta_end = Omega        Omega = ((v_j - v_i) . t) / L,  t = (-n_y, n_x)

An mz release at that end frees the joint and removes the row. A node where
EVERY incident member is released, and which carries no moment support, ends
up with a rotation that no row references at all -- see assembly.py, which
handles those coordinates rather than letting them count as freedoms.
"""

from __future__ import annotations

from typing import List

import numpy as np

from src.models.analyze import Member, Node
from src.plugins.analyze.dofs import DofMap

#: Members shorter than this have no defined axis and are skipped.
MIN_LENGTH = 1e-9


def member_rows(
    members: List[Member], node_map, dof_map: DofMap
) -> List[np.ndarray]:
    """Axial and rotational rows for every member."""
    rows: List[np.ndarray] = []

    for member in members:
        start = node_map.get(member.start_node_id)
        end = node_map.get(member.end_node_id)
        if start is None or end is None:
            continue
        if start.id not in dof_map or end.id not in dof_map:
            continue

        ix, iy, it = dof_map[start.id]
        jx, jy, jt = dof_map[end.id]

        dx = end.position.x - start.position.x
        dy = end.position.y - start.position.y
        L = float(np.hypot(dx, dy))
        if L < MIN_LENGTH:
            continue

        nx, ny = dx / L, dy / L

        releases = member.releases
        if not releases.start.fx and not releases.end.fx:
            row = np.zeros(dof_map.n_dof)
            row[ix], row[iy] = -nx, -ny
            row[jx], row[jy] = nx, ny
            rows.append(row)

        for released, theta_dof in (
            (releases.start.mz, it),
            (releases.end.mz, jt),
        ):
            if released:
                continue
            row = np.zeros(dof_map.n_dof)
            row[theta_dof] = -1.0
            row[ix], row[iy] = ny / L, -nx / L
            row[jx], row[jy] = -ny / L, nx / L
            rows.append(row)

    return rows
