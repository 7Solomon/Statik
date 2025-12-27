from datetime import datetime
import os
from flask import current_app, request, jsonify, Blueprint
from src.plugins.management.api import bp

@bp.route("/save", methods=["POST"])
def save_system():
    data = request.json
    
    name = data.get("name")
    system_data = data.get("system")
    
    if not name or not system_data:
        return jsonify({"error": "Name and system data are required"}), 400
    
    save_dir = os.path.join(name, current_app.app_state.system_save_dir)
    slug = save_system(name, system_data)
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

