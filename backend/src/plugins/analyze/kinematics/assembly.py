"""Assembly of the kinematic constraint matrix.

The mechanism analysis asks which velocity fields ``v`` satisfy every
constraint at once, i.e. what lies in the null space of

    C v = 0

with one row of C per scalar constraint. Rows come from supports.py,
members.py and scheiben.py.

UNREFERENCED ROTATIONS
----------------------
A nodal rotation that appears in NO row is not a degree of freedom of the
structure -- it is a coordinate that nothing defines. This happens at any
node where every incident member releases mz and no support fixes the
rotation, which is exactly what a pin joint is.

Counting those coordinates as freedoms reported a three-hinged arch, a rigid
and statically determinate structure, as a 3-fold mechanism: one phantom
freedom per hinged node. They are pinned here so the null space contains only
real motions.

The dead ``add_coupled_hinge_constraints`` in the old module was an attempt at
the same problem. It could not work: it only fired where two or more hinged
members met, so an arch's outer hinges stayed phantom, and it worked by tying
the node rotation to one member's rotation -- reintroducing the very stiffness
the hinge removes, which would have distorted the mode shapes.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

from src.models.analyze import StructuralSystem
from src.plugins.analyze.dofs import THETA, DofMap

from .members import member_rows
from .scheiben import scheibe_rows
from .supports import support_rows

#: A column with no entry larger than this is treated as unreferenced.
ZERO_COLUMN = 1e-14


def build_constraint_matrix(
    system: StructuralSystem, dof_map: DofMap
) -> Tuple[np.ndarray, List[int]]:
    """Assemble C, and pin any rotation no constraint references.

    Returns the matrix and the list of rotational DOF indices that had to be
    pinned, which the caller may report or ignore.
    """
    node_map = {n.id: n for n in system.nodes}

    rows: List[np.ndarray] = []
    rows.extend(support_rows(system.nodes, dof_map))
    rows.extend(member_rows(system.members, node_map, dof_map))
    rows.extend(scheibe_rows(system.scheiben, node_map, dof_map))

    C = (
        np.array(rows, dtype=float)
        if rows
        else np.zeros((0, dof_map.n_dof))
    )

    unreferenced = unreferenced_rotations(C, system, dof_map)
    for dof in unreferenced:
        row = np.zeros(dof_map.n_dof)
        row[dof] = 1.0
        C = np.vstack([C, row])

    return C, unreferenced


def unreferenced_rotations(
    C: np.ndarray, system: StructuralSystem, dof_map: DofMap
) -> List[int]:
    """Rotational DOFs that no constraint row mentions."""
    unreferenced = []

    for node in system.nodes:
        if node.id not in dof_map:
            continue
        dof = dof_map[node.id][THETA]
        if C.shape[0] == 0 or not np.any(np.abs(C[:, dof]) > ZERO_COLUMN):
            unreferenced.append(dof)

    return unreferenced
