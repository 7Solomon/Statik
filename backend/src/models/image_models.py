import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import numpy as np

from src.plugins.generator.image.stanli_symbols import BeamType, HingeType, LoadType, SupportType
from src.models.analyze_models import (
    StructuralSystem, Node, Member, Load, 
    Vec2, Supports, MemberProperties, Release, MemberReleases
)

@dataclass
class ImageNode:
    id: str
    pixel_x: float
    pixel_y: float
    support_type: SupportType = SupportType.FREIES_ENDE
    hinge_type: Optional[HingeType] = None
    rotation: float = 0.0

    def to_real_node(self, img_width: float, img_height: float, real_scale: float = 10.0) -> Node:
        """
        Converts pixel coordinates to real-world coordinates.
        Maps SupportType enum to Supports (fixX, fixY, fixM).
        """
        norm_x = self.pixel_x / img_width
        norm_y = self.pixel_y / img_height
        
        # Map enum to support constraints
        supports = self._convert_support_type()
        
        return Node(
            id=self.id,
            position=Vec2(
                x=norm_x * real_scale,
                y=norm_y * (real_scale * (img_height / img_width))
            ),
            supports=supports,
            rotation=self.rotation
        )
    
    def _convert_support_type(self) -> Supports:
        """Map SupportType enum to Supports constraints."""
        mapping = {
            SupportType.FREIES_ENDE: Supports(fix_x=False, fix_y=False, fix_m=False),
            SupportType.FESTLAGER: Supports(fix_x=True, fix_y=True, fix_m=False),
            SupportType.LOSLAGER: Supports(fix_x=False, fix_y=True, fix_m=False),
            SupportType.FESTE_EINSPANNUNG: Supports(fix_x=True, fix_y=True, fix_m=True),
            SupportType.GLEITLAGER: Supports(fix_x=True, fix_y=False, fix_m=False),
            SupportType.FEDER: Supports(fix_x=False, fix_y=10000.0, fix_m=False),  # Spring stiffness
            SupportType.TORSIONSFEDER: Supports(fix_x=False, fix_y=False, fix_m=5000.0),
        }
        return mapping.get(self.support_type, Supports())


