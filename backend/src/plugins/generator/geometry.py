import numpy as np
from typing import Tuple, List, Optional
from dataclasses import replace
import copy

# Import your NEW image models
from src.models.image_models import ImageSystem, ImageNode, ImageLoad

# Import your existing symbol definitions
from src.plugins.generator.image.stanli_symbols import StanliSupport, StanliHinge, StanliLoad

# Maximum symbol extents (in mm, converted to pixels in normalization)
MAX_SUPPORT_EXTENT_MM = 25.0  
MAX_LOAD_EXTENT_MM = 15.0     
MAX_HINGE_EXTENT_MM = 8.0     
PX_PER_MM = 4.0

from typing import Tuple
from src.models.image_models import ImageSystem
from src.plugins.generator.image.stanli_symbols import StanliSupport, StanliLoad, SupportType, LoadType

class GeometryProcessor:
    @staticmethod
    def get_structure_bounds_with_symbols(structure: ImageSystem) -> Tuple[float, float, float, float]:
        if not structure or not structure.nodes:
            return (0, 0, 0, 0)

        all_bounds = []

        # 1) Nodes + supports
        for node in structure.nodes:
            st = getattr(node, "support_type", None)

            x, y = node.pixel_x, node.pixel_y
            pos = (x, y)
            rotation = float(getattr(node, "rotation", 0.0) or 0.0)

            if st != SupportType.FREIES_ENDE:
                try:
                    bbox = StanliSupport(st).get_bbox(pos, rotation)
                    if bbox is not None:
                        all_bounds.append(bbox)
                        continue
                except Exception:
                    pass

            # fallback node bbox
            pad = 5.0
            all_bounds.append((x - pad, y - pad, x + pad, y + pad))

        # 2) Loads
        for load in getattr(structure, "loads", []):
            node_id = getattr(load, "node_id", None)
            if not node_id:
                continue

            node = next((n for n in structure.nodes if n.id == node_id), None)
            if not node:
                continue

            pos = (node.pixel_x, node.pixel_y)
            #lt = coerce_load_type(getattr(load, "load_type", None))
            lt = getattr(load, "load_type", None)

            try:
                rotation = float(getattr(load, "angle_deg", 0.0) or 0.0)
                length = 50.0
                bbox = StanliLoad(lt).get_bbox(pos, rotation, length)
                if bbox is not None:
                    all_bounds.append(bbox)
            except Exception:
                # fallback around the node if load bbox fails
                x, y = pos
                pad = 10.0
                all_bounds.append((x - pad, y - pad, x + pad, y + pad))

        # combine
        min_x = min(b[0] for b in all_bounds)
        min_y = min(b[1] for b in all_bounds)
        max_x = max(b[2] for b in all_bounds)
        max_y = max(b[3] for b in all_bounds)
        return (min_x, min_y, max_x, max_y)


    @staticmethod
    def normalize_coordinates(
        structure: ImageSystem,
        target_size: Tuple[int, int],
        margin: float = 0.1,
        in_place: bool = False
    ) -> ImageSystem:
        """
        Normalize node coordinates to fit inside target_size (width, height) with margin.
        Operates on ImageSystem.
        """
        if not structure or not structure.nodes:
            return structure

        # Get actual bounds
        min_x, min_y, max_x, max_y = GeometryProcessor.get_structure_bounds_with_symbols(structure)

        width = max_x - min_x
        height = max_y - min_y

        if width == 0 or height == 0:
            if in_place: return structure
            return copy.deepcopy(structure)

        tgt_w, tgt_h = target_size
        
        margin_x = min(tgt_w * margin, tgt_w * 0.4)
        margin_y = min(tgt_h * margin, tgt_h * 0.4)

        scale_x = (tgt_w - 2 * margin_x) / width
        scale_y = (tgt_h - 2 * margin_y) / height
        scale = min(scale_x, scale_y)

        center_x = tgt_w / 2
        center_y = tgt_h / 2
        struct_cx = (min_x + max_x) / 2
        struct_cy = (min_y + max_y) / 2

        def transform(x, y):
            new_x = center_x + (x - struct_cx) * scale
            new_y = center_y + (y - struct_cy) * scale
            return new_x, new_y

        if in_place:
            for node in structure.nodes:
                nx, ny = transform(node.pixel_x, node.pixel_y)
                node.pixel_x = nx
                node.pixel_y = ny
            # Loads follow nodes, but if they have independent positions, update them too
            for load in structure.loads:
                 if not load.node_id: # Only transform loads that aren't attached to nodes
                     lx, ly = transform(load.pixel_x, load.pixel_y)
                     load.pixel_x = lx
                     load.pixel_y = ly
            return structure

        # Create new nodes
        new_nodes = []
        for n in structure.nodes:
            nx, ny = transform(n.pixel_x, n.pixel_y)
            new_nodes.append(replace(n, pixel_x=nx, pixel_y=ny))

        # Create new loads (if they store position)
        new_loads = []
        for l in structure.loads:
            # If load is attached to a node, its position is usually derived from the node at render time
            # But if we store pixel_x/y on the load for convenience, we must update it
            if hasattr(l, 'pixel_x'):
                lx, ly = transform(l.pixel_x, l.pixel_y)
                new_loads.append(replace(l, pixel_x=lx, pixel_y=ly))
            else:
                new_loads.append(l)

        # Return new structure
        return replace(structure, nodes=new_nodes, loads=new_loads)


    @staticmethod
    def apply_perspective_transform(
        structure: ImageSystem,
        strength: float,
        image_size: Tuple[int, int],
        in_place: bool = False
    ) -> ImageSystem:
        """
        Apply pseudo‑perspective squeeze to ImageSystem.
        """
        if strength <= 0 or not structure.nodes:
            return structure

        img_w, img_h = image_size
        max_factor = max(0.0, 1.0 - strength * 0.1)

        def transform(x, y):
            t = y / img_h if img_h > 0 else 0
            x_factor = 1.0 - (1.0 - max_factor) * t
            return x * x_factor, y

        if in_place:
            for node in structure.nodes:
                nx, ny = transform(node.pixel_x, node.pixel_y)
                node.pixel_x = nx
                node.pixel_y = ny
            return structure

        new_nodes = []
        for n in structure.nodes:
            nx, ny = transform(n.pixel_x, n.pixel_y)
            new_nodes.append(replace(n, pixel_x=nx, pixel_y=ny))

        return replace(structure, nodes=new_nodes)
    
    @staticmethod
    def validate_bounds(
        structure: ImageSystem,
        image_size: Tuple[int, int],
        padding: float = 10.0
    ) -> bool:
        """
        Check if all structure elements are within image bounds.
        """
        if not structure or not structure.nodes:
            return True
        
        w, h = image_size
        min_x, min_y, max_x, max_y = GeometryProcessor.get_structure_bounds_with_symbols(structure)
        
        if min_x < padding or max_x > w - padding:
            return False
        if min_y < padding or max_y > h - padding:
            return False
        
        return True
