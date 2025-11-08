from flask import Blueprint

def register_routes(app):
    """Register all route blueprints"""
    from . import generation, dataset, models
    
    app.register_blueprint(generation.bp)
    app.register_blueprint(dataset.bp)
    app.register_blueprint(models.bp)