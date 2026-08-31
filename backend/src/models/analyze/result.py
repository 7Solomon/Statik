"""Analysis outputs.

Nothing here is drawn by the user; every type is produced by a solver.
RigidBody lives here rather than in base.py because it is an output of
the kinematics analysis, not a structural entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

import numpy as np

from .system import StructuralSystem


@dataclass
class RigidBody:
    id: int
    member_ids: List[str] 
    movement_type: str  # 'rotation' or 'translation'
    center_or_vector: np.ndarray

    def to_dict(self):
        return {
            "id": int(self.id),  #  Force standard Python int
            "member_ids": self.member_ids, # Force int list
            "movement_type": self.movement_type,
            "center_or_vector": [float(self.center_or_vector[0]), float(self.center_or_vector[1])]
        }


@dataclass
class KinematicMode:
    """Represents one specific independent movement (Degree of Freedom)"""
    index: int
    node_velocities: Dict[str, np.ndarray] # [vx, vy]
    scheibe_velocities: Dict[str, np.ndarray] #[vx, vy, omega]
    member_poles: Dict[str, np.ndarray]
    rigid_bodies: List[RigidBody]

    def to_dict(self):
        def vec_to_list(v):
            if v is None:
                return None
            return [float(x) for x in v]

        return {
            "index": int(self.index),
            "node_velocities": {k: vec_to_list(v) for k, v in self.node_velocities.items()},
            "scheibe_velocities": {k: vec_to_list(v) for k, v in self.scheibe_velocities.items()},
            "member_poles": {k: vec_to_list(v) for k, v in self.member_poles.items()},
            "rigid_bodies": [rb.to_dict() for rb in self.rigid_bodies]
        }


@dataclass
class KinematicResult:
    is_kinematic: bool
    dof: int
    system: Any 
    modes: List['KinematicMode'] = field(default_factory=list)

    def to_dict(self):
        return {
            "is_kinematic": bool(self.is_kinematic),
            "dof": int(self.dof),
            "modes": [m.to_dict() for m in self.modes],            
            "system": self.system.to_dict() if hasattr(self.system, 'to_dict') else None 
        }


@dataclass
class ElementContext:
    L: float
    c: float  # cos(theta)
    s: float  # sin(theta)
    T: np.ndarray  # Transformation Matrix (6x6)
    k_local: np.ndarray # Local Stiffness (6x6)
    k_global: np.ndarray # Global Stiffness (6x6)
    f_fixed_local: np.ndarray # Fixed End Forces (Local 6x1)


@dataclass
class StationResult:
    x: float
    N: float
    V: float
    M: float

    def to_dict(self):
        return {
            "x": float(self.x),
            "N": float(self.N),
            "V": float(self.V),
            "M": float(self.M)
        }


@dataclass
class MemberResult:
    memberId: str
    stations: List[StationResult]
    maxM: float
    minM: float
    maxV: float
    minV: float
    maxN: float
    minN: float

    def to_dict(self):
        return {
            "memberId": self.memberId,
            "stations": [s.to_dict() for s in self.stations],
            "maxM": float(self.maxM),
            "minM": float(self.minM),
            "maxV": float(self.maxV),
            "minV": float(self.minV),
            "maxN": float(self.maxN),
            "minN": float(self.minN),
        }


@dataclass
class FEMResult:
    success: bool
    system: StructuralSystem
    displacements: Dict[str, List[float]] # NodeId -> [dx, dy, rot]
    reactions: Dict[str, List[float]]     # NodeId -> [Rx, Ry, Mz]
    memberResults: Dict[str, MemberResult]

    def to_dict(self):
        # Helper to convert numpy arrays in dict values to list of floats
        def convert_vec(v):
            return [float(x) for x in v]

        return {
            "success": self.success,
            "system": self.system.to_dict(),
            "displacements": {k: convert_vec(v) for k, v in self.displacements.items()},
            "reactions": {k: convert_vec(v) for k, v in self.reactions.items()},
            "memberResults": {k: v.to_dict() for k, v in self.memberResults.items()}
        }
