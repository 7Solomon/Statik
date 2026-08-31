"""Assembly of the global stiffness matrix and load vector."""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np

from src.models.analyze import ElementContext, StructuralSystem

from . import loads as load_module
from .constraints import apply_discrete_constraints, apply_rigid_scheiben
from src.plugins.analyze.dofs import DofMap
from .element import condense_releases, local_stiffness
from .geometry import ElementGeometry


def build_element(system: StructuralSystem, member, node_map) -> ElementContext:
    """Everything about one member that both assembly and post-processing need."""
    start = node_map[member.start_node_id]
    end = node_map[member.end_node_id]

    geom = ElementGeometry.from_nodes(start, end)
    T = geom.T

    k_local = local_stiffness(member.properties, geom.L)

    f_fixed_local = np.zeros(6)
    for load in load_module.member_loads(system, member.id):
        f_fixed_local += load_module.fixed_end_forces(load, geom)

    # Stiffness and loads must be condensed together, against the same matrix.
    k_local, f_fixed_local = condense_releases(
        k_local, f_fixed_local, member.releases
    )

    return ElementContext(
        L=geom.L,
        c=geom.c,
        s=geom.s,
        T=T,
        k_local=k_local,
        k_global=T.T @ k_local @ T,
        f_fixed_local=f_fixed_local,
    )


def assemble(
    system: StructuralSystem, dof_map: DofMap
) -> Tuple[np.ndarray, np.ndarray, Dict[str, ElementContext]]:
    """Build K and F for the free (unconstrained) system.

    Returns the global stiffness matrix, the global load vector, and the
    per-member context needed to recover internal forces afterwards.
    """
    K = np.zeros((dof_map.n_dof, dof_map.n_dof))
    F = load_module.nodal_load_vector(system, dof_map)

    node_map = {n.id: n for n in system.nodes}
    contexts: Dict[str, ElementContext] = {}

    for member in system.members:
        ctx = build_element(system, member, node_map)
        contexts[member.id] = ctx

        dofs = dof_map.element(member.start_node_id, member.end_node_id)

        # Equivalent nodal loads carry the opposite sign of the fixed-end
        # forces; see the convention note in loads.py.
        f_fixed_global = ctx.T.T @ ctx.f_fixed_local

        for i, row in enumerate(dofs):
            F[row] -= f_fixed_global[i]
            for j, col in enumerate(dofs):
                K[row, col] += ctx.k_global[i, j]

    apply_rigid_scheiben(K, system, dof_map)
    apply_discrete_constraints(K, F, system, dof_map)

    return K, F, contexts
