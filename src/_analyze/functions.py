import numpy as np
from typing import List 

from src.plugins.analyze.sub_systems import find_rigid_subsystems
from src.plugins.analyze.kinematics_sub import analyze_subsystems
from models._analyze_custome_class import Bearing, DistributedLoad, Joint, PointLoad, ProblemDefinition

def check_static_determinacy(problem: ProblemDefinition) -> int:
    """
    f = a + 3 * (c - n) - r
    """
    a = sum(len([_ for _ in node.reactions if isinstance(_, Bearing)]) for node in problem.nodes)
    c, n = len(problem.connections), len(problem.nodes)
    r = 14 # NI
    #r=2

    f = a + 3 * (c - n) - r
    return f



def split_in_base_systems(problem: ProblemDefinition):
    """
    Splits the problem into base systems for easier analysis.
    """
    systems = find_rigid_subsystems(problem)
    analyze_subsystems(problem, systems)
