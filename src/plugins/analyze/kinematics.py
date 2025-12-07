from typing import Tuple, List, Dict
import numpy as np

# Ensure you have this import available or adjust accordingly
from models.analyze_models import StructuralSystem

def solve_kinematics(system: 'StructuralSystem') -> Tuple[List[Dict[int, np.ndarray]], int]:
    """
    Calculates the independent kinematic modes of the system.
    
    Returns:
        - modes: List of velocity dictionaries. Each dict is {node_id: np.array([vx, vy])}
        - dof: Number of kinematic degrees of freedom (int)
    """
    nodes = system.nodes
    members = system.members
    
    num_nodes = len(nodes)
    num_dofs = 2 * num_nodes 
    node_idx_map = {n.id: i for i, n in enumerate(nodes)}

    constraints = []

    # --- 1. Support Constraints (v = 0) ---
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
    # (v_j - v_i) · (r_j - r_i) = 0
    for m in members:
        i_idx = node_idx_map[m.start_node.id]
        j_idx = node_idx_map[m.end_node.id]
        
        dx = m.end_node.x - m.start_node.x
        dy = m.end_node.y - m.start_node.y
        L_sq = dx**2 + dy**2
        
        if L_sq < 1e-12: continue 
        
        L = np.sqrt(L_sq)
        nx = dx / L
        ny = dy / L
        
        row = np.zeros(num_dofs)
        row[2 * i_idx]     = -nx
        row[2 * i_idx + 1] = -ny
        row[2 * j_idx]     = nx
        row[2 * j_idx + 1] = ny
        constraints.append(row)

    # --- 3. Solve C * v = 0 ---
    
    # Case: No constraints
    if not constraints:
        dof = num_dofs
        # Return a simple translation mode as placeholder
        dummy_mode = {n.id: np.array([1.0, 0.0]) for n in nodes}
        return [dummy_mode], dof

    C_matrix = np.array(constraints)
    
    # SVD Decomposition
    # U * S * Vh = A
    # The rows of Vh corresponding to singular values ~ 0 form the null space basis.
    U, S, Vh = np.linalg.svd(C_matrix)
    
    tol = 1e-10
    rank = np.sum(S > tol)
    dof = num_dofs - rank 
    
    modes = []

    if dof > 0:
        # The null space vectors are the LAST 'dof' rows of Vh.
        # We iterate to extract each independent mode.
        for k in range(dof):
            # If dof=1, we want index -1. If dof=2, we want -1 and -2.
            row_idx = -(k + 1) 
            mode_shape = Vh[row_idx, :]
            
            # Normalize for visualization consistency (max velocity = 1.0)
            max_val = np.max(np.abs(mode_shape))
            if max_val > 1e-9:
                mode_shape = mode_shape / max_val
            
            # Build dictionary for this mode
            mode_dict = {}
            for n in nodes:
                idx = node_idx_map[n.id]
                vx = mode_shape[2 * idx]
                vy = mode_shape[2 * idx + 1]
                
                # Clean numerical noise
                if abs(vx) < 1e-10: vx = 0.0
                if abs(vy) < 1e-10: vy = 0.0
                
                # Store as numpy array (backend standard)
                mode_dict[n.id] = np.array([vx, vy])
            
            modes.append(mode_dict)
            
    else:
        # Stable Structure (DOF = 0)
        zero_mode = {n.id: np.array([0.0, 0.0]) for n in nodes}
        modes.append(zero_mode)
            
    return modes, dof
