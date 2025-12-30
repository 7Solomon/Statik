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
from src.plugins.generator.image.stanli_symbols import (
    LoadType, StanliSupport, StanliHinge, StanliLoad, 
    SupportType, HingeType, StanliSymbol
)

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
        return self.output_dir
    
    @classmethod
    def from_dataset_yaml(cls, dataset_yaml: str):
        dataset_yaml = Path(dataset_yaml)
        with open(dataset_yaml, "r") as f:
            data = yaml.safe_load(f)
        base = Path(data.get("path", dataset_yaml.parent)).resolve()

        class Cfg:
            output_dir = str(base)
            classes = tuple(data["names"])
            node_radius = 4
            support_size = 16
            image_size = (640, 640)

        return cls(datasets_dir=base.parent, classes=data["names"], dataset_id=base.name)
    
    def create_dataset_structure(self):
        for split in ['train', 'val', 'test']:
            (self.output_dir / split / 'images').mkdir(parents=True, exist_ok=True)
            (self.output_dir / split / 'labels').mkdir(parents=True, exist_ok=True)
        self._create_dataset_yaml()
    
    def _create_dataset_yaml(self):
        dataset_info = {
            'path': str(self.output_dir.absolute()),
            'train': 'train/images',
            'val': 'val/images',
            'test': 'test/images',
            'names': list(self.classes)
        }
        with open(self.output_dir / 'dataset.yaml', 'w', encoding="utf-8") as f:
            yaml.dump(dataset_info, f, default_flow_style=False)
    
    def save_sample(self, image: Image.Image, system: ImageSystem,
                filename: str, split: str = 'train'):
        # Create dirs just in case
        images_dir = self.output_dir / split / 'images'
        labels_dir = self.output_dir / split / 'labels'
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)
        
        # Save Image
        image_path = images_dir / f'{filename}.jpg'
        try:
            image.save(image_path, 'JPEG', quality=95)
        except Exception as e:
            print(f"[SAVE ERROR] Image {image_path}: {e}")
            return False
        
        # Generate Labels
        try:
            labels = self._structure_to_yolo_labels(system, image.size)
        except Exception as e:
            print(f"[LABELS ERROR] {e}")
            import traceback
            traceback.print_exc()
            labels = []
        
        # Save Labels
        label_path = labels_dir / f'{filename}.txt'
        try:
            with open(label_path, 'w', encoding="utf-8") as f:
                for label in labels:
                    f.write(' '.join(map(str, label)) + '\n')
        except Exception as e:
            print(f"[SAVE ERROR] Labels {label_path}: {e}")
            return False
        
        return True

    def _normalize_class_name(self, obj) -> str:
        if hasattr(obj, "name"): return obj.name
        s = str(obj)
        if "." in s: s = s.split(".")[-1]
        return s

    # --- Helpers for Enum Conversion ---
    def _get_support_enum(self, name: str) -> Optional[SupportType]:
        try: return SupportType[name]
        except KeyError: return None

    def _get_load_enum(self, name: str) -> Optional[LoadType]:
        key = name.upper()
        try:
            return LoadType[key]
        except KeyError:
            mapping = {
                'FORCE': LoadType.EINZELLAST,
                'FORCE_POINT': LoadType.EINZELLAST,
                'MOMENT': LoadType.MOMENT_UHRZEIGER,
            }
            return mapping.get(key)

    # --- CORE LABEL GENERATION LOGIC ---
    def _structure_to_yolo_labels(self, system: ImageSystem, image_size: Tuple[int, int]) -> List[List[float]]:
        labels = []
        w_img, h_img = image_size
        
        # 1. SUPPORTS
        for node in getattr(system, 'nodes', []):
            support_str = getattr(node, 'support_type', None)
            
            # Skip if None, "free", or "FREIES_ENDE" (assuming that isn't a valid detection class)
            if not support_str or str(support_str).upper() in ['FREE', 'FREIES_ENDE']:
                continue

            # Normalize string (e.g. SupportType.FESTLAGER -> "FESTLAGER")
            subtype = self._normalize_class_name(support_str)
            
            if subtype in self.classes:
                class_id = self.classes.index(subtype)
                stype_enum = self._get_support_enum(subtype)
                
                if stype_enum:
                    symbol = StanliSupport(stype_enum)
                    rotation = getattr(node, 'rotation', 0.0)
                    min_x, min_y, max_x, max_y = symbol.get_bbox((node.pixel_x, node.pixel_y), rotation=rotation)
                    self._add_label(labels, class_id, min_x, min_y, max_x, max_y, w_img, h_img)

        # 2. LOADS
        for load in getattr(system, 'loads', []):
            # 1. Map string type to Enum if necessary
            ltype = load.load_type
            if isinstance(ltype, str):
                ltype = self._get_load_enum(ltype) # Use your helper from renderer
            
            # 2. Get the symbol and bbox
            symbol = StanliLoad(ltype)
            node = next((n for n in system.nodes if n.id == load.node_id), None)
            pos = (node.pixel_x, node.pixel_y) if node else (load.pixel_x, load.pixel_y)
            
            min_x, min_y, max_x, max_y = symbol.get_bbox(pos, rotation=getattr(load, 'angle_deg', 0))
            self._add_label(labels, class_id, min_x, min_y, max_x, max_y, w_img, h_img)
                    
        return labels

    def _add_label(self, labels, class_id, min_x, min_y, max_x, max_y, w_img, h_img):
        """Helper to normalize and append label if valid."""
        # Clamp to image bounds
        min_x = max(0, min_x)
        min_y = max(0, min_y)
        max_x = min(w_img, max_x)
        max_y = min(h_img, max_y)

        # Calculate normalized center + width/height
        bw = (max_x - min_x)
        bh = (max_y - min_y)
        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2
        
        # Only add if it has non-zero size
        if bw > 0.5 and bh > 0.5: # at least 0.5px big
            labels.append([
                class_id, 
                cx / w_img, 
                cy / h_img, 
                bw / w_img, 
                bh / h_img
            ])

    def get_image_list(self, split: str = "train") -> List[Dict]:
        images_dir = self.output_dir / split / "images"
        if not images_dir.exists(): return []
        
        img_paths = sorted([p for p in images_dir.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}])
        return [{"index": i, "filename": p.name, "stem": p.stem} for i, p in enumerate(img_paths)]
    
    def get_labels_for_image(self, stem: str, split: str = "train") -> List[Dict]:
        label_path = self.output_dir / split / "labels" / f"{stem}.txt"
        labels = []
        if label_path.exists():
            with open(label_path, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) != 5: continue
                    try:
                        class_id = int(float(parts[0]))
                        cx, cy, w, h = map(float, parts[1:])
                        class_name = self.classes[class_id] if 0 <= class_id < len(self.classes) else str(class_id)
                        labels.append({"class_id": class_id, "class_name": class_name, "cx": cx, "cy": cy, "w": w, "h": h})
                    except: continue
        return labels
