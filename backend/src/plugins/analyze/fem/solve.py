"""The linear solve step."""

from __future__ import annotations

import numpy as np


class SingularSystemError(RuntimeError):
    """The stiffness matrix is not invertible: the structure is a mechanism."""


def solve_displacements(K: np.ndarray, F: np.ndarray) -> np.ndarray:
    """Solve K u = F for the nodal displacements.

    Raises SingularSystemError when the structure is kinematically unstable,
    which the caller turns into a failed FEMResult rather than a traceback.
    """
    try:
        return np.linalg.solve(K, F)
    except np.linalg.LinAlgError as exc:
        raise SingularSystemError(
            "Singular Matrix (Unstable Structure)"
        ) from exc
