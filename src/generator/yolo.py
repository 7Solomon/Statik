import os
import json
from typing import List, Dict, Tuple
from pathlib import Path
import yaml
from PIL import Image
from data.generator_class import Structure
import random
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from src.generator.image.stanli_symbols import StanliSupport, StanliHinge, StanliLoad, SupportType

class YOLODatasetManager:
    """Manages YOLO format dataset creation"""
    
    def __init__(self, config):
        self.config = config
        dirs = os.listdir(config.output_dir)
        self.output_dir = config.output_dir / str(len(dirs))

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
            'names': list(self.config.classes)
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
    
    def _normalize_class_name(self, obj) -> str:
        """Return uniform name (e.g. FESTE_EINSPANNUNG, VOLLGELENK)."""
        if hasattr(obj, "name"):
            return obj.name
        s = str(obj)
        if "." in s:
            s = s.split(".")[-1]
        return s

    def _class_id(self, name: str) -> int:
        names = list(self.config.classes)
        if name not in names:
            # Instead of silently producing -1 somewhere else, fail loud & early
            raise ValueError(
                f"Class '{name}' not found in config.classes. "
                f"Add it to DatasetConfig.classes or dataset.yaml names list.\nCurrent: {names}"
            )
        return names.index(name)


    def _structure_to_yolo_labels(self, structure: Structure, 
                                 image_size: Tuple[int, int]) -> List[List[float]]:
        """Convert structure to YOLO format labels with geometry-based bounding boxes."""
        labels = []
        w, h = image_size

        # Process nodes (supports only)
        for node in structure.nodes:
            if not getattr(node, "support_type", None):
                continue
            
            subtype = self._normalize_class_name(node.support_type)
            try:
                class_id = self._class_id(subtype)
            except ValueError:
                continue
            
            # Get actual geometry-based bbox
            support_symbol = StanliSupport(node.support_type)
            rotation = getattr(node, "rotation", 0.0)
            min_x, min_y, max_x, max_y = support_symbol.get_bbox(node.position, rotation)
            
            # Convert to YOLO format (normalized center + width/height)
            cx = ((min_x + max_x) / 2) / w
            cy = ((min_y + max_y) / 2) / h
            bw = (max_x - min_x) / w
            bh = (max_y - min_y) / h
            
            # Clamp to valid range and skip if degenerate
            if bw <= 0 or bh <= 0:
                continue
            cx = max(0, min(1, cx))
            cy = max(0, min(1, cy))
            bw = max(0, min(1, bw))
            bh = max(0, min(1, bh))
            
            labels.append([class_id, cx, cy, bw, bh])

        # Process hinges (separate from nodes)
        for hinge in getattr(structure, "hinges", []):
            node = structure.get_node_by_id(hinge.node_id)
            if not node:
                continue
            
            subtype = self._normalize_class_name(hinge.hinge_type)
            try:
                class_id = self._class_id(subtype)
            except ValueError:
                continue
            
            # Get actual geometry-based bbox
            hinge_symbol = StanliHinge(hinge.hinge_type)
            rotation = getattr(hinge, "rotation", 0.0)
            
            # Get connected node positions for context-aware hinges
            p_init = None
            p_end = None
            if hinge.start_node_id is not None:
                start_node = structure.get_node_by_id(hinge.start_node_id)
                if start_node:
                    p_init = start_node.position
            if hinge.end_node_id is not None:
                end_node = structure.get_node_by_id(hinge.end_node_id)
                if end_node:
                    p_end = end_node.position
            
            min_x, min_y, max_x, max_y = hinge_symbol.get_bbox(
                node.position, rotation, p_init, p_end
            )
            
            # Convert to YOLO format
            cx = ((min_x + max_x) / 2) / w
            cy = ((min_y + max_y) / 2) / h
            bw = (max_x - min_x) / w
            bh = (max_y - min_y) / h
            
            # Clamp and validate
            if bw <= 0 or bh <= 0:
                continue
            cx = max(0, min(1, cx))
            cy = max(0, min(1, cy))
            bw = max(0, min(1, bw))
            bh = max(0, min(1, bh))
            
            labels.append([class_id, cx, cy, bw, bh])

        # Optional: Process loads
        # Uncomment if you want to label loads as objects
        # for load in getattr(structure, "loads", []):
        #     node = structure.get_node_by_id(load.node_id)
        #     if not node:
        #         continue
        #     
        #     subtype = self._normalize_class_name(load.load_type)
        #     try:
        #         class_id = self._class_id(subtype)
        #     except ValueError:
        #         continue
        #     
        #     load_symbol = StanliLoad(load.load_type)
        #     rotation = getattr(load, "rotation", 0.0)
        #     min_x, min_y, max_x, max_y = load_symbol.get_bbox(node.position, rotation)
        #     
        #     cx = ((min_x + max_x) / 2) / w
        #     cy = ((min_y + max_y) / 2) / h
        #     bw = (max_x - min_x) / w
        #     bh = (max_y - min_y) / h
        #     
        #     if bw > 0 and bh > 0:
        #         labels.append([class_id, cx, cy, bw, bh])

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
                            list(self.config.classes)[class_id] 
                            if 0 <= class_id < len(self.config.classes) 
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
        for i in range(len(self.config.classes)):
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
