"""Kinematic (mechanism) analysis for 2D frames.

This package replaces the former single-file kinematics.py, and absorbs the
pole computation that used to sit in the sibling system.py. The pipeline runs
in one direction, and each stage lives in its own module:

    supports    constraint rows from nodal supports
    members     constraint rows from members (axial and rotational)
    scheiben    constraint rows from RIGID Scheiben
    assembly    the full constraint matrix C
    nullspace   {v : C v = 0}, i.e. the independent motions
    modes       null-space vectors -> KinematicMode
    poles       instantaneous centres, and grouping into rigid bodies

The DOF numbering is shared with the static solver
(src/plugins/analyze/dofs.py) so both use one definition of what DOF 3i+1 is.

``solve_kinematics`` keeps its original signature. ``analyse`` runs the whole
pipeline including poles, which is what the API endpoint wants.
"""

from __future__ import annotations

from typing import List, Tuple

from src.models.analyze import KinematicMode, KinematicResult, StructuralSystem
from src.plugins.analyze.dofs import DofMap

from .assembly import build_constraint_matrix
from .modes import build_modes
from .nullspace import null_space
from .poles import calculate_poles, group_into_subsystems

__all__ = [
    "solve_kinematics",
    "analyse",
    "calculate_poles",
    "group_into_subsystems",
]


def solve_kinematics(
    system: StructuralSystem,
) -> Tuple[List[KinematicMode], int]:
    """Find the independent motions of a system.

    Returns the mode shapes and the degree-of-freedom count. A rigid
    structure gives ``([], 0)``; an n-fold mechanism gives n modes, so the
    two always agree -- the old implementation could report a DOF count with
    no modes to go with it.
    """
    dof_map = DofMap(system.nodes)
    if dof_map.n_dof == 0:
        return [], 0

    C, _unreferenced = build_constraint_matrix(system, dof_map)
    basis, dof = null_space(C, dof_map.n_dof)

    if dof <= 0:
        return [], 0

    return build_modes(system, dof_map, basis), dof


def analyse(system: StructuralSystem) -> KinematicResult:
    """Run the full analysis, poles and rigid bodies included."""
    modes, dof = solve_kinematics(system)

    for mode in modes:
        poles, translation_dirs = calculate_poles(system, mode.node_velocities)
        mode.member_poles = poles
        mode.rigid_bodies = group_into_subsystems(poles, translation_dirs)

    return KinematicResult(
        is_kinematic=dof > 0,
        dof=dof,
        system=system,
        modes=modes,
    )
