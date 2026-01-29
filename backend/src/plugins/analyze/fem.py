import numpy as np
import copy
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from src.models.analyze_models import ElementContext, FEMResult, MemberResult, StationResult, StructuralSystem, Node, Member, Load, MemberReleases

STATIONS_PER_MEMBER = 21  # Resolution for drawing curves


def calculate_complex_fem(system: StructuralSystem) -> FEMResult:
    """
    Solves 2D Frame with Releases and Distributed Loads.
    """
    elastic_scheiben = [s for s in system.scheiben if s.type == 'ELASTIC']
    if elastic_scheiben:
        print(f"Warning: {len(elastic_scheiben)} ELASTIC Scheiben found.")
        print("ELASTIC Scheiben require 2D FEM meshing (not yet implemented).")
        print("They will be ignored in this analysis.")
    
    #  Map DoFs
    # [u, v, theta] for each node
    dof_map = {n.id: [i*3, i*3+1, i*3+2] for i, n in enumerate(system.nodes)}
    total_dof = len(system.nodes) * 3
    
    K_global = np.zeros((total_dof, total_dof))
    F_global = np.zeros(total_dof) # External Nodal Loads
    
    # Cache element data for post-processing
    elem_contexts: Dict[str, ElementContext] = {}

    # Process Members (Stiffness + Distributed Load -> Equivalent Nodal Load)
    for member in system.members:
        start_node = next(n for n in system.nodes if n.id == member.start_node_id)
        end_node = next(n for n in system.nodes if n.id == member.end_node_id)
        
        # A. Geometry
        L, c, s = get_geometry(start_node, end_node)
        T = get_transformation_matrix(c, s)
        
        # B. Raw Stiffness
        k_local = get_element_stiffness_local(member, L)
        
        # C. Handle Releases (Static Condensation)
        k_local, T_condensed = apply_static_condensation(k_local, member.releases)
        
        # D. Distributed Loads (Fixed End Actions)
        # Find loads acting on this MEMBER
        member_loads = [l for l in system.loads if l.scope == 'MEMBER' and l.member_id == member.id]
        f_fixed_local = np.zeros(6)
        
        for load in member_loads:
            # Accumulate Fixed End Forces (Local System)
            f_fixed_local += calculate_fixed_end_forces(load, L)

        # Handle release effects on Fixed End Forces
        # If a simplified hinge exists, moment capacity is 0, so FEM must be released
        f_fixed_local = apply_release_correction_to_loads(f_fixed_local, k_local, member.releases)

        # Transform Fixed End Forces to Global and SUBTRACT from F_global
        # (External Load = K*u + FixedForces  =>  K*u = External - FixedForces)
        f_fixed_global = T.T @ f_fixed_local
        
        # E. Assembly
        k_global = T.T @ k_local @ T
        elem_contexts[member.id] = ElementContext(L, c, s, T, k_local, k_global, f_fixed_local)
        
        dofs = dof_map[start_node.id] + dof_map[end_node.id]
        for i, r in enumerate(dofs):
            F_global[r] -= f_fixed_global[i] # Equivalent Load vector
            for j, c_idx in enumerate(dofs):
                K_global[r, c_idx] += k_global[i, j]
    
    # Process RIGID Scheiben as Penalty Constraints
    apply_scheibe_constraints(K_global, system.scheiben, system.nodes, dof_map)


    # Process Nodal Loads (Direct Application)
    for load in system.loads:
        if load.scope == 'NODE':
            dofs = dof_map[load.node_id]
            if load.type == 'POINT':
                rad = np.radians(load.angle)
                F_global[dofs[0]] += load.value * np.cos(rad)
                F_global[dofs[1]] += load.value * np.sin(rad)
            elif load.type == 'MOMENT':
                F_global[dofs[2]] += load.value

    #  Apply Supports
    for node in system.nodes:
        dofs = dof_map[node.id]
        if node.supports.fix_x: apply_support(K_global, F_global, dofs[0])
        if node.supports.fix_y: apply_support(K_global, F_global, dofs[1])
        if node.supports.fix_m: apply_support(K_global, F_global, dofs[2])

    #Solve
    try:
        U_global = np.linalg.solve(K_global, F_global)
    except np.linalg.LinAlgError:
        return {"success": False, "error": "Singular Matrix (Unstable Structure)"}

    # Post-Processing
    results = {
        "success": True, 
        "system": system.to_dict(),
        "displacements": {},
        "reactions": {},
        "memberResults": {}
    }

    # Extract Nodal Displacements
    for node in system.nodes:
        dofs = dof_map[node.id]
        results["displacements"][node.id] = list(U_global[dofs])

    # Extract Member Forces
    final_member_results = {}
    for member in system.members:
        ctx = elem_contexts[member.id]
        start_node = next(n for n in system.nodes if n.id == member.start_node_id)
        end_node = next(n for n in system.nodes if n.id == member.end_node_id)
        
        # Displacements
        dof_idxs = dof_map[start_node.id] + dof_map[end_node.id]
        u_global = U_global[dof_idxs]
        
        # Local Displacements
        u_local = ctx.T @ u_global
        
        # Internal Forces at Ends = K_local * u_local + Fixed_End_Forces
        f_ends = ctx.k_local @ u_local + ctx.f_fixed_local
        
        # Sampling along the beam (Superposition)
        member_loads = [l for l in system.loads if l.scope == 'MEMBER' and l.member_id == member.id]
        stations = compute_stations(ctx.L, f_ends, member_loads)
        
        stations_objs = [
            StationResult(s['x'], s['N'], s['V'], s['M']) 
            for s in stations
        ]
        
        # 2. Calculate Min/Max helpers
        max_m = max(s.M for s in stations_objs)
        min_m = min(s.M for s in stations_objs)
        max_v = max(s.V for s in stations_objs)
        min_v = min(s.V for s in stations_objs)
        max_n = max(s.N for s in stations_objs)
        min_n = min(s.N for s in stations_objs)

        # 3. Store directly in final dict
        final_member_results[member.id] = MemberResult(
            memberId=member.id,
            stations=stations_objs,
            maxM=max_m, minM=min_m,
            maxV=max_v, minV=min_v,
            maxN=max_n, minN=min_n
        )

        # End of Loop

        fem_result = FEMResult(
            success=True,
            system=system,
            displacements=results["displacements"],
            reactions=results["reactions"],
            memberResults=final_member_results # Use the populated dict
        )

        return fem_result.to_dict()

