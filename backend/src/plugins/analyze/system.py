import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from src.models.analyze_models import StructuralSystem, RigidBody

def calculate_poles(
    system: StructuralSystem, 
    # Key is now str (UUID), not int
    velocity_dict: Dict[str, np.ndarray] 
) -> Tuple[Dict[str, Optional[np.ndarray]], Dict[str, np.ndarray]]:
    """
    Calculates the Pole (ICR) for each member.
    Returns:
        - member_poles: {member_id: [px, py] or None}
        - translation_dirs: {member_id: [vx, vy] (normalized)} for infinite poles
    """
    member_poles: Dict[str, Optional[np.ndarray]] = {}
    translation_dirs: Dict[str, np.ndarray] = {}
    
    for member in system.members:
        nA = member._start_node 
        nB = member._end_node
        
        if not nA or not nB:
            continue

        vA = velocity_dict.get(nA.id, np.zeros(2))
        vB = velocity_dict.get(nB.id, np.zeros(2))
        
        # Access coordinates via property or position object
        r_BA = nB.coordinates - nA.coordinates
        v_BA = vB - vA
        
        L2 = np.dot(r_BA, r_BA)
        if L2 < 1e-12: continue

        # Calculate angular velocity omega
        # Cross product in 2D: x1*y2 - y1*x2
        omega = (r_BA[0] * v_BA[1] - r_BA[1] * v_BA[0]) / L2
        
        if abs(omega) < 1e-6:
            # --- Case: Pure Translation (Infinite Pole) ---
            member_poles[member.id] = None
            
            # Calculate normalized direction from one of the nodes
            norm = np.linalg.norm(vA)
            if norm > 1e-9:
                translation_dirs[member.id] = vA / norm
            else:
                translation_dirs[member.id] = np.zeros(2)
        else:
            # --- Case: Rotation (Finite Pole) ---
            # Pole calculation: P = A + r_AP
            # r_AP is rotated vA scaled by omega. 
            # Vector A is nA.coordinates
            
            # Formula derivation: vA = omega x r_PA => r_PA = (vA x k) / omega
            # P = A - r_PA
            
            # Using your implementation style:
            px = nA.position.x - vA[1] / omega
            py = nA.position.y + vA[0] / omega
            
            member_poles[member.id] = np.array([px, py])
            
    return member_poles, translation_dirs


def group_into_subsystems(
    member_poles: Dict[str, Optional[np.ndarray]], 
    translation_velocity_dict: Optional[Dict[str, np.ndarray]] = None,
    tolerance: float = 1e-4
) -> List[RigidBody]:
    """
    Groups members into Rigid Bodies (Scheiben) and returns structured objects.
    """
    # Helper dict structure to track groups during loop
    # {'type': str, 'val': vec, 'members': [id1, id2]}
    groups_data: List[Dict[str, Any]] = [] 

    for m_id, pole in member_poles.items():
        matched = False
        
        for group in groups_data:
            # CASE A: Finite Rotation
            if pole is not None and group['type'] == 'rotation':
                dist = np.linalg.norm(pole - group['val'])
                if dist < tolerance:
                    group['members'].append(m_id)
                    matched = True
                    break
            
            # CASE B: Pure Translation
            elif pole is None and group['type'] == 'translation':
                if translation_velocity_dict:
                    v_this = translation_velocity_dict.get(m_id, np.zeros(2))
                    v_group = group['val']
                    
                    # Check if normalized vectors are parallel (dot product ~ 1.0 or -1.0)
                    # Note: They are the same rigid body even if moving opposite? 
                    # Usually rigid body translates together, so dot product ~ 1.0
                    if np.isclose(np.dot(v_this, v_group), 1.0, atol=tolerance):
                        group['members'].append(m_id)
                        matched = True
                        break
                else:
                    # Fallback if no velocity data
                    group['members'].append(m_id)
                    matched = True
                    break

        if not matched:
            if pole is not None:
                groups_data.append({'type': 'rotation', 'val': pole, 'members': [m_id]})
            else:
                v_ref = np.zeros(2)
                if translation_velocity_dict:
                    v_ref = translation_velocity_dict.get(m_id, np.zeros(2))
                groups_data.append({'type': 'translation', 'val': v_ref, 'members': [m_id]})
    
    # Convert to RigidBody objects
    rigid_bodies = []
    for i, g in enumerate(groups_data):
        rb = RigidBody(
            id=i, # Keep integer ID for the Rigid Body itself
            member_ids=g['members'], # This is now List[str]
            movement_type=g['type'],
            center_or_vector=g['val']
        )
        rigid_bodies.append(rb)
        
    return rigid_bodies
