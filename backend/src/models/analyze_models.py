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
    fix_n: Union[bool, float] = False
    fix_v: Union[bool, float] = False
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
                "fixN": self.supports.fix_n,
                "fixV": self.supports.fix_v,
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
class DynamicSignal:
    type: Literal['HARMONIC', 'STEP', 'PULSE', 'RAMP']
    amplitude: float
    start_time: float = 0.0
    frequency: float = 0.0
    phase: float = 0.0
    end_time: float = 0.0
    offset: float = 0.0

    def to_dict(self):
        return {
            "type": self.type,
            "amplitude": self.amplitude,
            "startTime": self.start_time,
            "frequency": self.frequency,
            "phase": self.phase,
            "endTime": self.end_time,
            "offset": self.offset
        }

@dataclass
class Load:
    id: str
    scope: Literal['NODE', 'MEMBER']
    type: Literal['POINT', 'MOMENT', 'DISTRIBUTED', 'DYNAMIC_FORCE', 'DYNAMIC_MOMENT']
    value: float = 0.0 # Default to 0 for dynamic loads
    
    # -- Linkage --
    node_id: Optional[str] = None
    member_id: Optional[str] = None
    
    # -- Geometry --
    angle: float = 0.0
    is_global: bool = True
    
    # -- Member Positioning --
    ratio: Optional[float] = None
    
    # -- Distributed Params --
    start_ratio: Optional[float] = None
    end_ratio: Optional[float] = None
    start_value: Optional[float] = None
    end_value: Optional[float] = None

    signal: Optional[DynamicSignal] = None 

    def to_dict(self):
        base = {
            "id": self.id,
            "scope": self.scope,
            "type": self.type,
            "value": self.value,
            "isGlobal": self.is_global
        }

        # Add Signal if present
        if self.signal:
            base["signal"] = self.signal.to_dict()

        if self.scope == 'NODE':
            base["nodeId"] = self.node_id
            base["angle"] = self.angle
        
        elif self.scope == 'MEMBER':
            base["memberId"] = self.member_id
            if self.type == 'POINT':
                base["ratio"] = self.ratio
                base["angle"] = self.angle
            elif self.type == 'DISTRIBUTED':
                base["startRatio"] = self.start_ratio
                base["endRatio"] = self.end_ratio
                if self.start_value is not None: base["startValue"] = self.start_value
                if self.end_value is not None: base["endValue"] = self.end_value

        return base

    
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


