import numpy as np
from typing import Dict, Tuple, List
from src.models.analyze_models import StructuralSystem, Member, Scheibe, SpringConstraint, DamperConstraint, CableConstraint

def build_dof_map(system: StructuralSystem) -> Tuple[Dict, int]:
    """Create mapping from node DOFs to global DOF indices."""
    dof_map = {}
    dof_counter = 0
    for node in system.nodes:
        dof_map[node.id] = [dof_counter, dof_counter + 1, dof_counter + 2]
        dof_counter += 3
    return dof_map, dof_counter

def assemble_matrices(system: StructuralSystem, dof_map: Dict, n_dof: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Assemble global M, C, K matrices."""
    M = np.zeros((n_dof, n_dof))
    C = np.zeros((n_dof, n_dof))
    K = np.zeros((n_dof, n_dof))
    
    # 1. Members
    for member in system.members:
        M_elem, K_elem = _member_matrices(member, system, dof_map, n_dof)
        M += M_elem
        K += K_elem
        
    # 2. Scheiben (Mass distribution)
    for scheibe in system.scheiben:
        M_scheibe = _scheibe_mass_matrix(scheibe, system, dof_map, n_dof)
        M += M_scheibe
    # STIFFNESS OF SCHEIBEN
    for scheibe in system.scheiben:
        if scheibe.type == 'RIGID':
            K += _add_rigid_body_stiffness(scheibe, system, dof_map, n_dof)

    # 3. Constraints
    for constraint in system.constraints:
        if constraint.type == 'SPRING':
            K += _spring_stiffness_matrix(constraint, system, dof_map, n_dof)
        elif constraint.type == 'DAMPER':
            C += _damper_matrix(constraint, system, dof_map, n_dof)
            if constraint.k is not None:
                K += _damper_stiffness_matrix(constraint, system, dof_map, n_dof)
        elif constraint.type == 'CABLE':
            K += _cable_stiffness_matrix(constraint, system, dof_map, n_dof)
            
    # 4. Anti-singularity for free nodes (Epsilon mass)
    for i in range(n_dof):
        if M[i, i] < 1e-12:
            M[i, i] = 1e-6

    return M, C, K

# --- INTERNAL HELPERS (Same logic as before) ---

def _member_matrices(member: Member, system: StructuralSystem, dof_map: Dict, n_dof: int):
    start_node = next(n for n in system.nodes if n.id == member.start_node_id)
    end_node = next(n for n in system.nodes if n.id == member.end_node_id)
    
    dx = end_node.position.x - start_node.position.x
    dy = end_node.position.y - start_node.position.y
    L = np.sqrt(dx**2 + dy**2)
    
    if L < 1e-9: return np.zeros((n_dof, n_dof)), np.zeros((n_dof, n_dof))
    
    c, s = dx / L, dy / L
    E, A, I = member.properties.E, member.properties.A, member.properties.I
    m = member.properties.m if hasattr(member.properties, 'm') else 7850 * A
    
    # Local Matrices
    EA_L, EI_L, EI_L2, EI_L3 = E*A/L, E*I/L, E*I/L**2, E*I/L**3
    k_local = np.array([
        [ EA_L, 0, 0, -EA_L, 0, 0 ],
        [ 0, 12*EI_L3, 6*EI_L2, 0, -12*EI_L3, 6*EI_L2],
        [ 0, 6*EI_L2, 4*EI_L, 0, -6*EI_L2, 2*EI_L ],
        [-EA_L, 0, 0, EA_L, 0, 0 ],
        [ 0, -12*EI_L3, -6*EI_L2, 0, 12*EI_L3, -6*EI_L2],
        [ 0, 6*EI_L2, 2*EI_L, 0, -6*EI_L2, 4*EI_L ]
    ])
    
    # Releases
    if member.releases.start.mz: k_local[2, :] = k_local[:, 2] = 0
    if member.releases.end.mz: k_local[5, :] = k_local[:, 5] = 0

    m_half = m * L / 2
    m_local = np.diag([m_half, m_half, 0, m_half, m_half, 0])
    
    # Transformation
    T = np.zeros((6, 6))
    T[0:2, 0:2] = T[3:5, 3:5] = [[c, s], [-s, c]]
    T[2, 2] = T[5, 5] = 1
    
    k_global = T.T @ k_local @ T
    m_global = T.T @ m_local @ T
    
    # Assembly
    M_elem = np.zeros((n_dof, n_dof))
    K_elem = np.zeros((n_dof, n_dof))
    
    indices = dof_map[member.start_node_id] + dof_map[member.end_node_id]
    for i, gi in enumerate(indices):
        for j, gj in enumerate(indices):
            M_elem[gi, gj] += m_global[i, j]
            K_elem[gi, gj] += k_global[i, j]
            
    return M_elem, K_elem

def _scheibe_mass_matrix(scheibe: Scheibe, system: StructuralSystem, dof_map: Dict, n_dof: int):
    M = np.zeros((n_dof, n_dof))
    width = abs(scheibe.corner2.x - scheibe.corner1.x)
    height = abs(scheibe.corner2.y - scheibe.corner1.y)
    mass = width * height * scheibe.properties.thickness * scheibe.properties.rho
    
    if not scheibe.connections: return M
    mass_per_node = mass / len(scheibe.connections)
    
    for conn in scheibe.connections:
        if conn.node_id in dof_map:
            u, v, theta = dof_map[conn.node_id]
            M[u, u] += mass_per_node
            M[v, v] += mass_per_node
            M[theta, theta] += mass_per_node * (width*height)/24 # Approx inertia
    return M

def _constraint_matrix(node_i, node_j, val, dof_map, n_dof, is_axial=True):
    """Generic helper for springs/dampers"""
    res = np.zeros((n_dof, n_dof))
    if not node_i or not node_j: return res
    
    dx = node_j.position.x - node_i.position.x
    dy = node_j.position.y - node_i.position.y
    L = np.sqrt(dx**2 + dy**2)
    if L < 1e-9: return res
    
    c, s = dx/L, dy/L
    mat = val * np.array([[c*c, c*s, -c*c, -c*s],
                          [c*s, s*s, -c*s, -s*s],
                          [-c*c, -c*s, c*c, c*s],
                          [-c*s, -s*s, c*s, s*s]])
    
    indices = dof_map[node_i.id][:2] + dof_map[node_j.id][:2]
    for i, gi in enumerate(indices):
        for j, gj in enumerate(indices):
            res[gi, gj] += mat[i, j]
    return res

def _spring_stiffness_matrix(c: SpringConstraint, system, dof_map, n_dof):
    ni = next((n for n in system.nodes if n.id == c.start_node_id), None)
    nj = next((n for n in system.nodes if n.id == c.end_node_id), None)
    return _constraint_matrix(ni, nj, c.k, dof_map, n_dof)

def _damper_stiffness_matrix(c: DamperConstraint, system, dof_map, n_dof):
    ni = next((n for n in system.nodes if n.id == c.start_node_id), None)
    nj = next((n for n in system.nodes if n.id == c.end_node_id), None)
    return _constraint_matrix(ni, nj, c.k, dof_map, n_dof)

def _cable_stiffness_matrix(c: CableConstraint, system, dof_map, n_dof):
    ni = next((n for n in system.nodes if n.id == c.start_node_id), None)
    nj = next((n for n in system.nodes if n.id == c.end_node_id), None)
    # Estimate L for stiffness k = EA/L
    dx = nj.position.x - ni.position.x
    dy = nj.position.y - ni.position.y
    L = np.sqrt(dx**2 + dy**2)
    k = c.EA / L if L > 0 else 0
    return _constraint_matrix(ni, nj, k, dof_map, n_dof)

def _damper_matrix(c: DamperConstraint, system, dof_map, n_dof):
    ni = next((n for n in system.nodes if n.id == c.start_node_id), None)
    nj = next((n for n in system.nodes if n.id == c.end_node_id), None)
    return _constraint_matrix(ni, nj, c.c, dof_map, n_dof)

def _add_rigid_body_stiffness(scheibe, system, dof_map, n_dof):
    K_rigid = np.zeros((n_dof, n_dof))
    
    # We create a "web" of stiff connections between all corners
    # to prevent them from moving relative to each other.
    
    # A very high number (Penalty factor). 
    # Too high = numerical error. Too low = rubbery. 
    # 1e10 is usually a safe bet for standard units.
    E_rigid = 1e10 
    
    # Get all node IDs in the scheibe
    node_ids = [c.node_id for c in scheibe.connections]
    nodes = [n for n in system.nodes if n.id in node_ids]

    # Connect every node to every other node with a "Ghost Truss"
    import itertools
    for n1, n2 in itertools.combinations(nodes, 2):
        
        # Calculate direction
        dx = n2.position.x - n1.position.x
        dy = n2.position.y - n1.position.y
        L = np.sqrt(dx**2 + dy**2)
        
        if L < 1e-9: continue

        c = dx / L
        s = dy / L

        # Stiffness matrix for a truss element (Axial only)
        # We don't need bending, just hold the distance fixed.
        k_local = (E_rigid / L) * np.array([
            [ c*c, c*s, -c*c, -c*s],
            [ c*s, s*s, -c*s, -s*s],
            [-c*c, -c*s, c*c, c*s],
            [-c*s, -s*s, c*s, s*s]
        ])

        # Add to global K
        # Note: DOF map indices need to be handled carefully 
        # (This assumes DOFs 0 and 1 are X and Y translation)
        idx_1 = dof_map[n1.id]
        idx_2 = dof_map[n2.id]
        
        # Map local 4x4 to global
        indices = [idx_1[0], idx_1[1], idx_2[0], idx_2[1]]
        
        for i in range(4):
            for j in range(4):
                K_rigid[indices[i], indices[j]] += k_local[i, j]

    return K_rigid
