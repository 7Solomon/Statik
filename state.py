from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path 
import json

from src.generator.config import DatasetConfig
from src.generator.yolo import YOLODatasetManager
from src.vision.config import VisionConfig


@dataclass
class AppState:
    """Centralized application state management that coordinates all configs"""
    
    # Base directory for entire application
    content_dir: Path = Path("content")
    
    # Sub-configurations (initialized in __post_init__)
    dataset_config: DatasetConfig = field(init=False)
    vision_config: VisionConfig = field(init=False)
    
    # Runtime state
    trained_model_path: Optional[Path] = field(default=None, init=False)
    dataset_manager: Optional[YOLODatasetManager] = field(default=None, init=False)
    generation_status: dict = field(default=None, init=False)
    training_status: dict = field(default=None, init=False)
    
    def __post_init__(self):
        """Initialize all configurations with coordinated paths"""
        self.content_dir = Path(self.content_dir)
        self.content_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize dataset config with content_dir
        self.dataset_config = DatasetConfig()
        self.dataset_config.output_dir = self.content_dir / "datasets"
        
        # Initialize vision config with content_dir
        self.vision_config = VisionConfig(
            base_dir=self.content_dir / "vision"
        )
        
        # Initialize generation status
        self.generation_status = {
            'running': False,
            'progress': 0,
            'total': 0,
            'message': 'Ready to generate'
        }
        
        # Initialize training status
        self.training_status = {
            'running': False,
            'progress': 0,
            'total': 0,
            'message': '',
            'current_epoch': 0
        }
    
    def has_dataset(self) -> bool:
        """Check if dataset is available"""
        if self.dataset_dir is None:
            # Check if default dataset exists
            default_dataset = self.dataset_config.output_dir / "dataset.yaml"
            if default_dataset.exists():
                self.dataset_dir = self.dataset_config.output_dir
                return True
            return False
        return Path(self.dataset_dir).exists()
    
    def has_model(self) -> bool:
        """Check if trained model is available"""
        if self.trained_model_path is not None:
            return Path(self.trained_model_path).exists()
        
        # Check if production model exists
        prod_model = self.vision_config.get_production_model_path()
        if prod_model.exists():
            self.trained_model_path = prod_model
            return True
        
        # Check if any training run exists
        runs = self.vision_config.list_runs()
        if runs:
            latest_run = sorted(runs)[-1]
            best_model = self.vision_config.get_best_model_path(latest_run)
            if best_model.exists():
                self.trained_model_path = best_model
                return True
        
        return False
    
    def get_dataset_manager(self) -> Optional[YOLODatasetManager]:
        """Get or create dataset manager"""
        if not self.has_dataset():
            return None
        
        if self.dataset_manager is None:
            # Update dataset config with actual dataset directory
            self.dataset_config.output_dir = self.dataset_dir
            self.dataset_manager = YOLODatasetManager(
                self.dataset_config, 
                self.vision_config
            )
        
        return self.dataset_manager
    
    def set_dataset_dir(self, path: Path):
        """Set the dataset directory and reset manager"""
        self.dataset_dir = Path(path)
        self.dataset_manager = None  # Force recreation with new path
    
    def set_model_path(self, path: Path):
        """Set the trained model path"""
        self.trained_model_path = Path(path)
    
    def reset_dataset(self):
        """Reset dataset-related state"""
        self.dataset_dir = None
        self.dataset_manager = None
    
    def reset_model(self):
        """Reset model-related state"""
        self.trained_model_path = None
    
    def get_info(self) -> dict:
        """Get comprehensive state information"""
        return {
            'content_dir': str(self.content_dir.absolute()),
            'dataset': {
                'exists': self.has_dataset(),
                'path': str(self.dataset_dir) if self.dataset_dir else None,
                'output_dir': str(self.dataset_config.output_dir)
            },
            'model': {
                'exists': self.has_model(),
                'path': str(self.trained_model_path) if self.trained_model_path else None,
                'available_runs': self.vision_config.list_runs(),
                'available_models': self.vision_config.list_models()
            },
            'vision': {
                'base_dir': str(self.vision_config.base_dir),
                'datasets_dir': str(self.vision_config.datasets_dir),
                'models_dir': str(self.vision_config.models_dir),
                'runs_dir': str(self.vision_config.runs_dir)
            },
            'generation_status': self.generation_status
        }
    
    def save_state(self, filename: str = "app_state.json"):
        """Save current state to disk"""
        state_file = self.content_dir / filename
        state_data = {
            'dataset_dir': str(self.dataset_dir) if self.dataset_dir else None,
            'trained_model_path': str(self.trained_model_path) if self.trained_model_path else None,
        }
        with open(state_file, 'w') as f:
            json.dump(state_data, f, indent=2)
    
    def load_state(self, filename: str = "app_state.json"):
        """Load state from disk"""
        state_file = self.content_dir / filename
        if not state_file.exists():
            return False
        
        with open(state_file, 'r') as f:
            state_data = json.load(f)
        
        if state_data.get('dataset_dir'):
            self.dataset_dir = Path(state_data['dataset_dir'])
        if state_data.get('trained_model_path'):
            self.trained_model_path = Path(state_data['trained_model_path'])
        
        return True
    
    def print_summary(self):
        """Print state summary"""
        print("=" * 70)
        print("APPLICATION STATE")
        print("=" * 70)
        print(f"Content Directory: {self.content_dir.absolute()}")
        print()
        print("DATASET:")
        print(f"  Config output dir: {self.dataset_config.output_dir}")
        print(f"  Current dataset:   {self.dataset_dir if self.dataset_dir else 'None'}")
        print(f"  Exists:            {self.has_dataset()}")
        print()
        print("VISION:")
        print(f"  Base dir:     {self.vision_config.base_dir}")
        print(f"  Datasets dir: {self.vision_config.datasets_dir}")
        print(f"  Models dir:   {self.vision_config.models_dir}")
        print(f"  Runs dir:     {self.vision_config.runs_dir}")
        print()
        print("MODEL:")
        print(f"  Current model: {self.trained_model_path if self.trained_model_path else 'None'}")
        print(f"  Exists:        {self.has_model()}")
        print(f"  Available runs: {len(self.vision_config.list_runs())}")
        print(f"  Available models: {len(self.vision_config.list_models())}")
        print("=" * 70)