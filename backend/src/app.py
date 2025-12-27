from pathlib import Path
from flask import Flask
from flask_cors import CORS

def create_app(content_dir=Path("content")):
    """Flask app factory"""
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    CORS(app)
    
    # Initialize app state
    from src.state import AppState  # adjust import as needed
    app.app_state = AppState(content_dir=content_dir)
    app.app_state.load_state()
    
    # Register API blueprints
    from src.api.register import register_blueprints
    register_blueprints(app)
    
    return app