@dataclass
class StructuralSystem:
    nodes: List[Node] = field(default_factory=list)
    members: List[Member] = field(default_factory=list)
    loads: List[Load] = field(default_factory=list)
    scheiben: List[Scheibe] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list) 

    @classmethod
    def create(cls, nodes_data: List[dict], members_data: List[dict], loads_data: List[dict], scheiben_data: List[Dict], constraints_data: List[Dict]) -> 'StructuralSystem':
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
                    fix_n=sup.get("fixN", False),
                    fix_v=sup.get("fixV", False),
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
            scope = l_data.get("scope", "NODE")
            
            # Parse Signal if exists
            signal = None
            if "signal" in l_data and l_data["signal"]:
                s_data = l_data["signal"]
                signal = DynamicSignal(
                    type=s_data.get("type", "HARMONIC"),
                    amplitude=float(s_data.get("amplitude", 0)),
                    start_time=float(s_data.get("startTime", 0)),
                    frequency=float(s_data.get("frequency", 0)),
                    phase=float(s_data.get("phase", 0)),
                    end_time=float(s_data.get("endTime", 0)),
                    offset=float(s_data.get("offset", 0))
                )

            load = Load(
                id=str(l_data["id"]),
                scope=scope,
                type=l_data.get("type", "POINT"),
                value=float(l_data.get("value", 0.0)),
                node_id=l_data.get("nodeId"),
                member_id=l_data.get("memberId"),
                angle=float(l_data.get("angle", 0.0)),
                is_global=l_data.get("isGlobal", True),
                ratio=l_data.get("ratio") if l_data.get("ratio") is not None else None,
                start_ratio=l_data.get("startRatio"),
                end_ratio=l_data.get("endRatio"),
                start_value=l_data.get("startValue"),
                end_value=l_data.get("endValue"),
                signal=signal
            )
            
            # Simple validation
            if scope == "NODE" and not load.node_id: continue
            if scope == "MEMBER" and not load.member_id: continue
            
            system.loads.append(load)

        # SCHEIBEN
        for s_data in scheiben_data:
            # Parse corner positions
            c1 = s_data.get("corner1", {"x": 0, "y": 0})
            c2 = s_data.get("corner2", {"x": 0, "y": 0})
            
            # Parse additional points (for polygon, l_shape)
            additional_points = None
            if "additionalPoints" in s_data and s_data["additionalPoints"]:
                additional_points = [
                    Vec2(x=float(p["x"]), y=float(p["y"])) 
                    for p in s_data["additionalPoints"]
                ]
            
            # Parse properties
            props = s_data.get("properties", {})
            properties = ScheibeProperties(
                E=float(props.get("E", 30e9)),
                nu=float(props.get("nu", 0.2)),
                thickness=float(props.get("thickness", 0.2)),
                rho=float(props.get("rho", 2400))
            )
            
            # Parse connections
            connections = []
            for conn_data in s_data.get("connections", []):
                node_id = str(conn_data["nodeId"])
                
                if node_id not in node_map:
                    print(f"Warning: Scheibe {s_data['id']} references missing node {node_id}")
                    continue
                
                # Parse releases - handle null/None properly
                releases = None
                rel_data = conn_data.get("releases")
                
                # Only create Release object if releases is explicitly provided and not null
                if rel_data is not None:
                    releases = Release(
                        fx=rel_data.get("fx", False),
                        fy=rel_data.get("fy", False),
                        mz=rel_data.get("mz", False)
                    )
                
                connections.append(ScheibeConnection(
                    node_id=node_id,
                    releases=releases
                ))

            
            scheibe = Scheibe(
                id=str(s_data["id"]),
                shape=s_data.get("shape", "rectangle"),
                corner1=Vec2(x=float(c1["x"]), y=float(c1["y"])),
                corner2=Vec2(x=float(c2["x"]), y=float(c2["y"])),
                additional_points=additional_points,
                rotation=float(s_data.get("rotation", 0.0)),
                type=s_data.get("type", "RIGID"),
                properties=properties,
                connections=connections,
                mesh_level=int(s_data.get("meshLevel", 3))
            )
            
            system.scheiben.append(scheibe)
        # 5. Parse Constraints (NEW)

        for c_data in constraints_data:
            constraint_type = c_data.get("type")
            start_id = str(c_data["startNodeId"])
            end_id = str(c_data["endNodeId"])
            
            # Validate node references
            if start_id not in node_map or end_id not in node_map:
                print(f"Warning: Constraint {c_data['id']} references missing node")
                continue
            
            if constraint_type == "SPRING":
                constraint = SpringConstraint(
                    id=str(c_data["id"]),
                    start_node_id=start_id,
                    end_node_id=end_id,
                    k=float(c_data.get("k", 1000)),
                    preload=float(c_data.get("preload", 0)),
                    rotation=c_data.get("rotation")
                )
            elif constraint_type == "DAMPER":
                constraint = DamperConstraint(
                    id=str(c_data["id"]),
                    start_node_id=start_id,
                    end_node_id=end_id,
                    c=float(c_data.get("c", 100)),
                    k=float(c_data["k"]) if c_data.get("k") is not None else None,
                    rotation=c_data.get("rotation")
                )
            elif constraint_type == "CABLE":
                constraint = CableConstraint(
                    id=str(c_data["id"]),
                    start_node_id=start_id,
                    end_node_id=end_id,
                    EA=float(c_data.get("EA", 210000)),
                    prestress=float(c_data.get("prestress", 0)),
                    weight_per_length=float(c_data.get("weightPerLength", 0)),
                    rotation=c_data.get("rotation")
                )
            else:
                print(f"Warning: Unknown constraint type '{constraint_type}'")
                continue
            
            system.constraints.append(constraint)

        return system
    
    def to_dict(self):
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "members": [m.to_dict() for m in self.members],
            "loads": [l.to_dict() for l in self.loads],
            "scheiben": [s.to_dict() for s in self.scheiben],
            "constraints": [c.to_dict() for c in self.constraints]
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
    

################################
##############   FEM   ##########
################################

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
    
