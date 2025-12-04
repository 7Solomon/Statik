def register_blueprints(app):
    """Register all route blueprints"""
    from . import generation, datasets, models, symbols
    
    app.register_blueprint(generation.bp)
    app.register_blueprint(datasets.bp)
    app.register_blueprint(models.bp)
    app.register_blueprint(symbols.bp)