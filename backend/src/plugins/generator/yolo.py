import os
import json
import time
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import random
import uuid
import yaml
from PIL import Image

from src.models.image_models import ImageSystem
from src.plugins.generator.image.stanli_symbols import StanliSupport, StanliHinge, StanliLoad, SupportType

class YOLODatasetManager:
    """Manages YOLO format dataset creation"""
    
    def __init__(self, datasets_dir: Path, classes: List[str], dataset_id:str):
        self.classes = classes
        self.datasets_dir = datasets_dir

        self.dataset_id = dataset_id

        self.output_dir = self.datasets_dir / self.dataset_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[DATASET] Created dataset folder: {self.output_dir}")

    def get_output_dir(self) -> Path:
        """Return the unique dataset path."""
        return self.output_dir
    
    @classmethod
    def from_dataset_yaml(cls, dataset_yaml: str):
        """Create a manager by loading dataset.yaml."""
        dataset_yaml = Path(dataset_yaml)
        with open(dataset_yaml, "r") as f:
            data = yaml.safe_load(f)
        base = Path(data.get("path", dataset_yaml.parent)).resolve()

        class Cfg:
            output_dir = str(base)
            classes = tuple(data["names"])
            # Defaults for fields not needed by viewer
            node_radius = 4
            support_size = 16
            image_size = (640, 640)

        return cls(Cfg())
    
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
            'names': list(self.classes)
        }
        
        with open(self.output_dir / 'dataset.yaml', 'w') as f:
            yaml.dump(dataset_info, f, default_flow_style=False)
    
    def save_sample(self, image: Image.Image, system: ImageSystem,
                filename: str, split: str = 'train'):
        """Save image and labels - CREATE DIRECTORIES IF MISSING."""
        
        # CREATE DIRECTORIES if they don't exist
        images_dir = self.output_dir / split / 'images'
        labels_dir = self.output_dir / split / 'labels'
        
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)
        
        # Save image
        image_path = images_dir / f'{filename}.jpg'
        try:
            image.save(image_path, 'JPEG', quality=95)
        except Exception as e:
            print(f"[SAVE ERROR] Image {image_path}: {e}")
            return False
        
        # Create YOLO labels
        try:
            labels = self._structure_to_yolo_labels(system, image.size)
        except Exception as e:
            print(f"[LABELS ERROR] {e}")
            labels = []
        
        # Save labels
        label_path = labels_dir / f'{filename}.txt'
        try:
            with open(label_path, 'w') as f:
                for label in labels:
                    f.write(' '.join(map(str, label)) + '\n')
        except Exception as e:
            print(f"[SAVE ERROR] Labels {label_path}: {e}")
            return False
        
        return True  # Success!

    
    def _normalize_class_name(self, obj) -> str:
        """Return uniform name (e.g. FESTE_EINSPANNUNG, VOLLGELENK)."""
        if hasattr(obj, "name"):
            return obj.name
        s = str(obj)
        if "." in s:
            s = s.split(".")[-1]
        return s

    def _class_id(self, name: str) -> int:
        names = list(self.classes)
        if name not in names:
            # Instead of silently producing -1 somewhere else, fail loud & early
            raise ValueError(
                f"Class '{name}' not found in config.classes. "
                f"Add it to DatasetConfig.classes or dataset.yaml names list.\nCurrent: {names}"
            )
        return names.index(name)


    def _structure_to_yolo_labels(self, system: ImageSystem, image_size: Tuple[int, int]) -> List[List[float]]:
        """Simple bounding boxes - NO CRASHES."""
        labels = []
        w, h = image_size
        
        # Supports
        for node in getattr(system, 'nodes', []):
            support_type = getattr(node, 'support_type', None)
            if support_type and support_type != 'free':
                subtype = self._normalize_class_name(support_type)
                if subtype in self.classes:
                    class_id = self.classes.index(subtype)
                    
                    # FIXED 16x16 box around node center
                    x, y = node.pixel_x, node.pixel_y
                    half = 8.0
                    cx = (x / w)
                    cy = (y / h) 
                    bw = (16.0 / w)
                    bh = (16.0 / h)
                    
                    labels.append([class_id, cx, cy, bw, bh])
        
        # Loads  
        for load in getattr(system, 'loads', []):
            ltype = self._normalize_class_name(getattr(load, 'load_type', ''))
            if ltype in self.classes:
                class_id = self.classes.index(ltype)
                
                # Use node position or load position
                x = getattr(load, 'pixel_x', 320.0)
                y = getattr(load, 'pixel_y', 320.0)
                if hasattr(load, 'node_id') and load.node_id:
                    node = next((n for n in getattr(system, 'nodes', []) if n.id == load.node_id), None)
                    if node:
                        x, y = node.pixel_x, node.pixel_y
                
                # FIXED 24x24 box
                half = 12.0
                cx = (x / w)
                cy = (y / h)
                bw = (24.0 / w)
                bh = (24.0 / h)
                
                labels.append([class_id, cx, cy, bw, bh])
        
        return labels



    def get_image_list(self, split: str = "train") -> List[Dict]:
        """Get list of images with metadata for web viewer."""
        images_dir = self.output_dir / split / "images"
        if not images_dir.exists():
            return []
        
        img_paths = sorted([
            p for p in images_dir.glob("*") 
            if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
        ])
        
        return [
            {
                "index": i,
                "filename": p.name,
                "stem": p.stem,
            }
            for i, p in enumerate(img_paths)
        ]
    
    def get_labels_for_image(self, stem: str, split: str = "train") -> List[Dict]:
        """Get labels for a specific image in web-friendly format."""
        labels_dir = self.output_dir / split / "labels"
        label_path = labels_dir / f"{stem}.txt"
        
        labels = []
        if label_path.exists():
            with open(label_path, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) != 5:
                        continue
                    try:
                        class_id = int(float(parts[0]))
                        cx, cy, w, h = map(float, parts[1:])
                        class_name = (
                            list(self.classes)[class_id] 
                            if 0 <= class_id < len(self.classes) 
                            else f"class_{class_id}"
                        )
                        labels.append({
                            "class_id": class_id,
                            "class_name": class_name,
                            "cx": cx,
                            "cy": cy,
                            "w": w,
                            "h": h,
                        })
                    except Exception:
                        continue
        return labels
    
    def get_class_colors(self) -> Dict[int, str]:
        """Get color mapping for each class (as hex colors)."""
        import matplotlib.pyplot as plt
        cmap = plt.get_cmap("tab20")
        colors = {}
        for i in range(len(self.classes)):
            rgba = cmap(i % 20)
            # Convert to hex
            hex_color = "#{:02x}{:02x}{:02x}".format(
                int(rgba[0] * 255),
                int(rgba[1] * 255),
                int(rgba[2] * 255)
            )
            colors[i] = hex_color
        return colors

#def visualize_yolo_dataset(
#    dataset: str | YOLODatasetManager,
#    split: str = "train",
#    indices: List[int] = None,
#    shuffle: bool = False,
#    invert_y: bool = False,
#):
#    """Convenience function to visualize a dataset using dataset.yaml."""
#    if isinstance(dataset, str):
#        mgr = YOLODatasetManager.from_dataset_yaml(dataset)
#    elif isinstance(dataset, YOLODatasetManager):
#        mgr = dataset
#    mgr.visualize_dataset(split=split, indices=indices, shuffle=shuffle, invert_y=invert_y)
