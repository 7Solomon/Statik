"""Static FEM solver for 2D frames.

This package replaces the former single-file fem.py. The pipeline runs in one
direction, and each stage lives in its own module:

    dofs        node ids  -> global DOF indices
    geometry    length, orientation, the one transformation convention
    element     local stiffness, end releases by static condensation
    loads       nodal loads and member fixed-end forces
    constraints rigid Scheiben, springs, cables, dampers
    assembly    K and F for the free system
    boundary    supports, including skewed ones
    solve       K u = F
    postprocess end forces, reactions, N/V/M diagrams, envelopes

Only ``solve_static`` is public. ``calculate_complex_fem`` is kept as an alias
so existing callers keep working.

REMAINING GAP: ELASTIC Scheiben need 2D meshing and are ignored; the caller is
warned through the logger. Cables are modelled as linear-elastic bars, so they
resist compression instead of going slack.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import numpy as np

from src.models.analyze import FEMResult, StructuralSystem

from .assembly import assemble
from .boundary import apply_supports, nodal_rotation_matrix
from .constraints import unsupported_features
from src.plugins.analyze.dofs import DofMap
from .geometry import ZeroLengthMemberError
from .postprocess import (
    build_member_result,
    member_end_forces,
    nodal_displacements,
    sample_stations,
    support_reactions,
)
from .solve import SingularSystemError, solve_displacements
from . import loads as _loads

logger = logging.getLogger(__name__)

__all__ = ["solve_static", "calculate_complex_fem"]


def solve_static(system: StructuralSystem) -> Dict[str, Any]:
    """Solve a 2D frame under static loads.

    Always returns a serialisable dict. On failure that is
    ``{"success": False, "error": ...}``; on success it is
    ``FEMResult.to_dict()``.
    """
    for warning in unsupported_features(system):
        logger.warning("%s", warning)

    dof_map = DofMap(system.nodes)

    try:
        K, F, contexts = assemble(system, dof_map)
    except ZeroLengthMemberError as exc:
        return {"success": False, "error": str(exc)}

    # Work in each node's own frame so skewed supports restrain the direction
    # they actually point in. T is the identity when nothing is rotated.
    T = nodal_rotation_matrix(system, dof_map)
    K_nodal = T.T @ K @ T
    F_nodal = T.T @ F

    # apply_supports overwrites the restrained rows, so keep the free system
    # for the reaction recovery below.
    K_bc = K_nodal.copy()
    F_bc = F_nodal.copy()
    restrained = apply_supports(K_bc, F_bc, system, dof_map)

    try:
        U_nodal = solve_displacements(K_bc, F_bc)
    except SingularSystemError as exc:
        return {"success": False, "error": str(exc)}

    U_global = T @ U_nodal

    # R = K u - F is zero at free DOFs and the support reaction at restrained
    # ones. Computed in the nodal frame, then rotated back to global axes.
    residual = K_nodal @ U_nodal - F_nodal
    reaction_nodal = np.zeros_like(residual)
    if restrained:
        reaction_nodal[restrained] = residual[restrained]
    reaction_global = T @ reaction_nodal

    member_results = {}
    for member in system.members:
        ctx = contexts[member.id]
        dofs = dof_map.element(member.start_node_id, member.end_node_id)
        f_ends = member_end_forces(ctx, U_global[dofs])
        stations = sample_stations(
            ctx, f_ends, _loads.member_loads(system, member.id)
        )
        member_results[member.id] = build_member_result(member.id, stations)

    result = FEMResult(
        success=True,
        system=system,
        displacements=nodal_displacements(system, dof_map, U_global),
        reactions=support_reactions(system, dof_map, reaction_global),
        memberResults=member_results,
    )
    return result.to_dict()


#: Backwards-compatible alias for the original entry point.
calculate_complex_fem = solve_static
