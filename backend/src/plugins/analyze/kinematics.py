from typing import Any, Tuple, List, Dict, Optional
import numpy as np

from src.models.analyze_models import RigidBody, Scheibe, StructuralSystem, KinematicMode, Member, Node



def solve_kinematics(system: 'StructuralSystem') -> Tuple[List[KinematicMode], int]:
    """
    Solves the kinematic analysis of a structural system.
    """
    nodes = system.nodes
    members = system.members
    scheiben = system.scheiben
    num_nodes = len(nodes)
    
    num_dofs = 3 * num_nodes
    node_idx_map = {n.id: i for i, n in enumerate(nodes)}
    
    constraints = []
    
    add_support_constraints(nodes, node_idx_map, num_dofs, constraints)
    add_member_constraints(members, nodes, node_idx_map, num_dofs, constraints)
    add_scheibe_constraints(scheiben, nodes, node_idx_map, num_dofs, constraints)
    
    if not constraints:
        return [], num_dofs
    
    C_matrix = np.array(constraints)
    U, S, Vh = np.linalg.svd(C_matrix, full_matrices=True)
    
    tol = 1e-10
    rank = np.sum(S > tol)
    dof_count = num_dofs - rank
    
    modes_result: List[KinematicMode] = []
    
    if dof_count > 0:
        for k in range(dof_count):
            row_idx = -(k + 1)
            mode_vec = Vh[row_idx, :]
            
            # Normalize
            max_val = np.max(np.abs(mode_vec))
            if max_val > 1e-9:
                mode_vec /= max_val
            
            # Build node velocities
            node_velocities = {}
            is_mechanism = False
            
            for n in nodes:
                idx = node_idx_map[n.id]
                vx = mode_vec[3*idx]
                vy = mode_vec[3*idx+1]
                vtheta = mode_vec[3*idx+2]
                
                node_velocities[n.id] = np.array([vx, vy])
                
                # Check for ANY non-zero velocity (translation OR rotation)
                if np.sqrt(vx**2 + vy**2) > 1e-6 or abs(vtheta) > 1e-6:
                    is_mechanism = True
            
            # Calculate Scheibe velocities
            scheibe_velocities = {}
            for scheibe in scheiben:
                vel = calculate_scheibe_velocity(scheibe, mode_vec, nodes, node_idx_map)
                if vel is not None:
                    scheibe_velocities[scheibe.id] = vel
                    # Also check scheibe motion
                    if np.sqrt(vel[0]**2 + vel[1]**2) > 1e-6 or abs(vel[2]) > 1e-6:
                        is_mechanism = True
            
            if is_mechanism:
                rigid_bodies = detect_rigid_bodies(scheiben, node_velocities, nodes, node_idx_map, mode_vec)
                
                km = KinematicMode(
                    index=k,
                    node_velocities=node_velocities,
                    member_poles={},
                    rigid_bodies=rigid_bodies,
                    scheibe_velocities=scheibe_velocities
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
        is_fixed_x = bool(n.supports.fix_n)
        is_fixed_y = bool(n.supports.fix_v)
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
            
def add_scheibe_constraints(
    scheiben: List[Scheibe],
    nodes: List[Node],
    node_idx_map: Dict[str, int],
    num_dofs: int,
    constraints: List[np.ndarray]
) -> None:
    """
    Adds rigid body constraints for Scheiben.
    
    A RIGID Scheibe constrains all connected nodes to move as a single rigid body.
    This means:
    1. All nodes have the same rotation
    2. Relative positions remain constant (rigid body kinematics)
    
    For ELASTIC scheiben: No kinematic constraints (handled in FEM)
    """
    for scheibe in scheiben:
        # Only RIGID scheiben impose kinematic constraints
        if scheibe.type != 'RIGID':
            continue
        
        # Get nodes with rigid connections (no releases)
        rigid_node_ids = [
            conn.node_id 
            for conn in scheibe.connections 
            if conn.releases is None  # No releases = rigid connection
        ]
        
        if len(rigid_node_ids) < 2:
            continue  # Need at least 2 nodes to constrain
        
        # Strategy: Make first node the "reference" node
        # All other nodes must move rigidly relative to it
        ref_node_id = rigid_node_ids[0]
        ref_idx = node_idx_map[ref_node_id]
        ref_node = nodes[ref_idx]
        
        # Reference DOFs
        ref_ux = 3 * ref_idx
        ref_uy = 3 * ref_idx + 1
        ref_theta = 3 * ref_idx + 2
        
        # Constrain all other nodes to move rigidly with reference
        for other_node_id in rigid_node_ids[1:]:
            other_idx = node_idx_map[other_node_id]
            other_node = nodes[other_idx]
            
            # Other DOFs
            other_ux = 3 * other_idx
            other_uy = 3 * other_idx + 1
            other_theta = 3 * other_idx + 2
            
            # Calculate relative position vector
            dx = other_node.position.x - ref_node.position.x
            dy = other_node.position.y - ref_node.position.y
            
            # CONSTRAINT 1: Rotation must be equal
            # θ_other - θ_ref = 0
            row_rotation = np.zeros(num_dofs)
            row_rotation[other_theta] = 1.0
            row_rotation[ref_theta] = -1.0
            constraints.append(row_rotation)
            
            # CONSTRAINT 2: X-displacement follows rigid body motion
            # u_other - u_ref + dy * θ_ref = 0
            row_ux = np.zeros(num_dofs)
            row_ux[other_ux] = 1.0
            row_ux[ref_ux] = -1.0
            row_ux[ref_theta] = dy  # Rotation coupling
            constraints.append(row_ux)
            
            # CONSTRAINT 3: Y-displacement follows rigid body motion
            # v_other - v_ref - dx * θ_ref = 0
            row_uy = np.zeros(num_dofs)
            row_uy[other_uy] = 1.0
            row_uy[ref_uy] = -1.0
            row_uy[ref_theta] = -dx  # Rotation coupling
            constraints.append(row_uy)
        
        # Handle nodes with releases (hinged connections to Scheibe)
        for conn in scheibe.connections:
            if conn.releases is None:
                continue  # Already handled above
            
            # Node is hinged to the Scheibe - only partial constraint
            node_idx = node_idx_map[conn.node_id]
            node = nodes[node_idx]
            
            node_ux = 3 * node_idx
            node_uy = 3 * node_idx + 1
            node_theta = 3 * node_idx + 2
            
            dx = node.position.x - ref_node.position.x
            dy = node.position.y - ref_node.position.y
            
            # If moment is released (mz=True), allow relative rotation
            # But still constrain translation to follow rigid body
            if not conn.releases.mz:
                # No moment release = constrain rotation
                row = np.zeros(num_dofs)
                row[node_theta] = 1.0
                row[ref_theta] = -1.0
                constraints.append(row)
            
            # If axial or shear are NOT released, constrain translation
            if not conn.releases.fx:
                # Constrain X displacement
                row = np.zeros(num_dofs)
                row[node_ux] = 1.0
                row[ref_ux] = -1.0
                row[ref_theta] = dy
                constraints.append(row)
            
            if not conn.releases.fy:
                # Constrain Y displacement
                row = np.zeros(num_dofs)
                row[node_uy] = 1.0
                row[ref_uy] = -1.0
                row[ref_theta] = -dx
                constraints.append(row)

def detect_rigid_bodies(
    scheiben: List[Scheibe],
    node_velocities: Dict[str, np.ndarray],
    nodes: List[Node],
    node_idx_map: Dict[str, int],
    mode_vec: np.ndarray
) -> List[RigidBody]:
    """
    Detect which Scheiben are moving as rigid bodies in this kinematic mode.
    
    Returns:
        List of RigidBody objects with movement characterization
    """
    rigid_bodies = []
    
    for scheibe_idx, scheibe in enumerate(scheiben):
        if scheibe.type != 'RIGID':
            continue
        
        # Get rigid connections
        rigid_node_ids = [
            conn.node_id 
            for conn in scheibe.connections 
            if conn.releases is None
        ]
        
        if len(rigid_node_ids) < 2:
            continue
        
        # Check if all nodes have consistent rigid body motion
        # Get first node as reference
        ref_id = rigid_node_ids[0]
        ref_idx = node_idx_map[ref_id]
        ref_node = nodes[ref_idx]
        
        ref_vx = mode_vec[3 * ref_idx]
        ref_vy = mode_vec[3 * ref_idx + 1]
        ref_omega = mode_vec[3 * ref_idx + 2]
        
        # Check if this is a pure translation or rotation
        is_rigid_motion = True
        movement_type = None
        
        # Test if all nodes follow rigid body kinematics
        for node_id in rigid_node_ids[1:]:
            idx = node_idx_map[node_id]
            node = nodes[idx]
            
            vx = mode_vec[3 * idx]
            vy = mode_vec[3 * idx + 1]
            omega = mode_vec[3 * idx + 2]
            
            # Check rotation consistency
            if abs(omega - ref_omega) > 1e-6:
                is_rigid_motion = False
                break
            
            # Check translation consistency (rigid body formula)
            dx = node.position.x - ref_node.position.x
            dy = node.position.y - ref_node.position.y
            
            expected_vx = ref_vx - dy * ref_omega
            expected_vy = ref_vy + dx * ref_omega
            
            if abs(vx - expected_vx) > 1e-6 or abs(vy - expected_vy) > 1e-6:
                is_rigid_motion = False
                break
        
        if not is_rigid_motion:
            continue
        
        # Characterize movement type
        trans_mag = np.sqrt(ref_vx**2 + ref_vy**2)
        rot_mag = abs(ref_omega)
        
        if rot_mag < 1e-6 and trans_mag > 1e-6:
            # Pure translation
            movement_type = "translation"
            direction = np.array([ref_vx, ref_vy])
            direction /= np.linalg.norm(direction)  # Normalize
            center_or_vector = direction
            
        elif rot_mag > 1e-6:
            # Rotation (possibly with translation = instant center)
            movement_type = "rotation"
            
            # Calculate instant center (pole)
            if trans_mag < 1e-6:
                # Pure rotation around reference point
                center_or_vector = np.array([ref_node.position.x, ref_node.position.y])
            else:
                # General motion - find instant center
                # IC is perpendicular to velocity, distance = v/ω
                r = trans_mag / rot_mag
                vx_perp = -ref_vy / trans_mag
                vy_perp = ref_vx / trans_mag
                
                center_or_vector = np.array([
                    ref_node.position.x + r * vx_perp,
                    ref_node.position.y + r * vy_perp
                ])
        else:
            # No movement
            continue
        
        # Create RigidBody object
        rigid_body = RigidBody(
            id=scheibe_idx,
            member_ids=[], # NO MEMEBER MAYBE ADD SCHEIBE
            movement_type=movement_type,
            center_or_vector=center_or_vector
        )
        
        rigid_bodies.append(rigid_body)
    
    return rigid_bodies


def calculate_scheibe_velocity(
    scheibe: Scheibe,
    mode_vec: np.ndarray,
    nodes: List[Node],
    node_idx_map: Dict[str, int]
) -> Optional[np.ndarray]:
    """
    Calculate [vx, vy, omega] velocity of Scheibe center.
    
    For RIGID Scheiben: Calculate from any connected node (they all move rigidly)
    For ELASTIC Scheiben: Return None (deforms with FEM)
    """
    if scheibe.type != 'RIGID':
        return None
    
    # Get a rigid connection node
    rigid_node_ids = [
        conn.node_id 
        for conn in scheibe.connections 
        if conn.releases is None
    ]
    
    if len(rigid_node_ids) == 0:
        return None
    
    # Use first rigid node as reference
    ref_id = rigid_node_ids[0]
    ref_idx = node_idx_map[ref_id]
    ref_node = nodes[ref_idx]
    
    # Node velocity
    node_vx = mode_vec[3 * ref_idx]
    node_vy = mode_vec[3 * ref_idx + 1]
    node_omega = mode_vec[3 * ref_idx + 2]
    
    # Scheibe center
    cx = (scheibe.corner1.x + scheibe.corner2.x) / 2
    cy = (scheibe.corner1.y + scheibe.corner2.y) / 2
    
    # Relative position from node to center
    dx = cx - ref_node.position.x
    dy = cy - ref_node.position.y
    
    # Center velocity using rigid body kinematics
    # v_center = v_node + omega × r
    center_vx = node_vx - dy * node_omega
    center_vy = node_vy + dx * node_omega
    
    # Angular velocity is the same for all points in rigid body
    center_omega = node_omega
    
    return np.array([center_vx, center_vy, center_omega])



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
