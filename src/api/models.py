from flask import Blueprint, jsonify, request, current_app
from datetime import datetime
import threading

bp = Blueprint('models', __name__)


@bp.route('/api/models')
def list_models():
    """List all available models"""
    app_state = current_app.app_state
    models = []
    runs = app_state.vision_config.list_runs()
    
    for run in runs:
        best_model = app_state.vision_config.get_best_model_path(run)
        if best_model.exists():
            created_timestamp = best_model.stat().st_ctime
            created_str = datetime.fromtimestamp(created_timestamp).strftime('%Y-%m-%d %H:%M:%S')
            
            models.append({
                'name': f"model_{run}",
                'run_name': run,
                'path': str(best_model),
                'created': created_str
            })
    
    models.sort(key=lambda x: x['created'], reverse=True)
    return jsonify(models)


@bp.route('/api/models/<run_name>', methods=['DELETE'])
def delete_model(run_name):
    """Delete a model run"""
    try:
        import shutil
        app_state = current_app.app_state
        run_path = app_state.vision_config.runs_dir / run_name
        if run_path.exists():
            shutil.rmtree(run_path)
            model_path = app_state.vision_config.get_best_model_path(run_name)
            if app_state.trained_model_path == model_path:
                app_state.reset_model()
                app_state.save_state()
            return jsonify({'status': 'success'})
        return jsonify({'error': 'Model not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/train', methods=['POST'])
def train_model():
    """Train a YOLO model on a dataset"""
    app_state = current_app.app_state
    
    if app_state.training_status.get('running', False):
        return jsonify({'error': 'Training already in progress'}), 400
    
    data = request.json
    dataset_name = data.get('dataset_name')
    epochs = data.get('epochs', 50)
    batch_size = data.get('batch_size', 16)
    learning_rate = data.get('learning_rate', 0.01)
    base_model = data.get('base_model', 'yolov8n.pt')
    patience = data.get('patience', 50)
    image_size = data.get('image_size', 640)
    
    if not dataset_name:
        return jsonify({'error': 'dataset_name is required'}), 400
    
    # Verify dataset exists
    dataset_path = app_state.dataset_config.output_dir / dataset_name
    if not dataset_path.exists():
        return jsonify({'error': f'Dataset {dataset_name} not found'}), 404
    
    def training_thread():
        try:
            from src.vision.trainer import YOLOTrainer
            
            app_state.training_status = {
                'running': True,
                'progress': 0,
                'total': epochs,
                'message': 'Initializing training...',
                'current_epoch': 0
            }
            
            # Create trainer with dataset path
            trainer = YOLOTrainer(app_state.dataset_config, model_path=base_model)
            
            # Override dataset path for this training
            app_state.vision_config.output_dir = dataset_path
            
            # Train the model
            results = trainer.train(
                dataset_path=dataset_path,
                epochs=epochs,
                batch_size=batch_size,
                learning_rate=learning_rate,
                patience=patience,
                project=str(app_state.vision_config.runs_dir),
                name=f'train_{dataset_name}'
            )
            
            # Update state with new model
            best_model_path = app_state.vision_config.get_best_model_path(f'train_{dataset_name}')
            app_state.set_trained_model(best_model_path)
            app_state.training_status['message'] = 'Training complete!'
            app_state.save_state()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            app_state.training_status['message'] = f'Error: {str(e)}'
        finally:
            app_state.training_status['running'] = False
    
    thread = threading.Thread(target=training_thread, daemon=True)
    thread.start()
    
    return jsonify({'status': 'started'})


@bp.route('/api/train/status')
def get_training_status():
    """Get current training status"""
    return jsonify(current_app.app_state.training_status)