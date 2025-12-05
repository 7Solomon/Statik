from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
import numpy as np

@dataclass
class Node:
    """
    Represents a joint in the system.
    [Knoten]
    
    A node defines a position in space and its specific boundary conditions.
    """
    id: int
    x: float
    y: float
    
    # Boundary Conditions
    # If True, the movement in that direction is blocked (Supported).
    fix_x: bool = False
    fix_y: bool = False
    
    # Only relevant for Frames (Rahmen), usually False for Trusses (Fachwerke)
    fix_m: bool = False

    @property
    def coordinates(self) -> np.ndarray:
        """Returns position as a vector"""
        return np.array([self.x, self.y])

@dataclass
class Member:
    """
    Represents a connection between two nodes.
    [Stab]
    
    Kinematically, this represents a 'distance constraint' between two points.
    """
    id: int
    start_node: Node
    end_node: Node
    
    # System properties can be added here later (e.g., EA, EI)
    # For pure kinematics (rigid body), we only need geometry.

    def length(self) -> float:
        """Calculates the length of the member"""
        return np.linalg.norm(self.end_node.coordinates - self.start_node.coordinates)
    
    def direction_vector(self) -> np.ndarray:
        """
        Returns the normalized direction vector
        """
        delta = self.end_node.coordinates - self.start_node.coordinates
        return delta / np.linalg.norm(delta)

@dataclass
class StructuralSystem:
    """
    The container for the entire system.
    [Tragwerk / System]
    """
    nodes: List[Node] = field(default_factory=list)
    members: List[Member] = field(default_factory=list)

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
    
    @classmethod
    def create(cls, nodes_data: List[dict], members_data: List[dict]) -> 'StructuralSystem':
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
