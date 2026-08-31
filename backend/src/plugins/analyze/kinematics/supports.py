"""Constraint rows contributed by nodal supports.

Each row expresses one scalar equation ``row . v = 0`` over the global
velocity vector, so a row is a linear constraint on the mechanism's motion.

A support restrains a direction in the NODE's own frame. For a node with a
non-zero ``rotation`` that frame is turned relative to the global axes, which
is how a skewed roller is expressed.
"""

from __future__ import annotations

from typing import List

import numpy as np

from src.models.analyze import Node
from src.plugins.analyze.dofs import THETA, U, V, DofMap


def support_rows(nodes: List[Node], dof_map: DofMap) -> List[np.ndarray]:
    """One row per restrained direction."""
    rows: List[np.ndarray] = []

    for node in nodes:
        if node.id not in dof_map:
            continue
        u_i, v_i, t_i = dof_map[node.id]

        alpha = np.radians(node.rotation)
        c, s = np.cos(alpha), np.sin(alpha)

        if node.supports.fix_n:
            # Local u' = u cos(a) + v sin(a) = 0
            row = np.zeros(dof_map.n_dof)
            row[u_i], row[v_i] = c, s
            rows.append(row)

        if node.supports.fix_v:
            # Local v' = -u sin(a) + v cos(a) = 0
            row = np.zeros(dof_map.n_dof)
            row[u_i], row[v_i] = -s, c
            rows.append(row)

        if node.supports.fix_m:
            row = np.zeros(dof_map.n_dof)
            row[t_i] = 1.0
            rows.append(row)

    return rows
