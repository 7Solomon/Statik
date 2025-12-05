from typing import List

from src.plugins.analyze.bool_checker import has_combined_xyM
from models._analyze_custome_class import Bearing, Joint, ProblemDefinition, SubSystem

def check_kinematics(system: SubSystem, problem: ProblemDefinition):
    """
    Checks the kinematic constraints of the problem.
    """
    bearings_per_system = []
    for node_id in system.nodes:
        node = problem.node(node_id)
        reactions = node.reactions

        bearings = [_ for _ in reactions if isinstance(_, Bearing)]
        joints = [_ for _ in reactions if isinstance(_, Joint)]
        system.bearings.append(bearings)
        system.joints.append(joints)

        bearings_per_system.extend((r, node.position) for r in bearings)
    #print(f"bearings_per_system: {bearings_per_system}")
    xym_info = has_combined_xyM(bearings_per_system)
    return xym_info


def analyze_subsystems(problem: ProblemDefinition, systems: List[SubSystem]):
    for system in systems:
        system.isNotKinematic = not check_kinematics(system, problem)
        print(f"System {system.id} isNotKinematic: {system.isNotKinematic}")
    
