"""Discrete two-node constraints: springs, dampers and cables."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Union


@dataclass
class SpringConstraint:
    id: str
    start_node_id: str
    end_node_id: str
    k: float  # Spring stiffness (kN/m)
    type: Literal['SPRING'] = 'SPRING'  # MOVED AFTER NON-DEFAULTS
    preload: float = 0.0  # Initial force (kN)
    rotation: Optional[float] = None
    
    def to_dict(self):
        result = {
            "id": self.id,
            "type": self.type,
            "startNodeId": self.start_node_id,
            "endNodeId": self.end_node_id,
            "k": float(self.k),
            "preload": float(self.preload)
        }
        if self.rotation is not None:
            result["rotation"] = float(self.rotation)
        return result


@dataclass
class DamperConstraint:
    id: str
    start_node_id: str
    end_node_id: str
    c: float  # Damping coefficient (kN·s/m)
    type: Literal['DAMPER'] = 'DAMPER'  # MOVED AFTER NON-DEFAULTS
    k: Optional[float] = None  # Optional parallel stiffness
    rotation: Optional[float] = None
    
    def to_dict(self):
        result = {
            "id": self.id,
            "type": self.type,
            "startNodeId": self.start_node_id,
            "endNodeId": self.end_node_id,
            "c": float(self.c)
        }
        if self.k is not None:
            result["k"] = float(self.k)
        if self.rotation is not None:
            result["rotation"] = float(self.rotation)
        return result


@dataclass
class CableConstraint:
    id: str
    start_node_id: str
    end_node_id: str
    EA: float  # Axial stiffness (kN)
    type: Literal['CABLE'] = 'CABLE'
    prestress: float = 0.0  # Initial tension (kN)
    weight_per_length: float = 0.0  # Self-weight (kN/m)
    rotation: Optional[float] = None
    
    def to_dict(self):
        result = {
            "id": self.id,
            "type": self.type,
            "startNodeId": self.start_node_id,
            "endNodeId": self.end_node_id,
            "EA": float(self.EA),
            "prestress": float(self.prestress),
            "weightPerLength": float(self.weight_per_length)
        }
        if self.rotation is not None:
            result["rotation"] = float(self.rotation)
        return result


Constraint = Union[SpringConstraint, DamperConstraint, CableConstraint]
