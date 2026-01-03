from dataclasses import dataclass, field
from typing import Tuple, List, Optional
from pathlib import Path

from src.plugins.generator.image.stanli_symbols import HingeType, LoadType, SupportType

@dataclass
class DatasetConfig:
    """Configuration for dataset generation - paths coordinated by AppState"""
    # --- Generation Settings---
    train_ratio: float = 0.8
    val_ratio: float = 0.15
    test_ratio: float = 0.05
    
    # Image generation
    image_size: Tuple[int, int] = (640, 640)
    background_color: Tuple[int, int, int] = (255, 255, 255)
    
    # Structure generation
    min_nodes: int = 4
    max_nodes: int = 12
    grid_size: Tuple[int, int] = (5, 5)
    connection_probability: float = 0.7
    
    # Visual properties
    node_radius: int = 8
    beam_width: int = 3
    support_size: int = 20
    node_color: Tuple[int, int, int] = (50, 50, 200)
    beam_color: Tuple[int, int, int] = (100, 100, 100)
    support_color: Tuple[int, int, int] = (200, 50, 50)
    
    # Augmentation
    enable_rotation: bool = True
    rotation_range: Tuple[int, int] = (0, 360)
    enable_perspective: bool = True
    perspective_strength: float = 0.15
    enable_noise: bool = True
    noise_intensity: float = 0.05
    enable_blur: bool = True
    blur_kernels: List[int] = field(default_factory=lambda: [3, 5, 7])
    
    randomize_positions: bool = True
    enforce_static_determinacy: bool = True
    scheibe_complexity: float = 0.6
    
    support_line_width: int = 3
    beam_connection_size: int = 6
    symbol_scale: float = 1.0
    
    # YOLO classes
    classes: List[str] = field(default_factory=lambda: (
        [e.name for e in SupportType] + 
        [e.name for e in LoadType] +
        [e.name for e in HingeType]
    ))