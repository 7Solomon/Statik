import base64
import shutil
import threading
import traceback

import yaml
from src.plugins.generator.generate import DatasetPipeline
from src.plugins.generator.config import DatasetConfig

from flask import Blueprint, request, jsonify, current_app, send_file, abort
import os
from pathlib import Path
from typing import Dict, Any, Optional

import sys

bp = Blueprint('generation', __name__, url_prefix='/api/generation')

_pipeline_cache: Dict[str, Any] = {}
_generation_lock = threading.Lock()


def get_pipeline(datasets_dir: str, config_path: Optional[str]) -> 'DatasetPipeline':
    """Get cached or create new DatasetPipeline."""
    cache_key = f"{datasets_dir}:{config_path or 'default'}"
    
    if cache_key not in _pipeline_cache:
        if config_path and Path(config_path).exists():
            config = DatasetConfig.from_yaml(config_path)
        else:
            config = DatasetConfig()
        
        # Initialize pipeline
        pipeline = DatasetPipeline(datasets_dir=Path(datasets_dir), config=config)
        _pipeline_cache[cache_key] = pipeline
    
    return _pipeline_cache[cache_key]

@bp.route("/yolo_dataset", methods=["POST"])
def gen_yolo_dataset():
    """Generate YOLO dataset with Locking."""
    
    # 2. CHECK LOCK
    if _generation_lock.locked():
        return jsonify({
            "error": "A generation task is already in progress. Please wait."
        }), 429

    # Acquire lock (non-blocking check done above, but safe context manager here)
    with _generation_lock:
        try:
            data = request.get_json()
            num_samples = data.get("num_samples", 1000)
            datasets_dir = data.get("datasets_dir", "./content/datasets")
            config_path = data.get("config_path")
            
            datasets_path = Path(datasets_dir)
            datasets_path.mkdir(parents=True, exist_ok=True)

            # Get Pipeline
            pipeline = get_pipeline(str(datasets_dir), config_path)

            sys.stdout.write(f"[GENERATION] Starting {num_samples} samples...\n")
            sys.stdout.flush()

    
            output_dir = pipeline.generate_dataset(num_samples)
            
            # Verify output_dir exists (fallback logic)
            if not output_dir or not Path(output_dir).exists():
                # Fallback: try to find the most recently created folder
                all_subdirs = [d for d in datasets_path.iterdir() if d.is_dir()]
                if all_subdirs:
                    output_dir = max(all_subdirs, key=os.path.getmtime)
                else:
                    raise Exception("Output directory could not be determined")

            output_dir = Path(output_dir)

            # Calculate stats for response
            train_size = int(num_samples * pipeline.config.train_ratio)
            val_size = int(num_samples * pipeline.config.val_ratio)
            test_size = num_samples - train_size - val_size

            sys.stdout.write(f"[SUCCESS] Finished: {output_dir}\n")
            sys.stdout.flush()

            return jsonify({
                "success": True,
                "dataset_path": str(output_dir),
                "dataset_yaml": str(output_dir / "dataset.yaml"),
                "num_samples": num_samples,
                "splits": {"train": train_size, "val": val_size, "test": test_size},
                "classes": pipeline.config.classes
            })

        except Exception as e:
            sys.stderr.write(f"[ERROR] {str(e)}\n")
            sys.stderr.write(traceback.format_exc())
            sys.stderr.flush()
            return jsonify({"error": str(e)}), 500
        

@bp.route("/dataset/delete", methods=["POST"])
def delete_dataset():
    """Delete a dataset folder."""
    try:
        data = request.get_json()
        dataset_path = Path(data.get('dataset_path', ''))
        
        base_dir = Path("./content/datasets").resolve()
        target_path = dataset_path.resolve()

        if not str(target_path).startswith(str(base_dir)):
            pass 

        if not target_path.exists():
            return jsonify({"error": "Dataset not found"}), 404

        # 3. Check if it looks like a dataset (safety)
        if not (target_path / "dataset.yaml").exists():
             return jsonify({"error": "Invalid dataset folder (missing dataset.yaml)"}), 400

        # 4. Delete Recursively
        shutil.rmtree(target_path)
        
        return jsonify({"success": True, "message": f"Deleted {target_path.name}"})

    except Exception as e:
        sys.stderr.write(f"[DELETE ERROR] {e}\n")
        return jsonify({"error": str(e)}), 500

@bp.route("/preview_symbols", methods=["POST"])
def preview_symbols():
    """Preview symbol galleries."""
    if _generation_lock.locked():
         return jsonify({"error": "Cannot preview while generating."}), 429
         
    try:
        data = request.get_json()
        pipeline = get_pipeline(data.get("datasets_dir", "./content/datasets"), data.get("config_path"))
        pipeline.preview_symbols()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@bp.route("/list_datasets", methods=["GET"])
