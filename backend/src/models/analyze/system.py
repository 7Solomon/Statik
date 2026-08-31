"""The complete structural system and its parsing from frontend JSON.

StructuralSystem.create is the single boundary where camelCase payload keys become snake_case Python attributes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .base import (
    Member, MemberProperties, MemberReleases, Node, Release, Supports,
)
from .constraint import (
    CableConstraint, Constraint, DamperConstraint, SpringConstraint,
)
from .excitation import DynamicSignal, Load
from .scheiben import Scheibe, ScheibeConnection, ScheibeProperties
from .utils import Vec2


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
