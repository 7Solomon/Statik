from typing import Tuple, List, Dict, Optional
import numpy as np

from src.models.analyze_models import StructuralSystem, KinematicMode, Member, Node


def solve_kinematics(system: 'StructuralSystem') -> Tuple[List[KinematicMode], int]:
    """
    Solves the kinematic analysis of a structural system.
    
    Returns:
        - List of kinematic modes (mechanisms)
        - Total degrees of freedom
    """
    nodes = system.nodes
    members = system.members
    num_nodes = len(nodes)
    
    # 3 DOFs per node (u, v, theta)
    num_dofs = 3 * num_nodes
    
    # Map UUIDs to matrix indices
    node_idx_map = {n.id: i for i, n in enumerate(nodes)}
    
    constraints = []
    
    # Support Constraints
    add_support_constraints(nodes, node_idx_map, num_dofs, constraints)
    
    # Member Constraints
    add_member_constraints(members, nodes, node_idx_map, num_dofs, constraints)
    
    ## Coupled Hinge Constraints  (TO FIX THE "Mechanisms with double hinges" Limitation)
    #add_coupled_hinge_constraints(members, nodes, node_idx_map, num_dofs, constraints)
    
    
    # --- 4. Solve SVD ---
    if not constraints:
        return [], num_dofs
    
    C_matrix = np.array(constraints)
    U, S, Vh = np.linalg.svd(C_matrix, full_matrices=True)
    
    tol = 1e-10
    rank = np.sum(S > tol)
    dof_count = num_dofs - rank
    
    modes_result: List[KinematicMode] = []
    
    if dof_count > 0:
        # The Null Space corresponds to the last 'dof_count' rows of Vh
        for k in range(dof_count):
            row_idx = -(k + 1)
            mode_vec = Vh[row_idx, :]
            
            # Normalize
            max_val = np.max(np.abs(mode_vec))
            if max_val > 1e-9:
                mode_vec /= max_val
            
            # Build node velocities dictionary
            node_velocities = {}
            is_mechanism = False
            
            for n in nodes:
                idx = node_idx_map[n.id]
                vx = mode_vec[3*idx]
                vy = mode_vec[3*idx+1]
                vt = mode_vec[3*idx+2]
                
                # Store [vx, vy]
                node_velocities[n.id] = np.array([vx, vy])
                
                if np.sqrt(vx**2 + vy**2) > 1e-6:
                    is_mechanism = True
            
            if is_mechanism:
                km = KinematicMode(
                    index=k,
                    node_velocities=node_velocities,
                    member_poles={},
                    rigid_bodies=[]
                )
                modes_result.append(km)
    
    return modes_result, dof_count


def add_support_constraints(
    nodes: List[Node],
    node_idx_map: Dict[str, int],
    num_dofs: int,
    constraints: List[np.ndarray]
) -> None:
    """
    Adds support boundary condition constraints.
    """
    for n in nodes:
        idx = node_idx_map[n.id]
        u_i, v_i, t_i = 3*idx, 3*idx+1, 3*idx+2
        
        # Access nested supports
        is_fixed_x = bool(n.supports.fix_x)
        is_fixed_y = bool(n.supports.fix_y)
        is_fixed_m = bool(n.supports.fix_m)
        
        # Rotation Matrix for Support Angle
        alpha = np.radians(n.rotation)
        c, s = np.cos(alpha), np.sin(alpha)
        
        if is_fixed_x:  # Constrain Local X
            # Local u' = u*c + v*s = 0
            row = np.zeros(num_dofs)
            row[u_i], row[v_i] = c, s
            constraints.append(row)
        
        if is_fixed_y:  # Constrain Local Y
            # Local v' = -u*s + v*c = 0
            row = np.zeros(num_dofs)
            row[u_i], row[v_i] = -s, c
            constraints.append(row)
        
        if is_fixed_m:  # Constrain Rotation
            row = np.zeros(num_dofs)
            row[t_i] = 1.0
            constraints.append(row)


