import numpy as np
from typing import Dict, List, Optional, Tuple
from models.analyze_models import Node, Member, RigidBody, StructuralSystem


def calculate_poles(
    system: StructuralSystem, 
    velocity_dict: Dict[int, np.ndarray]
) -> Tuple[Dict[int, Optional[np.ndarray]], Dict[int, np.ndarray]]:
    """
    Calculates the Pole (ICR) for each member.
    Returns:
        - member_poles: {member_id: [px, py] or None}
        - translation_dirs: {member_id: [vx, vy] (normalized)} for members with infinite poles
    """
    member_poles = {}
    translation_dirs = {}
    
    for member in system.members:
        nA = member.start_node
        nB = member.end_node
        
        vA = velocity_dict[nA.id]
        vB = velocity_dict[nB.id]
        
        r_BA = nB.coordinates - nA.coordinates
        v_BA = vB - vA
        
        L2 = np.dot(r_BA, r_BA)
        
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
            # r_AP is rotated vA scaled by omega
            px = nA.x - vA[1] / omega
            py = nA.y + vA[0] / omega
            member_poles[member.id] = np.array([px, py])
            
    return member_poles, translation_dirs

def group_into_subsystems(
    member_poles: Dict[int, Optional[np.ndarray]], 
    translation_velocity_dict: Dict[int, np.ndarray] = None,
    tolerance: float = 1e-4
) -> List[RigidBody]:
    """
    Groups members into Rigid Bodies (Scheiben) and returns structured objects.
    """
    groups_data = [] # Temporary storage for algorithm

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
                    
                    # Check if normalized vectors are close
                    if np.isclose(np.abs(np.dot(v_this, v_group)), 1.0, atol=tolerance):
                        group['members'].append(m_id)
                        matched = True
                        break
                else:
                    # If no velocity data, group all translating members together (fallback)
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
            id=i,
            member_ids=g['members'],
            movement_type=g['type'],
            center_or_vector=g['val']
        )
        rigid_bodies.append(rb)
        
    return rigid_bodies


def test_pipeline():

    ### DREI GELENK BOGEN
    system = StructuralSystem()
    n0 = system.add_node(0, 0, fix_x=True, fix_y=True)
    n1 = system.add_node(10, 0, fix_x=True, fix_y=True)
    n2 = system.add_node(5, 5) # The "Apex"
    
    # Left Leg (broken into two parts to test grouping)
    n3 = system.add_node(2.5, 2.5) 
    m0 = system.add_member(n0.id, n3.id) # Part 1 of Left Leg
    m1 = system.add_member(n3.id, n2.id) # Part 2 of Left Leg
    
    # Right Leg (one single member)
    m2 = system.add_member(n2.id, n1.id)
    
    node_velocities = {
        0: np.array([0.0, 0.0]),
        1: np.array([0.0, 0.0]),
        2: np.array([-5.0, 5.0]), # Top Node velocity
        3: np.array([-2.5, 2.5])  # Mid Node velocity (Linear interpolation of N0 and N2)
    }
    
    print("\n--- Running Pipeline ---")
    
    # 1. Calculate Poles
    poles = calculate_poles(system, node_velocities)
    print("Calculated Poles:")
    for mid, pole in poles.items():
        p_str = f"[{pole[0]:.2f}, {pole[1]:.2f}]" if pole is not None else "Infinity"
        print(f"  Member {mid}: {p_str}")

    # 2. Prepare Translation Directions (for infinite poles)
    vel_dirs = {}
    for m in system.members:
        if poles[m.id] is None:
            # Avoid division by zero if node is fixed
            v_node = node_velocities[m.start_node.id]
            norm = np.linalg.norm(v_node)
            if norm > 1e-9:
                vel_dirs[m.id] = v_node / norm
            else:
                vel_dirs[m.id] = np.zeros(2)

    # 3. Group
    rigid_bodies = group_into_subsystems(poles, vel_dirs)

    print(f"\nIdentified {len(rigid_bodies)} rigid bodies (Scheiben).")
    for i, body in enumerate(rigid_bodies):
        print(f"  Body {i+1} (Members {body})")
        
        # Verification
        if 0 in body and 1 in body:
            print("    -> SUCCESS: Left leg parts (Members 0 & 1) are grouped correctly!")
        if 2 in body:
             print("    -> Member 2 is separate (correct, as it rotates differently).")