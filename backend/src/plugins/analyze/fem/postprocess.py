"""Recovery of internal forces, reactions, and the N/V/M diagrams.

Member end forces come from

    f_ends = k_local @ u_local + f_fixed_local
           = [N1, V1, M1, N2, V2, M2]      (local coordinates)

The diagrams then follow from equilibrium of the left-hand free body cut at
distance x from the start node, with ``p`` the load intensity measured
positive downward (local -y), matching the sign convention in loads.py:

    N(x) = -N1
    V(x) =  V1 - integral(p)
    M(x) =  M1 - V1 * x + double_integral(p)

The minus sign on the V1*x term is what makes the diagram close. The previous
implementation used ``M1 + V1 * x`` and subtracted the load term, which left
the free end of a cantilever reporting twice the built-in moment instead of
zero. tests/test_fem.py pins both ends of that check.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from src.models.analyze import (
    ElementContext,
    Load,
    MemberResult,
    StationResult,
)

from src.plugins.analyze.dofs import DofMap
from .geometry import ElementGeometry
from .loads import distributed_profile, local_components

#: Sampling resolution along each member, used for drawing the curves.
STATIONS_PER_MEMBER = 21


def member_end_forces(ctx: ElementContext, u_global: np.ndarray) -> np.ndarray:
    """Local end forces of one member from its global nodal displacements."""
    u_local = ctx.T @ u_global
    return ctx.k_local @ u_local + ctx.f_fixed_local


def _trapezoid_effects(p1: float, p2: float, a: float, b: float, x: float):
    """Resultant and its moment about x, for the loaded part left of x.

    Integrating the linear intensity p(u) = p1 + k u over u in [0, t], where
    u is measured from a and t = clip(x, a, b) - a:

        resultant = p1 t + k t^2 / 2
        moment about x = (x - a) * resultant - (p1 t^2 / 2 + k t^3 / 3)
    """
    span = b - a
    if span <= 0.0 or x <= a:
        return 0.0, 0.0

    t = min(x, b) - a
    slope = (p2 - p1) / span

    resultant = p1 * t + slope * t ** 2 / 2.0
    first_moment = p1 * t ** 2 / 2.0 + slope * t ** 3 / 3.0
    return resultant, (x - a) * resultant - first_moment


def sample_stations(
    ctx: ElementContext, f_ends: np.ndarray, loads: List[Load]
) -> List[StationResult]:
    """Evaluate N, V and M at evenly spaced points along the member."""
    L = ctx.L
    geom = ElementGeometry(L=L, c=ctx.c, s=ctx.s)

    N_start = -f_ends[0]
    V_start = f_ends[1]
    M_start = f_ends[2]

    # Pre-resolve each load into downward-positive intensities and positions.
    spans = []
    points = []
    for load in loads:
        if load.type == "DISTRIBUTED":
            spans.append(distributed_profile(load, L))
        elif load.type == "POINT":
            _, w_y = local_components(load, geom)
            ratio = 0.5 if load.ratio is None else float(load.ratio)
            points.append((-w_y, float(np.clip(ratio, 0.0, 1.0)) * L))

    stations: List[StationResult] = []
    for i in range(STATIONS_PER_MEMBER):
        x = (i / (STATIONS_PER_MEMBER - 1)) * L

        N = N_start
        V = V_start
        M = M_start - V_start * x

        for p1, p2, a, b in spans:
            resultant, moment = _trapezoid_effects(p1, p2, a, b, x)
            V -= resultant
            M += moment

        for p, a in points:
            if x >= a:
                V -= p
                M += p * (x - a)

        stations.append(StationResult(x=x, N=N, V=V, M=M))

    return stations


def build_member_result(member_id: str, stations: List[StationResult]) -> MemberResult:
    """Wrap sampled stations with their envelope values."""
    return MemberResult(
        memberId=member_id,
        stations=stations,
        maxM=max(s.M for s in stations),
        minM=min(s.M for s in stations),
        maxV=max(s.V for s in stations),
        minV=min(s.V for s in stations),
        maxN=max(s.N for s in stations),
        minN=min(s.N for s in stations),
    )


def nodal_displacements(system, dof_map: DofMap, U_global) -> Dict[str, List[float]]:
    """Per-node [u, v, theta], ready for serialisation."""
    return {
        node.id: [float(v) for v in U_global[dof_map[node.id]]]
        for node in system.nodes
        if node.id in dof_map
    }


def support_reactions(
    system,
    dof_map: DofMap,
    reaction_vector: np.ndarray,
) -> Dict[str, List[float]]:
    """Per-node [Rx, Ry, Mz] in GLOBAL axes, for nodes carrying a support.

    ``reaction_vector`` must already be masked to the restrained DOFs in the
    nodes' own frames before being rotated back to global axes. It is not
    re-masked here: a support skewed by ``node.rotation`` restrains one local
    direction, and that single reaction legitimately shows up in both global
    components, so masking again by fix_n / fix_v would discard part of it.
    """
    reactions: Dict[str, List[float]] = {}

    for node in system.nodes:
        if node.id not in dof_map:
            continue
        supports = node.supports
        if not any((supports.fix_n, supports.fix_v, supports.fix_m)):
            continue

        dofs = dof_map[node.id]
        reactions[node.id] = [float(reaction_vector[d]) for d in dofs]

    return reactions
