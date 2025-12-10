# kinematics.py
from typing import Tuple, List, Dict
import numpy as np
from models.analyze_models import StructuralSystem

def solve_kinematics(system: 'StructuralSystem') -> Tuple[List[Dict[int, np.ndarray]], int]:

    print(system)
    nodes = system.nodes
    members = system.members
    num_nodes = len(nodes)
    
    # UPGRADE: 3 DOFs per node (u, v, theta)
    num_dofs = 3 * num_nodes
    
    node_idx_map = {n.id: i for i, n in enumerate(nodes)}
    constraints = []

    # --- 1. Support Constraints ---
    for n in nodes:
        idx = node_idx_map[n.id]
        u_i, v_i, t_i = 3*idx, 3*idx+1, 3*idx+2
        
        # Rotation Matrix for Support Angle
        # Global U = u*cos(a) - v*sin(a) ... wait, we constrain LOCAL DOFs
        # Local u' = U*cos(a) + V*sin(a)
        # Local v' = -U*sin(a) + V*cos(a)
        
        alpha = np.radians(n.support_angle)
        c, s = np.cos(alpha), np.sin(alpha)

        if n.fix_x_local: # Constrain Local X (Roller direction)
            row = np.zeros(num_dofs)
            row[u_i], row[v_i] = c, s 
            constraints.append(row)

        if n.fix_y_local: # Constrain Local Y (Normal direction)
            row = np.zeros(num_dofs)
            row[u_i], row[v_i] = -s, c
            constraints.append(row)
            
        if n.fix_m: # Constrain Rotation
            row = np.zeros(num_dofs)
            row[t_i] = 1.0
            constraints.append(row)

    # --- 2. Member Constraints ---
    for m in members:
        i = node_idx_map[m.start_node.id]
        j = node_idx_map[m.end_node.id]
        
        ix, iy, it = 3*i, 3*i+1, 3*i+2
        jx, jy, jt = 3*j, 3*j+1, 3*j+2

        dx = m.end_node.x - m.start_node.x
        dy = m.end_node.y - m.start_node.y
        L = np.sqrt(dx**2 + dy**2)
        nx, ny = dx/L, dy/L # Axial vector

        # A. AXIAL (Longitudinal) Constraint
        # (vj - vi) * n = 0  => No stretch
        # ONLY if NO Normal Force release (release_n) is present at EITHER end
        if not m.releases['start']['n'] and not m.releases['end']['n']:
            row = np.zeros(num_dofs)
            row[ix], row[iy] = -nx, -ny
            row[jx], row[jy] = nx, ny
            constraints.append(row)

        # B. TRANSVERSE + ROTATIONAL Constraints (Beam Theory)
        # We relate node rotation to member rigid body rotation.
        # Transverse vector t = (-ny, nx)
        
        # Check Rigidity
        fixed_start = not m.releases['start']['m']
        fixed_end = not m.releases['end']['m']
        
        # If a node is rigidly connected to the beam, its theta must match 
        # the beam's rigid body rotation rate: omega_beam.
        # omega_beam ~ (v_trans_j - v_trans_i) / L
        
        # Constraint: theta_i - ( (vj - vi) * t ) / L = 0
        
        # Transverse dot product terms:
        # (vj - vi) * t = (uj - ui)*(-ny) + (vj - vi)*(nx)
        #               = -uj*ny + ui*ny + vj*nx - vi*nx
        
        # Coeffs for (vj - vi) * t / L:
        # ui: ny/L, vi: -nx/L
        # uj: -ny/L, vj: nx/L

        if fixed_start:
            row = np.zeros(num_dofs)
            # Term: - theta_i
            row[it] = -1.0 
            # Term: + Omega_beam
            row[ix], row[iy] = ny/L, -nx/L
            row[jx], row[jy] = -ny/L, nx/L
            constraints.append(row)

        if fixed_end:
            row = np.zeros(num_dofs)
            # Term: - theta_j
            row[jt] = -1.0
            # Term: + Omega_beam
            row[ix], row[iy] = ny/L, -nx/L
            row[jx], row[jy] = -ny/L, nx/L
            constraints.append(row)

    # --- 3. Solve SVD ---
    if not constraints:
         # Return generic movement
         return [], num_dofs

    C_matrix = np.array(constraints)
    U, S, Vh = np.linalg.svd(C_matrix)
    tol = 1e-10
    rank = np.sum(S > tol)
    dof = num_dofs - rank
    
    modes = []
    if dof > 0:
        for k in range(dof):
            row_idx = -(k + 1)
            mode_vec = Vh[row_idx, :]
            
            # Normalize
            max_val = np.max(np.abs(mode_vec))
            if max_val > 1e-9: mode_vec /= max_val
            
            mode_dict = {}
            for n in nodes:
                idx = node_idx_map[n.id]
                # Extract u, v (ignore theta for visualization)
                vx = mode_vec[3*idx]
                vy = mode_vec[3*idx+1]
                mode_dict[n.id] = np.array([vx, vy])

            # keep only modes with translations
            is_mechanism_mode = False
            for n in nodes:
                if np.linalg.norm(mode_dict[n.id]) > 1e-6:
                    is_mechanism_mode = True
                    break

            if is_mechanism_mode:
                modes.append(mode_dict)
            
    return modes, dof
