from custome_class_definitions import Bearing, DistributedLoad, Joint, PointLoad, ProblemDefinition
import numpy as np
from typing import List 

def check_static_determinacy(problem: ProblemDefinition) -> int:
    """
    f = a + 3 * (c - n) - r
    """
    # total number of support reaction components
    a = sum(len([_ for _ in node.reactions if isinstance(_, Bearing)]) for node in problem.nodes)
    # number of connections
    c = len(problem.connections)
    # number of nodes
    n = len(problem.nodes)
    # internal releases (hinges).
    r = 2 # NI

    print(f"Static indeterminacy check: a = {a}, c = {c}, n = {n}, r = {r}")
    # Degree of static indeterminacy
    f = a + 3 * (c - n) - r

    if f == 0:
        print(f"Statically determinate (f = {f}). The system can be calculated.")
    elif f > 0:
        print(f"Statically indeterminate (f = {f}). Cannot be solved with equilibrium equations alone.")
    else: # f < 0
        print(f"Unstable/Kinematic (f = {f}). The system is not in equilibrium.")

    return f

def fixed_joint_reaction(joint_reactions_1: List[Joint], joint_reactions_2: List[Joint]):

    #for joint in joint_reactions_1:
    #    print(f"Analyzing joint reaction at {joint.vector} with value {joint.value}")
#
    #for joint in joint_reactions_2:
    #    print(f"Analyzing joint reaction at {joint.vector} with value {joint.value}")

    #print(len(joint_reactions_1), len(joint_reactions_2))
    if len(joint_reactions_1) != len(joint_reactions_2):
        return False
    else:
        #print("Joint reactions are balanced.")
        if len(joint_reactions_1) == 3:
            vectors = [joint.vector for joint in joint_reactions_1]
            has_x = any(vector[0] == 1 and vector[1] == 0 and vector[2] == 0 for vector in vectors)
            has_y = any(vector[0] == 0 and vector[1] == 1 and vector[2] == 0 for vector in vectors)
            has_m = any(vector[0] == 0 and vector[1] == 0 and vector[2] == 1 for vector in vectors)
            if has_x and has_y and has_m:
                return True
    return False

def split_in_base_systems(problem: ProblemDefinition):
    """
    Splits the problem into base systems for easier analysis.
    """
    #print(problem)
    
    for connection in problem.connections:
        print(f"Connection from {connection.from_node} to {connection.to_node} with length {connection.length}")
        Joint_reaction_1 = [_ for _ in problem.node(connection.from_node).reactions if isinstance(_, Joint) and _.from_node == connection.to_node]
        Joint_reaction_2 = [_ for _ in problem.node(connection.to_node).reactions if isinstance(_, Joint) and _.from_node == connection.from_node]
        is_fixed = fixed_joint_reaction(Joint_reaction_1, Joint_reaction_2)
        print(f"Is connection fixed? {is_fixed}")
        #print(f"Joint reactions for connection: {Joint_reaction_1}, {Joint_reaction_2}")

def calculate_reaction_forces(problem: ProblemDefinition):
    """
    Calculates the reaction forces for a statically determinate 2D system.
    Solves the system of linear equations A*x = b, where:
    - A is the coefficient matrix from the equilibrium equations.
    - x is the vector of unknown reaction force magnitudes.
    - b is the vector of known external loads and moments.
    """
    unknowns = []
    node_map = {node.id: node for node in problem.nodes}

    # GEt
    for node in problem.nodes:
        for i, bearing in enumerate(node.bearings):
            direction = 'x' if bearing.vector[0] else ('y' if bearing.vector[1] else 'm')
            unknowns.append({
                "name": f"R_{node.id}_{direction}",
                "node_id": node.id,
                "vector": np.array(bearing.vector, dtype=float)
            })

    if len(unknowns) != 3:
        print(f"Error: Expected 3 unknown reactions for a 2D system, but found {len(unknowns)}.")
        return None

    print('MOMENT NEEDS TO BE SMARTER - NOT JUST THE FIRST NODE')
    pivot_node = problem.nodes[0]
    pivot_pos = np.array(pivot_node.position, dtype=float)

    A = np.zeros((3, 3))
    b = np.zeros(3)

    # Populate matrix A with coefficients of the unknown reactions
    for i, unknown in enumerate(unknowns):
        node_pos = np.array(node_map[unknown["node_id"]].position, dtype=float)
        A[0, i] = unknown["vector"][0]  # x-component
        A[1, i] = unknown["vector"][1]  # y-component
        
        # Moment arm r = (node_pos - pivot_pos)
        r = node_pos - pivot_pos
        # Moment = r x F. For 2D, M = r_x*F_y - r_y*F_x
        # F is the reaction force vector, e.g., F = [R_Ax, 0, 0]
        # So moment is r[0]*unknown['vector'][1] - r[1]*unknown['vector'][0]
        # Plus any moment reaction M (vector[2])
        A[2, i] = r[0] * unknown["vector"][1] - r[1] * unknown["vector"][0] + unknown["vector"][2]

    # Populate vector b with the negative of external loads and moments
    for load in problem.loads:
        force = np.array(load.ve, dtype=float)
        
        if isinstance(load, PointLoad):
            # For a point load, 'force' is the total force vector
            load_pos = np.array(load.position, dtype=float)
            
        elif isinstance(load, DistributedLoad):
            start_pos = np.array(load.position[0], dtype=float)
            end_pos = np.array(load.position[1], dtype=float)
            
            # Calculate the length of the distributed load
            length = np.linalg.norm(end_pos - start_pos)
            if length == 0:
                continue # Skip zero-length loads
            
            # 'force' (from load.ve) is per unit length, so multiply by length for total force
            force *= length
            
            # The resultant force acts at the midpoint of the distributed load
            load_pos = (start_pos + end_pos) / 2.0
            
        else:
            print(f"Unknown load type: {type(load)}. Skipping.")
            continue

        b[0] -= force[0]  # -Fx
        b[1] -= force[1]  # -Fy

        # Moment arm r = (load_pos - pivot_pos)
        r = load_pos - pivot_pos
        # Moment from force: r_x*F_y - r_y*F_x
        # Plus any moment from the load itself
        b[2] -= (r[0] * force[1] - r[1] * force[0] + force[2])

    # 3. Solve the system for the unknown reaction magnitudes
    try:
        reaction_magnitudes = np.linalg.solve(A, b)
        
        results = {unknowns[i]["name"]: reaction_magnitudes[i] for i in range(len(unknowns))}
        print("Calculated Reaction Forces:")
        for name, value in results.items():
            print(f"  {name}: {value:.2f}")
        return results
    except np.linalg.LinAlgError:
        print("Error: The system is singular. Could not solve for reaction forces.")
        return None