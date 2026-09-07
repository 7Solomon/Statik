from dataclasses import dataclass, field
from typing import Tuple, List, Optional
from pathlib import Path

from src.plugins.generator.image.stanli_symbols import detectable_class_names

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
    # Point-load arrow length in pixels (must match renderer, labels, and normalize bounds)
    load_arrow_length_px: float = 40.0
    
    # Structure generation
    min_nodes: int = 4
    max_nodes: int = 12
    grid_size: Tuple[int, int] = (5, 5)
    connection_probability: float = 0.7
    # Relative weights for beam / cantilever / frame / truss archetypes.
    archetype_weights: List[float] = field(default_factory=lambda: [0.32, 0.18, 0.28, 0.22])
    
    # Visual properties
    node_radius: int = 8
    beam_width: int = 3
    support_size: int = 20
    node_color: Tuple[int, int, int] = (50, 50, 200)
    beam_color: Tuple[int, int, int] = (100, 100, 100)
    support_color: Tuple[int, int, int] = (200, 50, 50)
    
    # Augmentation
    # Structural drawings are gravity aligned: the ground is at the bottom and
    # supports hang below their node. Rotating uniformly over 0-360 taught the
    # model that support orientation carries no information, which throws away
    # the strongest cue for which side is "ground". Keep it to drafting slop.
    enable_rotation: bool = True
    rotation_range: Tuple[int, int] = (-6, 6)
    # The old pseudo-perspective was a 1.5% horizontal squeeze of node
    # coordinates only (max_factor = 1 - strength*0.1), so it changed nothing a
    # model could notice. Real photo robustness needs a homography applied to
    # the raster with the labels pushed through the same matrix; until that
    # exists, leave it off rather than pretend.
    enable_perspective: bool = False
    perspective_strength: float = 0.15
    enable_noise: bool = True
    noise_intensity: float = 0.05
    enable_blur: bool = True
    blur_kernels: List[int] = field(default_factory=lambda: [3, 5, 7])

    # How much of the frame the structure fills. Randomised per sample so the
    # symbol-to-image size ratio varies - symbols are drawn at a fixed pixel
    # size, so a constant margin means every Festlager in the dataset is exactly
    # the same number of pixels wide.
    margin_range: Tuple[float, float] = (0.06, 0.28)
    # Two symbol boxes overlapping by more than this share of the smaller box
    # make the layout a poor one, so a tighter margin is tried first.
    max_symbol_overlap: float = 0.25
    # Past this, one symbol is essentially drawn on top of another: two
    # ground-truth boxes over one patch of ink, which the detector cannot
    # win. Such a sample is dropped rather than labelled wrong.
    discard_symbol_overlap: float = 0.6
    
    # Per-sample ink, paper, stroke weight, fonts and annotation clutter.
    # Off reproduces the old uniform black-on-white look.
    randomize_appearance: bool = True

    randomize_positions: bool = True
    enforce_static_determinacy: bool = True
    scheibe_complexity: float = 0.6
    
    support_line_width: int = 3
    beam_connection_size: int = 6
    symbol_scale: float = 1.0
    
    # YOLO classes. Only symbols the generator actually draws and that are
    # visually distinct from every other class - see stanli_symbols for what is
    # excluded and why.
    classes: List[str] = field(default_factory=detectable_class_names)
