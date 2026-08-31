"""Core structural entities: nodes, members and their properties.

These are the inputs a user draws. Analysis outputs live in result.py."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union

import numpy as np

from .utils import Vec2


@dataclass
class Supports:
    # SupportValue = boolean | number (Stiffness)
    fix_n: Union[bool, float] = False
    fix_v: Union[bool, float] = False
    fix_m: Union[bool, float] = False


@dataclass
class MemberProperties:
    E: float  # Young's Modulus
    A: float  # Area
    I: float  # Moment of Inertia


@dataclass
class Release:
    fx: bool = False # Axial
    fy: bool = False # Shear
    mz: bool = False # Moment


@dataclass
class MemberReleases:
    start: Release
    end: Release


@dataclass
class Node:
    id: str  # UUID
    position: Vec2
    supports: Supports
    rotation: float = 0.0

    @property
    def coordinates(self) -> np.ndarray:
        return self.position.to_array()
    
    def to_dict(self):
        return {
            "id": self.id,
            "position": {"x": self.position.x, "y": self.position.y},
            "rotation": self.rotation,
            "supports": {
                "fixN": self.supports.fix_n,
                "fixV": self.supports.fix_v,
                "fixM": self.supports.fix_m
            }
        }


@dataclass
class Member:
    id: str
    start_node_id: str
    end_node_id: str
    
    properties: MemberProperties
    releases: MemberReleases

    # References to actual Node objects (populated during system creation)
    _start_node: Optional[Node] = field(default=None, repr=False)
    _end_node: Optional[Node] = field(default=None, repr=False)

    def length(self) -> float:
        if not self._start_node or not self._end_node:
            return 0.0
        return np.linalg.norm(self._end_node.coordinates - self._start_node.coordinates)

    def to_dict(self):
        return {
            "id": self.id,
            "startNodeId": self.start_node_id, # Convert back to camelCase for frontend!
            "endNodeId": self.end_node_id,     # Convert back to camelCase for frontend!
            "releases": {
                "start": {"fx": self.releases.start.fx, "fy": self.releases.start.fy, "mz": self.releases.start.mz},
                "end": {"fx": self.releases.end.fx, "fy": self.releases.end.fy, "mz": self.releases.end.mz},
            }
        }
