"""Constraints that add stiffness or force outside the member elements.

Two families:

  * RIGID Scheiben, tied together with a penalty formulation.
  * Discrete SPRING / DAMPER / CABLE constraints between two nodes.

The discrete constraints use the same axial-bar stiffness as the dynamics
assembly (langrage/assebly.py, _constraint_matrix) so the two solvers agree
about what a spring is.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from src.models.analyze import StructuralSystem

from src.plugins.analyze.dofs import THETA, U, V, DofMap

#: Penalty stiffness for rigid-body coupling. Large enough to dominate the
#: member stiffnesses, small enough to stay clear of the conditioning limit.
RIGID_PENALTY = 1e12

#: Constraints shorter than this have no defined axis.
MIN_LENGTH = 1e-9


def apply_rigid_scheiben(
    K: np.ndarray, system: StructuralSystem, dof_map: DofMap
) -> None:
    """Tie the nodes of each RIGID Scheibe into one rigid body, in place.

    For nodes i and a reference node r separated by (dx, dy):

        theta_i = theta_r
        u_i     = u_r - dy * theta_r
        v_i     = v_r + dx * theta_r

    Each is enforced by adding PENALTY * (constraint)^2 to the strain energy.
    """
    node_map = {n.id: n for n in system.nodes}

    for scheibe in system.scheiben:
        if scheibe.type != "RIGID":
            continue

        rigid_ids = [
            conn.node_id
            for conn in scheibe.connections
            if conn.releases is None and conn.node_id in dof_map
        ]
        if len(rigid_ids) < 2:
            continue

        ref_id = rigid_ids[0]
        ref = node_map[ref_id]
        ref_dofs = dof_map[ref_id]

        for other_id in rigid_ids[1:]:
            other = node_map[other_id]
            other_dofs = dof_map[other_id]

            dx = other.position.x - ref.position.x
            dy = other.position.y - ref.position.y

            _couple(K, other_dofs[THETA], ref_dofs[THETA])
            _couple(K, other_dofs[U], ref_dofs[U])
            _couple(K, other_dofs[V], ref_dofs[V])

            # Rotation cross-terms for the lever arms.
            _cross(K, other_dofs[U], ref_dofs[U], ref_dofs[THETA], dy)
            _cross(K, other_dofs[V], ref_dofs[V], ref_dofs[THETA], -dx)


def _couple(K: np.ndarray, i: int, j: int) -> None:
    """Penalise (x_i - x_j)^2."""
    K[i, i] += RIGID_PENALTY
    K[i, j] -= RIGID_PENALTY
    K[j, i] -= RIGID_PENALTY
    K[j, j] += RIGID_PENALTY


def _cross(K: np.ndarray, i: int, j: int, theta: int, arm: float) -> None:
    """Penalty cross-terms coupling a translation pair to a rotation."""
    K[i, theta] += RIGID_PENALTY * arm
    K[theta, i] += RIGID_PENALTY * arm
    K[j, theta] -= RIGID_PENALTY * arm
    K[theta, j] -= RIGID_PENALTY * arm


def apply_discrete_constraints(
    K: np.ndarray, F: np.ndarray, system: StructuralSystem, dof_map: DofMap
) -> None:
    """Add spring, cable and damper contributions, in place.

    Statics sees:

      * SPRING -- axial stiffness ``k``, plus ``preload`` as an axial force.
      * CABLE  -- axial stiffness ``EA / L``, plus ``prestress`` as an axial
        force. Modelled as linear-elastic: a real cable goes slack in
        compression, which needs an iterative solve and is not done here.
      * DAMPER -- contributes nothing statically unless a parallel stiffness
        ``k`` is given. Its damping coefficient ``c`` is a velocity term and
        only matters to the dynamics solver.

    PRELOAD / PRESTRESS SIGN: positive means tension, which pulls the two end
    nodes toward one another.
    """
    node_map = {n.id: n for n in system.nodes}

    for constraint in system.constraints:
        axis = _axis(constraint, node_map, dof_map)
        if axis is None:
            continue
        c, s, L, dofs = axis

        stiffness = 0.0
        pretension = 0.0

        if constraint.type == "SPRING":
            stiffness = constraint.k
            pretension = constraint.preload
        elif constraint.type == "CABLE":
            stiffness = constraint.EA / L
            pretension = constraint.prestress
        elif constraint.type == "DAMPER":
            stiffness = 0.0 if constraint.k is None else constraint.k

        if stiffness:
            _add_axial_stiffness(K, dofs, c, s, stiffness)
        if pretension:
            # Tension pulls the start node toward the end node and vice versa.
            F[dofs[0]] += pretension * c
            F[dofs[1]] += pretension * s
            F[dofs[2]] -= pretension * c
            F[dofs[3]] -= pretension * s


def _axis(
    constraint, node_map, dof_map: DofMap
) -> Optional[Tuple[float, float, float, List[int]]]:
    """Direction cosines, length and the four translational DOFs, or None."""
    start = node_map.get(constraint.start_node_id)
    end = node_map.get(constraint.end_node_id)
    if start is None or end is None:
        return None
    if start.id not in dof_map or end.id not in dof_map:
        return None

    dx = end.position.x - start.position.x
    dy = end.position.y - start.position.y
    L = float(np.hypot(dx, dy))
    if L < MIN_LENGTH:
        return None

    dofs = dof_map[start.id][:2] + dof_map[end.id][:2]
    return dx / L, dy / L, L, dofs


def _add_axial_stiffness(
    K: np.ndarray, dofs: List[int], c: float, s: float, k: float
) -> None:
    """Two-node axial bar stiffness along the direction (c, s)."""
    block = k * np.array([
        [c * c, c * s, -c * c, -c * s],
        [c * s, s * s, -c * s, -s * s],
        [-c * c, -c * s, c * c, c * s],
        [-c * s, -s * s, c * s, s * s],
    ])
    for i, gi in enumerate(dofs):
        for j, gj in enumerate(dofs):
            K[gi, gj] += block[i, j]


def unsupported_features(system: StructuralSystem) -> List[str]:
    """Describe anything in the system the static solve still ignores."""
    warnings = []

    elastic = [s for s in system.scheiben if s.type == "ELASTIC"]
    if elastic:
        warnings.append(
            "%d ELASTIC Scheibe(n) ignored: 2D meshing is not implemented"
            % len(elastic)
        )

    return warnings
