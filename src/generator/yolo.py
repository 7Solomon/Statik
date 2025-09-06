import os
import json
from typing import List, Dict, Tuple
from pathlib import Path
import yaml
from PIL import Image
from data.generator_class import Structure

class YOLODatasetManager:
    """Manages YOLO format dataset creation"""
    
    def __init__(self, config):
        self.config = config
        self.output_dir = Path(config.output_dir)
    
    def create_dataset_structure(self):
        """Create YOLO dataset folder structure"""
        # Create main directories
        for split in ['train', 'val', 'test']:
            (self.output_dir / split / 'images').mkdir(parents=True, exist_ok=True)
            (self.output_dir / split / 'labels').mkdir(parents=True, exist_ok=True)
        
        # Create dataset.yaml
        self._create_dataset_yaml()
    
    def _create_dataset_yaml(self):
        """Create YOLO dataset configuration file"""
        dataset_info = {
            'path': str(self.output_dir.absolute()),
            'train': 'train/images',
            'val': 'val/images',
            'test': 'test/images',
            'names': {i: name for i, name in enumerate(self.config.classes)}
        }
        
        with open(self.output_dir / 'dataset.yaml', 'w') as f:
            yaml.dump(dataset_info, f, default_flow_style=False)
    
    def save_sample(self, image: Image.Image, structure: Structure, 
                   filename: str, split: str = 'train'):
        """Save image and labels in YOLO format"""
        # Save image
        image_path = self.output_dir / split / 'images' / f'{filename}.jpg'
        image.save(image_path, 'JPEG', quality=95)
        
        # Create YOLO format labels
        labels = self._structure_to_yolo_labels(structure, image.size)
        
        # Save labels
        label_path = self.output_dir / split / 'labels' / f'{filename}.txt'
        with open(label_path, 'w') as f:
            for label in labels:
                f.write(' '.join(map(str, label)) + '\n')
    
    def _structure_to_yolo_labels(self, structure: Structure, 
                                 image_size: Tuple[int, int]) -> List[List[float]]:
        """Convert structure to YOLO format labels"""
        labels = []
        w, h = image_size
        
        for node in structure.nodes:
            x, y = node.position
            
            # Normalize coordinates to [0, 1]
            x_norm = x / w
            y_norm = y / h
            
            # Node bounding box (small box around node)
            box_size = self.config.node_radius * 2 / min(w, h)
            
            if node.support_type:
                # Support class
                class_id = 1  # support
                # Larger bounding box for supports
                box_size = self.config.support_size / min(w, h)
            else:
                # Regular node class  
                class_id = 0  # node
            
            # YOLO format: class_id, x_center, y_center, width, height
            labels.append([class_id, x_norm, y_norm, box_size, box_size])
        
        return labels