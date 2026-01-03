import threading
import pandas as pd
from pathlib import Path
from flask import Blueprint, request, jsonify
from ultralytics import YOLO
import shutil
import time
import requests

bp = Blueprint('models', __name__, url_prefix='/api/models')

_training_lock = threading.Lock()
_current_training = {
    "is_running": False,
    "model_name": None,
    "dataset_path": None,
    "progress": {},
    "start_time": None
}

# --- Directory Configuration ---
CONTENT_ROOT = Path("./content")
MODELS_ROOT = CONTENT_ROOT / "models"
WEIGHTS_ROOT = CONTENT_ROOT / "weights"

# Ensure directories exist
MODELS_ROOT.mkdir(parents=True, exist_ok=True)
WEIGHTS_ROOT.mkdir(parents=True, exist_ok=True)

class TrainingThread(threading.Thread):
    def __init__(self, dataset_path, model_name, epochs=50, imgsz=640):
        super().__init__()
        self.dataset_path = Path(dataset_path)
        self.model_name = model_name
        self.epochs = epochs
        self.imgsz = imgsz
        # Ultralytics saves to: project/name
        self.output_dir = MODELS_ROOT / model_name

    def _get_base_weights(self):
        """Ensures yolov8n.pt exists in content/weights/ to avoid root clutter"""
        weight_path = WEIGHTS_ROOT / "yolov8n.pt"
        if not weight_path.exists():
            print(f"Downloading base weights to {weight_path}...")
            # Download manually or let YOLO handle it, but moving it is safer
            # Simple manual download to ensure location:
            url = "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt"
            try:
                response = requests.get(url, stream=True)
                with open(weight_path, 'wb') as f:
                    shutil.copyfileobj(response.raw, f)
            except Exception as e:
                print(f"Failed to download weights manually, falling back to auto: {e}")
                return "yolov8n.pt" # Fallback to default behavior
        return str(weight_path)

    def run(self):
        global _current_training
        try:
            # 1. Get path to base weights (inside content/weights)
            base_weight_path = self._get_base_weights()

            # 2. Load model from that specific path
            model = YOLO(base_weight_path) 
            
            # 3. Start training
            # project=MODELS_ROOT ensures output goes to ./content/models/{model_name}
            results = model.train(
                data=str(self.dataset_path / "dataset.yaml"),
                epochs=self.epochs,
                imgsz=self.imgsz,
                project=str(MODELS_ROOT.absolute()), # Use absolute path to be safe
                name=self.model_name,
                exist_ok=True,
                device='cpu' # Change to '0' if you have CUDA
            )
        except Exception as e:
            print(f"Training Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            with _training_lock:
                _current_training["is_running"] = False

@bp.route("/train", methods=["POST"])
def start_training():
    global _current_training
    
    if _training_lock.locked() or _current_training["is_running"]:
        return jsonify({"error": "A training task is already in progress"}), 429

    data = request.get_json()
    dataset_path = data.get("dataset_path")
    model_name = data.get("model_name", f"model_{int(time.time())}")
    epochs = int(data.get("epochs", 10))

    if not dataset_path or not Path(dataset_path).exists():
        return jsonify({"error": "Invalid dataset path"}), 400

    _current_training = {
        "is_running": True,
        "model_name": model_name,
        "dataset_path": dataset_path,
        "start_time": time.time(),
        "progress": {}
    }

    thread = TrainingThread(dataset_path, model_name, epochs)
    thread.start()

    return jsonify({"success": True, "model_name": model_name})

@bp.route("/status", methods=["GET"])
def get_status():
    """Returns current training metrics by reading the results.csv"""
    if not _current_training["is_running"]:
        return jsonify({"is_running": False})

    # Path logic: ./content/models/{model_name}/results.csv
    model_dir = MODELS_ROOT / _current_training["model_name"]
    results_csv = model_dir / "results.csv"
    
    metrics = []
    if results_csv.exists():
        try:
            df = pd.read_csv(results_csv)
            # Clean column names (ultralytics adds spaces)
            df.columns = [c.strip() for c in df.columns]
            metrics = df.to_dict(orient="records")
        except Exception:
            pass

    return jsonify({
        **_current_training,
        "metrics": metrics
    })

@bp.route("/list", methods=["GET"])
def list_models():
    models = []
    # Loop through ./content/models
    if MODELS_ROOT.exists():
        for d in MODELS_ROOT.iterdir():
            # Check if it looks like a valid training run
            if d.is_dir() and (d / "weights" / "best.pt").exists():
                models.append({
                    "name": d.name,
                    "path": str(d),
                    "created": d.stat().st_mtime
                })
    
    # Sort by newest first
    models.sort(key=lambda x: x['created'], reverse=True)
    return jsonify(models)
