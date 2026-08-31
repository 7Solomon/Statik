"""Mapping between node identifiers and global degree-of-freedom indices.

Every node carries three DOFs in a fixed order: [u, v, theta]
  u     translation along global +x
  v     translation along global +y
  theta rotation, positive counter-clockwise
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from src.models.analyze import Node

DOFS_PER_NODE = 3

#: Offsets within a node's DOF triple.
U, V, THETA = 0, 1, 2


class DofMap:
    """Assigns a contiguous block of global DOF indices to each node."""

    def __init__(self, nodes: Iterable[Node]):
        self._indices: Dict[str, List[int]] = {}
        counter = 0
        for node in nodes:
            self._indices[node.id] = [counter, counter + 1, counter + 2]
            counter += DOFS_PER_NODE
        self.n_dof = counter

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._indices

    def __getitem__(self, node_id: str) -> List[int]:
        return self._indices[node_id]

    def __len__(self) -> int:
        return len(self._indices)

    def node_ids(self) -> Iterable[str]:
        return self._indices.keys()

    def element(self, start_node_id: str, end_node_id: str) -> List[int]:
        """The six global indices of a two-node element, start node first."""
        return self._indices[start_node_id] + self._indices[end_node_id]
