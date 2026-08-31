"""Support conditions, including skewed (rotated) supports.

A support is imposed in the node's OWN frame. For a node with a non-zero
``rotation`` that frame is turned relative to the global axes, so a roller can
restrain a direction that is neither horizontal nor vertical.

The system is therefore rotated into per-node local frames before the
restraints are applied:

    u_global = T_sys @ u_local
    K_local  = T_sys.T @ K_global @ T_sys
    F_local  = T_sys.T @ F_global

T_sys is block diagonal with one 3x3 block per node, identity for every
unrotated node -- so when nothing is rotated it is the identity matrix and
this costs only a multiply. langrage/solver.py does the same thing for the
dynamics path.

GAP: ``Supports`` values may be a float stiffness rather than a bool, but any
truthy value is treated as fully rigid here.
"""

from __future__ import annotations

from typing import List

import numpy as np

from src.models.analyze import StructuralSystem

from src.plugins.analyze.dofs import THETA, U, V, DofMap

#: Rotations smaller than this are treated as axis-aligned.
MIN_ROTATION = 1e-9


def nodal_rotation_matrix(
    system: StructuralSystem, dof_map: DofMap
) -> np.ndarray:
    """Block-diagonal local-to-global transformation, one block per node."""
    T = np.eye(dof_map.n_dof)

    for node in system.nodes:
        if node.id not in dof_map:
            continue
        if abs(node.rotation) < MIN_ROTATION:
            continue

        alpha = np.radians(node.rotation)
        c, s = np.cos(alpha), np.sin(alpha)
        iu, iv, ith = dof_map[node.id]

        T[iu, iu] = c
        T[iu, iv] = -s
        T[iv, iu] = s
        T[iv, iv] = c
        T[ith, ith] = 1.0

    return T


def has_skewed_supports(system: StructuralSystem) -> bool:
    """True when any node defines a rotated support frame."""
    return any(abs(n.rotation) >= MIN_ROTATION for n in system.nodes)


def fixed_dofs(system: StructuralSystem, dof_map: DofMap) -> List[int]:
    """Global indices of every restrained DOF, in the nodes' own frames."""
    restrained = []
    for node in system.nodes:
        if node.id not in dof_map:
            continue
        dofs = dof_map[node.id]
        if node.supports.fix_n:
            restrained.append(dofs[U])
        if node.supports.fix_v:
            restrained.append(dofs[V])
        if node.supports.fix_m:
            restrained.append(dofs[THETA])
    return restrained


def apply_supports(
    K: np.ndarray, F: np.ndarray, system: StructuralSystem, dof_map: DofMap
) -> List[int]:
    """Impose zero displacement at restrained DOFs, in place.

    Returns the restrained indices so the caller can recover reactions from
    copies of K and F taken beforehand.
    """
    restrained = fixed_dofs(system, dof_map)

    for idx in restrained:
        K[idx, :] = 0.0
        K[:, idx] = 0.0
        K[idx, idx] = 1.0
        F[idx] = 0.0

    return restrained
