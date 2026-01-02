from flask import Blueprint, request, jsonify, current_app

bp = Blueprint('systems_management', __name__, url_prefix='/api/systems_management')

@bp.route("/save", methods=["POST"])
def save_system():
    data = request.json
    name = data.get("name")
    system_data = data.get("system")
    
    if not name or not system_data:
        return jsonify({"error": "Name and system data are required"}), 400
    
    try:
        # Call the manager on app_state
        manager = current_app.app_state.system_manager
        slug = manager.save_system(name, system_data)
        
        return jsonify({
            "message": "Saved successfully", 
            "slug": slug
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/list", methods=["GET"])
def list_systems():
    # Returns: [{"name": "Beam 1", "slug": "beam-1", "saved_at": "..."}...]
    manager = current_app.app_state.system_manager
    systems = manager.list_systems()
    return jsonify(systems)


@bp.route("/load/<slug>", methods=["GET"]) 
def load_system(slug): 
    manager = current_app.app_state.system_manager
    system_data = manager.load_system(slug)
    
    if system_data:
        return jsonify(system_data)
        
    return jsonify({"error": "Not found"}), 404


@bp.route("/delete/<slug>", methods=["DELETE"])
def delete_system(slug):
    manager = current_app.app_state.system_manager
    success = manager.delete_system(slug)
    
    if success:
        return jsonify({"message": "Deleted successfully"}), 200
        
    return jsonify({"error": "System not found"}), 404
