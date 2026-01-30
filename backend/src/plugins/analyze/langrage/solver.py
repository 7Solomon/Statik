import numpy as np
from scipy.linalg import eig
from scipy.integrate import odeint
from typing import List, Dict, Tuple
from src.models.langrage import ModalResult, TimeStepResult
from src.models.analyze_models import StructuralSystem

# In solver.py

def apply_boundary_conditions(M, C, K, system, dof_map):
    
    # 1. ROTATE MATRICES for nodes with non-zero rotation
    # We must rotate the global system equations so that the DOFs align with the Node's local axes.
    # Only then can we simply "delete" the rows/cols for the supports.
    
    for node in system.nodes:
        if abs(node.rotation) > 1e-6:
            # Create Rotation Matrix for this node (3x3)
            # Angle in radians (assuming node.rotation is degrees)
            alpha = np.radians(node.rotation)
            c, s = np.cos(alpha), np.sin(alpha)
            
            # T_node maps [u_local, v_local, th_local] -> [u_global, v_global, th_global]
            # [ u_g ]   [ c  -s   0 ] [ u_l ]
            # [ v_g ] = [ s   c   0 ] [ v_l ]
            # [ th_g]   [ 0   0   1 ] [ th_l]
            
            T_node = np.array([
                [c, -s, 0],
                [s,  c, 0],
                [0,  0, 1]
            ])
            
            # We need to apply this to the full system matrices M, C, K.
            # This is done by T.T * K * T.
            # But constructing a full (n_dof x n_dof) T matrix is wasteful.
            # Instead, we just rotate the 3x3 block and the cross-terms (rows/cols) for this node.
            
            # Actually, the easiest way to code this clearly (but slightly inefficiently) 
            # is to build the full Global Rotation Matrix T_sys.
            
            # Or, we can do it block-wise (better for performance).
            
            idx = dof_map[node.id] # indices [u, v, th]
            
            # We need to transform the ROWS and COLUMNS corresponding to this node.
            # K_new = T_trans * K_old * T_trans^T (Change of basis)
            
            # Let's use a full transformation matrix approach for clarity and robustness
            # (unless n_dof is > 1000, this is instant).

    # --- IMPLEMENTATION ---
    
    n_dof = M.shape[0]
    T_global = np.eye(n_dof)
    
    for node in system.nodes:
        if abs(node.rotation) > 1e-6:
            alpha = np.radians(node.rotation)
            c, s = np.cos(alpha), np.sin(alpha)
            
            # Indices for this node
            i, j, k = dof_map[node.id]
            
            # Update the diagonal block for this node
            # Note: The inverse rotation is the transpose.
            # We want equations in LOCAL coordinates.
            # u_global = R * u_local
            
            T_global[i, i] = c
            T_global[i, j] = -s
            T_global[j, i] = s
            T_global[j, j] = c

    # Transform the System Matrices to the Local Coordinate Bases
    # K_local_basis = T_global.T @ K_global @ T_global
    
    M = T_global.T @ M @ T_global
    C = T_global.T @ C @ T_global
    K = T_global.T @ K @ T_global
    
    # 2. NOW APPLY BOUNDARY CONDITIONS (Standard logic)
    # Because M, C, K are now in "aligned" coordinates, 
    # fixN correctly suppresses the "Normal" (Local X) direction.
    
    free_dofs = []
    fixed_dofs = []

    for node in system.nodes:
        dofs = dof_map[node.id]
        
        # Now these checks refer to the Local (Rotated) axes
        if not node.supports.fix_n: free_dofs.append(dofs[0])
        else: fixed_dofs.append(dofs[0])
        
        if not node.supports.fix_v: free_dofs.append(dofs[1])
        else: fixed_dofs.append(dofs[1])
        
        if not node.supports.fix_m: free_dofs.append(dofs[2])
        else: fixed_dofs.append(dofs[2])

    M_red = M[np.ix_(free_dofs, free_dofs)]
    C_red = C[np.ix_(free_dofs, free_dofs)]
    K_red = K[np.ix_(free_dofs, free_dofs)]

    # Important: Return T_global so we can rotate results BACK to global for plotting!
    return M_red, C_red, K_red, free_dofs, fixed_dofs, T_global 


