from typing import List
from analyze.bool_checker import has_combined_xyM
from data.custome_class_definitions import Bearing, Joint, ProblemDefinition

def check_kinematics(system: set[str], problem: ProblemDefinition):
    """
    Checks the kinematic constraints of the problem.
    """
    bearings_per_system = []
    for node_id in system:
        reactions = problem.node(node_id).reactions
        bearings_per_system.extend(r for r in reactions if isinstance(r, Bearing))
    if has_combined_xyM(bearings_per_system):
        return True
    return False
    #print(f"System {system} has {bearings_per_system} bearings.")


def analyze_subsystems(problem: ProblemDefinition, systems: List[set[str]]):
    for system in systems:
        if check_kinematics(system, problem):
            print(f"System {system} is kinematically valid.")
        else:
            print(f"System {system} is not kinematically valid.")
