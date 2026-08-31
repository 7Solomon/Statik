"""Local element stiffness and the treatment of end releases.

DOF ordering inside every 6x6 element matrix and 6-vector:

    0: u1   1: v1   2: theta1   3: u2   4: v2   5: theta2
"""

from __future__ import annotations

from typing import Tuple

import numpy as np

from src.models.analyze import MemberProperties, MemberReleases

#: Element-local DOF indices, named so the matrix assembly reads clearly.
U1, V1, TH1, U2, V2, TH2 = range(6)


def local_stiffness(properties: MemberProperties, L: float) -> np.ndarray:
    """Euler-Bernoulli frame element: axial plus bending, no shear deformation."""
    E, A, I = properties.E, properties.A, properties.I

    ea = E * A / L
    b = 12.0 * E * I / L ** 3
    c = 6.0 * E * I / L ** 2
    d = 4.0 * E * I / L
    e = 2.0 * E * I / L

    return np.array([
        [ea, 0.0, 0.0, -ea, 0.0, 0.0],
        [0.0, b, c, 0.0, -b, c],
        [0.0, c, d, 0.0, -c, e],
        [-ea, 0.0, 0.0, ea, 0.0, 0.0],
        [0.0, -b, -c, 0.0, b, -c],
        [0.0, c, e, 0.0, -c, d],
    ])


def condense_releases(
    k: np.ndarray, f_fixed: np.ndarray, releases: MemberReleases
) -> Tuple[np.ndarray, np.ndarray]:
    """Eliminate released rotational DOFs from the stiffness AND the loads.

    For a released DOF r the element carries no moment there, so

        k_ru u_u + k_rr u_r + f_r = 0   =>   u_r = -(k_ru u_u + f_r) / k_rr

    Substituting back condenses both quantities together:

        k <- k_ij - k_ir k_rj / k_rr
        f <- f_i  - k_ir f_r  / k_rr

    Both must be condensed with the SAME matrix, in the same order, which is
    why they are done in one function. Condensing only the stiffness -- as the
    previous code did, its load-side counterpart being a stub whose body was a
    bare ``pass`` -- leaves a hinged end still carrying its clamped fixed-end
    moment. For a uniform load on a member hinged at both ends that is the
    difference between the correct qL^2/8 sagging moment and a spurious pair
    of qL^2/12 end moments.

    Only mz releases are handled; fx and fy releases are accepted by the model
    but have no effect here.
    """
    k = np.array(k, dtype=float, copy=True)
    f = np.array(f_fixed, dtype=float, copy=True)

    released = []
    if releases.start.mz:
        released.append(TH1)
    if releases.end.mz:
        released.append(TH2)

    for dof in released:
        pivot = k[dof, dof]
        if abs(pivot) < 1e-30:
            # Already released by an earlier condensation; nothing to remove.
            continue
        column = k[:, dof].copy()
        f = f - column * (f[dof] / pivot)
        k = k - np.outer(column / pivot, k[dof, :])
        k[dof, :] = 0.0
        k[:, dof] = 0.0
        f[dof] = 0.0

    return k, f