# --- HELPER FUNCTIONS ---

def get_geometry(n1: Node, n2: Node):
    dx, dy = n2.coordinates[0] - n1.coordinates[0], n2.coordinates[1] - n1.coordinates[1]
    L = np.sqrt(dx**2 + dy**2)
    return L, dx/L, dy/L

def get_transformation_matrix(c, s):
    z = np.zeros((3,3))
    block = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])
    return np.block([[block, z], [z, block]])

def get_element_stiffness_local(m: Member, L: float):
    E, A, I = m.properties.E, m.properties.A, m.properties.I
    k = np.zeros((6,6))
    # Axial
    a = E*A/L
    k[0,0]=a; k[0,3]=-a; k[3,0]=-a; k[3,3]=a
    # Bending
    b, c, d, e = 12*E*I/L**3, 6*E*I/L**2, 4*E*I/L, 2*E*I/L
    k[1,1]=b; k[1,2]=c; k[1,4]=-b; k[1,5]=c
    k[2,1]=c; k[2,2]=d; k[2,4]=-c; k[2,5]=e
    k[4,1]=-b; k[4,2]=-c; k[4,4]=b; k[4,5]=-c
    k[5,1]=c; k[5,2]=e; k[5,4]=-c; k[5,5]=d
    return k

def calculate_fixed_end_forces(load: Load, L: float):
    # Returns [Fx1, Fy1, M1, Fx2, Fy2, M2]
    # Currently handles UNIFORM DISTRIBUTED LOAD (UDL) only
    # Add switch case for Point Loads on Beam if needed
    f = np.zeros(6)
    if load.type == 'DISTRIBUTED':
        # Assuming load is acting perpendicular to beam (Local Y)
        # q = load value (Force/Length)
        q = load.value 
        
        # Fy = qL/2
        f[1] = q*L/2
        f[4] = q*L/2
        
        # M = qL^2/12
        f[2] = (q * L**2) / 12
        f[5] = -(q * L**2) / 12
    return f

def apply_static_condensation(k: np.ndarray, releases: MemberReleases):
    """
    Modifies stiffness matrix k to account for hinges.
    Rows/Cols: 0:u1, 1:v1, 2:th1, 3:u2, 4:v2, 5:th2
    """
    # Simple Condensation for Mz releases (Indices 2 and 5)
    # If Start Hinge (idx 2)
    if releases.start.mz:
        # Condense row/col 2
        # K_cond = K_uu - K_uk * inv(K_kk) * K_ku
        # For single DoF release, simpler:
        # K_new = K_ij - K_i2 * K_2j / K_22
        fact = k[:, 2] / k[2, 2]
        k = k - np.outer(fact, k[2, :])
        k[2, :] = 0; k[:, 2] = 0 # Explicit zeroing
        
    if releases.end.mz:
        # Condense row/col 5
        fact = k[:, 5] / k[5, 5]
        k = k - np.outer(fact, k[5, :])
        k[5, :] = 0; k[:, 5] = 0

    return k, None # Returns modified K

