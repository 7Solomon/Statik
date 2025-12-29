import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Literal
import numpy as np

from src.models.analyze_models import StructuralSystem, Node, Member, Load

@dataclass
class ImageNode:
    id: str
    pixel_x: float
    pixel_y: float
    support_type: Literal['fixed', 'pinned', 'roller', 'free'] = 'free'
    
    # Optional: YOLO Bounding Box (cx, cy, w, h) normalized 0-1
    yolo_bbox: Optional[Tuple[float, float, float, float]] = None

    def to_real_node(self, img_width: float, img_height: float, real_scale: float = 10.0) -> Node:
        """
        Converts pixel coordinates to real-world coordinates (e.g., meters).
        real_scale: How many meters the image width represents.
        """
        # Normalize (0 to 1)
        norm_x = self.pixel_x / img_width
        norm_y = self.pixel_y / img_height
        
        # Scale to real units (e.g., 0 to 10 meters)
        # Note: We usually invert Y for physics (Up is positive), but check your coordinate system
        return Node(
            id=self.id,
            x=norm_x * real_scale,
            y=norm_y * (real_scale * (img_height / img_width)), # Maintain aspect ratio
            support=self.support_type
        )

@dataclass
class ImageMember:
    id: str
    start_node_id: str
    end_node_id: str
    thickness_px: int = 2

    def to_real_member(self) -> Member:
        return Member(
            id=self.id,
            start_node_id=self.start_node_id,
            end_node_id=self.end_node_id
        )

@dataclass
class ImageLoad:
    id: str
    node_id: Optional[str] = None
    member_id: Optional[str] = None
    
    # Visual properties
    pixel_x: float = 0
    pixel_y: float = 0
    angle_deg: float = 0
    load_type: Literal['force_point', 'moment', 'dist_uniform'] = 'force_point'
    
    # Text label to render (e.g., "10kN")
    label_text: str = "10kN"

    def to_real_load(self) -> Load:
        # Simplification: assuming point load for now
        # You would parse "10kN" to 10.0 here if needed
        return Load(
            id=self.id,
            node_id=self.node_id,
            fx=0, # Placeholder, as image generation is random
            fy=-10 
        )

@dataclass
class ImageSystem:
    width: int
    height: int
    nodes: List[ImageNode] = field(default_factory=list)
    members: List[ImageMember] = field(default_factory=list)
    loads: List[ImageLoad] = field(default_factory=list)

    def convert_to_real_system(self, real_width_meters: float = 20.0) -> StructuralSystem:
        """
        Converts this visual-only system into a physical StructuralSystem
        ready for the FEM solver.
        """
        real_nodes = [n.to_real_node(self.width, self.height, real_width_meters) for n in self.nodes]
        real_members = [m.to_real_member() for m in self.members]
        real_loads = [l.to_real_load() for l in self.loads]
        
        return StructuralSystem(
            nodes=real_nodes,
            members=real_members,
            loads=real_loads
        )
