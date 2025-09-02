from analyze.sub_systems import find_rigid_subsystems
from analyze.yikes import analyze_subsystems
from data.custome_class_definitions import Bearing, DistributedLoad, Joint, PointLoad, ProblemDefinition
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
    r = 14 # NI
    #r=2
    #print(f"Static indeterminacy check: a = {a}, c = {c}, n = {n}, r = {r}")
    # Degree of static indeterminacy
    f = a + 3 * (c - n) - r

    #if f == 0:
    #    print(f"Statically determinate (f = {f}). The system can be calculated.")
    #elif f > 0:
    #    print(f"Statically indeterminate (f = {f}). Cannot be solved with equilibrium equations alone.")
    #else: # f < 0
    #    print(f"Unstable/Kinematic (f = {f}). The system is not in equilibrium.")

    return f



def split_in_base_systems(problem: ProblemDefinition):
    """
    Splits the problem into base systems for easier analysis.
    """
    systems = find_rigid_subsystems(problem)
    analyze_subsystems(problem, systems)
