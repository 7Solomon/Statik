"""Element geometry and the single coordinate-transform convention.

LOCAL AXES
    local x runs from the start node to the end node
    local y is local x rotated +90 degrees, i.e. the direction (-s, c)
    local theta coincides with global theta

The transformation matrix T maps GLOBAL to LOCAL:

    u_local = T @ u_global

so an element matrix expressed locally becomes global via ``T.T @ k @ T``,
and a local force vector becomes global via ``T.T @ f``.

Having exactly one definition of T is the point of this module: the old code
carried three different ones (fem.py, load_vertor.py and langrage/assebly.py)
and they were not all consistent with each other.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.models.analyze import Node

#: Members shorter than this are treated as degenerate.
MIN_LENGTH = 1e-9


class ZeroLengthMemberError(ValueError):
    """Raised when a member's two nodes coincide."""


@dataclass(frozen=True)
class ElementGeometry:
    """Length and orientation of a two-node element."""

    L: float
    c: float  # cos(theta) == dx / L
    s: float  # sin(theta) == dy / L

    @classmethod
    def from_nodes(cls, start: Node, end: Node) -> "ElementGeometry":
        dx = end.position.x - start.position.x
        dy = end.position.y - start.position.y
        length = float(np.hypot(dx, dy))
        if length < MIN_LENGTH:
            raise ZeroLengthMemberError(
                "member between %s and %s has zero length" % (start.id, end.id)
            )
        return cls(L=length, c=dx / length, s=dy / length)

    @property
    def T(self) -> np.ndarray:
        """6x6 global-to-local transformation for a two-node element."""
        block = np.array([
            [self.c, self.s, 0.0],
            [-self.s, self.c, 0.0],
            [0.0, 0.0, 1.0],
        ])
        zero = np.zeros((3, 3))
        return np.block([[block, zero], [zero, block]])

    def to_local(self, fx_global: float, fy_global: float) -> "tuple[float, float]":
        """Resolve a global force vector into local axial and transverse parts."""
        axial = fx_global * self.c + fy_global * self.s
        transverse = -fx_global * self.s + fy_global * self.c
        return axial, transverse
