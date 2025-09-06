from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from src.generator.image.stanli_symbols import BeamType, HingeType, LoadType, SupportType

@dataclass
class Node:
    id: int
    position: Tuple[float, float]
    support_type: Optional[SupportType] = None

@dataclass 
class Beam:
    id: int
    node1_id: int
    node2_id: int
    beam_type: BeamType = BeamType.BENDING_WITH_FIBER
    rounded_start: bool = False
    rounded_end: bool = False

@dataclass
class Hinge:
    id: int
    node_id: int
    hinge_type: HingeType
    rotation: float = 0
    start_node_id: Optional[int] = None
    end_node_id: Optional[int] = None
    orientation: int = 0

@dataclass
class Load:
    id: int
    node_id: int
    load_type: LoadType
    rotation: float = 0
    magnitude: float = 1.0

@dataclass
class Structure:
    nodes: List[Node]
    beams: List[Beam]
    hinges: List[Hinge]
    loads: List[Load]
    
    def get_node_by_id(self, node_id: int) -> Optional[Node]:
        return next((n for n in self.nodes if n.id == node_id), None)
    
    def get_beams_for_node(self, node_id: int) -> List[Beam]:
        return [b for b in self.beams if b.node1_id == node_id or b.node2_id == node_id]
