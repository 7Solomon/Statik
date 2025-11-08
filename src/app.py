from flask import Flask
from flask_cors import CORS
from pathlib import Path

from state import AppState


def create_app(content_dir=Path("content")):
    """Flask app factory"""
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    CORS(app)
    
    # Initialize app state
    app.app_state = AppState(content_dir=content_dir)
    app.app_state.load_state()
    
    # Register blueprints
    from src.api.routes import register_routes
    register_routes(app)
    
    return app