def solve_eigenvalues(M_red, K_red, system, dof_map, free_dofs, T_global=None) -> List[ModalResult]:
    """
    Solves the generalized eigenvalue problem K*v = lambda*M*v.
    Returns mode shapes in GLOBAL coordinates.
    """
    if M_red.shape[0] == 0:
        return []

    # Solve Generalized Eigenvalue Problem
    # scipy.linalg.eig(A, B) solves A v = lambda B v
    eigenvalues, eigenvectors = eig(K_red, M_red)
    
    # Filter valid modes (Real, non-negative)
    # Numerical noise can cause tiny complex parts or negative real parts
    valid_modes = []
    for i in range(len(eigenvalues)):
        lam = eigenvalues[i]
        # Check if essentially real and non-negative
        if abs(np.imag(lam)) < 1e-10 and np.real(lam) > -1e-5:
            valid_modes.append((np.real(lam), eigenvectors[:, i]))

    # Sort by frequency (lowest lambda first)
    valid_modes.sort(key=lambda x: abs(x[0]))
    
    modes = []
    
    # Calculate total DOFs for reconstruction
    # (Assuming dof_map covers all nodes and max index is at the end)
    max_dof = 0
    for indices in dof_map.values():
        max_dof = max(max_dof, max(indices))
    n_dof_total = max_dof + 1

    for lam, vec in valid_modes:
        omega = np.sqrt(np.abs(lam))
        freq = omega / (2 * np.pi)
        period = 1/freq if freq > 1e-5 else None 
        
        # 1. Reconstruct Full Vector in LOCAL (Rotated) Coordinates
        # Start with zeros
        u_local_full = np.zeros(n_dof_total)
        
        # Fill in the calculated free DOFs
        # vec contains only the reduced DOFs
        for i, global_dof_idx in enumerate(free_dofs):
            u_local_full[global_dof_idx] = float(np.real(vec[i]))
            
        # 2. Transform to GLOBAL Coordinates
        # The solver worked in the rotated basis (u_local).
        # We need u_global = T * u_local for visualization.
        if T_global is not None:
            u_global_full = T_global @ u_local_full
        else:
            u_global_full = u_local_full

        # 3. Map to Node Structure
        full_shape = {}
        for node in system.nodes:
            dofs = dof_map[node.id] # [dof_x, dof_y, dof_theta]
            
            # Extract values from the Global Vector
            node_vals = [
                u_global_full[dofs[0]], 
                u_global_full[dofs[1]], 
                u_global_full[dofs[2]]
            ]
            full_shape[node.id] = node_vals
            
        modes.append(ModalResult(freq, period, omega, full_shape))
        
    return modes

def check_stability(M_red, C_red, K_red) -> Tuple[bool, float]:
    # Simple check on stiffness
    # Real stability requires eigenvalues of system matrix A
    # Here we just check if K is positive definite
    try:
        np.linalg.cholesky(K_red)
        stable = True
    except np.linalg.LinAlgError:
        stable = False
        
    # Approx damping ratio of first mode
    try:
        w1 = np.sqrt(np.abs(np.linalg.eigvals(np.linalg.inv(M_red) @ K_red)[0]))
        c_crit = 2 * w1
        c_max = np.max(np.abs(C_red))
        ratio = c_max / c_crit if c_crit > 0 else 0
    except:
        ratio = 0
        
    return stable, ratio


def integrate_time_history(
    M, C, K, 
    system, dof_map, free_dofs, 
    t_span, dt, force_func,
    T_global=None
) -> List[TimeStepResult]:
    
    n = M.shape[0] # Size of reduced system
    M_inv = np.linalg.inv(M)
    
    def func(state, t):
        u, u_dot = state[:n], state[n:]
        F = np.zeros(n)
        
        # Note: Ideally, if force_func specifies Global Forces, 
        # we should also rotate F_global -> F_local here.
        # Assuming for now force_func is simple or matches local directions.
        if force_func:
            for i, fdof in enumerate(free_dofs):
                F[i] = force_func(t, fdof)
        
        # Solve EOM: M*u_ddot + C*u_dot + K*u = F
        u_ddot = M_inv @ (F - C @ u_dot - K @ u)
        return np.concatenate([u_dot, u_ddot])
    
    t_eval = np.arange(t_span[0], t_span[1], dt)
    y0 = np.zeros(2*n)
    
    # Solve the ODE
    # Result `sol` is in REDUCED, LOCAL coordinates
    sol = odeint(func, y0, t_eval)
    
    # Determine total number of DOFs for reconstruction
    # (Assuming dof_map indices cover 0 to max)
    max_dof = 0
    for indices in dof_map.values():
        max_dof = max(max_dof, max(indices))
    n_dof_total = max_dof + 1
    
    results = []
    for i, t in enumerate(t_eval):
        # Extract state at this time step
        u_red = sol[i, :n]
        u_dot_red = sol[i, n:]
        
        # 1. Expand Reduced -> Full Local
        u_local = np.zeros(n_dof_total)
        v_local = np.zeros(n_dof_total)
        
        for idx, global_idx in enumerate(free_dofs):
            u_local[global_idx] = u_red[idx]
            v_local[global_idx] = u_dot_red[idx]
            
        # 2. Transform Full Local -> Full Global
        # This converts the rotated support displacements back to Global X/Y
        if T_global is not None:
            u_global = T_global @ u_local
            v_global = T_global @ v_local
        else:
            u_global = u_local
            v_global = v_local
            
        # 3. Map to Nodes
        disps, vels = {}, {}
        for node in system.nodes:
            dofs = dof_map[node.id]
            
            disps[node.id] = [
                float(u_global[dofs[0]]), 
                float(u_global[dofs[1]]), 
                float(u_global[dofs[2]])
            ]
            
            vels[node.id] = [
                float(v_global[dofs[0]]), 
                float(v_global[dofs[1]]), 
                float(v_global[dofs[2]])
            ]
            
        # Energies 
        # (Scalar quantities are invariant under rotation, so reduced/local is fine)
        ke = 0.5 * u_dot_red @ M @ u_dot_red
        pe = 0.5 * u_red @ K @ u_red
        
        results.append(TimeStepResult(
            t, disps, vels, {}, ke, pe, 0.0, ke+pe
        ))
        
    return results