import threading
import pandas as pd
from pathlib import Path
from flask import Blueprint, request, jsonify
#from ultralytics import YOLO
import shutil
import time

raise NotImplementedError("JUST FOR TESTS")
bp = Blueprint('models', __name__, url_prefix='/models')

_training_lock = threading.Lock()
_current_training = {
    "is_running": False,
    "model_name": None,
    "dataset_path": None,
    "progress": {},
    "start_time": None
}

MODELS_ROOT = Path("./content/models")
MODELS_ROOT.mkdir(parents=True, exist_ok=True)

class TrainingThread(threading.Thread):
    def __init__(self, dataset_path, model_name, epochs=50, imgsz=640):
        super().__init__()
        self.dataset_path = Path(dataset_path)
        self.model_name = model_name
        self.epochs = epochs
        self.imgsz = imgsz
        self.output_dir = MODELS_ROOT / model_name

    def run(self):
        global _current_training
        try:
            # Load a base model (e.g., YOLOv8n)
            model = YOLO("yolov8n.pt") 
            
            # Start training
            # Note: project/name determines where results are saved
            results = model.train(
                data=str(self.dataset_path / "dataset.yaml"),
                epochs=self.epochs,
                imgsz=self.imgsz,
                project=str(MODELS_ROOT),
                name=self.model_name,
                exist_ok=True,
                device='cpu' # Change to '0' if you have CUDA
            )
        except Exception as e:
            print(f"Training Error: {e}")
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
    for d in MODELS_ROOT.iterdir():
        if d.is_dir() and (d / "weights" / "best.pt").exists():
            models.append({
                "name": d.name,
                "path": str(d),
                "created": d.stat().st_mtime
            })
    return jsonify(models)