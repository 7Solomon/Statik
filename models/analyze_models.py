from dataclasses import dataclass, field
from typing import List, Literal, Tuple, Optional, Dict, Union
import numpy as np


@dataclass
class Load:
    id: int
    type: Literal['force', 'moment', 'distributed']
    
    # Values: [Fx, Fy, M] or [q_start, q_end]
    values: list[float]  
    
    location_type: Literal['node', 'member', 'global']
    location_id: int
    
    # t can be float (point) or tuple (range) or None (node)
    t: Union[float, Tuple[float, float], None] = None

    # Helper to get vector for nodal loads (legacy support)
    def to_vector(self) -> np.ndarray:
        if len(self.values) >= 3:
             return np.array(self.values[:3])
        # Pad with zeros if values are missing (e.g. only q given)
        padded = self.values + [0.0] * (3 - len(self.values))
        return np.array(padded[:3])

@dataclass
class Node:
    id: int
    x: float
    y: float
    fix_x: bool = False
    fix_y: bool = False
    fix_m: bool = False

    @property
    def coordinates(self) -> np.ndarray:
        return np.array([self.x, self.y])

@dataclass
class Member:
    id: int
    start_node: Node
    end_node: Node

    def length(self) -> float:
        return np.linalg.norm(self.end_node.coordinates - self.start_node.coordinates)
    
    def direction_vector(self) -> np.ndarray:
        delta = self.end_node.coordinates - self.start_node.coordinates
        return delta / np.linalg.norm(delta)

@dataclass
class StructuralSystem:
    nodes: List[Node] = field(default_factory=list)
    members: List[Member] = field(default_factory=list)
    loads: List[Load] = field(default_factory=list)

    def add_node(self, x: float, y: float, fix_x=False, fix_y=False) -> Node:
        new_id = len(self.nodes)
        node = Node(new_id, x, y, fix_x, fix_y)
        self.nodes.append(node)
        return node

    def add_member(self, start_node_id: int, end_node_id: int) -> Member:
        start = next(n for n in self.nodes if n.id == start_node_id)
        end = next(n for n in self.nodes if n.id == end_node_id)
        new_id = len(self.members)
        member = Member(new_id, start, end)
        self.members.append(member)
        return member

    def add_load(self, node_id: int, fx=0.0, fy=0.0, m=0.0) -> Load:
        new_id = len(self.loads)
        load = Load(
            id=new_id, 
            type='force' if m == 0 else 'moment',
            values=[fx, fy, m],
            location_type='node',
            location_id=node_id,
            t=None
        )
        self.loads.append(load)
        return load
    
    @classmethod
    def create(cls, nodes_data: List[dict], members_data: List[dict], loads_data: List[dict]) -> 'StructuralSystem':
        system = cls()
        id_to_node = {}
        for n in nodes_data:
            node = Node(
                id=int(n["id"]),
                x=float(n["x"]),
                y=float(n["y"]),
                fix_x=bool(n.get("fix_x", False)),
                fix_y=bool(n.get("fix_y", False)),
                fix_m=bool(n.get("fix_m", False)),
            )
            system.nodes.append(node)
            id_to_node[node.id] = node

        for m in members_data:
            if m["startNodeId"] not in id_to_node or m["endNodeId"] not in id_to_node:
                raise ValueError(f"Member references missing node: {m}")
            start = id_to_node[m["startNodeId"]]
            end = id_to_node[m["endNodeId"]]
            member = Member(
                id=int(m["id"]),
                start_node=start,
                end_node=end,
            )
            system.members.append(member)
        
        for l in loads_data:
            raw_t = l.get('t')
            parsed_t = None
            if raw_t is not None:
                if isinstance(raw_t, list):
                    parsed_t = tuple(raw_t)
                else:
                    parsed_t = float(raw_t)

            load = Load(
                id=int(l['id']),
                type=l['type'],
                values=[float(v) for v in l.get('values', [])],
                location_type=l['locationType'],
                location_id=int(l['locationId']),
                t=parsed_t
            )
            system.loads.append(load)
            
        return system


@dataclass
class RigidBody:
    """
    Represents a connected group of members moving together (Scheibe).
    """
    id: int
    member_ids: List[int]
    
    # 'rotation' or 'translation'
    movement_type: str
    
    # If rotation: coordinates of the Pole (ICR) [px, py]
    # If translation: velocity vector [vx, vy]
    center_or_vector: np.ndarray

    def to_dict(self):
        """Helper for JSON serialization"""
        return {
            "id": self.id,
            "member_ids": self.member_ids,
            "movement_type": self.movement_type,
            "center_or_vector": [float(self.center_or_vector[0]), float(self.center_or_vector[1])]
        }

@dataclass
class KinematicResult:
    is_kinematic: bool
    dof: int
    node_velocities: Dict[int, np.ndarray] = field(default_factory=dict)
    member_poles: Dict[int, np.ndarray] = field(default_factory=dict)
    rigid_bodies: List[RigidBody] = field(default_factory=list)

    def to_dict(self):
        """Serializes the entire result object for the API."""
        
        def vec_to_list(v):
            return [float(v[0]), float(v[1])] if v is not None else None

        return {
            "is_kinematic": bool(self.is_kinematic),
            "dof": int(self.dof),
            
            "node_velocities": {
                int(k): vec_to_list(v) for k, v in self.node_velocities.items()
            },
            "member_poles": {
                int(k): vec_to_list(v) for k, v in self.member_poles.items()
            },
            "rigid_bodies": [rb.to_dict() for rb in self.rigid_bodies]
        }