def list_datasets():
    """List ALL valid datasets."""
    datasets_dir = request.args.get("datasets_dir", "./content/datasets")
    datasets_path = Path(datasets_dir)
    sys.stderr.write(f"{datasets_path}\n")
    
    datasets = []
    if datasets_path.exists():
        for d in datasets_path.iterdir():
            if d.is_dir() and (d / "dataset.yaml").exists():
                datasets.append({
                    "path": str(d),
                    "yaml": str(d / "dataset.yaml"),
                    "created": d.stat().st_mtime,
                    "name": d.name 
                })
    
    datasets.sort(key=lambda x: x['created'], reverse=True)
    
    print(f"[LIST] Found {len(datasets)} datasets: {[d['name'] for d in datasets]}")
    return jsonify({"datasets": datasets, "total": len(datasets)})



@bp.route("/clear_cache", methods=["POST"])
def clear_pipeline_cache():
    """Clear cached pipelines (for config changes)."""
    global _pipeline_cache
    old_len = len(_pipeline_cache)
    _pipeline_cache.clear()
    return jsonify({
        "success": True,
        "cleared": old_len,
        "remaining": 0
    })





##### VIS GENERATION
@bp.route("/dataset/info", methods=["POST"])
def dataset_info():
    """Get dataset metadata."""
    try:
        data = request.get_json()
        dataset_path = Path(data['dataset_path'])
        yaml_path = dataset_path / "dataset.yaml"
        
        if not yaml_path.exists():
            return jsonify({"error": "dataset.yaml not found"}), 404
        
        with open(yaml_path, 'r') as f:
            data_yaml = yaml.safe_load(f)
        
        return jsonify({
            "path": str(dataset_path),
            "classes": data_yaml.get("names", []),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.route("/dataset/images", methods=["POST"])
def dataset_images():
    """Get image list."""
    try:
        data = request.get_json()
        dataset_path = Path(data['dataset_path'])
        split = data['split']
        
        images_dir = dataset_path / split / "images"
        if not images_dir.exists():
            return jsonify([])
        
        img_paths = sorted([
            p for p in images_dir.glob("*") 
            if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
        ])
        
        return jsonify([
            {"index": i, "filename": p.name, "stem": p.stem}
            for i, p in enumerate(img_paths)
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
@bp.route("/dataset/labels_batch", methods=["POST"])
def dataset_labels_batch():
    """
    Get labels for multiple images in one request to reduce server log spam.
    Expects JSON: { "dataset_path": str, "split": str, "stems": [str] }
    """
    try:
        data = request.get_json()
        dataset_path = Path(data.get('dataset_path', ''))
        split = data.get('split', 'train')
        stems = data.get('stems', [])  # List of IDs e.g. ["train_0", "train_1"]
        
        # 1. Load class names once
        yaml_path = dataset_path / "dataset.yaml"
        classes = []
        if yaml_path.exists():
            try:
                with open(yaml_path, 'r') as f:
                    data_yaml = yaml.safe_load(f)
                    classes = data_yaml.get("names", [])
            except Exception:
                pass # Fallback to empty classes if yaml is broken

        results = {}
        
        # 2. Iterate through all requested stems
        labels_dir = dataset_path / split / "labels"
        
        for stem in stems:
            label_path = labels_dir / f"{stem}.txt"
            
            # Default to empty list if no label file exists
            if not label_path.exists():
                results[stem] = []
                continue
                
            file_labels = []
            try:
                with open(label_path, "r") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) != 5: continue
                        
                        # Parse YOLO format: class_id cx cy w h
                        class_id = int(float(parts[0]))
                        cx, cy, w, h = map(float, parts[1:])
                        
                        # Resolve class name
                        if 0 <= class_id < len(classes):
                            class_name = classes[class_id]
                        else:
                            class_name = f"class_{class_id}"
                            
                        file_labels.append({
                            "class_id": class_id, 
                            "class_name": class_name, 
                            "cx": cx, "cy": cy, "w": w, "h": h
                        })
            except Exception:
                pass # Skip malformed files
                
            results[stem] = file_labels

        return jsonify(results)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@bp.route("/dataset/images_batch", methods=["POST"])
def dataset_images_batch():
    """
    Get multiple images as Base64 strings in one request.
    Expects JSON: { "dataset_path": str, "split": str, "filenames": [str] }
    """
    try:
        data = request.get_json()
        dataset_path = Path(data.get('dataset_path', ''))
        split = data.get('split', 'train')
        filenames = data.get('filenames', []) # List of files e.g. ["train_0.jpg", "train_1.jpg"]

        images_dir = dataset_path / split / "images"
        results = {}

        for filename in filenames:
            image_path = images_dir / filename
            
            if image_path.exists():
                try:
                    # Read binary and encode to base64
                    with open(image_path, "rb") as img_file:
                        encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
                        
                    # Return standard Data URI scheme
                    mime_type = "image/png" if filename.lower().endswith('.png') else "image/jpeg"
                    results[filename] = f"data:{mime_type};base64,{encoded_string}"
                except Exception as e:
                    results[filename] = None # Error reading specific file
            else:
                results[filename] = None # File not found

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 400
