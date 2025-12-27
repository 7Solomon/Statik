from flask import Blueprint, jsonify, send_from_directory, request, current_app
from datetime import datetime
from pathlib import Path

bp = Blueprint('dataset', __name__)

@bp.route('/api/datasets')
def list_datasets():
    """List all available datasets"""
    app_state = current_app.app_state
    
    # Check both potential dataset locations
    datasets_dirs = [
        app_state.dataset_config.output_dir,
        Path('data/datasets'),  # Common alternative
        Path('datasets')
    ]
    
    datasets = []
    seen_names = set()
    
    for datasets_dir in datasets_dirs:
        if not datasets_dir.exists():
            continue
            
        for dataset_dir in datasets_dir.iterdir():
            if not dataset_dir.is_dir() or dataset_dir.name in seen_names:
                continue
            
            # Check if it's a valid YOLO dataset
            yaml_file = dataset_dir / "dataset.yaml"
            train_dir = dataset_dir / 'train' / 'images'
            
            if yaml_file.exists() or train_dir.exists():
                seen_names.add(dataset_dir.name)
                
                # Count images
                image_count = 0
                for split in ['train', 'val', 'test']:
                    images_dir = dataset_dir / split / 'images'
                    if images_dir.exists():
                        image_count += len(list(images_dir.glob('*.jpg'))) + \
                                     len(list(images_dir.glob('*.png')))
                
                # Get creation time (handle different OS)
                try:
                    created_timestamp = dataset_dir.stat().st_birthtime
                except AttributeError:
                    created_timestamp = dataset_dir.stat().st_ctime
                
                created_str = datetime.fromtimestamp(created_timestamp).strftime('%Y-%m-%d %H:%M:%S')
                
                datasets.append({
                    'name': dataset_dir.name,
                    'path': str(dataset_dir),
                    'created': created_str,
                    'images': image_count,
                    'splits': {
                        'train': len(list((dataset_dir / 'train' / 'images').glob('*'))) if (dataset_dir / 'train' / 'images').exists() else 0,
                        'val': len(list((dataset_dir / 'val' / 'images').glob('*'))) if (dataset_dir / 'val' / 'images').exists() else 0,
                        'test': len(list((dataset_dir / 'test' / 'images').glob('*'))) if (dataset_dir / 'test' / 'images').exists() else 0,
                    }
                })
    
    datasets.sort(key=lambda x: x['created'], reverse=True)
    return jsonify(datasets)

@bp.route('/api/datasets/<name>', methods=['DELETE'])
def delete_dataset(name):
    """Delete a dataset"""
    try:
        import shutil
        app_state = current_app.app_state
        
        # Search in multiple locations
        for base_dir in [app_state.dataset_config.output_dir, Path('data/datasets'), Path('datasets')]:
            dataset_path = base_dir / name
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
        
        # Search in multiple locations
        for base_dir in [app_state.dataset_config.output_dir, Path('data/datasets'), Path('datasets')]:
            dataset_path = base_dir / name
            if dataset_path.exists():
                app_state.set_dataset_dir(dataset_path)
                app_state.save_state()
                return jsonify({'status': 'success', 'path': str(dataset_path)})
        
        return jsonify({'error': 'Dataset not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Keep your existing routes for images, labels, colors, etc.
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

@bp.route('/images/<split>/<filename>')
def serve_image(split, filename):
    """Serve image files"""
    app_state = current_app.app_state
    if not app_state.has_dataset():
        return "No dataset", 404
    image_dir = app_state.dataset_dir / split / 'images'
    return send_from_directory(image_dir, filename)
