import os
from pathlib import Path
from flask import Flask
from flask_cors import CORS

def create_app(content_dir=Path("content")):
    if os.environ.get("RUNNING_IN_DOCKER") == "true":
        base_dir = Path("/app")
    else:
        base_dir = Path(__file__).resolve().parent.parent.parent
    
    frontend_dist = base_dir / "frontend" / "dist" / "client"
    
    # Debug to be sure
    print(f"--- ENVIRONMENT: {'DOCKER' if os.environ.get('RUNNING_IN_DOCKER') else 'LOCAL'} ---")
    print(f"--- FRONTEND PATH: {frontend_dist} ---")
    print(f"--- PATH EXISTS: {frontend_dist.exists()} ---")

    app = Flask(__name__,
                template_folder=str(frontend_dist),     # Looks for index.html
                static_folder=str(frontend_dist)
                )                

    CORS(app)
    
    from src.state import AppState 
    app.app_state = AppState(content_dir=content_dir)
    app.app_state.load_state()
    
    # Register API blueprints
    #from src._api.register import register_blueprints
    #register_blueprints(app)
    from src.plugins.analyze.api import api
    from src.plugins.management.api import systems
    from src.plugins.generator.api import generation
    from src.plugins.models.api import models
    app.register_blueprint(api.bp)
    app.register_blueprint(systems.bp)
    app.register_blueprint(generation.bp)
    app.register_blueprint(models.bp)

    
    from flask import send_from_directory
    
    @app.route("/", defaults={'path': ''})
    @app.route("/<path:path>")
    def serve_react(path):
        if path.startswith("api/") or path.startswith("api"):
            return "API endpoint not found", 404
        
        if path != "" and (frontend_dist / path).exists():
            return send_from_directory(frontend_dist, path)
        
        return send_from_directory(frontend_dist, "index.html")

    print("--- REGISTERED ROUTES ---")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule}")
    print("-------------------------")


    return app
