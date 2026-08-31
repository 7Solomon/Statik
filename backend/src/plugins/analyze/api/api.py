
from src.plugins.analyze.langrage.core import analyze_lagrangian_dynamics
from src.plugins.analyze.fem import calculate_complex_fem
from src.plugins.analyze.simplify import prune_cantilevers
from flask import current_app, request, jsonify, Blueprint
from src.plugins.analyze.kinematics import analyse as analyse_kinematics
from src.models.analyze import StructuralSystem, KinematicResult
import numpy as np

import sys
import traceback


bp = Blueprint('analyze', __name__, url_prefix='/api/analyze')
@bp.route("/kinematics", methods=["POST"])
def analyze_system():
    payload = request.get_json(force=True)
    print(payload)
    try:
        system = StructuralSystem.create(
            payload.get("nodes", []), 
            payload.get("members", []),
            payload.get("loads", []),
            payload.get("scheiben", []),
            payload.get("constraints", [])
        )

        result = analyse_kinematics(system)

        # 5. Send Response
        return jsonify(result.to_dict()), 200

    except Exception as e:
        traceback.print_exc() 
        return jsonify({"error": str(e)}), 500

@bp.route("/simplify", methods=["POST"])
def simplify():
    payload = request.get_json(force=True)
    try:
        system = StructuralSystem.create(
            payload.get("nodes", []), 
            payload.get("members", []),
            payload.get("loads", []),
            payload.get("scheiben", []),
            payload.get("constraints", [])
        )
        simplified_system = prune_cantilevers(system)
        return jsonify(simplified_system.to_dict()), 200 
    except Exception as e:
        print(e)

@bp.route("/solution", methods=["POST"])
def solution():
    payload = request.get_json(force=True)
    try:
        system = StructuralSystem.create(
            payload.get("nodes", []), 
            payload.get("members", []),
            payload.get("loads", []),
            payload.get("scheiben", []),
            payload.get("constraints", [])

        )
        print(system)
        fem_solution_dict = calculate_complex_fem(system)
        print(fem_solution_dict)
        
        if not fem_solution_dict.get("success", False):
            error_message = fem_solution_dict.get("error", "Unknown calculation error")
            return jsonify({
                "success": False,
                "error": error_message
            }), 200 
        
        # Success case
        return jsonify(fem_solution_dict), 200
        
    except Exception as e:
        print(f"FEM Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 200

@bp.post("/dynamics")
def analyze_dynamics():
    try:
        payload = request.get_json(force=True)
        try:
            system = StructuralSystem.create(
                payload.get("nodes", []), 
                payload.get("members", []),
                payload.get("loads", []),
                payload.get("scheiben", []),
                payload.get("constraints", [])
            )
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Invalid system data: {str(e)}",
                "error_type": "ValidationError"
            }), 200

        
        result = analyze_lagrangian_dynamics(
            system=system,
            t_span=(0.0, 5.0),  # 5 seconds
            dt=0.02,            # 10ms timestep
        )
        
        # Check internal success flag if your analyzer returns one
        if not result.success:
            return jsonify(result.to_dict()), 200

        return jsonify(result.to_dict()), 200

    except Exception as e:
        print(f"Dynamic Analysis Error: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Calculation failed: {str(e)}",
            "error_type": "ServerError"
        }), 200
