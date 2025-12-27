from pathlib import Path
from flask import Flask
from flask_cors import CORS

def create_app(content_dir=Path("content")):
    """Flask app factory"""
    
    base_dir = Path(__file__).parent.parent.parent
    frontend_dist = base_dir / "frontend" / "dist"

    app = Flask(__name__, 
                template_folder=str(frontend_dist),     # Looks for index.html
                static_folder=str(frontend_dist),       # Looks for assets/ here
                static_url_path='')                     # Serve assets at root URL (e.g. /assets/index.js)

    CORS(app)
    
    from src.state import AppState 
    app.app_state = AppState(content_dir=content_dir)
    app.app_state.load_state()
    
    # Register API blueprints
    #from src._api.register import register_blueprints
    #register_blueprints(app)
    from src.plugins.analyze.api import api
    app.register_blueprint(api.bp)

    
    from flask import send_from_directory
    
    @app.route("/", defaults={'path': ''})
    @app.route("/<path:path>")
    def serve_react(path):
        if path != "" and (frontend_dist / path).exists():
            return send_from_directory(frontend_dist, path)
        return send_from_directory(frontend_dist, "index.html")

    return app