def add_member_constraints(
    members: List[Member],
    nodes: List[Node],
    node_idx_map: Dict[str, int],
    num_dofs: int,
    constraints: List[np.ndarray]
) -> None:
    """
    Adds member kinematic constraints (axial and rotational).
    """
    for m in members:
        # Access internal node references or use ID map
        i = node_idx_map[m.start_node_id]
        j = node_idx_map[m.end_node_id]
        
        ix, iy, it = 3*i, 3*i+1, 3*i+2
        jx, jy, jt = 3*j, 3*j+1, 3*j+2
        
        # Calculate Length and Direction on the fly
        start_coords = nodes[i].coordinates
        end_coords = nodes[j].coordinates
        
        dx = end_coords[0] - start_coords[0]
        dy = end_coords[1] - start_coords[1]
        L = np.sqrt(dx**2 + dy**2)
        
        if L < 1e-9:
            continue  # Ignore zero-length members
        
        nx, ny = dx/L, dy/L  # Axial unit vector
        
        # True = Released (Hinge), False = Fixed
        rel_start_ax = m.releases.start.fx
        rel_end_ax = m.releases.end.fx
        rel_start_mom = m.releases.start.mz
        rel_end_mom = m.releases.end.mz
        
        # A. AXIAL (Longitudinal) Constraint
        # If EITHER end has an axial release, the member can telescope
        if not rel_start_ax and not rel_end_ax:
            # (vj - vi) · n = 0
            row = np.zeros(num_dofs)
            row[ix], row[iy] = -nx, -ny
            row[jx], row[jy] = nx, ny
            constraints.append(row)
        
        # B. ROTATIONAL Constraints (Beam Theory)
        # We relate node rotation to member rigid body rotation (Omega_beam)
        
        # If Start is Fixed (NOT released)
        if not rel_start_mom:
            row = np.zeros(num_dofs)
            # theta_i - Omega_beam = 0
            # Omega_beam ≈ ((vj - vi) · t_vec) / L
            # t_vec = (-ny, nx)
            row[it] = -1.0  # Node rotation
            # Omega terms
            row[ix], row[iy] = ny/L, -nx/L
            row[jx], row[jy] = -ny/L, nx/L
            constraints.append(row)
        
        # If End is Fixed (NOT released)
        if not rel_end_mom:
            row = np.zeros(num_dofs)
            row[jt] = -1.0  # Node rotation
            # Omega terms (Same beam rotation)
            row[ix], row[iy] = ny/L, -nx/L
            row[jx], row[jy] = -ny/L, nx/L
            constraints.append(row)

def add_coupled_hinge_constraints(
    members: List[Member],
    nodes: List[Node],
    node_idx_map: Dict[str, int],
    num_dofs: int,
    constraints: List[np.ndarray]
) -> None:
    """
    Couples hinged members to prevent mechanisms.
    Strategy: Make one member control the node rotation.
    """
    
    # Build mapping
    node_hinges: Dict[str, List[Tuple[Member, bool]]] = {}
    
    for member in members:
        if member.releases.start.mz:
            node_id = member.start_node_id
            if node_id not in node_hinges:
                node_hinges[node_id] = []
            node_hinges[node_id].append((member, True))
        
        if member.releases.end.mz:
            node_id = member.end_node_id
            if node_id not in node_hinges:
                node_hinges[node_id] = []
            node_hinges[node_id].append((member, False))
    
    # Process nodes with multiple hinges
    for node_id, hinged_members in node_hinges.items():
        if len(hinged_members) < 2:
            continue
        
        node = next(n for n in nodes if n.id == node_id)
        should_couple = getattr(node, 'couple_hinges', True)
        
        if not should_couple:
            continue
        
        # STRATEGY: Pick first member to control node rotation
        # This constrains: θ_node = Ω_member1
        control_member, is_start = hinged_members[0]
        
        idx = node_idx_map[node_id]
        node_theta_dof = 3 * idx + 2
        
        # Get member geometry
        i = node_idx_map[control_member.start_node_id]
        j = node_idx_map[control_member.end_node_id]
        
        coords_i = nodes[i].coordinates
        coords_j = nodes[j].coordinates
        
        dx = coords_j[0] - coords_i[0]
        dy = coords_j[1] - coords_i[1]
        L = np.sqrt(dx**2 + dy**2)
        
        if L < 1e-9:
            continue
        
        nx, ny = dx/L, dy/L
        
        # Constraint: θ_node - Ω_member = 0
        row = np.zeros(num_dofs)
        row[node_theta_dof] = -1.0  # θ_node
        
        # Ω_member terms
        row[3*i] = ny/L
        row[3*i+1] = -nx/L
        row[3*j] = -ny/L
        row[3*j+1] = nx/L
        
        constraints.append(row)
