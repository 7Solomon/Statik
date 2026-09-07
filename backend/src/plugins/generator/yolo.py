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
from src.plugins.generator.image.placement import (
    clip_polygon, compute_placements, polygon_area,
)
from src.plugins.generator.image.stanli_symbols import detectable_class_names

class YOLODatasetManager:
    """Manages YOLO format dataset creation"""
    
    def __init__(
        self,
        datasets_dir: Path,
        classes: List[str],
        dataset_id: str,
        load_arrow_length_px: float = 40.0,
    ):
        self.classes = list(classes)
        self.datasets_dir = datasets_dir
        self.dataset_id = dataset_id
        self.load_arrow_length_px = load_arrow_length_px
        # Instances actually written, per class. A class that ends on zero is a
        # bug, not a quirk: it costs capacity and silently skews val metrics.
        self.class_counts: Dict[str, int] = {name: 0 for name in self.classes}

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

        return cls(
            datasets_dir=base.parent,
            classes=data["names"],
            dataset_id=base.name,
            load_arrow_length_px=float(data.get("load_arrow_length_px", 40.0)),
        )
    
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
            'names': list(self.classes),
            'load_arrow_length_px': self.load_arrow_length_px,
            # Labels are 4-corner oriented boxes, so this dataset only trains
            # against a *-obb model. Recorded here so a detect-task model
            # pointed at it fails loudly instead of misreading the coordinates.
            'task': 'obb',
        }
        with open(self.output_dir / 'dataset.yaml', 'w', encoding="utf-8") as f:
            yaml.dump(dataset_info, f, default_flow_style=False)

    def class_histogram(self) -> Dict[str, int]:
        return dict(self.class_counts)

    def empty_classes(self) -> List[str]:
        return [name for name, n in self.class_counts.items() if n == 0]
    
    def save_sample(self, image: Image.Image, system: ImageSystem,
                filename: str, split: str = 'train'):
        # Create dirs just in case
        images_dir = self.output_dir / split / 'images'
        labels_dir = self.output_dir / split / 'labels'
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)
        
        # Labels first: an image without a matching label file is silently
        # trained on as a pure-background sample, which is worse than skipping it.
        try:
            labels = self._structure_to_yolo_labels(system, image.size)
        except Exception as e:
            print(f"[LABELS ERROR] {e}")
            import traceback
            traceback.print_exc()
            return False

        image_path = images_dir / f'{filename}.jpg'
        try:
            image.save(image_path, 'JPEG', quality=95)
        except Exception as e:
            print(f"[SAVE ERROR] Image {image_path}: {e}")
            return False
        
        label_path = labels_dir / f'{filename}.txt'
        try:
            with open(label_path, 'w', encoding="utf-8") as f:
                for label in labels:
                    f.write(' '.join(map(str, label)) + '\n')
        except Exception as e:
            print(f"[SAVE ERROR] Labels {label_path}: {e}")
            image_path.unlink(missing_ok=True)
            return False

        for label in labels:
            name = self.classes[int(label[0])]
            self.class_counts[name] = self.class_counts.get(name, 0) + 1
        
        return True

    # --- CORE LABEL GENERATION LOGIC ---
    def _structure_to_yolo_labels(self, system: ImageSystem, image_size: Tuple[int, int]) -> List[List[float]]:
        """Labels derived from the exact placements the renderer drew.

        YOLO OBB format: `class x1 y1 x2 y2 x3 y3 x4 y4`, normalised, four
        corners in draw order. See stanli_symbols._obb_from_ops for why the
        boxes are oriented rather than axis-aligned.
        """
        labels: List[List[float]] = []
        w_img, h_img = image_size

        for placement in compute_placements(system, self.load_arrow_length_px):
            if placement.class_name not in self.classes:
                continue
            corners = placement.corners()
            if not corners:
                continue
            self._add_label(labels, self.classes.index(placement.class_name),
                            corners, w_img, h_img)

        return labels

    def _add_label(self, labels, class_id, corners, w_img, h_img):
        """Normalise and append, dropping symbols that fell out of the frame.

        A rotated box cannot be clipped to the frame and stay a rotated box, so
        instead of trimming it the symbol is kept whole or dropped, judged on
        how much of its area still lands on the image.
        """
        full = polygon_area(corners)
        if full <= 0:
            return

        frame = [(0.0, 0.0), (float(w_img), 0.0),
                 (float(w_img), float(h_img)), (0.0, float(h_img))]
        visible = polygon_area(clip_polygon(corners, frame))

        # A symbol that is mostly outside the frame is a partial glyph the model
        # cannot classify; teaching it that such a stub is a full Festlager is
        # how you manufacture false positives on real images.
        if visible / full < 0.6:
            return

        row = [class_id]
        for x, y in corners:
            # Ultralytics wants normalised coordinates; a corner just off the
            # edge is clamped rather than dropping an otherwise good symbol.
            row.append(min(1.0, max(0.0, x / w_img)))
            row.append(min(1.0, max(0.0, y / h_img)))
        labels.append(row)

    def debug_overlay(self, image: Image.Image, system: ImageSystem) -> Image.Image:
        """Draw YOLO boxes using the same geometry as training labels (QA / regression checks)."""
        from PIL import ImageDraw

        out = image.copy()
        draw = ImageDraw.Draw(out)
        w, h = out.size
        labels = self._structure_to_yolo_labels(system, (w, h))
        for row in labels:
            cid = int(row[0])
            pts = [(row[1 + 2 * i] * w, row[2 + 2 * i] * h) for i in range(4)]
            name = self.classes[cid] if 0 <= cid < len(self.classes) else str(cid)
            draw.polygon(pts, outline="red")
            for i in range(4):  # polygon() ignores width, so stroke the edges
                draw.line([pts[i], pts[(i + 1) % 4]], fill="red", width=2)
            draw.text((pts[0][0], max(0, pts[0][1] - 12)), name, fill="red")
        return out

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
                    if len(parts) != 9: continue
                    try:
                        class_id = int(float(parts[0]))
                        coords = list(map(float, parts[1:]))
                        corners = [(coords[2 * i], coords[2 * i + 1]) for i in range(4)]
                        xs = [c[0] for c in corners]
                        ys = [c[1] for c in corners]
                        class_name = self.classes[class_id] if 0 <= class_id < len(self.classes) else str(class_id)
                        # Both shapes: `corners` is the truth, cx/cy/w/h is the
                        # enclosing box that existing viewers already draw.
                        labels.append({"class_id": class_id, "class_name": class_name,
                                       "corners": corners,
                                       "cx": (min(xs) + max(xs)) / 2,
                                       "cy": (min(ys) + max(ys)) / 2,
                                       "w": max(xs) - min(xs), "h": max(ys) - min(ys)})
                    except: continue
        return labels
