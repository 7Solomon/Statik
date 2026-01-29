import copy
import uuid
from src.models.analyze_models import StructuralSystem, Load, Node, Member
import numpy as np
from typing import List, Dict, Tuple, Optional
import sys

def get_node_loads_vector(system: StructuralSystem, node_id: str) -> np.ndarray:
    """
    Sums up all Nodal loads (Fx, Fy, M) currently acting on a specific node.
    Returns: np.array([Fx, Fy, M])
    """
    res = np.zeros(3)
    
    for load in system.loads:
        if load.scope == 'NODE' and load.node_id == node_id:
            if load.type == 'POINT':
                # Convert Angle to Components
                angle_rad = np.radians(load.angle)
                fx = load.value * np.cos(angle_rad)
                fy = load.value * np.sin(angle_rad)
                res[0] += fx
                res[1] += fy
            elif load.type == 'MOMENT':
                res[2] += load.value
                
    return res

def add_equivalent_load(system: StructuralSystem, node_id: str, force_vec: np.ndarray) -> None:
    """
    Creates and appends new Load objects to the system for the given force vector.
    """
    # 1. Force X
    if abs(force_vec[0]) > 1e-9:
        system.loads.append(Load(
            id=str(uuid.uuid4()),
            scope='NODE',
            type='POINT',
            node_id=node_id,
            value=force_vec[0],
            angle=0.0
        ))
        
    # 2. Force Y
    if abs(force_vec[1]) > 1e-9:
        system.loads.append(Load(
            id=str(uuid.uuid4()),
            scope='NODE',
            type='POINT',
            node_id=node_id,
            value=force_vec[1],
            angle=90.0
        ))
        
    # 3. Moment
    if abs(force_vec[2]) > 1e-9:
        system.loads.append(Load(
            id=str(uuid.uuid4()),
            scope='NODE',
            type='MOMENT',
            node_id=node_id,
            value=force_vec[2]
        ))

def build_adjacency_map(nodes: List[Node], members: List[Member]) -> Dict[str, List[str]]:
    """Helper to build { node_id: [member_id, ...] } map."""
    adj = {n.id: [] for n in nodes}
    for m in members:
        if m.start_node_id in adj: adj[m.start_node_id].append(m.id)
        if m.end_node_id in adj: adj[m.end_node_id].append(m.id)
    return adj

def prune_cantilevers(system_in: StructuralSystem) -> StructuralSystem:
    """
    Iteratively removes statically determinate 'leaves' (cantilevers) from the system.
    Also handles Scheibe connections.
    Returns a NEW simplified StructuralSystem.
    """
    # Work on a deep copy to keep original safe
    system = copy.deepcopy(system_in)
    
    changed = True
    while changed:
        changed = False
        
        # 1. Rebuild lookup maps (State is mutating)
        node_map = {n.id: n for n in system.nodes}
        member_map = {m.id: m for m in system.members}
        adjacency = build_adjacency_map(system.nodes, system.members)
        
        # Build Scheibe connection map: {node_id: [scheibe1, scheibe2, ...]}
        scheibe_connections = {n.id: [] for n in system.nodes}
        for scheibe in system.scheiben:
            for conn in scheibe.connections:
                if conn.node_id in scheibe_connections:
                    scheibe_connections[conn.node_id].append(scheibe)
        
        # 2. Find candidate nodes (Degree 1, No Support, Not in Scheibe)
        nodes_to_prune = []
        for n_id, connected_m_ids in adjacency.items():
            if len(connected_m_ids) == 1:
                node = node_map[n_id]
                
                # Check if it has any fixity
                has_support = node.supports.fix_x or node.supports.fix_y or node.supports.fix_m
                
                # Check if connected to any Scheibe (Scheiben act as constraints)
                connected_to_scheibe = len(scheibe_connections.get(n_id, [])) > 0
                
                # Only prune if: no support AND not in a Scheibe
                if not has_support and not connected_to_scheibe:
                    nodes_to_prune.append(n_id)

        # 3. Process Pruning
        for tip_node_id in nodes_to_prune:
            # --- A. Identify Geometry ---
            member_id = adjacency[tip_node_id][0]
            member = member_map[member_id]
            
            # Identify Root
            if member.start_node_id == tip_node_id:
                root_node = node_map[member.end_node_id]
            else:
                root_node = node_map[member.start_node_id]
            
            # --- B. Transfer Forces ---
            F_tip = get_node_loads_vector(system, tip_node_id)  # [Fx, Fy, M]
            
            tip_node = node_map[tip_node_id]
            r = tip_node.coordinates - root_node.coordinates  # Vector from Root to Tip
            
            F_root_x = F_tip[0]
            F_root_y = F_tip[1]
            
            # Moment Transfer: M_root = M_tip + (r x F)
            M_transport = r[0] * F_tip[1] - r[1] * F_tip[0]
            M_root = F_tip[2] + M_transport
            
            add_equivalent_load(system, root_node.id, np.array([F_root_x, F_root_y, M_root]))
            
            # --- C. Delete Elements ---
            # Remove Member
            system.members = [m for m in system.members if m.id != member_id]
            
            # Remove Node
            system.nodes = [n for n in system.nodes if n.id != tip_node_id]
            
            # Remove Loads on the deleted Tip Node
            system.loads = [
                l for l in system.loads 
                if not (l.scope == 'NODE' and l.node_id == tip_node_id)
            ]
            
            # Remove Scheibe connections to deleted node (shouldn't happen, but be safe)
            for scheibe in system.scheiben:
                scheibe.connections = [
                    conn for conn in scheibe.connections 
                    if conn.node_id != tip_node_id
                ]
            
            # Flag to run another pass (chains of members)
            changed = True
            
            # Break inner loop to rebuild maps safely
            break
    
    # Optional: Remove empty Scheiben (no connections left)
    system.scheiben = [
        s for s in system.scheiben 
        if len(s.connections) > 0
    ]
    
    print(system)
    return system
