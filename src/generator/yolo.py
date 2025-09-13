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

class YOLODatasetManager:
    """Manages YOLO format dataset creation"""
    
    def __init__(self, config):
        self.config = config
        self.output_dir = Path(config.output_dir)

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
        """Return the final symbolic name (e.g. FIXED_SUPPORT) from Enum or string."""
        if hasattr(obj, "name"):
            return obj.name
        s = str(obj)
        if "." in s:                    
            s = s.split(".")[-1]
        return s
    def _class_id(self, name: str) -> int:
        names = list(self.config.classes)
        if name not in names:
            raise ValueError(f"Class '{name}' not found in config.classes: {names}")
        return names.index(name)

    def _structure_to_yolo_labels(self, structure: Structure, 
                                 image_size: Tuple[int, int]) -> List[List[float]]:
        """Convert structure to YOLO format labels"""
        labels = []
        w, h = image_size

        for node in structure.nodes:
            x, y = node.position
            x_norm = x / w
            y_norm = y / h

            # default small box for nodes
            box_size = self.config.node_radius * 2 / min(w, h)
            
            if getattr(node, "support_type", None):
                subtype = self._normalize_class_name(node.support_type)
                class_id = self._class_id(subtype)
                box_size = self.config.support_size / min(w, h)
            elif getattr(node, "hinge_type", None):
                subtype = self._normalize_class_name(node.hinge_type)
                class_id = self._class_id(subtype)
            else:
                print(f"Warning: Node {node.id} has no support_type or hinge_type")
                #raise ValueError(f"Node {node.id} has no support_type or hinge_type")

            labels.append([class_id, x_norm, y_norm, box_size, box_size])

        # TODO: add beam_connection labels

        return labels

    def visualize_dataset(
        self,
        split: str = "train",
        indices: List[int] = None,
        shuffle: bool = False,
        invert_y: bool = False,
        figsize: Tuple[int, int] = (8, 8),
    ):
        """
        Interactive viewer for YOLO dataset (arrow keys to navigate).
        Keys:
          - Right/Left: next/prev image
          - F: toggle invert_y (flip Y axis)
          - Q or Esc: quit
        """
        images_dir = self.output_dir / split / "images"
        labels_dir = self.output_dir / split / "labels"
        if not images_dir.exists():
            print(f"Images dir not found: {images_dir}")
            return

        img_paths = sorted([p for p in images_dir.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}])
        if not img_paths:
            print(f"No images in {images_dir}")
            return

        # Subset by indices if provided
        if indices:
            img_paths = [img_paths[i] for i in indices if 0 <= i < len(img_paths)]

        if shuffle:
            random.shuffle(img_paths)

        class_names = list(self.config.classes)
        cmap = plt.get_cmap("tab20")
        colors = {i: cmap(i % 20) for i in range(len(class_names))}

        fig, ax = plt.subplots(1, 1, figsize=figsize)
        fig.canvas.manager.set_window_title(f"YOLO {split} viewer")

        state = {"i": 0, "invert_y": invert_y}

        def load_labels_for(img_path: Path):
            lbl_path = labels_dir / (img_path.stem + ".txt")
            items = []
            if lbl_path.exists():
                with open(lbl_path, "r") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) != 5:
                            continue
                        try:
                            cid = int(float(parts[0]))
                            cx, cy, w, h = map(float, parts[1:])
                            items.append((cid, cx, cy, w, h))
                        except Exception:
                            continue
            return items

        def draw(idx: int):
            ax.clear()
            img_path = img_paths[idx]
            img = Image.open(img_path).convert("RGB")
            ax.imshow(img)
            ax.set_axis_off()

            W, H = img.size
            labels = load_labels_for(img_path)

            for cid, cx, cy, w, h in labels:
                # Optionally invert Y (useful if your generator's Y origin is bottom-left)
                cy_draw = 1.0 - cy if state["invert_y"] else cy

                box_w = w * W
                box_h = h * H
                x = cx * W - box_w / 2
                y = cy_draw * H - box_h / 2

                color = colors.get(cid, (1, 0, 0, 0.8))
                rect = Rectangle((x, y), box_w, box_h, linewidth=2, edgecolor=color, facecolor="none")
                ax.add_patch(rect)
                label = class_names[cid] if 0 <= cid < len(class_names) else f"class_{cid}"
                ax.text(
                    x,
                    max(0, y - 4),
                    label,
                    color="white",
                    fontsize=9,
                    bbox=dict(facecolor=color, edgecolor="none", alpha=0.6, pad=1),
                )

            ax.set_title(
                f"[{idx+1}/{len(img_paths)}] {img_path.name} | invert_y={state['invert_y']} | {split}",
                fontsize=10,
            )
            fig.canvas.draw_idle()

        def on_key(event):
            if event.key in ("right", "d"):
                state["i"] = (state["i"] + 1) % len(img_paths)
                draw(state["i"])
            elif event.key in ("left", "a"):
                state["i"] = (state["i"] - 1) % len(img_paths)
                draw(state["i"])
            elif event.key in ("f",):
                state["invert_y"] = not state["invert_y"]
                draw(state["i"])
            elif event.key in ("q", "escape"):
                plt.close(fig)

        fig.canvas.mpl_connect("key_press_event", on_key)
        draw(state["i"])
        plt.tight_layout()
        plt.show()
    

def visualize_yolo_dataset(
    dataset: str | YOLODatasetManager,
    split: str = "train",
    indices: List[int] = None,
    shuffle: bool = False,
    invert_y: bool = False,
):
    """Convenience function to visualize a dataset using dataset.yaml."""
    if isinstance(dataset, str):
        mgr = YOLODatasetManager.from_dataset_yaml(dataset)
    elif isinstance(dataset, YOLODatasetManager):
        mgr = dataset
    mgr.visualize_dataset(split=split, indices=indices, shuffle=shuffle, invert_y=invert_y)