@dataclass
class ImageMember:
    id: str
    start_node_id: str
    end_node_id: str
    thickness_px: int = 2
    beam_type: BeamType = BeamType.FACHWERK
    
    # Store hinge/release info if needed
    start_hinge: Optional[HingeType] = None
    end_hinge: Optional[HingeType] = None

    def to_real_member(self) -> Member:
        """
        Convert to Member with proper releases and default properties.
        """
        # Default material properties (can be made configurable)
        properties = MemberProperties(
            E=210e9,  # Steel Young's modulus (Pa)
            A=0.01,   # Cross-section area (m²)
            I=0.0001  # Moment of inertia (m⁴)
        )
        
        # Adjust properties based on beam type
        if self.beam_type == BeamType.FACHWERK:
            # Truss: no bending, only axial
            properties.I = 1e-12  # Negligible bending stiffness
        elif self.beam_type == BeamType.BIEGUNG_MIT_FASER:
            properties.I = 0.001  # Higher bending stiffness
        
        # Convert hinges to releases
        releases = self._convert_hinges_to_releases()
        
        return Member(
            id=self.id,
            start_node_id=self.start_node_id,
            end_node_id=self.end_node_id,
            properties=properties,
            releases=releases
        )
    
    def _convert_hinges_to_releases(self) -> MemberReleases:
        """Map HingeType to Release constraints."""
        def hinge_to_release(hinge: Optional[HingeType]) -> Release:
            if hinge is None:
                return Release(fx=False, fy=False, mz=False)
            
            mapping = {
                HingeType.VOLLGELENK: Release(fx=False, fy=False, mz=True),  # Moment release
                HingeType.HALBGELENK: Release(fx=False, fy=False, mz=True),
                HingeType.SCHUBGELENK: Release(fx=False, fy=True, mz=False),  # Shear release
                HingeType.NORMALKRAFTGELENK: Release(fx=True, fy=False, mz=False),  # Axial release
                HingeType.BIEGESTEIFE_ECKE: Release(fx=False, fy=False, mz=False),  # Rigid
            }
            return mapping.get(hinge, Release())
        
        return MemberReleases(
            start=hinge_to_release(self.start_hinge),
            end=hinge_to_release(self.end_hinge)
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
    
    load_type: LoadType = LoadType.EINZELLAST
    
    # Text label to render (e.g., "10kN")
    label_text: str = "10kN"
    
    # For distributed loads
    start_ratio: Optional[float] = None
    end_ratio: Optional[float] = None

    def to_real_load(self) -> Load:
        """
        Convert ImageLoad to analyze_models.Load with proper scope/type.
        """
        # Extract magnitude from label
        magnitude = self._extract_magnitude()
        
        # Determine scope
        scope = 'MEMBER' if self.member_id else 'NODE'
        
        # Map LoadType enum to Load.type
        if self.load_type == LoadType.EINZELLAST:
            load_type = 'POINT'
        elif self.load_type in (LoadType.MOMENT_UHRZEIGER, LoadType.MOMENT_GEGEN_UHRZEIGER):
            load_type = 'MOMENT'
        elif self.load_type == LoadType.STRECKENLAST:
            load_type = 'DISTRIBUTED'
        else:
            load_type = 'POINT'
        
        # Adjust sign for clockwise moments (structural convention)
        if self.load_type == LoadType.MOMENT_UHRZEIGER:
            magnitude = -abs(magnitude)  # Clockwise = negative
        elif self.load_type == LoadType.MOMENT_GEGEN_UHRZEIGER:
            magnitude = abs(magnitude)   # Counter-clockwise = positive
        
        return Load(
            id=self.id,
            scope=scope,
            type=load_type,
            value=magnitude,
            node_id=self.node_id,
            member_id=self.member_id,
            angle=self.angle_deg,
            is_global=True,
            ratio=0.5 if scope == 'MEMBER' and load_type == 'POINT' else None,
            start_ratio=self.start_ratio if load_type == 'DISTRIBUTED' else None,
            end_ratio=self.end_ratio if load_type == 'DISTRIBUTED' else None,
            start_value=magnitude if load_type == 'DISTRIBUTED' else None,
            end_value=magnitude if load_type == 'DISTRIBUTED' else None
        )
    
    def _extract_magnitude(self) -> float:
        """Extract numeric value from label like '10kN' or '5.5 kN/m'."""
        try:
            # Remove common units and extract number
            cleaned = self.label_text.replace('kN', '').replace('kN/m', '').replace(' ', '')
            return float(''.join(c for c in cleaned if c.isdigit() or c in '.-'))
        except:
            return 10.0  # Default fallback


@dataclass
class ImageSystem:
    width: int
    height: int
    nodes: List[ImageNode] = field(default_factory=list)
    members: List[ImageMember] = field(default_factory=list)
    loads: List[ImageLoad] = field(default_factory=list)

    def convert_to_real_system(self, real_width_meters: float = 20.0) -> StructuralSystem:
        """
        Convert visual system to physical StructuralSystem with proper typing.
        """
        real_nodes = [n.to_real_node(self.width, self.height, real_width_meters) 
                      for n in self.nodes]
        real_members = [m.to_real_member() for m in self.members]
        real_loads = [l.to_real_load() for l in self.loads]
        
        # Build system and link member node references
        system = StructuralSystem(
            nodes=real_nodes,
            members=real_members,
            loads=real_loads
        )
        
        # Link members to their nodes (for length calculations, etc.)
        node_map = {n.id: n for n in real_nodes}
        for member in system.members:
            member._start_node = node_map.get(member.start_node_id)
            member._end_node = node_map.get(member.end_node_id)
        
        return system
