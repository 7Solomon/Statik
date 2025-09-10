from ultralytics import YOLO
from pathlib import Path
import yaml

class YOLOTrainer:
    def __init__(self, config, model_path: str = 'yolov8n.pt'):
        self.config = config
        self.model = YOLO(model_path)
        
    def train(self, 
            epochs: int = 50,
            batch_size: int = 16,
            learning_rate: float = 0.01,
            patience: int = 50,
            project: str = None,
            name: str = 'structural_detection'):

        # Verify dataset exists
        dataset_path = Path(self.config.output_dir)
        data_yaml = dataset_path / "dataset.yaml"
        if not data_yaml.exists():
            raise FileNotFoundError(f"Dataset YAML not found: {data_yaml}")

        if project is None:
            project = str(dataset_path.parent / "runs" / "detect")

        train_params = {
            "data": str(data_yaml),
            "epochs": epochs,
            "imgsz": self.config.image_size[0],
            "batch": batch_size,
            "lr0": learning_rate,
            "project": project,
            "name": name,
            "device": "cpu",
            "workers": 8,
            "patience": patience,
            "save": True,
            "plots": True,
            "verbose": True,
        }

        print(f"Starting training with parameters:")
        print(f"  - Image size: {self.config.image_size}")
        print(f"  - Classes: {self.config.classes}")
        print(f"  - Dataset: {self.config.output_dir}")
        print(f"  - Epochs: {epochs}")
        print(f"  - Batch size: {batch_size}")

        results = self.model.train(**train_params)
        print(f"Training completed! Best model saved to: {results.save_dir}")
        return results

    def validate(self, model_path: str = None):
        """Validate trained model"""
        if model_path is None:
            model_path = f"{self.config.output_dir}/../runs/structural_detection/weights/best.pt"
        
        if not Path(model_path).exists():
            print(f"Model not found at {model_path}")
            return None
            
        model = YOLO(model_path)
        data_yaml = self.prepare_data_yaml()
        
        results = model.val(
            data=data_yaml,
            imgsz=self.config.image_size[0],
            batch=16,
            save_json=True,
            save_hybrid=True,
            conf=0.001,
            iou=0.6,
            max_det=300,
            half=False,
            device='cpu',
            dnn=False,
            plots=True,
            rect=False,
            split='val'
        )
        
        return results
    
    def predict(self, source: str, model_path: str = None, save_results: bool = True):
        """Run inference with trained model"""
        if model_path is None:
            model_path = f"{self.config.output_dir}/../runs/detect/structural_detection/weights/best.pt"
        
        if not Path(model_path).exists():
            print(f"Model not found at {model_path}")
            return None
            
        model = YOLO(model_path)
        
        results = model.predict(
            source=source,
            imgsz=self.config.image_size[0],
            conf=0.25,
            iou=0.45,
            max_det=1000,
            half=False,
            device='cpu',
            save=save_results,
            save_txt=True,
            save_conf=True,
            save_crop=False,
            show=False,
            verbose=True
        )
        
        return results
    
    def export_model(self, model_path: str = None, formats: list = None):
        """Export model to different formats"""
        if model_path is None:
            model_path = f"{self.config.output_dir}/../runs/detect/structural_detection/weights/best.pt"
            
        if formats is None:
            formats = ['onnx', 'engine']  # TensorRT for deployment
            
        if not Path(model_path).exists():
            print(f"Model not found at {model_path}")
            return
            
        model = YOLO(model_path)
        
        for format_type in formats:
            try:
                model.export(
                    format=format_type,
                    imgsz=self.config.image_size[0],
                    half=False,
                    int8=False,
                    dynamic=False,
                    simplify=True,
                    opset=None,
                    workspace=4,
                    nms=False
                )
                print(f"Successfully exported to {format_type}")
            except Exception as e:
                print(f"Failed to export to {format_type}: {e}")

def train_yolo(config):
    """Training function using config"""
    trainer = YOLOTrainer(config, model_path='yolov8n.pt')
    
    # Train with config-based parameters
    results = trainer.train(
        epochs=50,
        batch_size=16,
        learning_rate=0.01,
        patience=50,
        name='structural_detection_v1'
    )
    
    # Validate the model
    print("\nValidating model...")
    val_results = trainer.validate()
    
    # Export for deployment
    print("\nExporting model...")
    trainer.export_model(formats=['onnx'])
    
    return results
