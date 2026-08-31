"""Load handling: nodal loads and member fixed-end forces.

SIGN CONVENTIONS
----------------
These were previously implicit and inconsistent between fem.py and
load_vertor.py. They are now stated once, here.

Global axes are physics-style: +x right, +y up, theta counter-clockwise.

``Load.angle`` is degrees counter-clockwise from +x, so a load of value P at
angle -90 (or -P at +90) pulls downward.

A MEMBER ``DISTRIBUTED`` load has no angle. Its ``value`` acts perpendicular
to the member, and a POSITIVE value points "down" in the member's local
frame -- that is, along local -y. This matches how the frontend draws it
(see frontend/app/features/drawing/ForceRenderer.ts, drawDistributedLoad).
Throughout this module ``p`` denotes such a downward-positive intensity.

``f_fixed_local`` is the fixed-end force vector, defined so that

    equivalent nodal load contribution = -T.T @ f_fixed_local
    member end forces                  =  k_local @ u_local + f_fixed_local

Both consumers must agree on this or loads come out backwards. Because of the
minus sign in the first relation, a load acting along local -y produces a
POSITIVE f_fixed_local entry at the transverse DOFs.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

from src.models.analyze import Load, StructuralSystem

from src.plugins.analyze.dofs import DofMap
from .element import TH1, TH2, U1, U2, V1, V2
from .geometry import ElementGeometry

#: 4-point Gauss-Legendre rule on [-1, 1]. The integrand below is a cubic
#: shape function times a linear intensity, so this is exact.
_GAUSS_X = np.array([
    -0.8611363115940526, -0.3399810435848563,
    0.3399810435848563, 0.8611363115940526,
])
_GAUSS_W = np.array([
    0.3478548451374538, 0.6521451548625461,
    0.6521451548625461, 0.3478548451374538,
])

#: Loaded spans shorter than this are ignored.
MIN_LOADED_SPAN = 1e-12


def member_loads(system: StructuralSystem, member_id: str) -> List[Load]:
    """All loads bound to one member."""
    return [
        load for load in system.loads
        if load.scope == "MEMBER" and load.member_id == member_id
    ]


def local_components(load: Load, geom: ElementGeometry) -> Tuple[float, float]:
    """Resolve a member load into (axial, transverse) local components."""
    rad = np.radians(load.angle)
    fx = load.value * np.cos(rad)
    fy = load.value * np.sin(rad)
    if not load.is_global:
        # Angle already measured from the member axis.
        return fx, fy
    return geom.to_local(fx, fy)


def distributed_profile(load: Load, L: float) -> Tuple[float, float, float, float]:
    """Resolve a DISTRIBUTED load into (p_start, p_end, x_start, x_end).

    ``startValue``/``endValue`` fall back to ``value`` exactly as the frontend
    renderer does, and ``startRatio``/``endRatio`` default to the full span.
    All four were previously parsed by the model and then ignored.
    """
    start_ratio = 0.0 if load.start_ratio is None else float(load.start_ratio)
    end_ratio = 1.0 if load.end_ratio is None else float(load.end_ratio)
    a = float(np.clip(start_ratio, 0.0, 1.0)) * L
    b = float(np.clip(end_ratio, 0.0, 1.0)) * L
    if b < a:
        a, b = b, a

    p1 = load.value if load.start_value is None else float(load.start_value)
    p2 = load.value if load.end_value is None else float(load.end_value)
    return p1, p2, a, b


def hermite(x: float, L: float) -> np.ndarray:
    """Beam shape functions [N_v1, N_th1, N_v2, N_th2] at position x."""
    xi = x / L
    return np.array([
        1.0 - 3.0 * xi ** 2 + 2.0 * xi ** 3,
        L * (xi - 2.0 * xi ** 2 + xi ** 3),
        3.0 * xi ** 2 - 2.0 * xi ** 3,
        L * (-xi ** 2 + xi ** 3),
    ])


def fixed_end_forces(load: Load, geom: ElementGeometry) -> np.ndarray:
    """Fixed-end forces for one member load, in local coordinates."""
    if load.type == "DISTRIBUTED":
        return _distributed_fixed_end_forces(load, geom)
    if load.type == "POINT":
        return _point_fixed_end_forces(load, geom)
    # MOMENT and the DYNAMIC_* types are not member loads in the static solve.
    return np.zeros(6)


def _distributed_fixed_end_forces(load: Load, geom: ElementGeometry) -> np.ndarray:
    """Linearly varying load over an arbitrary portion of the member.

    Computed as the consistent load vector ``integral(N(x) p(x) dx)`` over the
    loaded span, which covers uniform, partial and trapezoidal cases with one
    formula. For a full-length uniform load it reduces to the familiar
    [pL/2, pL^2/12, pL/2, -pL^2/12].
    """
    L = geom.L
    p1, p2, a, b = distributed_profile(load, L)

    span = b - a
    f = np.zeros(6)
    if span < MIN_LOADED_SPAN:
        return f

    half = span / 2.0
    for xg, w in zip(_GAUSS_X, _GAUSS_W):
        x = a + half * (xg + 1.0)
        t = (x - a) / span
        p = p1 + (p2 - p1) * t
        N = hermite(x, L)
        contribution = w * half * p * N
        f[V1] += contribution[0]
        f[TH1] += contribution[1]
        f[V2] += contribution[2]
        f[TH2] += contribution[3]

    return f


def _point_fixed_end_forces(load: Load, geom: ElementGeometry) -> np.ndarray:
    """Concentrated load at ``ratio`` along the member.

    Clamped-clamped fixed-end formulae. Previously this lived only in the
    unreferenced load_vertor.py, so member point loads were silently dropped.
    """
    L = geom.L
    ratio = 0.5 if load.ratio is None else float(load.ratio)
    a = float(np.clip(ratio, 0.0, 1.0)) * L
    b = L - a

    w_x, w_y = local_components(load, geom)

    f = np.zeros(6)
    # Axial part splits by lever arm.
    f[U1] = -w_x * b / L
    f[U2] = -w_x * a / L
    # Transverse part: standard clamped-clamped reactions.
    f[V1] = -w_y * b ** 2 * (3.0 * a + b) / L ** 3
    f[TH1] = -w_y * a * b ** 2 / L ** 2
    f[V2] = -w_y * a ** 2 * (a + 3.0 * b) / L ** 3
    f[TH2] = w_y * a ** 2 * b / L ** 2
    return f


def nodal_load_vector(system: StructuralSystem, dof_map: DofMap) -> np.ndarray:
    """Global force vector from loads applied directly to nodes."""
    F = np.zeros(dof_map.n_dof)

    for load in system.loads:
        if load.scope != "NODE":
            continue
        if not load.node_id or load.node_id not in dof_map:
            continue

        dofs = dof_map[load.node_id]
        if load.type == "POINT":
            rad = np.radians(load.angle)
            F[dofs[0]] += load.value * np.cos(rad)
            F[dofs[1]] += load.value * np.sin(rad)
        elif load.type == "MOMENT":
            F[dofs[2]] += load.value

    return F
