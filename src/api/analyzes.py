from flask import request, jsonify, Blueprint
from src.analyze.kinematics import solve_kinematics
from src.analyze.system import calculate_poles, group_into_subsystems
from models.analyze_models import Node, Member, StructuralSystem, KinematicResult
import numpy as np


bp = Blueprint('analyze', __name__, url_prefix='/analyze')


@bp.route("/system", methods=["POST"])
def analyze_system():
    payload = request.get_json(force=True)
    try:
        system = StructuralSystem.create(
            payload.get("nodes", []), 
            payload.get("members", [])
        )
        
        node_velocities, dof = solve_kinematics(system)
        poles, trans_dirs = calculate_poles(system, node_velocities)
        rigid_bodies = group_into_subsystems(poles, trans_dirs)
        
        result = KinematicResult(
            is_kinematic=(dof > 0),
            dof=dof,
            node_velocities=node_velocities,
            member_poles=poles,
            rigid_bodies=rigid_bodies
        )
        
        response = result.to_dict()
        response["system"] = {
            "nodes": payload.get("nodes", []),
            "members": payload.get("members", []),
            "gridSize": payload.get("gridSize", 1.0)
        }
        print(response)
        return jsonify(response), 200

    except ValueError as e:
        print(e)
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(e)
        return jsonify({"error": "Internal Analysis Error", "details": str(e)}), 500
