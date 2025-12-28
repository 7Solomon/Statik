from src.models.analyze_models import Load, Member, StructuralSystem
import numpy as np
from typing import Dict, Tuple

def assemble_load_vector(system: 'StructuralSystem', dof_map: Dict[str, Tuple[int, int, int]]) -> np.ndarray:
    """
    Constructs the Global Load Vector (F).
    
    Args:
        system: The StructuralSystem containing nodes, members, and loads.
        dof_map: A dictionary mapping Node ID -> (DOF_X_Index, DOF_Y_Index, DOF_M_Index)
                 This tells us where in the F-vector each node lives.
                 
    Returns:
        F: The Global Force Vector (numpy array)
    """
    
    # 1. Determine size of vector (3 DOFs per node)
    n_dofs = len(system.nodes) * 3
    F = np.zeros(n_dofs)

    for load in system.loads:
        
        # ==========================================================
        # CASE A: LOAD ON NODE (Direct addition)
        # ==========================================================
        if load.scope == 'NODE':
            if not load.node_id or load.node_id not in dof_map:
                continue
                
            dof_indices = dof_map[load.node_id] # (ix, iy, im)
            
            if load.type == 'POINT':
                # Convert Angle/Magnitude to X/Y components
                angle_rad = np.radians(load.angle)
                fx = load.value * np.cos(angle_rad)
                fy = load.value * np.sin(angle_rad) # Usually negative for gravity if angle is 270 (-90)
                
                # Add to Global Vector
                F[dof_indices[0]] += fx
                F[dof_indices[1]] += fy
                
            elif load.type == 'MOMENT':
                # Add directly to Moment DOF
                F[dof_indices[2]] += load.value

        # ==========================================================
        # CASE B: LOAD ON MEMBER (Equivalent Nodal Forces)
        # ==========================================================
        elif load.scope == 'MEMBER':
            # Find the member
            member = next((m for m in system.members if m.id == load.member_id), None)
            if not member:
                continue
                
            # Get Start/End Nodes
            node_s = next((n for n in system.nodes if n.id == member.start_node_id), None)
            node_e = next((n for n in system.nodes if n.id == member.end_node_id), None)
            
            if not node_s or not node_e:
                continue

            # Calculate Local Equivalent Forces
            # (This returns a vector of 6 values: [fx_s, fy_s, mz_s, fx_e, fy_e, mz_e])
            f_local = calculate_fixed_end_forces(member, load)
            
            # Transform to Global Coordinates
            f_global = transform_local_to_global(f_local, member)
            
            # Add to Global F Vector
            dofs_s = dof_map[member.start_node_id]
            dofs_e = dof_map[member.end_node_id]
            
            # Add Start Node contributions
            F[dofs_s[0]] += f_global[0]
            F[dofs_s[1]] += f_global[1]
            F[dofs_s[2]] += f_global[2]
            
            # Add End Node contributions
            F[dofs_e[0]] += f_global[3]
            F[dofs_e[1]] += f_global[4]
            F[dofs_e[2]] += f_global[5]

    return F

def calculate_fixed_end_forces(member: 'Member', load: 'Load') -> np.ndarray:
    """
    Calculates the reaction forces at the ends of a fixed beam.
    Returns [Fx1, Fy1, M1, Fx2, Fy2, M2] in LOCAL coordinates.
    """
    L = member.length()
    f = np.zeros(6)
    
    # --- POINT LOAD ON MEMBER ---
    if load.type == 'POINT':
        # Distance from start node 'a'
        a = load.ratio * L
        b = L - a
        P = load.value # Magnitude
        
        # Assuming Force is Perpendicular to Beam (Local Y)
        # If you support angled loads on beams, you need to project P first.
        # For now, let's assume P acts in Local Y (transverse).
        print(Warning("HERE ANGLE NEDS TO BE ADDED!"))
        
        # Standard formulas for Fixed-Fixed Beam with Point Load
        # Fy1
        f[1] = (P * b**2 * (3*a + b)) / L**3
        # M1
        f[2] = (P * a * b**2) / L**2
        # Fy2
        f[4] = (P * a**2 * (a + 3*b)) / L**3
        # M2 (Note sign convention: usually Counter-Clockwise is positive)
        f[5] = -(P * a**2 * b) / L**2
        
    # --- DISTRIBUTED LOAD ---
    elif load.type == 'DISTRIBUTED':
        # Simplified: Uniform Load over full length
        # You'd need more complex math for partial trapezoidal loads
        w = load.value # N/m
        
        # If Partial load, math is harder. Let's assume full length for this example:
        # Fy1
        f[1] = (w * L) / 2
        # M1
        f[2] = (w * L**2) / 12
        # Fy2
        f[4] = (w * L) / 2
        # M2
        f[5] = -(w * L**2) / 12

    return f

def transform_local_to_global(f_local: np.ndarray, member: 'Member') -> np.ndarray:
    """
    Transforms a 6-element force vector from Local to Global system.
    """
    dx = member._end_node.position.x - member._start_node.position.x
    dy = member._end_node.position.y - member._start_node.position.y
    L = np.hypot(dx, dy)
    c = dx / L
    s = dy / L
    
    # Rotation Matrix for 2 Nodes (6x6)
    T = np.zeros((6, 6))
    block = np.array([
        [c, -s, 0],
        [s,  c, 0],
        [0,  0, 1]
    ])
    T[0:3, 0:3] = block
    T[3:6, 3:6] = block
    
    return T @ f_local
