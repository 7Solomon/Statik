from flask import Blueprint, jsonify, send_from_directory, request, current_app
from datetime import datetime

bp = Blueprint('dataset', __name__)


@bp.route('/api/images/<split>')
def get_images(split):
    """Get list of images for a split"""
    manager = current_app.app_state.get_dataset_manager()
    if manager is None:
        return jsonify({'error': 'No dataset generated yet'}), 404
    
    images = manager.get_image_list(split)
    return jsonify(images)


@bp.route('/api/labels/<split>/<stem>')
def get_labels(split, stem):
    """Get labels for a specific image"""
    manager = current_app.app_state.get_dataset_manager()
    if manager is None:
        return jsonify({'error': 'No dataset loaded'}), 404
    
    labels = manager.get_labels_for_image(stem, split)
    return jsonify(labels)


@bp.route('/api/colors')
def get_colors():
    """Get class colors"""
    manager = current_app.app_state.get_dataset_manager()
    if manager is None:
        return jsonify({})
    
    colors = manager.get_class_colors()
    return jsonify(colors)


@bp.route('/images/<split>/<path:filename>')
def serve_image(split, filename):
    """Serve image files"""
    app_state = current_app.app_state
    if not app_state.has_dataset():
        return "No dataset", 404
    
    image_dir = app_state.dataset_dir / split / 'images'
    return send_from_directory(image_dir, filename)


@bp.route('/api/datasets')
def list_datasets():
    """List all available datasets"""
    app_state = current_app.app_state
    datasets_dir = app_state.dataset_config.output_dir
    datasets = []
    
    if datasets_dir.exists():
        for dataset_dir in datasets_dir.iterdir():
            if dataset_dir.is_dir():
                yaml_file = dataset_dir / "dataset.yaml"
                if yaml_file.exists():
                    train_images_dir = dataset_dir / 'train' / 'images'
                    image_count = 0
                    if train_images_dir.exists():
                        image_count = len(list(train_images_dir.glob('*.jpg'))) + len(list(train_images_dir.glob('*.png')))
                    
                    created_timestamp = dataset_dir.stat().st_birthtime
                    created_str = datetime.fromtimestamp(created_timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    
                    datasets.append({
                        'name': dataset_dir.name,
                        'path': str(dataset_dir),
                        'created': created_str,
                        'images': image_count
                    })
    
    datasets.sort(key=lambda x: x['created'], reverse=True)
    return jsonify(datasets)


@bp.route('/api/datasets/<name>', methods=['DELETE'])
def delete_dataset(name):
    """Delete a dataset"""
    try:
        import shutil
        app_state = current_app.app_state
        dataset_path = app_state.dataset_config.output_dir / name
        if dataset_path.exists():
            shutil.rmtree(dataset_path)
            if app_state.dataset_dir == dataset_path:
                app_state.reset_dataset()
                app_state.save_state()
            return jsonify({'status': 'success'})
        return jsonify({'error': 'Dataset not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/datasets/<name>/load', methods=['POST'])
def load_dataset(name):
    """Load a specific dataset"""
    try:
        app_state = current_app.app_state
        dataset_path = app_state.dataset_config.output_dir / name
        if not dataset_path.exists():
            return jsonify({'error': 'Dataset not found'}), 404
        
        app_state.set_dataset_dir(dataset_path)
        app_state.save_state()
        return jsonify({'status': 'success', 'path': str(dataset_path)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500