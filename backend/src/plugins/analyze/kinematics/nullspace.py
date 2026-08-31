"""Null space of the constraint matrix: the mechanism's degrees of freedom.

The number of independent motions is ``n_dof - rank(C)``, and a basis for them
is the trailing rows of Vh from the SVD of C.

RANK TOLERANCE
--------------
The threshold separating real constraints from numerical noise must scale
with the matrix, not be a fixed number. Rotational constraint entries are of
order 1/L, so with the previous hardcoded ``tol = 1e-10`` a rigid cantillever
spanning 1e10 units had its rotational constraints discarded as noise and was
reported as a mechanism. The relative tolerance used here is the same rule
numpy applies in ``matrix_rank``.

Rows are also normalised to unit length first. Scaling a row does not change
the row space, so the null space is unaffected, but it stops a single
large-magnitude row from dominating the singular values and makes the
tolerance meaningful across mixed constraint types.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np


def null_space(C: np.ndarray, n_dof: int) -> Tuple[np.ndarray, int]:
    """Return an orthonormal basis for {v : C v = 0} and its dimension.

    The basis is returned as an array of shape (dof, n_dof), one motion per
    row.
    """
    if n_dof == 0:
        return np.zeros((0, 0)), 0

    if C.shape[0] == 0:
        return np.eye(n_dof), n_dof

    normalised = _normalise_rows(C)
    if normalised.shape[0] == 0:
        return np.eye(n_dof), n_dof

    _, S, Vh = np.linalg.svd(normalised, full_matrices=True)

    tol = S[0] * max(normalised.shape) * np.finfo(float).eps
    rank = int(np.sum(S > tol))
    dof = n_dof - rank

    if dof <= 0:
        return np.zeros((0, n_dof)), 0

    # The trailing rows of Vh span the null space.
    return Vh[rank:, :].copy(), dof


def _normalise_rows(C: np.ndarray) -> np.ndarray:
    """Scale every row to unit length, dropping rows that are entirely zero."""
    norms = np.linalg.norm(C, axis=1)
    keep = norms > 0.0
    if not np.any(keep):
        return np.zeros((0, C.shape[1]))
    return C[keep] / norms[keep, None]
