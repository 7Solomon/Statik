from datetime import datetime
from flask import current_app, request, jsonify, Blueprint
from src.plugins.analyze.kinematics import solve_kinematics
from src.plugins.analyze.system import calculate_poles, group_into_subsystems
from models.analyze_models import Node, Member, StructuralSystem, KinematicResult
import numpy as np


bp = Blueprint('analyze', __name__, url_prefix='/analyze')

@bp.route("/system", methods=["POST"])
def analyze_system():
    payload = request.get_json(force=True)
    try:
        system = StructuralSystem.create(
            payload.get("nodes", []), 
            payload.get("members", []),
            payload.get("loads", [])
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
            "loads": payload.get("loads", []),
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


@bp.route("/save", methods=["POST"])
def save_system():
    data = request.json
    
    name = data.get("name")
    system_data = data.get("system")
    
    if not name or not system_data:
        return jsonify({"error": "Name and system data are required"}), 400
        
    slug = current_app.app_state.system_config.save_system(name, system_data)
    return jsonify({"message": "Saved successfully", "slug": slug}), 201

@bp.route("/list", methods=["GET"])
def list_systems():
    """
        [{"name": name, "slug": slug, "saved_at": date}...]
    """
    return current_app.app_state.system_config.list_systems()

@bp.route("/load/<slug>", methods=["GET"]) 
def load_system(slug): 
    data = current_app.app_state.system_config.load_system(slug)
    print(data)
    if data:
        return jsonify(data)
    return jsonify({"error": "Not found"}), 404

@bp.route("/delete/<slug>", methods=["DELETE"])  # Use DELETE method for REST compliance
def delete_system(slug):
    success = current_app.app_state.system_config.delete_system(slug)
    if success:
        return jsonify({"message": "Deleted successfully"}), 200
    return jsonify({"error": "System not found"}), 404

