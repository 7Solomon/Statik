from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from datetime import datetime


@dataclass
class VisionConfig:
    """Configuration for YOLO training and prediction - paths coordinated by AppState"""
    
    # Base directory (set by AppState)
    base_dir: Path = Path("temp_vision")  # Default, gets overridden
    
    # Subdirectories (auto-created)
    datasets_dir: Path = field(init=False)
    models_dir: Path = field(init=False)
    runs_dir: Path = field(init=False)
    predictions_dir: Path = field(init=False)
    uploads_dir: Path = field(init=False)
    
    # Current session
    dataset_name: str = "structural_dataset"
    model_name: str = "structural_model"
    run_name: Optional[str] = None
    
    # Model settings
    base_model: str = "yolov8n.pt"
    
    def __post_init__(self):
        """Initialize directory structure"""
        self.base_dir = Path(self.base_dir)
        
        # Define subdirectories
        self.datasets_dir = self.base_dir / "datasets"
        self.models_dir = self.base_dir / "models"
        self.runs_dir = self.base_dir / "runs"
        self.predictions_dir = self.base_dir / "predictions"
        self.uploads_dir = self.base_dir / "uploads"
        
        # Create all directories
        for dir_path in [self.datasets_dir, self.models_dir, self.runs_dir, 
                         self.predictions_dir, self.uploads_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Auto-generate run name if not provided
        if self.run_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.run_name = f"{self.model_name}_{timestamp}"
    
    @property
    def current_dataset_dir(self) -> Path:
        """Get current dataset directory"""
        return self.datasets_dir / self.dataset_name
    
    @property
    def current_run_dir(self) -> Path:
        """Get current training run directory"""
        return self.runs_dir / self.run_name
    
    @property
    def current_model_dir(self) -> Path:
        """Get directory for saving trained models"""
        path = self.models_dir / self.model_name
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_best_model_path(self, run_name: Optional[str] = None) -> Path:
        """Get path to best model weights from a training run"""
        if run_name is None:
            run_name = self.run_name
        return self.runs_dir / run_name / "weights" / "best.pt"
    
    def get_last_model_path(self, run_name: Optional[str] = None) -> Path:
        """Get path to last model checkpoint from a training run"""
        if run_name is None:
            run_name = self.run_name
        return self.runs_dir / run_name / "weights" / "last.pt"
    
    def list_datasets(self) -> list[str]:
        """List all available datasets"""
        if not self.datasets_dir.exists():
            return []
        return [d.name for d in self.datasets_dir.iterdir() if d.is_dir()]
    
    def list_models(self) -> list[str]:
        """List all saved models"""
        if not self.models_dir.exists():
            return []
        return [m.name for m in self.models_dir.iterdir() if m.is_dir()]
    
    def list_runs(self) -> list[str]:
        """List all training runs"""
        if not self.runs_dir.exists():
            return []
        return [r.name for r in self.runs_dir.iterdir() if r.is_dir()]
    
    def get_model_info(self, model_name: str) -> dict:
        """Get information about a saved model"""
        model_dir = self.models_dir / model_name
        if not model_dir.exists():
            return {}
        
        best_model = model_dir / "best.pt"
        return {
            "name": model_name,
            "path": str(model_dir),
            "best_model_exists": best_model.exists(),
            "best_model_path": str(best_model) if best_model.exists() else None,
            "created": model_dir.stat().st_ctime if model_dir.exists() else None
        }
    
    def save_trained_model(self, source_run_name: Optional[str] = None, 
                          target_model_name: Optional[str] = None):
        """Copy best model from run directory to models directory"""
        import shutil
        
        if source_run_name is None:
            source_run_name = self.run_name
        if target_model_name is None:
            target_model_name = self.model_name
        
        source_path = self.get_best_model_path(source_run_name)
        if not source_path.exists():
            raise FileNotFoundError(f"No trained model found at {source_path}")
        
        target_dir = self.models_dir / target_model_name
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / "best.pt"
        
        shutil.copy2(source_path, target_path)
        
        # Also copy last.pt and results
        last_source = source_path.parent / "last.pt"
        if last_source.exists():
            shutil.copy2(last_source, target_dir / "last.pt")
        
        results_source = source_path.parent.parent / "results.csv"
        if results_source.exists():
            shutil.copy2(results_source, target_dir / "results.csv")
        
        print(f"Model saved to: {target_path}")
        return target_path
    
    def get_production_model_path(self, model_name: Optional[str] = None) -> Path:
        """Get path to production model (from models directory)"""
        if model_name is None:
            model_name = self.model_name
        return self.models_dir / model_name / "best.pt"