def apply_scheibe_constraints(
    K_global: np.ndarray,
    scheiben: List,
    nodes: List[Node],
    dof_map: Dict[str, List[int]]
) -> None:
    """
    Apply rigid body constraints for RIGID Scheiben using penalty method.
    
    For each RIGID Scheibe with N connected nodes:
    - All nodes must move together as a rigid body
    - Use penalty stiffness to enforce constraints
    """
    PENALTY = 1e12  # Large penalty factor
    
    for scheibe in scheiben:
        if scheibe.type != 'RIGID':
            continue  # Skip ELASTIC scheiben
        
        # Get rigid connections (no releases)
        rigid_node_ids = [
            conn.node_id 
            for conn in scheibe.connections 
            if conn.releases is None
        ]
        
        if len(rigid_node_ids) < 2:
            continue  # Need at least 2 nodes to constrain
        
        # Get node objects
        node_map = {n.id: n for n in nodes}
        
        # Use first node as reference
        ref_id = rigid_node_ids[0]
        ref_node = node_map[ref_id]
        ref_dofs = dof_map[ref_id]
        
        # Constrain all other nodes to move rigidly with reference
        for other_id in rigid_node_ids[1:]:
            if other_id == ref_id:
                continue
            
            other_node = node_map[other_id]
            other_dofs = dof_map[other_id]
            
            # Relative position
            dx = other_node.position.x - ref_node.position.x
            dy = other_node.position.y - ref_node.position.y
            
            # CONSTRAINT 1: Equal rotation (theta_other = theta_ref)
            # Penalty form: PENALTY * (theta_other - theta_ref)^2
            i_theta = other_dofs[2]
            j_theta = ref_dofs[2]
            
            K_global[i_theta, i_theta] += PENALTY
            K_global[i_theta, j_theta] -= PENALTY
            K_global[j_theta, i_theta] -= PENALTY
            K_global[j_theta, j_theta] += PENALTY
            
            # CONSTRAINT 2: X-displacement rigid body motion
            # u_other = u_ref - dy * theta_ref
            # Penalty form: PENALTY * (u_other - u_ref + dy*theta_ref)^2
            i_ux = other_dofs[0]
            j_ux = ref_dofs[0]
            
            K_global[i_ux, i_ux] += PENALTY
            K_global[i_ux, j_ux] -= PENALTY
            K_global[j_ux, i_ux] -= PENALTY
            K_global[j_ux, j_ux] += PENALTY
            
            # Cross terms with rotation
            K_global[i_ux, j_theta] += PENALTY * dy
            K_global[j_theta, i_ux] += PENALTY * dy
            K_global[j_ux, j_theta] -= PENALTY * dy
            K_global[j_theta, j_ux] -= PENALTY * dy
            
            # CONSTRAINT 3: Y-displacement rigid body motion
            # v_other = v_ref + dx * theta_ref
            # Penalty form: PENALTY * (v_other - v_ref - dx*theta_ref)^2
            i_uy = other_dofs[1]
            j_uy = ref_dofs[1]
            
            K_global[i_uy, i_uy] += PENALTY
            K_global[i_uy, j_uy] -= PENALTY
            K_global[j_uy, i_uy] -= PENALTY
            K_global[j_uy, j_uy] += PENALTY
            
            # Cross terms with rotation
            K_global[i_uy, j_theta] -= PENALTY * dx
            K_global[j_theta, i_uy] -= PENALTY * dx
            K_global[j_uy, j_theta] += PENALTY * dx
            K_global[j_theta, j_uy] += PENALTY * dx


def apply_release_correction_to_loads(f_fixed: np.ndarray, k_condensed: np.ndarray, releases: MemberReleases):
    # If a node is hinged, it cannot sustain a Fixed End Moment.
    # The moment must be released and redistributed as shear.
    
    # Start Hinge
    if releases.start.mz:
        # Moment M1 must be 0.
        # We apply -M1 and distribute it to other DoFs based on condensed stiffness?
        # Actually simpler: Statics. For Propped Cantilever with UDL:
        # M_fixed_end = qL^2/8, V = 3qL/8, 5qL/8
        # General approach: Force M=0 manually and adjust Shear
        # NOTE: This is a complex topic. 
        # Simplified approach: Zero the moment, and adjust shears by M/L couple
        M_rel = f_fixed[2]
        shear_corr = M_rel / 10.0 # Placeholder length? No we need L.
        # This function signature needs L. For now, strict FEM solvers usually 
        # handle this by solving the auxiliary equation u_aux = K_kk^-1 * (F_k - K_ku * u_u)
        pass 
    
    return f_fixed

def compute_stations(L: float, f_ends: np.ndarray, loads: List[Load]):
    # f_ends: [Nx1, Vy1, M1, Nx2, Vy2, M2] (Local)
    # N(x) = -Nx1
    # V(x) = Vy1 - integral(q)
    # M(x) = M1 + Vy1*x - integral(integral(q))
    
    stations = []
    N_start = -f_ends[0]
    V_start = f_ends[1]
    M_start = f_ends[2]
    
    for i in range(STATIONS_PER_MEMBER):
        x = (i / (STATIONS_PER_MEMBER - 1)) * L
        
        # Base forces from reactions
        N = N_start
        V = V_start
        M = M_start + V_start * x
        
        # Load superposition
        for load in loads:
            if load.type == 'DISTRIBUTED':
                q = load.value
                # V(x) -= q*x
                V -= q * x
                # M(x) -= q*x^2 / 2
                M -= (q * x**2) / 2
                
        stations.append({"x": x, "N": N, "V": V, "M": M})
    
    return stations

def apply_support(K, F, idx):
    K[idx, :] = 0
    K[:, idx] = 0
    K[idx, idx] = 1.0
    F[idx] = 0.0

