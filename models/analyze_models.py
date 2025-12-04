from dataclasses import dataclass, field
from typing import List, Tuple, Optional
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
    fix_x: bool = False  # DE: [translate:fest in x-Richtung]
    fix_y: bool = False  # DE: [translate:fest in y-Richtung]
    
    # Only relevant for Frames (Rahmen), usually False for Trusses (Fachwerke)
    fix_m: bool = False  # DE: [translate:drehfest / Einspannung]

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
    start_node: Node  # DE: [translate:Anfangsknoten]
    end_node: Node    # DE: [translate:Endknoten]
    
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



@dataclass
class KinematicResult:
    """
    Stores the result of a kinematic analysis.
    DE: [translate:Kinematisches Ergebnis]
    """
    is_mechanism: bool
    dof: int  # Degree of Freedom (Laufgrad f)
    
    # The movement vector (eigenmode) for every node
    # Key: Node ID, Value: [vx, vy] (Velocity vector)
    node_velocities: dict[int, np.ndarray] = field(default_factory=dict)

    # The calculated Pole (ICR) for every member
    # Key: Member ID, Value: [px, py] (Pole coordinates)
    member_poles: dict[int, np.ndarray] = field(default_factory=dict)
    
    # Groups of members that move together as one Rigid Body
    # [Starrkörper / Scheiben]
    rigid_bodies: List[List[int]] = field(default_factory=list)