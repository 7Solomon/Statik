from flask import current_app, request, jsonify, Blueprint
from src.plugins.analyze.kinematics import solve_kinematics
from src.plugins.analyze.system import calculate_poles, group_into_subsystems
from src.models.analyze_models import KinematicMode, Node, Member, StructuralSystem, KinematicResult
import numpy as np

import sys
import traceback


bp = Blueprint('analyze', __name__, url_prefix='/analyze')
@bp.route("/kinematics", methods=["POST"])
def analyze_system():
    payload = request.get_json(force=True)
    print(payload)
    try:
        system = StructuralSystem.create(
            payload.get("nodes", []), 
            payload.get("members", []),
            []
            #payload.get("loads", [])
        )

        modes_objects, dof = solve_kinematics(system) 
        
        for mode in modes_objects:
            poles, trans_dirs = calculate_poles(system, mode.node_velocities)
            
            rigid_bodies = group_into_subsystems(poles, trans_dirs)
            
            # Update the existing mode object
            mode.member_poles = poles
            mode.rigid_bodies = rigid_bodies
        
        # 4. Create Result
        result = KinematicResult(
            is_kinematic=(dof > 0),
            dof=dof,
            system=system,
            modes=modes_objects # These are now fully populated
        )

        # 5. Send Response
        return jsonify(result.to_dict()), 200

    except Exception as e:
        traceback.print_exc() 
        return jsonify({"error": str(e)}), 500
