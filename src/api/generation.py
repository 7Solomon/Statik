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
    num_samples = model.get('num_samples', 100)
    dataset_name = model.get('dataset_name', f'dataset_{num_samples}')
    
    def status_update(current, total, message):
        """Callback for pipeline to update status"""
        app_state.generation_status.update({
            'progress': current,
            'total': total,
            'message': message,
            'percentage': int((current / total) * 100) if total > 0 else 0
        })
    
    def generation_thread():
        try:
            app_state.generation_status.update({
                'running': True,
                'progress': 0,
                'total': num_samples,
                'message': 'Initializing generation...',
                'percentage': 0,
                'dataset_name': dataset_name
            })
            
            # Create pipeline with status callback
            pipeline = DatasetPipeline(app_state.dataset_config, status_callback=status_update)
            
            # Generate dataset
            output_dir = pipeline.generate_dataset(num_samples)
            
            # Set dataset directory in app state
            app_state.set_dataset_dir(output_dir)
            
            app_state.generation_status.update({
                'progress': num_samples,
                'message': f'Complete! Dataset saved to {dataset_name}',
                'percentage': 100
            })
            app_state.save_state()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            app_state.generation_status['message'] = f'Error: {str(e)}'
        finally:
            app_state.generation_status['running'] = False
    
    thread = threading.Thread(target=generation_thread, daemon=True)
    thread.start()
    
    return jsonify({'status': 'started', 'dataset_name': dataset_name})

@bp.route('/api/status')
def get_status():
    """Get current generation status"""
    return jsonify(current_app.app_state.generation_status)

@bp.route('/api/state')
def get_app_state():
    """Get current application state"""
    return jsonify(current_app.app_state.get_info())
