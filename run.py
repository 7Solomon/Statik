from flask import Flask, render_template, jsonify, send_from_directory, request
from pathlib import Path
import threading
from src.generator.generate import DatasetPipeline, DatasetConfig
from src.generator.yolo import YOLODatasetManager

app = Flask(__name__)
app.config['DATASET_DIR'] = None
app.config['GENERATION_STATUS'] = {
    'running': False,
    'progress': 0,
    'total': 0,
    'message': 'Ready to generate'
}

dataset_manager = None

@app.route('/')
def index():
    """Main page with generation and visualization"""
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate_dataset():
    """Start dataset generation in background thread"""
    global dataset_manager
    
    if app.config['GENERATION_STATUS']['running']:
        return jsonify({'error': 'Generation already in progress'}), 400
    
    data = request.json
    num_samples = data.get('num_samples', 100)
    
    def generation_thread():
        try:
            app.config['GENERATION_STATUS']['running'] = True
            app.config['GENERATION_STATUS']['progress'] = 0
            app.config['GENERATION_STATUS']['total'] = num_samples
            app.config['GENERATION_STATUS']['message'] = 'Generating dataset...'
            
            config = DatasetConfig()
            pipeline = DatasetPipeline(config)
            pipeline.generate_dataset(num_samples=num_samples)
            
            app.config['DATASET_DIR'] = str(config.output_dir)
            app.config['GENERATION_STATUS']['message'] = 'Generation complete!'
            
            # Initialize dataset manager for visualization
            dataset_manager = YOLODatasetManager(config)
            
        except Exception as e:
            app.config['GENERATION_STATUS']['message'] = f'Error: {str(e)}'
        finally:
            app.config['GENERATION_STATUS']['running'] = False
    
    thread = threading.Thread(target=generation_thread, daemon=True)
    thread.start()
    
    return jsonify({'status': 'started'})

@app.route('/api/status')
def get_status():
    """Get current generation status"""
    return jsonify(app.config['GENERATION_STATUS'])

@app.route('/api/images/<split>')
def get_images(split):
    """Get list of images for a split"""
    global dataset_manager
    
    if not app.config['DATASET_DIR']:
        return jsonify({'error': 'No dataset generated yet'}), 404
    
    if dataset_manager is None:
        config = DatasetConfig()
        config.output_dir = app.config['DATASET_DIR']
        dataset_manager = YOLODatasetManager(config)
    
    images = dataset_manager.get_image_list(split)
    return jsonify(images)

@app.route('/api/labels/<split>/<stem>')
def get_labels(split, stem):
    """Get labels for a specific image"""
    global dataset_manager
    
    if dataset_manager is None:
        return jsonify({'error': 'No dataset loaded'}), 404
    
    labels = dataset_manager.get_labels_for_image(stem, split)
    return jsonify(labels)

@app.route('/api/colors')
def get_colors():
    """Get class colors"""
    global dataset_manager
    
    if dataset_manager is None:
        return jsonify({})
    
    colors = dataset_manager.get_class_colors()
    return jsonify(colors)

@app.route('/images/<split>/<path:filename>')
def serve_image(split, filename):
    """Serve image files"""
    if not app.config['DATASET_DIR']:
        return "No dataset", 404
    
    image_dir = Path(app.config['DATASET_DIR']) / split / 'images'
    return send_from_directory(image_dir, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
