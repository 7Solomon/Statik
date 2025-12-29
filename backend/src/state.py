from dataclasses import dataclass, field, asdict
from pathlib import Path 
import json
from src.plugins.generator.config import DatasetConfig
from src.plugins.management.sytem_manager import SystemManager

@dataclass
class AppState:
    """Centralized application state"""
    content_dir: Path
    
    config: dict = field(default_factory=dict)
    
    system_manager: SystemManager = field(init=False)
    dataset_config: DatasetConfig = field(default_factory=DatasetConfig)

    def __post_init__(self):
        self.content_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Managers
        templates_path = self.content_dir / "system_templates"
        self.system_manager = SystemManager(templates_path)

    def save_state(self, filename: str = "app_state.json"):
        """Save current global config to disk"""
        state_file = self.content_dir / filename
        
        # Save self.config
        data_to_save = {
            "user_config": self.config,
            "dataset_config": asdict(self.dataset_config)
        }
        
        try:
            with open(state_file, 'w') as f:
                json.dump(data_to_save, f, indent=2)
            print(f"State saved to {state_file}")
        except Exception as e:
            print(f"Failed to save state: {e}")
    
    def load_state(self, filename: str = "app_state.json"):
        """Load state from disk and UPDATE self.config + self.dataset_config."""
        state_file = self.content_dir / filename
        
        if not state_file.exists():
            print("No previous state found.")
            return False
        
        try:
            with open(state_file, 'r') as f:
                loaded_data = json.load(f)
            
            # Load user config
            if "user_config" in loaded_data:
                self.config.update(loaded_data["user_config"])
            
            # Load dataset config (convert dict back to dataclass)
            if "dataset_config" in loaded_data:
                # Update dataclass fields directly
                for key, value in loaded_data["dataset_config"].items():
                    if hasattr(self.dataset_config, key):
                        setattr(self.dataset_config, key, value)
            
            print("State loaded successfully.")
            return True
        except Exception as e:
            print(f"Failed to load state: {e}")
            return False
    def reset_dataset_config(self):
        """Reset dataset config to defaults."""
        self.dataset_config = DatasetConfig()
