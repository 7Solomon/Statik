from flask import Blueprint, jsonify, request, current_app
import threading

from src.generator.generate import DatasetPipeline

bp = Blueprint('generation', __name__)


@bp.route('/api/generate', methods=['POST'])
def generate_dataset():
    """Start dataset generation in background thread"""
    app_state = current_app.app_state
    
    if app_state.generation_status['running']:
        return jsonify({'error': 'Generation already in progress'}), 400
    
    data = request.json
    num_samples = data.get('num_samples', 100)
    
    def generation_thread():
        try:
            app_state.generation_status['running'] = True
            app_state.generation_status['progress'] = 0
            app_state.generation_status['total'] = num_samples
            app_state.generation_status['message'] = 'Generating dataset...'
            
            pipeline = DatasetPipeline(app_state.dataset_config)
            pipeline.generate_dataset(num_samples)
            
            app_state.set_dataset_dir(app_state.dataset_config.output_dir)
            app_state.generation_status['progress'] = num_samples
            app_state.generation_status['message'] = 'Generation complete!'
            app_state.save_state()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            app_state.generation_status['message'] = f'Error: {str(e)}'
        finally:
            app_state.generation_status['running'] = False
    
    thread = threading.Thread(target=generation_thread, daemon=True)
    thread.start()
    
    return jsonify({'status': 'started'})


@bp.route('/api/status')
def get_status():
    """Get current generation status"""
    return jsonify(current_app.app_state.generation_status)


@bp.route('/api/state')
def get_app_state():
    """Get current application state"""
    return jsonify(current_app.app_state.get_info())