"""Scheiben: rigid or elastic 2D panels tied to a set of nodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional

from .base import Release
from .utils import Vec2


@dataclass
class ScheibeProperties:
    E: float        # Young's modulus (Pa)
    nu: float       # Poisson's ratio
    thickness: float  # Thickness (m)
    rho: float      # Density (kg/m³)


@dataclass
class ScheibeConnection:
    node_id: str
    releases: Optional[Release] = None


@dataclass
class Scheibe:
    id: str
    shape: Literal['rectangle', 'circle', 'triangle', 'polygon']
    
    # Geometry
    corner1: Vec2
    corner2: Vec2
    additional_points: Optional[List[Vec2]] = None
    rotation: float = 0.0
    
    # Analysis type
    type: Literal['RIGID', 'ELASTIC'] = 'RIGID'
    
    # Material properties
    properties: ScheibeProperties = field(default_factory=lambda: ScheibeProperties(E=30e9, nu=0.2, thickness=0.2, rho=2400))
    
    # Connections to nodes
    connections: List[ScheibeConnection] = field(default_factory=list)
    
    # Meshing
    mesh_level: int = 3  # 1-5
    
    def to_dict(self):
        result = {
            "id": self.id,
            "shape": self.shape,
            "corner1": {"x": self.corner1.x, "y": self.corner1.y},
            "corner2": {"x": self.corner2.x, "y": self.corner2.y},
            "rotation": self.rotation,
            "type": self.type,
            "properties": {
                "E": self.properties.E,
                "nu": self.properties.nu,
                "thickness": self.properties.thickness,
                "rho": self.properties.rho
            },
            "connections": [
            {
                "nodeId": conn.node_id,
                "releases": None if conn.releases is None else {  # ← Explicitly None
                    "fx": conn.releases.fx,
                    "fy": conn.releases.fy,
                    "mz": conn.releases.mz
                }
            }
                for conn in self.connections
            ],
            "meshLevel": self.mesh_level
        }
        
        if self.additional_points:
            result["additionalPoints"] = [
                {"x": p.x, "y": p.y} for p in self.additional_points
            ]
        
        return result
