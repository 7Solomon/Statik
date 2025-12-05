from typing import Tuple
import numpy as np 

from models.analyze_models import StructuralSystem

def solve_kinematics(system: 'StructuralSystem') -> Tuple[dict, int]:
    """
    Calculates node velocities by solving the homogeneous system C * v = 0.
    Returns:
        - velocity_dict: {node_id: np.array([vx, vy])}
        - dof: Number of kinematic degrees of freedom (0 = stable/static)
    """
    nodes = system.nodes
    members = system.members
    
    num_nodes = len(nodes)
    num_dofs = 2 * num_nodes  # 2 DOF per node (x, y)
    
    # Map node_id -> global index in the matrix (0 to 2*N-1)
    # node 0 -> indices 0,1; node 1 -> indices 2,3...
    node_idx_map = {n.id: i for i, n in enumerate(nodes)}

    constraints = []

    # --- 1. Support Constraints ---
    # If a node is fixed in X or Y, that velocity component must be 0.
    for n in nodes:
        idx = node_idx_map[n.id]
        
        if n.fix_x:
            row = np.zeros(num_dofs)
            row[2 * idx] = 1.0
            constraints.append(row)
            
        if n.fix_y:
            row = np.zeros(num_dofs)
            row[2 * idx + 1] = 1.0
            constraints.append(row)

    # --- 2. Member Constraints (Rigid Body Assumption) ---
    # The relative velocity along the member axis must be zero.
    # Equation: (v_j - v_i) · (r_j - r_i) = 0
    for m in members:
        i_idx = node_idx_map[m.start_node.id]
        j_idx = node_idx_map[m.end_node.id]
        
        # Geometry vector (r_j - r_i)
        dx = m.end_node.x - m.start_node.x
        dy = m.end_node.y - m.start_node.y
        L_sq = dx**2 + dy**2
        
        if L_sq < 1e-12: continue  # Skip zero-length members
        
        # Normalized direction vector n = (nx, ny)
        L = np.sqrt(L_sq)
        nx = dx / L
        ny = dy / L
        
        # Constraint row: [-nx, -ny, ... , +nx, +ny]
        # Corresponding to -v_ix - v_iy + v_jx + v_jy = 0 (projected)
        row = np.zeros(num_dofs)
        
        # Start Node coeffs
        row[2 * i_idx]     = -nx
        row[2 * i_idx + 1] = -ny
        
        # End Node coeffs
        row[2 * j_idx]     = nx
        row[2 * j_idx + 1] = ny
        
        constraints.append(row)

    # --- 3. Solve C * v = 0 ---
    if not constraints:
        # No constraints -> Everything moves freely
        dof = num_dofs
        # Just give some random unit velocity to everything for visualization
        velocity_dict = {n.id: np.array([1.0, 0.0]) for n in nodes}
        return velocity_dict, dof

    C_matrix = np.array(constraints)
    
    # Use Singular Value Decomposition (SVD) to find the Nullspace
    # The Nullspace contains the "kinematic Modes"
    U, S, Vt = np.linalg.svd(C_matrix)
    
    # Calculate Rank and Nullity (DOF)
    # Tolerance for floating point "zero"
    tol = 1e-10
    rank = np.sum(S > tol)
    dof = num_dofs - rank  # Nullity = Total DOFs - Constraints Rank
    
    velocity_dict = {}
    
    if dof > 0:
        # Structure is UNSTABLE (kinematic)
        # The last 'dof' rows of Vt are the basis vectors for the motion.
        # We usually just take the *last* row (the "dominant" or "first" kinematic mode).
        mode_shape = Vt[-1, :]
        
        # Normalize the mode shape so maximum velocity is 1.0 (for nice visualization)
        max_val = np.max(np.abs(mode_shape))
        if max_val > 1e-9:
            mode_shape = mode_shape / max_val
            
        # Map back to nodes
        for n in nodes:
            idx = node_idx_map[n.id]
            vx = mode_shape[2 * idx]
            vy = mode_shape[2 * idx + 1]
            
            # Clean noise
            if abs(vx) < 1e-10: vx = 0.0
            if abs(vy) < 1e-10: vy = 0.0
            
            velocity_dict[n.id] = np.array([vx, vy])
    else:
        # Structure is STABLE
        for n in nodes:
            velocity_dict[n.id] = np.array([0.0, 0.0])
            
    return velocity_dict, dof