from dataclasses import dataclass, field
from typing import List, Literal, Tuple, Optional, Dict, Union, Any
import numpy as np

# --- Helper Data Structures matching TS nested interfaces ---

@dataclass
class Vec2:
    x: float
    y: float

    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y])

@dataclass
class Supports:
    # SupportValue = boolean | number (Stiffness)
    fix_x: Union[bool, float] = False
    fix_y: Union[bool, float] = False
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

# --- Main Entities ---

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
                "fixX": self.supports.fix_x,
                "fixY": self.supports.fix_y,
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
@dataclass
class Load:
    id: str
    
    target: Literal['node', 'member']
    target_id: str
    
    type: Literal['point_force', 'distributed_force', 'moment']
    
    # [val] or [start, end]
    values: List[float]
    
    system: Literal['global', 'local'] = 'global'
    angle: float = 0.0
    
    # Optional positioning
    t_start: Optional[float] = None
    t_end: Optional[float] = None

    def to_dict(self):
        return {
            "id": self.id,
            "target": self.target,
            "target_id": self.target_id, # Ensure camelCase if frontend expects it (targetId)
            "type": self.type,
            "values": self.values,
            "system": self.system,
            "angle": self.angle,
            "t_start": self.t_start,
            "t_end": self.t_end
        }
# --- System & Factory ---

@dataclass
class StructuralSystem:
    nodes: List[Node] = field(default_factory=list)
    members: List[Member] = field(default_factory=list)
    loads: List[Load] = field(default_factory=list)

    @classmethod
    def create(cls, nodes_data: List[dict], members_data: List[dict], loads_data: List[dict]) -> 'StructuralSystem':
        system = cls()
        node_map = {}

        # 1. Parse Nodes
        for n_data in nodes_data:
            # Handle nested objects safely
            pos = n_data.get("position", {"x": 0, "y": 0})
            sup = n_data.get("supports", {})
            
            node = Node(
                id=str(n_data["id"]),
                position=Vec2(x=float(pos["x"]), y=float(pos["y"])),
                supports=Supports(
                    fix_x=sup.get("fixX", False),
                    fix_y=sup.get("fixY", False),
                    fix_m=sup.get("fixM", False)
                ),
                rotation=float(n_data.get("rotation", 0.0))
            )
            system.nodes.append(node)
            node_map[node.id] = node

        # 2. Parse Members
        for m_data in members_data:
            # Check for missing nodes
            start_id = str(m_data["startNodeId"])
            end_id = str(m_data["endNodeId"])
            
            if start_id not in node_map or end_id not in node_map:
                raise ValueError(f"Member {m_data['id']} references missing node")

            # Properties
            props = m_data.get("properties", {})
            
            # Releases
            rels = m_data.get("releases", {})
            r_start = rels.get("start", {})
            r_end = rels.get("end", {})

            member = Member(
                id=str(m_data["id"]),
                start_node_id=start_id,
                end_node_id=end_id,
                properties=MemberProperties(
                    E=float(props.get("E", 0)),
                    A=float(props.get("A", 0)),
                    I=float(props.get("I", 0))
                ),
                releases=MemberReleases(
                    start=Release(fx=r_start.get("fx", False), fy=r_start.get("fy", False), mz=r_start.get("mz", False)),
                    end=Release(fx=r_end.get("fx", False), fy=r_end.get("fy", False), mz=r_end.get("mz", False))
                ),
                _start_node=node_map[start_id],
                _end_node=node_map[end_id]
            )
            system.members.append(member)

        # 3. Parse Loads
        for l_data in loads_data:
            load = Load(
                id=str(l_data["id"]),
                target=l_data["target"],
                target_id=str(l_data["targetId"]),
                type=l_data["type"],
                values=[float(v) for v in l_data.get("values", [])],
                system=l_data.get("system", "global"),
                angle=float(l_data.get("angle", 0.0)),
                t_start=l_data.get("t_start"),
                t_end=l_data.get("t_end")
            )
            system.loads.append(load)

        return system
    
    def to_dict(self):
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "members": [m.to_dict() for m in self.members],
            "loads": [l.to_dict() for l in self.loads] 
        }
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
    node_velocities: Dict[str, np.ndarray] 
    member_poles: Dict[str, np.ndarray]
    rigid_bodies: List[RigidBody]

    def to_dict(self):
        def vec_to_list(v):
            return [float(v[0]), float(v[1])] if v is not None else None

        return {
            "index": int(self.index),
            "velocities": {k: vec_to_list(v) for k, v in self.node_velocities.items()},
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