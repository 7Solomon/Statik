from flask import render_template, send_from_directory
from src.app import create_app
import os

app = create_app()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/static/templates/<path:filename>')
def serve_template(filename):
    """Serve HTML template fragments for the frontend"""
    template_dir = os.path.join(app.static_folder, 'templates')

    
    print(f"[DEBUG] Serving template: {template_dir}/{filename}")
    
    if not os.path.exists(os.path.join(template_dir, filename)):
        print(f"[ERROR] Template not found: {filename}")
        print(f"[DEBUG] Template dir exists: {os.path.exists(template_dir)}")
        if os.path.exists(template_dir):
            print(f"[DEBUG] Available files: {os.listdir(template_dir)}")
        return f"Template not found: {filename}", 404
    
    return send_from_directory(template_dir, filename)

if __name__ == '__main__':
    app.run(debug=True)
